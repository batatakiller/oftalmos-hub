import json
import os
from supabase_helper import SupabaseHelper

# Configurações do Novo Formato
NEW_TABLE = "feriados"
OLD_TABLE = "calendario_atendimento"
JSON_FILE = "feriados_aracaju_2026.json"

def perform_sanitization():
    print("🧹 Iniciando processo de sanitização e migração...")
    
    # 1. Iniciar Helper do Supabase
    try:
        db = SupabaseHelper()
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return

    # 2. LIMPEZA: Remover feriados da tabela antiga (onde tipo era 'feriado')
    print(f"  [-] Removendo logs antigos de '{OLD_TABLE}'...")
    try:
        # A biblioteca postgrest permite deleção baseada em filtros
        db.client.table(OLD_TABLE).delete().eq("tipo", "feriado").execute()
        print("  ✅ Tabela antiga limpa!")
    except Exception as e:
        print(f"  [!] Erro ao limpar tabela antiga (talvez já esteja vazia): {e}")

    # 3. MIGRACAO: Carregar os dados novos estruturados
    if not os.path.exists(JSON_FILE):
        print(f"❌ Erro: Arquivo {JSON_FILE} não encontrado!")
        return

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        feriados_data = json.load(f)

    print(f"🚀 Subindo {len(feriados_data)} itens para o NOVO FORMATO na tabela '{NEW_TABLE}'...")

    for item in feriados_data:
        try:
            # Formato esperado pela nova tabela: data, titulo, tipo
            # Mapa de meses (seguro para o script de migração direta)
            MONTHS_MAP = {
                "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4,
                "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8,
                "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
            }
            
            m_num = MONTHS_MAP.get(item['mes'], 1)
            final_iso_date = f"{int(item['ano']):04d}-{int(m_num):02d}-{int(item['dia']):02d}"

            payload = {
                "data": final_iso_date,
                "titulo": item["nome"],
                "tipo": item["tipo"].lower() # 'nacional', 'municipal', etc.
            }

            print(f"  [*] Inserindo: {item['nome']} ({final_iso_date}) como {item['tipo']}")
            # Usando upsert para garantir idempotecia
            db.upsert(NEW_TABLE, payload)

        except Exception as e:
            print(f"  [X] Erro ao processar item {item}: {e}")

    print("\n✅ TUDO PRONTO! Tabela antiga sanitizada e novos feriados migrados.")

if __name__ == "__main__":
    perform_sanitization()
