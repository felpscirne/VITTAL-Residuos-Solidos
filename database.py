from sqlalchemy import create_engine
import pandas as pd

DATABASE_URI = "postgresql://postgres:postgres@localhost:5432/projeto"
engine = create_engine(DATABASE_URI)

def get_anos_options():
    try:
        anos_df = pd.read_sql("SELECT DISTINCT EXTRACT(YEAR FROM data_hora) AS ano FROM registro ORDER BY ano DESC", engine)
        options = [{'label': str(int(ano)), 'value': int(ano)} for ano in anos_df['ano']]
        valor_inicial = options[0]['value'] if options else None
        return options, valor_inicial
    except Exception as e:
        print(f"Erro ao buscar anos: {e}")
        return [{'label': '2024', 'value': 2024}], 2024 