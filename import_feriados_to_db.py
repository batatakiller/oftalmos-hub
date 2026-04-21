import json
import os
from datetime import datetime
import pytz
from supabase_helper import SupabaseHelper

# Configuração de Fuso Horário
TIMEZONE = pytz.timezone("America/Maceio") # Fuso de Aracaju/SE (UTC-3)
CURRENT_YEAR = 2026
TABLE_NAME = "feriados"

# Mapeamento de meses para números
MONTHS_MAP = {
    "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4,
    "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8,
    "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
}

def migrate():
    # 1. Carregar JSON de feriados
    filename = f"feriados_aracaju_{CURRENT_YEAR}.json"
    if not os.path.exists(filename):
        print(f"❌ Erro: Arquivo {filename} não encontrado!")
        return

    with open(filename, "r", encoding="utf-8") as f:
        feriados_data = json.load(f)

    # 2. Iniciar Helper do Supabase
    try:
        db = SupabaseHelper()
    except Exception as e:
        print(str(e))
        return

    print(f"🚀 Iniciando migração de {len(feriados_data)} itens para a tabela '{TABLE_NAME}'...")

    for item in feriados_data:
        try:
            day = item["dia"]
            month_name = item["mes"]
            year = item.get("ano", CURRENT_YEAR)
            month = MONTHS_MAP.get(month_name, 1)

            # Formata apenas a DATA (YYYY-MM-DD) para coluna DATE do Postgres
            iso_date = f"{year:04d}-{month:02d}-{day:02d}"

            # Preparar dados para o Supabase (Limpo, sem descrição repetida)
            payload = {
                "data": iso_date,
                "titulo": item["nome"],
                "tipo": item["tipo"] # Agora virá: 'nacional', 'municipal', etc.
            }

            print(f"  [*] Subindo: {item['nome']} ({iso_date}) como {item['tipo']}")
            db.upsert(TABLE_NAME, payload)

        except Exception as e:
            print(f"  [X] Erro ao processar item {item}: {e}")

    print("\n✅ Migração para nova tabela concluída com sucesso!")

if __name__ == "__main__":
    migrate()
