from sqlalchemy import create_engine
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")
ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": int(os.getenv("DB_POOL_RECYCLE_SECONDS", 1800)),
    "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT_SECONDS", 30)),
    "connect_args": {
        "options": f"-c timezone={APP_TIMEZONE}",
    },
}

engine = create_engine(DATABASE_URL, **ENGINE_OPTIONS)


# Função para obter opções de anos
def get_anos_options():
    try:
        anos_df = pd.read_sql("SELECT DISTINCT EXTRACT(YEAR FROM data_hora) AS ano FROM registro ORDER BY ano DESC", engine)
        options = [{'label': str(int(ano)), 'value': int(ano)} for ano in anos_df['ano']]
        valor_inicial = options[0]['value'] if options else None
        return options, valor_inicial
    except Exception as e:
        print(f"Erro ao buscar anos: {e}")
        return [{'label': '2024', 'value': 2024}], 2024 
