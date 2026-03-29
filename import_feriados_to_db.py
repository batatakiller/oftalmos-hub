import json
import os
from datetime import datetime
import pytz
from supabase_helper import SupabaseHelper

# Configuração de Fuso Horário
TIMEZONE = pytz.timezone("America/Maceio") # Fuso de Aracaju/SE (UTC-3)
CURRENT_YEAR = 2026
TABLE_NAME = "calendario_atendimento"

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

    print(f"🚀 Iniciando migração de {len(feriados_data)} itens para o Supabase...")

    for item in feriados_data:
        try:
            # Converter "17 Março" para objeto Datetime
            parts = item["data"].split(" ")
            day = int(parts[0])
            month_name = parts[1]
            month = MONTHS_MAP.get(month_name, 1)

            # Criar datetime com fuso horário correto (meia-noite do feriado)
            dt = datetime(CURRENT_YEAR, month, day, 0, 0, 0)
            localized_dt = TIMEZONE.localize(dt)

            # Preparar dados para o Supabase
            payload = {
                "start_time": localized_dt.isoformat(),
                "titulo": item["nome"],
                "tipo": "feriado",
                "descricao": f"Feriado Extraído: {item['tipo']}",
                "status": "bloqueado"
            }

            # Usar UPSERT para evitar duplicatas baseadas no start_time
            # (Assumindo que você criou a CONSTRAINT no SQL conforme instruído)
            print(f"  [*] Subindo: {item['nome']} ({day}/{month})")
            db.upsert(TABLE_NAME, payload)

        except Exception as e:
            print(f"  [X] Erro ao processar item {item}: {e}")

    print("\n✅ Migração concluída com sucesso! Verifique seu dashboard do Supabase.")

if __name__ == "__main__":
    migrate()
