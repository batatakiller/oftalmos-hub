import requests
import json
import uuid

N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0NTZmMmQ5My1kYWZmLTQ1NDEtOTI4ZS1iNmEwZTVjZDc0YjgiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiYWZjNDQ0NjMtNjI2NS00MTlkLTllYjEtZDU2ZGRjMDZhNmM4IiwiaWF0IjoxNzc0NjMxMjY0fQ.NlG9dHsL4G0cGAsyFj-0pSSIw44kSnigza7-ah1tFF8"
N8N_URL = "http://n8n-oftalmos.147.15.99.72.sslip.io"
WORKFLOW_ID = "xI8obEj1Cmwp9yr7"

def gen_id(): return str(uuid.uuid4())

def build_workflow():
    nodes = []
    
    # 1. Schedule Trigger (Cron a cada 15 min)
    nodes.append({
        "parameters": {
            "rule": {
                "interval": [ { "field": "minutes", "minutesInterval": 15 } ]
            }
        },
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.2,
        "position": [0, 0],
        "id": gen_id(),
        "name": "A Cada 15 Minutos"
    })

    # 2. Supabase - Puxar Consultas (status = 'confirmada')
    nodes.append({
        "parameters": {
            "operation": "getAll",
            "tableId": "consultas",
            "limit": 50,
            "filters": {
                "conditions": [
                    {
                        "keyName": "status",
                        "condition": "eq",
                        "keyValue": "confirmada"
                    }
                ]
            }
        },
        "type": "n8n-nodes-base.supabase",
        "typeVersion": 1,
        "position": [200, 0],
        "id": gen_id(),
        "name": "Puxar Consultas Ativas",
        "credentials": { "supabaseApi": { "id": "yFRA7QVqDaaABj8B", "name": "Supabase account" } }
    })

    # 3. Filtro Lógico de Tempo (Code Node)
    js_code = """const now = new Date();
const results = [];
for (const item of $input.all()) {
    const consulta = item.json;
    if (!consulta.data_hora) continue;
    
    const dataConsulta = new Date(consulta.data_hora);
    const diffMs = dataConsulta - now;
    const diffHours = diffMs / (1000 * 60 * 60);
    const obs = consulta.observacoes || "";
    
    let lembrete_tipo = null;
    
    // Entre 23.5h e 24.5h e sem a tag [L1D] (Lembrete 1 Dia)
    if (diffHours >= 23.5 && diffHours <= 24.5 && !obs.includes("[L1D]")) {
        lembrete_tipo = "1_DIA";
    }
    // Entre 2.5h e 3.5h e sem a tag [L3H] (Lembrete 3 Horas)
    else if (diffHours >= 2.5 && diffHours <= 3.5 && !obs.includes("[L3H]")) {
        lembrete_tipo = "3_HORAS";
    }
    
    if (lembrete_tipo) {
        consulta.lembrete_tipo = lembrete_tipo;
        results.push({ json: consulta });
    }
}
return results;"""

    nodes.append({
        "parameters": {
            "jsCode": js_code
        },
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [400, 0],
        "id": gen_id(),
        "name": "Filtrar Consultas da Janela"
    })

    # 4. Split In Batches (Processar uma por uma)
    nodes.append({
        "parameters": {
            "batchSize": 1,
            "options": {}
        },
        "type": "n8n-nodes-base.splitInBatches",
        "typeVersion": 3,
        "position": [600, 0],
        "id": gen_id(),
        "name": "Loop por Consulta"
    })

    # 5. Supabase - Puxar Paciente
    nodes.append({
        "parameters": {
            "operation": "get",
            "tableId": "pacientes",
            "matchType": "anyId",
            "matchValue": "={{ $json.paciente_id }}"
        },
        "type": "n8n-nodes-base.supabase",
        "typeVersion": 1,
        "position": [850, 0],
        "id": gen_id(),
        "name": "Puxar Telefone Paciente",
        "credentials": { "supabaseApi": { "id": "yFRA7QVqDaaABj8B", "name": "Supabase account" } }
    })

    # 6. Set Mensagem
    js_msg = """let msg = "";
const consulta = $('Loop por Consulta').item.json;
const paciente = $json;
const data = new Date(consulta.data_hora);
const horaFomatada = data.getHours().toString().padStart(2, '0') + ':' + data.getMinutes().toString().padStart(2, '0');

if (consulta.lembrete_tipo === "1_DIA") {
    msg = `Olá ${paciente.nome || ''}, tudo bem? Passando para lembrar da sua consulta oftalmológica amanhã às ${horaFomatada}. Nos vemos em breve!`;
} else if (consulta.lembrete_tipo === "3_HORAS") {
    msg = `Olá ${paciente.nome || ''}! Lembrete rápido: sua consulta oftalmológica é hoje às ${horaFomatada}! A Clínica Oftalmos aguarda por você.`;
}

return msg;"""

    nodes.append({
        "parameters": {
            "assignments": {
                "assignments": [
                    {
                        "id": gen_id()[:8],
                        "name": "mensagem_texto",
                        "value": f"={{{{ {js_msg} }}}}",
                        "type": "string"
                    }
                ]
            },
            "options": {}
        },
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [1050, 0],
        "id": gen_id(),
        "name": "Gerar Texto do Lembrete"
    })

    # 7. Evolution API Enviar
    nodes.append({
        "parameters": {
            "resource": "messages-api",
            "instanceName": "Oftalmos",
            "remoteJid": "={{ $json.telefone }}",
            "messageText": "={{ $json.mensagem_texto }}",
            "options_message": {}
        },
        "type": "n8n-nodes-evolution-api.evolutionApi",
        "typeVersion": 1,
        "position": [1250, 0],
        "id": gen_id(),
        "name": "Disparar WhatsApp",
        "credentials": { "evolutionApi": { "id": "GTNdup0sU4cqj3oR", "name": "Evolution account" } }
    })

    # 8. Supabase - Atualizar Observações
    tag_logic = "={{ ($('Loop por Consulta').item.json.observacoes || '') + ' [' + ($('Loop por Consulta').item.json.lembrete_tipo === '1_DIA' ? 'L1D' : 'L3H') + ']' }}"
    nodes.append({
        "parameters": {
            "operation": "update",
            "tableId": "consultas",
            "filters": {
                "conditions": [
                    {
                        "keyName": "id",
                        "condition": "eq",
                        "keyValue": "={{ $('Loop por Consulta').item.json.id }}"
                    }
                ]
            },
            "fieldsUi": {
                "fieldValues": [
                    {
                        "fieldId": "observacoes",
                        "fieldValue": tag_logic
                    }
                ]
            }
        },
        "type": "n8n-nodes-base.supabase",
        "typeVersion": 1,
        "position": [1450, 0],
        "id": gen_id(),
        "name": "Marcar Lembrete como Enviado na Consulta",
        "credentials": { "supabaseApi": { "id": "yFRA7QVqDaaABj8B", "name": "Supabase account" } }
    })

    # Conexões
    connections = {
        "A Cada 15 Minutos": { "main": [[{"node": "Puxar Consultas Ativas", "type": "main", "index": 0}]] },
        "Puxar Consultas Ativas": { "main": [[{"node": "Filtrar Consultas da Janela", "type": "main", "index": 0}]] },
        "Filtrar Consultas da Janela": { "main": [[{"node": "Loop por Consulta", "type": "main", "index": 0}]] },
        "Loop por Consulta": { "main": [
            [{"node": "Puxar Telefone Paciente", "type": "main", "index": 0}], # Loop (executa)
            [] # Fim do Loop
        ]},
        "Puxar Telefone Paciente": { "main": [[{"node": "Gerar Texto do Lembrete", "type": "main", "index": 0}]] },
        "Gerar Texto do Lembrete": { "main": [[{"node": "Disparar WhatsApp", "type": "main", "index": 0}]] },
        "Disparar WhatsApp": { "main": [[{"node": "Marcar Lembrete como Enviado na Consulta", "type": "main", "index": 0}]] },
        "Marcar Lembrete como Enviado na Consulta": { "main": [[{"node": "Loop por Consulta", "type": "main", "index": 0}]] } # Retorna ao Loop
    }

    update_data = {
        "name": "Automação de Lembretes - Cron", # Rename workflow slightly
        "nodes": nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1"}
    }

    put_resp = requests.put(
        f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
        headers={"X-N8N-API-KEY": N8N_API_KEY, "Content-Type": "application/json"},
        json=update_data
    )
    
    if put_resp.status_code == 200:
        print("Workflow de Follow-up (Cron) criado com sucesso!")
    else:
        print("Erro ao atualizar o workflow:")
        print(put_resp.text)

if __name__ == "__main__":
    build_workflow()
