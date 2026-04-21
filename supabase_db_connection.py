import os
from supabase import create_client, Client
from dotenv import load_dotenv

def get_supabase_client() -> Client:
    """Carrega credenciais e retorna um cliente Supabase configurado."""
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        raise ValueError("❌ Erro: Credenciais do Supabase não encontradas no .env")
        
    return create_client(url, key)

def test_connection():
    """Verifica se a conexão com o Supabase está ativa e funcional."""
    try:
        supabase = get_supabase_client()
        # Uma consulta simples para validar a conexão
        res = supabase.table('medicos').select('count', count='exact').limit(1).execute()
        
        print("✅ Conexão com Supabase estabelecida com sucesso!")
        print(f"📡 Estado: Online")
        
        # Opcional: mostrar quantos médicos estão cadastrados
        if hasattr(res, 'count'):
             print(f"📊 Registros encontrados na tabela 'medicos': {res.count}")
             
    except Exception as e:
        print(f"❌ Erro ao conectar ao Supabase: {e}")

if __name__ == "__main__":
    test_connection()
