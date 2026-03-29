from supabase_helper import SupabaseHelper
import json

def add_demo_card():
    # 1. Iniciar o Helper
    db = SupabaseHelper()
    
    # 2. Definir os dados do Cartão Kanban
    # Imagine que este card foi gerado a partir de um atendimento no n8n
    card_data = {
        "titulo": "Primeiro Atendimento: Daniel (Oftalmos)",
        "descricao": "Paciente solicita agendamento urgente para exame de catarata. Canal: WhatsApp.",
        "coluna": "triagem",          # Status inicial do kanban
        "prioridade": "alta",        # baixa, media, alta
        "posicao": 1,                # Ordem dentro da coluna
        "whatsapp_cliente": "557999887766" # Número para follow-up futuro
    }
    
    print(f"🚀 Enviando card '{card_data['titulo']}' para o Kanban do Supabase...")
    
    # 3. Inserir na tabela kanban_cards
    # (Lembre-se de ter executado o SQL de criação da tabela no Dashboard antes de rodar este script)
    response = db.insert("kanban_cards", card_data)
    
    if response:
        print("\n✅ CARTÃO CRIADO COM SUCESSO! No Dashboard você verá:")
        print(f"   ID: {response.data[0]['id']}")
        print(f"   Coluna: {response.data[0]['coluna']}")
        print(f"   Criado em: {response.data[0]['criado_em']}")
    else:
        print("\n❌ FALHA ao criar cartão. Verifique se o SQL da tabela foi executado.")

if __name__ == "__main__":
    add_demo_card()
