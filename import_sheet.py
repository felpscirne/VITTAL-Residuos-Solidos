import pandas as pd
import os
from sqlalchemy import create_engine
import re


DATABASE_URI = "postgresql://postgres:postgres@localhost:5432/projeto" 
PASTA_PLANILHAS = "sheets"
NOME_TABELA_REGISTRO = "registro" 


COLUMNS_NAMES = [
    "ticket", "placa", "data_hora", "produto", "transportadora", "fornecedor_cliente",
    "peso_entrada", "peso_saida", "peso_liquido", "peso_embalagem_liquido", 
    "peso_embalagem_liquido_corrigido", "peso_nota_fiscal", "placa_veiculo",
    "diferenca_peso", "diferenca_peso_porcentagem", "nro_nota_fiscal", "setor", 
    "destino_procedencia"
]

def carregar_planilhas_em_dataframe(pasta):
    
    lista_de_dataframes = []
    
    
    arquivos = [f for f in os.listdir(pasta) if f.endswith('.ods') and not f.startswith('~')]
    print(f"Encontrados {len(arquivos)} arquivos na pasta '{pasta}':")

    for arquivo in arquivos:
        caminho_completo = os.path.join(pasta, arquivo)
        try:
            df = pd.read_excel(caminho_completo, engine='odf', skiprows=2)
            
            
            if df.shape[1] >= len(COLUMNS_NAMES):
                df = df.iloc[:, :len(COLUMNS_NAMES)]
                df.columns = COLUMNS_NAMES
                lista_de_dataframes.append(df)
                print(f"  - Lido com sucesso: {arquivo}")
            else:
                 print(f"  - ERRO: {arquivo} tem colunas insuficientes. Esperado {len(COLUMNS_NAMES)}, encontrado {df.shape[1]}")
                 
        except Exception as e:
            print(f"  - ERRO ao ler {arquivo}: {e}")
            
    if not lista_de_dataframes:
        return pd.DataFrame()
        
    return pd.concat(lista_de_dataframes, ignore_index=True)

def limpar_dataframe(df):
    
    print("entrei")
    
    df['placa'] = df['placa'].astype(str).str.strip()
    
    # colunas vazias viram None
    for col in ["transportadora", "nro_nota_fiscal", "destino_procedencia"]:
        df[col] = df[col].astype(str).str.replace('nan', '', regex=False).str.strip()
        df[col] = df[col].replace({'': None}) 
        
    colunas_peso = [
        "peso_entrada", "peso_saida", "peso_liquido", "peso_embalagem_liquido", 
        "peso_embalagem_liquido_corrigido", "peso_nota_fiscal", "diferenca_peso"
    ]
    for col in colunas_peso:
        df[col] = df[col].astype(str).str.replace("kg", "", regex=False).str.strip()
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # coluna de porcentagem
    df['diferenca_peso_porcentagem'] = df['diferenca_peso_porcentagem'].astype(str).str.replace("%", "", regex=False).str.strip()
    df['diferenca_peso_porcentagem'] = pd.to_numeric(df['diferenca_peso_porcentagem'], errors='coerce')

    # coluna de data/hora
    df['data_hora'] = pd.to_datetime(df['data_hora'], errors='coerce')

    df = df.dropna(subset=['ticket', 'data_hora'])
    
    return df

def enviar_para_postgres(df, db_uri, table_name):

    if df.empty:
        print("Nenhum dado para enviar ao banco.")
        return
        
    try:
        engine = create_engine(db_uri)
        
       
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        
        print("Importação para o banco de dados concluída com sucesso.")
    
    except Exception as e:
        print(f"Ocorreu um erro ao enviar dados para o Postgres: {e}")

if __name__ == "__main__":
    df_bruto = carregar_planilhas_em_dataframe(PASTA_PLANILHAS)
    
    if not df_bruto.empty:
        df_limpo = limpar_dataframe(df_bruto)
        enviar_para_postgres(df_limpo, DATABASE_URI, NOME_TABELA_REGISTRO)
    else:
        print("Nenhuma planilha foi carregada.")