import requests
import json
import os

N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0NTZmMmQ5My1kYWZmLTQ1NDEtOTI4ZS1iNmEwZTVjZDc0YjgiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiYWZjNDQ0NjMtNjI2NS00MTlkLTllYjEtZDU2ZGRjMDZhNmM4IiwiaWF0IjoxNzc0NjMxMjY0fQ.NlG9dHsL4G0cGAsyFj-0pSSIw44kSnigza7-ah1tFF8"
N8N_URL = "http://n8n-oftalmos.147.15.99.72.sslip.io"
WORKFLOW_ID = "fm9Ik6r9E7gWRg3E"
JSON_FILE = "/Users/daniel/N8N Oftalmos/iris_workflow_latest.json"

def add_storage_node():
    # Carregar o JSON do workflow
    with open(JSON_FILE, 'r') as f:
        workflow = json.load(f)

    # 1. Definir o novo nó
    new_node = {
        "parameters": {
            "resource": "storage",
            "operation": "upload",
            "bucketId": "chat_media",
            "fileName": "={{ $('Info').first().json.id_mensagem }}.jpg",
            "binaryPropertyName": "data"
        },
        "type": "n8n-nodes-base.supabase",
        "typeVersion": 1,
        "position": [2112, 528],
        "id": "supabase-storage-upload",
        "name": "Upload Supabase",
        "credentials": {
            "supabaseApi": {
                "id": "yFRA7QVqDaaABj8B",
                "name": "Supabase account"
            }
        }
    }

    # Adicionar o nó se não existir
    if not any(n['name'] == "Upload Supabase" for n in workflow['nodes']):
        workflow['nodes'].append(new_node)
        print("Novo nó 'Upload Supabase' adicionado.")
    else:
        print("Aviso: Nó 'Upload Supabase' já existe.")

    # 2. Atualizar conexões
    connections = workflow['connections']
    
    # Remover conexão direta Converter Imagem -> Analisar Imagem
    if "Converter Imagem" in connections:
        output_0 = connections["Converter Imagem"]["main"][0]
        connections["Converter Imagem"]["main"][0] = [c for c in output_0 if c["node"] != "Analisar Imagem"]
        
        # Adicionar conexão Converter Imagem -> Upload Supabase
        if not any(c["node"] == "Upload Supabase" for c in connections["Converter Imagem"]["main"][0]):
            connections["Converter Imagem"]["main"][0].append({"node": "Upload Supabase", "type": "main", "index": 0})
            print("Conexão 'Converter Imagem' -> 'Upload Supabase' adicionada.")

    # Adicionar conexão Upload Supabase -> Analisar Imagem
    connections["Upload Supabase"] = {
        "main": [
            [
                {"node": "Analisar Imagem", "type": "main", "index": 0}
            ]
        ]
    }
    print("Conexão 'Upload Supabase' -> 'Analisar Imagem' adicionada.")

    # Preparar payload para n8n API
    update_data = {
        "name": workflow.get("name"),
        "nodes": workflow.get("nodes"),
        "connections": workflow.get("connections"),
        "settings": {
            "executionOrder": "v1"
        }
    }

    url = f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}"
    headers = {
        "X-N8N-API-KEY": N8N_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.put(url, headers=headers, json=update_data)
    
    if response.status_code == 200:
        print("Workflow 'Agente Íris' atualizado com armazenamento de imagens!")
    else:
        print(f"Erro ao atualizar: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    add_storage_node()
