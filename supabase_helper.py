import os
from supabase import create_client, Client
from dotenv import load_dotenv

class SupabaseHelper:
    def __init__(self):
        # Carregar variáveis do .env
        load_dotenv()
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not url or not key:
            raise ValueError("❌ Erro: Credenciais do Supabase não encontradas no .env")
            
        self.client: Client = create_client(url, key)

    def insert(self, table: str, data: dict):
        """Insere dados em uma tabela."""
        try:
            return self.client.table(table).insert(data).execute()
        except Exception as e:
            print(f"❌ Erro ao inserir: {e}")
            return None

    def query(self, table: str, filters: dict = None):
        """Busca dados em uma tabela com filtros opcionais."""
        try:
            query = self.client.table(table).select("*")
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            return query.execute()
        except Exception as e:
            print(f"❌ Erro ao buscar: {e}")
            return None

    def update(self, table: str, filters: dict, data: dict):
        """Atualiza dados baseados em filtros."""
        try:
            query = self.client.table(table).update(data)
            for key, value in filters.items():
                query = query.eq(key, value)
            return query.execute()
        except Exception as e:
            print(f"❌ Erro ao atualizar: {e}")
            return None

    def upsert(self, table: str, data: dict):
        """Insere ou atualiza se já existir (baseado na PK)."""
        try:
            return self.client.table(table).upsert(data).execute()
        except Exception as e:
            print(f"❌ Erro no upsert: {e}")
            return None
