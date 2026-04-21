import requests
import json
import os

from dotenv import load_dotenv
load_dotenv()

N8N_API_KEY = os.getenv("N8N_API_KEY")
N8N_URL = os.getenv("N8N_URL", "http://n8n-oftalmos.147.15.99.72.sslip.io")
WORKFLOW_ID = "FaClhUaGLTNxb0oN"

def update_workflow():
    # 1. Carregar o workflow base do arquivo JSON
    with open('mcp_workflow_formatted.json', 'r') as f:
        workflow = json.load(f)

    # 2. Definir o novo nó de validação de CPF
    cpf_validation_node = {
        "parameters": {
            "name": "validar_cpf",
            "description": "Valida matematicamente um CPF brasileiro (checksum). Aceita números puros ou formatados (000.000.000-00). Retorna se é válido, o CPF formatado e o motivo do erro se houver.",
            "jsCode": """function validateCPF(cpf) {
  if (!cpf) return { isValid: false, reason: "CPF não informado" };
  cpf = cpf.replace(/[^\\d]/g, '');
  if (cpf.length !== 11 || /^(\\d)\\1+$/.test(cpf)) return { isValid: false, reason: "Formato inválido ou números repetidos" };
  
  let sum = 0, rest;
  for (let i = 1; i <= 9; i++) sum += parseInt(cpf.substring(i-1, i)) * (11 - i);
  rest = (sum * 10) % 11;
  if ((rest === 10) || (rest === 11)) rest = 0;
  if (rest !== parseInt(cpf.substring(9, 10))) return { isValid: false, reason: "Primeiro dígito verificador inválido" };
  
  sum = 0;
  for (let i = 1; i <= 10; i++) sum += parseInt(cpf.substring(i-1, i)) * (12 - i);
  rest = (sum * 10) % 11;
  if ((rest === 10) || (rest === 11)) rest = 0;
  if (rest !== parseInt(cpf.substring(10, 11))) return { isValid: false, reason: "Segundo dígito verificador inválido" };
  
  return { 
    isValid: true, 
    formatted: cpf.replace(/(\\d{3})(\\d{3})(\\d{3})(\\d{2})/, "$1.$2.$3-$4"),
    cpf: cpf
  };
}

const inputCpf = $fromAI("cpf", "O CPF do paciente (pode ser apenas números ou formatado com pontos e traço)");
return validateCPF(inputCpf);"""
        },
        "type": "@n8n/n8n-nodes-langchain.toolCode",
        "typeVersion": 1,
        "position": [320, -192],
        "id": "validar-cpf-tool-id",
        "name": "Validar CPF"
    }

    # Novo SQL para Verificar Disponibilidade
    new_availability_sql = """SELECT 
    p.data_v as data,
    slots.horario::time as horario_disponivel,
    m.nome as nome_medico
FROM (
    SELECT generate_series(CURRENT_DATE, CURRENT_DATE + 90, '1 day'::interval)::date AS data_v
) p
JOIN horarios_disponiveis h ON h.medico_id = COALESCE(
    (SELECT id FROM medicos WHERE id::text = NULLIF(TRIM('{{ $fromAI("medico_id") }}'), '') AND ativo = true LIMIT 1),
    (SELECT id FROM medicos WHERE nome ILIKE '%' || NULLIF(TRIM('{{ $fromAI("nome_medico") }}'), '') || '%' AND ativo = true ORDER BY (nome = TRIM('{{ $fromAI("nome_medico") }}')) DESC LIMIT 1)
)
     AND h.dia_semana = EXTRACT(DOW FROM p.data_v)
JOIN medicos m ON m.id = h.medico_id
JOIN especialidades e ON e.id = m.especialidade_id
CROSS JOIN LATERAL generate_series(
    (p.data_v + h.hora_inicio)::timestamp,
    (p.data_v + h.hora_fim - (COALESCE(e.duracao_padrao_min, 30) * interval '1 minute'))::timestamp,
    (COALESCE(e.duracao_padrao_min, 30) * interval '1 minute')
) AS slots(horario)
WHERE (NULLIF(TRIM('{{ $fromAI("data") }}'), '') IS NULL OR p.data_v = NULLIF(TRIM('{{ $fromAI("data") }}'), '')::date)
  AND h.ativo = true
  AND m.ativo = true
  AND slots.horario > (CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo' - interval '1 minute')
  AND NOT EXISTS (SELECT 1 FROM feriados f WHERE f.data = p.data_v)
  AND NOT EXISTS (
      SELECT 1 FROM consultas c 
      WHERE c.medico_id = h.medico_id 
        AND c.data_hora::date = p.data_v
        AND (c.data_hora::time, c.data_hora::time + (COALESCE(c.duracao_min, e.duracao_padrao_min, 30) * interval '1 minute')) 
            OVERLAPS 
            (slots.horario::time, slots.horario::time + (COALESCE(e.duracao_padrao_min, 30) * interval '1 minute'))
        AND c.status != 'cancelada'
  )
ORDER BY p.data_v, slots.horario
LIMIT 50;"""

    # 3. Adicionar/Atualizar nós
    cpf_exists = False
    for node in workflow['nodes']:
        if node['name'] == "Validar CPF":
            node['parameters'] = cpf_validation_node['parameters']
            cpf_exists = True
        if node['name'] == "Verificar Disponibilidade":
            node['parameters']['query'] = new_availability_sql
    
    if not cpf_exists:
        workflow['nodes'].append(cpf_validation_node)

    # 4. Configurar a conexão com o MCP Server Trigger (ai_tool)
    if "Validar CPF" not in workflow['connections']:
        workflow['connections']["Validar CPF"] = {
            "ai_tool": [
                [
                    {
                        "node": "MCP Server Trigger",
                        "type": "ai_tool",
                        "index": 0
                    }
                ]
            ]
        }

    # 5. Sincronizar activeVersion se existir (para manter o arquivo JSON consistente)
    if "activeVersion" in workflow:
        workflow["activeVersion"]["nodes"] = workflow["nodes"]
        workflow["connections"] = workflow["connections"]

    # 6. Preparar o corpo da requisição para a API
    payload = {
        "name": workflow.get("name", "MCP Server Workflow"),
        "nodes": workflow["nodes"],
        "connections": workflow["connections"],
        "settings": {
            "executionOrder": "v1"
        }
    }

    # 7. Enviar a atualização
    url = f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}"
    headers = {
        "X-N8N-API-KEY": N8N_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.put(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        print("Workflow atualizado com sucesso no n8n com a ferramenta de CPF!")
        # Salvar o JSON atualizado localmente também
        with open('mcp_workflow_formatted.json', 'w') as f:
            json.dump(workflow, f, indent=2)
    else:
        print(f"Erro ao atualizar: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    update_workflow()
