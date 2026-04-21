import requests
import json

N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0NTZmMmQ5My1kYWZmLTQ1NDEtOTI4ZS1iNmEwZTVjZDc0YjgiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiYWZjNDQ0NjMtNjI2NS00MTlkLTllYjEtZDU2ZGRjMDZhNmM4IiwiaWF0IjoxNzc0NjMxMjY0fQ.NlG9dHsL4G0cGAsyFj-0pSSIw44kSnigza7-ah1tFF8"
N8N_URL = "http://n8n-oftalmos.147.15.99.72.sslip.io"
WORKFLOW_ID = "fm9Ik6r9E7gWRg3E"
SUPABASE_URL = "http://supabasekong-oftalmos.147.15.99.72.sslip.io"

def enable_folders():
    response = requests.get(
        f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
        headers={"X-N8N-API-KEY": N8N_API_KEY}
    )
    workflow = response.json()
    nodes = workflow.get("nodes", [])

    for node in nodes:
        # Patch das URLs de Upload físico
        if node["name"] == "Upload para Supabase Storage":
            node["parameters"]["url"] = f"={SUPABASE_URL}/storage/v1/object/chat_media/{{{{ $(\"Info\").first().json.telefone }}}}/{{{{ $(\"Info\").first().json.id_mensagem }}}}.{{{{ $binary.data.mimeType.includes('video') ? 'mp4' : 'jpg' }}}}"
        elif node["name"] == "Upload para Supabase Storage1":
            node["parameters"]["url"] = f"={SUPABASE_URL}/storage/v1/object/chat_media/{{{{ $(\"Info\").first().json.telefone }}}}/{{{{ $(\"Info\").first().json.id_mensagem }}}}.pdf"

        # Patch das atualizações nas tabelas SQL
        elif node["name"] == "Update a row":
            js_code = """={{ (function() { 
    const telefone = $("Info").first().json.telefone;
    const id = $("Info").first().json.id_mensagem; 
    
    // Pega o binário do nó anterior (Converter Imagem)
    const binaryData = $("Converter Imagem").first().binary.data;
    const isVideo = (binaryData.mimeType || '').includes('video'); 
    const ext = isVideo ? 'mp4' : 'jpg';
    
    // URL Pública com o numero de telefone compondo uma pasta
    const url = `http://supabasekong-oftalmos.147.15.99.72.sslip.io/storage/v1/object/public/chat_media/${telefone}/${id}.${ext}`; 
    
    if (isVideo) { 
        return `<video src="${url}" controls style="border-radius:8px; max-width:100%;"></video>`; 
    } else { 
        return `<img src="${url}" style="border-radius:8px; max-width:100%;">`; 
    } 
})() }}"""
            for field in node["parameters"]["fieldsUi"]["fieldValues"]:
                if field["fieldId"] == "message":
                    field["fieldValue"] = js_code
                    
        elif node["name"] == "Update a row Documento":
            js_code = """={{ `<a href="http://supabasekong-oftalmos.147.15.99.72.sslip.io/storage/v1/object/public/chat_media/${$('Info').first().json.telefone}/${$('Info').first().json.id_mensagem}.pdf" target="_blank">📄 Ver Arquivo PDF</a>` }}"""
            for field in node["parameters"]["fieldsUi"]["fieldValues"]:
                if field["fieldId"] == "message":
                    field["fieldValue"] = js_code

    update_data = {
        "name": workflow.get("name"),
        "nodes": nodes,
        "connections": workflow.get("connections"),
        "settings": {"executionOrder": "v1"}
    }

    resp = requests.put(
        f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
        headers={"X-N8N-API-KEY": N8N_API_KEY, "Content-Type": "application/json"},
        json=update_data
    )
    
    if resp.status_code == 200:
        print("Organização por pastas por paciente implementada!")
    else:
        print(f"Erro ao atualizar: {resp.status_code}")

if __name__ == "__main__":
    enable_folders()
