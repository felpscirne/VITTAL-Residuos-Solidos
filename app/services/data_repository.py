import pandas as pd
from app.database import engine
from app.extensions import cache


# --- 1. DADOS GERAIS / OVERVIEW ---

@cache.memoize(timeout=600)
def get_kpis_gerais():
    query = "SELECT COUNT(*) AS total_registros, MIN(data_hora) AS data_inicio, MAX(data_hora) AS data_fim FROM registro"
    try:
        df = pd.read_sql(query, engine)
        kpis = df.iloc[0]
        return {
            'total': kpis['total_registros'],
            'inicio': kpis['data_inicio'].strftime('%d/%m/%Y') if pd.notnull(kpis['data_inicio']) else 'N/D',
            'fim': kpis['data_fim'].strftime('%d/%m/%Y') if pd.notnull(kpis['data_fim']) else 'N/D'
        }
    except Exception:
        return {'total': 'N/D', 'inicio': 'N/D', 'fim': 'N/D'}

@cache.memoize()
def get_qtde_por_ano():
    query = "SELECT EXTRACT(YEAR FROM data_hora) AS ano, COUNT(*) AS qtde FROM registro GROUP BY ano ORDER BY ano"
    try:
        df = pd.read_sql(query, engine)
        df['ano'] = df['ano'].astype(str)
        return df
    except Exception:
        return pd.DataFrame()

@cache.memoize()
def get_top_produtos_geral():
    query = "SELECT produto, COUNT(*) AS qtde FROM registro GROUP BY produto ORDER BY qtde DESC LIMIT 10"
    return pd.read_sql(query, engine)

# --- 2. AUXILIARES (Usado em Gerenciar Eventos) ---

@cache.memoize()
def get_list_setores():
    try:
        query = "SELECT DISTINCT setor FROM registro WHERE setor IS NOT NULL ORDER BY setor"
        df = pd.read_sql(query, engine)
        return df['setor'].tolist()
    except Exception:
        return []

# --- 3. ANÁLISE DE SETORES ---

@cache.memoize()
def get_dados_setores_macro():
    query = """
    SELECT 
        setor, 
        AVG(peso_embalagem_liquido_corrigido) as "Média de Peso (kg)",
        COUNT(*) as quantidade
    FROM registro 
    WHERE 
        setor IS NOT NULL AND
        setor != 'ACERTO DE PESO' AND
        setor != 'CANDIOTA'
    GROUP BY setor
    """
    return pd.read_sql(query, engine)

@cache.memoize()
def get_dados_setor_temporal(setor, ano):
    query = """
    SELECT 
        EXTRACT(MONTH FROM data_hora) as mes,
        AVG(peso_embalagem_liquido_corrigido) as media_peso
    FROM registro
    WHERE 
        setor = %(setor)s AND 
        EXTRACT(YEAR FROM data_hora) = %(ano)s
    GROUP BY mes
    ORDER BY mes
    """
    return pd.read_sql(query, engine, params={'setor': setor, 'ano': ano})

# --- 4. ANÁLISE DE EMPRESAS ---

@cache.memoize()
def get_ranking_empresas():
    query = """
    SELECT 
        fornecedor_cliente, 
        COUNT(*) as quantidade,
        SUM(peso_embalagem_liquido_corrigido) as peso_total
    FROM registro 
    WHERE fornecedor_cliente IS NOT NULL
    GROUP BY fornecedor_cliente 
    ORDER BY quantidade DESC
    LIMIT 50
    """
    return pd.read_sql(query, engine)

@cache.memoize()
def get_empresa_temporal(empresa, ano):
    base_query = " FROM registro WHERE EXTRACT(YEAR FROM data_hora) = %(ano)s"
    params = {'ano': ano}
    
    if empresa != 'todas':
        base_query += " AND fornecedor_cliente = %(empresa)s"
        params['empresa'] = empresa
        
    query1 = "SELECT EXTRACT(MONTH FROM data_hora) AS mes, COUNT(*) AS qtde" + base_query + " GROUP BY mes ORDER BY mes"
    query2 = "SELECT EXTRACT(MONTH FROM data_hora) AS mes, AVG(peso_embalagem_liquido_corrigido) AS media" + base_query + " GROUP BY mes ORDER BY mes"
    
    df_vol = pd.read_sql(query1, engine, params=params)
    df_med = pd.read_sql(query2, engine, params=params)
    return df_vol, df_med

# --- 5. ANÁLISE DE PRODUTOS ---

@cache.memoize()
def get_ranking_produtos():
    query = """
    SELECT produto, COUNT(*) as quantidade, SUM(peso_embalagem_liquido_corrigido) as peso_total
    FROM registro WHERE produto IS NOT NULL GROUP BY produto ORDER BY quantidade DESC LIMIT 50 
    """
    return pd.read_sql(query, engine)

