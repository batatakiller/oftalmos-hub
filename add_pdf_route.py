import requests
import json
import uuid

N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0NTZmMmQ5My1kYWZmLTQ1NDEtOTI4ZS1iNmEwZTVjZDc0YjgiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiYWZjNDQ0NjMtNjI2NS00MTlkLTllYjEtZDU2ZGRjMDZhNmM4IiwiaWF0IjoxNzc0NjMxMjY0fQ.NlG9dHsL4G0cGAsyFj-0pSSIw44kSnigza7-ah1tFF8"
N8N_URL = "http://n8n-oftalmos.147.15.99.72.sslip.io"
WORKFLOW_ID = "fm9Ik6r9E7gWRg3E"

def uuid_gen(): return str(uuid.uuid4())

def add_pdf_route():
    resp = requests.get(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}", headers={"X-N8N-API-KEY": N8N_API_KEY})
    workflow = resp.json()
    nodes = workflow.get("nodes", [])
    connections = workflow.get("connections", {})

    # 1. Update Info Node
    info_node = next(n for n in nodes if n["name"] == "Info")
    assignments = info_node["parameters"]["assignments"]["assignments"]
    if not any(a["name"] == "eh_documento" for a in assignments):
        assignments.append({
            "id": uuid_gen()[:8],
            "name": "eh_documento",
            "value": "={{ ($json.body.data?.messageType || $json.body.message?.messageType || '').toLowerCase().includes('document') }}",
            "type": "boolean"
        })

    # 2. Update 'Tipo de mensagem' switch
    switch_node = next(n for n in nodes if n["name"] == "Tipo de mensagem")
    rules = switch_node["parameters"]["rules"]["values"]
    if not any(r.get("outputKey") == "Documento" for r in rules):
        rules.append({
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                "conditions": [
                    {
                        "id": uuid_gen()[:8],
                        "leftValue": "={{ $('Info').first().json.eh_documento }}",
                        "rightValue": "",
                        "operator": { "type": "boolean", "operation": "true", "singleValue": True }
                    }
                ],
                "combinator": "and"
            },
            "renameOutput": True,
            "outputKey": "Documento"
        })

    # 3. Create PDF branch nodes
    new_nodes = []
    
    # Obter Documento Base64
    new_nodes.append({
        "parameters": {
            "resource": "chat-api",
            "operation": "get-media-base64",
            "instanceName": "={{ $('Info').first().json.instancia }}",
            "messageId": "={{ $('Info').first().json.id_mensagem }}"
        },
        "type": "n8n-nodes-evolution-api.evolutionApi",
        "typeVersion": 1,
        "position": [1776, 1200],
        "id": uuid_gen(),
        "name": "Obter Documento Base64",
        "credentials": { "evolutionApi": { "id": "GTNdup0sU4cqj3oR", "name": "Evolution account" } }
    })

    # Converter Documento
    new_nodes.append({
        "parameters": {
            "operation": "toBinary",
            "sourceProperty": "data.base64",
            "options": {}
        },
        "type": "n8n-nodes-base.convertToFile",
        "typeVersion": 1.1,
        "position": [1984, 1200],
        "id": uuid_gen(),
        "name": "Converter Documento"
    })

    # Upload Documento
    new_nodes.append({
        "parameters": {
            "resource": "storage",
            "operation": "upload",
            "bucketId": "chat_media",
            "fileName": "={{ $('Info').first().json.id_mensagem }}.pdf",
            "binaryPropertyName": "data"
        },
        "type": "n8n-nodes-base.supabase",
        "typeVersion": 1,
        "position": [2320, 1200],
        "id": uuid_gen(),
        "name": "Upload Documento",
        "credentials": { "supabaseApi": { "id": "yFRA7QVqDaaABj8B", "name": "Supabase account" } }
    })

    # Update a row Documento
    new_nodes.append({
        "parameters": {
            "operation": "update",
            "tableId": "whatsapp_mensagens",
            "filters": {
                "conditions": [
                    {
                        "keyName": "message_id",
                        "condition": "eq",
                        "keyValue": "={{ $(\"Info\").first().json.id_mensagem }}"
                    }
                ]
            },
            "fieldsUi": {
                "fieldValues": [
                    {
                        "fieldId": "message",
                        "fieldValue": "={{ `<a href=\"http://supabasekong-oftalmos.147.15.99.72.sslip.io/storage/v1/object/public/chat_media/${$('Info').first().json.id_mensagem}.pdf\" target=\"_blank\">📄 Ver Arquivo PDF</a>` }}"
                    }
                ]
            }
        },
        "type": "n8n-nodes-base.supabase",
        "typeVersion": 1,
        "position": [2576, 1200],
        "id": uuid_gen(),
        "name": "Update a row Documento",
        "credentials": { "supabaseApi": { "id": "yFRA7QVqDaaABj8B", "name": "Supabase account" } }
    })

    # Filter out any exact duplicate named nodes before appending
    existing_node_names = set(n["name"] for n in nodes)
    for new_n in new_nodes:
        if new_n["name"] not in existing_node_names:
            nodes.append(new_n)

    # 4. Update Preparar Input IA JS Code
    prep_ia_node = next(n for n in nodes if n["name"] == "Preparar Input IA")
    js_code = """let textoFinal = '';

// Check current input item first
if ($json.mensagem) {
    textoFinal = $json.mensagem;
} 
// Fallback to node-specific checks
else if ($('Concatenar mensagens').isExecuted) {
    textoFinal = $('Concatenar mensagens').first().json.mensagem;
} else if ($('Set mensagem áudio').isExecuted) {
    textoFinal = $('Set mensagem áudio').first().json.mensagem;
} else if ($('Update a row Documento').isExecuted) {
    const info = $('Info').first().json;
    const caption = info.mensagem || '';
    textoFinal = (caption ? `[Mensagem]: ${caption}\\n` : '') + '[Sistema]: O paciente anexou um documento PDF.';
} else if ($('Set mensagem imagem').isExecuted || $('Update a row').isExecuted) {
    const info = $('Info').first().json;
    const caption = info.mensagem || '';
    let description = '';
    if ($('Set mensagem imagem').isExecuted) {
        description = $('Set mensagem imagem').first().json.mensagem || '';
    }
    textoFinal = `[Mensagem]: ${caption}\\n[Contexto Imagem]: ${description}`;
}

if (!textoFinal || textoFinal.trim() === '') {
    textoFinal = 'Mensagem vazia ou anexo sem legenda.';
}

return [{ json: { input: textoFinal } }];"""
    prep_ia_node["parameters"]["jsCode"] = js_code

    # 5. Connect the nodes
    if "Tipo de mensagem" not in connections:
         connections["Tipo de mensagem"] = {"main": [[] for _ in range(4)]} # At least 4 outputs now
    
    # Ensure Documento is correctly placed in outputs (it's the 4th rule, index 3 because index 0 is Texto, 1 is Áudio, 2 is Imagem, 3 is Documento)
    # Wait, the node has dynamically generated outputs depending on rules length.
    # In n8n, switch nodes outputs match the array of rules.
    # index 3 will be the Documento route.
    while len(connections["Tipo de mensagem"]["main"]) < 4:
        connections["Tipo de mensagem"]["main"].append([])
    
    # Document route -> Obter Documento Base64
    if not any(conn["node"] == "Obter Documento Base64" for conn in connections["Tipo de mensagem"]["main"][3]):
        connections["Tipo de mensagem"]["main"][3].append({"node": "Obter Documento Base64", "type": "main", "index": 0})
    
    connections["Obter Documento Base64"] = {"main": [[{"node": "Converter Documento", "type": "main", "index": 0}]]}
    connections["Converter Documento"] = {"main": [[{"node": "Upload Documento", "type": "main", "index": 0}]]}
    connections["Upload Documento"] = {"main": [[{"node": "Update a row Documento", "type": "main", "index": 0}]]}
    
    # Update a row Documento -> Preparar Input IA
    connections["Update a row Documento"] = {"main": [[{"node": "Preparar Input IA", "type": "main", "index": 0}]]}

    update_data = {
        "name": workflow.get("name"),
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
        print("Nova rota para Documentos (PDF) implementada com sucesso!")
    else:
        print("Erro ao subir a rota:")
        print(put_resp.text)

if __name__ == "__main__":
    add_pdf_route()