@cache.memoize()
def get_fornecedores_por_produto(produto):
    query = """
    SELECT fornecedor_cliente, COUNT(*) as quantidade
    FROM registro
    WHERE produto = %(produto)s AND fornecedor_cliente IS NOT NULL
    GROUP BY fornecedor_cliente ORDER BY quantidade DESC LIMIT 20
    """
    return pd.read_sql(query, engine, params={'produto': produto})

@cache.memoize()
def get_produtos_por_setor(setor):
    query = """
    SELECT produto, COUNT(*) as quantidade
    FROM registro
    WHERE setor = %(setor)s AND produto IS NOT NULL
    GROUP BY produto ORDER BY quantidade DESC LIMIT 20
    """
    return pd.read_sql(query, engine, params={'setor': setor})

# --- 6. FLUXO DE CAIXA (CANDIOTA) ---

@cache.memoize()
def get_fluxo_macro():
    query = """
    SELECT 
        EXTRACT(YEAR FROM data_hora) as year,
        EXTRACT(MONTH FROM data_hora) as month,
        SUM(CASE WHEN setor = 'CANDIOTA' THEN peso_embalagem_liquido_corrigido ELSE 0 END) as saidas,
        SUM(CASE WHEN setor != 'CANDIOTA' AND setor != 'ACERTO DE PESO' THEN peso_embalagem_liquido_corrigido ELSE 0 END) as entradas
    FROM registro
    GROUP BY year, month
    ORDER BY year, month
    """
    try:
        df = pd.read_sql(query, engine)
        if not df.empty:
            df['balanco'] = (df['entradas'] - df['saidas']).round(2)
            df['entradas'] = df['entradas'].round(2)
            df['saidas'] = df['saidas'].round(2)
            df['periodo'] = pd.to_datetime(df.assign(day=1)[['year', 'month', 'day']]).dt.strftime('%Y-%m')
        return df
    except Exception:
        return pd.DataFrame()

@cache.memoize()
def get_fluxo_micro():
    query = """
    SELECT
        EXTRACT(YEAR FROM data_hora) as year,
        EXTRACT(MONTH FROM data_hora) as month,
        setor,
        SUM(peso_embalagem_liquido_corrigido) as peso_kg
    FROM registro
    WHERE setor != 'ACERTO DE PESO'
    GROUP BY year, month, setor
    ORDER BY year, month, setor
    """
    try:
        df = pd.read_sql(query, engine)
        if not df.empty:
            df['periodo'] = pd.to_datetime(df.assign(day=1)[['year', 'month', 'day']]).dt.strftime('%Y-%m')
        return df
    except Exception:
        return pd.DataFrame()

# --- 7. ANÁLISE DE HORÁRIOS ---

@cache.memoize()
def get_heatmap_data():
    query = """
    SELECT 
        EXTRACT(DOW FROM data_hora) as dia_semana_num,
        EXTRACT(HOUR FROM data_hora) as hora_do_dia,
        EXTRACT(YEAR FROM data_hora) as ano,
        EXTRACT(MONTH FROM data_hora) as mes,
        COUNT(*) as numero_de_registros
    FROM registro
    GROUP BY ano, mes, dia_semana_num, hora_do_dia
    """
    return pd.read_sql(query, engine)

# --- 8. ANÁLISE DE FROTA ---

@cache.memoize()
def get_frota_data():
    query = """
    SELECT 
        placa_veiculo,
        COALESCE(fornecedor_cliente, 'Não Especificada') as entidade_responsavel,
        COUNT(*) as total_viagens,
        AVG(peso_liquido) as peso_medio_por_viagem
    FROM registro
    WHERE 
        setor != 'CANDIOTA' AND setor != 'ACERTO DE PESO'
        AND peso_liquido > 0 AND placa_veiculo IS NOT NULL
    GROUP BY placa_veiculo, fornecedor_cliente
    ORDER BY total_viagens DESC;
    """
    df = pd.read_sql(query, engine)
    if not df.empty:
        df['peso_medio_por_viagem'] = df['peso_medio_por_viagem'].round(2)
    return df

# --- 9. TABELA REGISTROS (Sem Cache longo, pois tem muitos filtros) ---

def get_registros_filtrados(ano, mes, ticket):
    query = "SELECT * FROM registro WHERE 1=1"
    params = {}
    if ano:
        query += " AND EXTRACT(YEAR FROM data_hora) = %(ano)s"
        params['ano'] = ano
    if mes:
        query += " AND EXTRACT(MONTH FROM data_hora) = %(mes)s"
        params['mes'] = mes
    if ticket:
        try:
            params['ticket'] = int(ticket)
            query += " AND ticket = %(ticket)s"
        except ValueError:
            pass 
    query += " ORDER BY data_hora DESC LIMIT 1000"
    
    df = pd.read_sql(query, engine, params=params)
    if not df.empty and 'data_hora' in df.columns:
        df['data_hora'] = df['data_hora'].astype(str)
    return df