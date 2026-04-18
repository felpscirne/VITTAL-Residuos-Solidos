import pandas as pd
from app.database import engine
from app.extensions import cache

TYPE_ALL = "todos"

# --- 1. DADOS GERAIS / OVERVIEW ---


def _fill_monthly_gaps(df, value_columns):
    if df is None or df.empty or "ds" not in df.columns:
        return df

    filled = df.copy()
    filled["ds"] = pd.to_datetime(filled["ds"])
    full_range = pd.date_range(
        filled["ds"].min(),
        filled["ds"].max(),
        freq="MS",
    )
    filled = filled.set_index("ds").reindex(full_range).rename_axis("ds").reset_index()

    for column in value_columns:
        if column in filled.columns:
            filled[column] = pd.to_numeric(filled[column], errors="coerce").fillna(0)

    return filled


def _fill_daily_gaps(df, value_columns):
    if df is None or df.empty or "ds" not in df.columns:
        return df

    filled = df.copy()
    filled["ds"] = pd.to_datetime(filled["ds"])
    full_range = pd.date_range(
        filled["ds"].min(),
        filled["ds"].max(),
        freq="D",
    )
    filled = filled.set_index("ds").reindex(full_range).rename_axis("ds").reset_index()

    for column in value_columns:
        if column in filled.columns:
            filled[column] = pd.to_numeric(filled[column], errors="coerce").fillna(0)

    return filled


def _apply_tipo_residuo_filter(base_where, params, tipo_residuo):
    if tipo_residuo and tipo_residuo != TYPE_ALL:
        params["tipo_residuo"] = tipo_residuo
        return f"{base_where}\n        AND COALESCE(tipo_de_residuo, produto) = %(tipo_residuo)s"
    return base_where


def _build_quinzenal_query(where_clause):
    return f"""
    SELECT
        (
            DATE_TRUNC('month', data_hora)::date
            + CASE WHEN EXTRACT(DAY FROM data_hora) <= 15 THEN INTERVAL '0 day' ELSE INTERVAL '15 day' END
        )::date AS ds,
        SUM(peso_embalagem_liquido_corrigido) AS y
    FROM registro
    WHERE {where_clause}
    GROUP BY ds
    ORDER BY ds
    """


def _build_daily_query(where_clause):
    return f"""
    SELECT
        DATE_TRUNC('day', data_hora)::date AS ds,
        SUM(peso_embalagem_liquido_corrigido) AS y
    FROM registro
    WHERE {where_clause}
    GROUP BY ds
    ORDER BY ds
    """


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

@cache.memoize(timeout=3600)
def get_qtde_por_ano():
    query = "SELECT EXTRACT(YEAR FROM data_hora) AS ano, COUNT(*) AS qtde FROM registro GROUP BY ano ORDER BY ano"
    try:
        df = pd.read_sql(query, engine)
        df['ano'] = df['ano'].astype(str)
        return df
    except Exception:
        return pd.DataFrame()

@cache.memoize(timeout=3600)
def get_top_produtos_geral():
    query = "SELECT produto, COUNT(*) AS qtde FROM registro GROUP BY produto ORDER BY qtde DESC LIMIT 10"
    return pd.read_sql(query, engine)


@cache.memoize(timeout=3600)
def get_volume_quinzenal(tipo_residuo=TYPE_ALL):
    params = {}
    where_clause = _apply_tipo_residuo_filter(
        """
        data_hora IS NOT NULL
        AND peso_embalagem_liquido_corrigido IS NOT NULL
        AND setor != 'ACERTO DE PESO'
        """,
        params,
        tipo_residuo,
    )
    query = _build_quinzenal_query(where_clause)
    try:
        df = pd.read_sql(query, engine, params=params)
        if not df.empty:
            df["ds"] = pd.to_datetime(df["ds"])
            df["y"] = pd.to_numeric(df["y"], errors="coerce").fillna(0)
        return df
    except Exception:
        return pd.DataFrame(columns=["ds", "y"])


@cache.memoize(timeout=3600)
def get_volume_diario(tipo_residuo=TYPE_ALL, fill_gaps=True):
    params = {}
    where_clause = _apply_tipo_residuo_filter(
        """
        data_hora IS NOT NULL
        AND peso_embalagem_liquido_corrigido IS NOT NULL
        AND setor != 'ACERTO DE PESO'
        """,
        params,
        tipo_residuo,
    )
    query = _build_daily_query(where_clause)
    try:
        df = pd.read_sql(query, engine, params=params)
        if not df.empty:
            df["ds"] = pd.to_datetime(df["ds"])
            df["y"] = pd.to_numeric(df["y"], errors="coerce").fillna(0)
            if fill_gaps:
                df = _fill_daily_gaps(df, ["y"])
        return df
    except Exception:
        return pd.DataFrame(columns=["ds", "y"])


@cache.memoize(timeout=3600)
def get_entradas_quinzenais(tipo_residuo=TYPE_ALL):
    params = {}
    where_clause = _apply_tipo_residuo_filter(
        """
        data_hora IS NOT NULL
        AND peso_embalagem_liquido_corrigido IS NOT NULL
        AND setor != 'ACERTO DE PESO'
        AND setor != 'CANDIOTA'
        """,
        params,
        tipo_residuo,
    )
    query = _build_quinzenal_query(where_clause)
    try:
        df = pd.read_sql(query, engine, params=params)
        if not df.empty:
            df["ds"] = pd.to_datetime(df["ds"])
            df["y"] = pd.to_numeric(df["y"], errors="coerce").fillna(0)
        return df
    except Exception:
        return pd.DataFrame(columns=["ds", "y"])


@cache.memoize(timeout=3600)
def get_entradas_diarias(tipo_residuo=TYPE_ALL, fill_gaps=True):
    params = {}
    where_clause = _apply_tipo_residuo_filter(
        """
        data_hora IS NOT NULL
        AND peso_embalagem_liquido_corrigido IS NOT NULL
        AND setor != 'ACERTO DE PESO'
        AND setor != 'CANDIOTA'
        """,
        params,
        tipo_residuo,
    )
    query = _build_daily_query(where_clause)
    try:
        df = pd.read_sql(query, engine, params=params)
        if not df.empty:
            df["ds"] = pd.to_datetime(df["ds"])
            df["y"] = pd.to_numeric(df["y"], errors="coerce").fillna(0)
            if fill_gaps:
                df = _fill_daily_gaps(df, ["y"])
        return df
    except Exception:
        return pd.DataFrame(columns=["ds", "y"])


@cache.memoize(timeout=3600)
def get_saidas_quinzenais(tipo_residuo=TYPE_ALL):
    params = {}
    where_clause = _apply_tipo_residuo_filter(
        """
        data_hora IS NOT NULL
        AND peso_embalagem_liquido_corrigido IS NOT NULL
        AND setor = 'CANDIOTA'
        """,
        params,
        tipo_residuo,
    )
    query = _build_quinzenal_query(where_clause)
    try:
        df = pd.read_sql(query, engine, params=params)
        if not df.empty:
            df["ds"] = pd.to_datetime(df["ds"])
            df["y"] = pd.to_numeric(df["y"], errors="coerce").fillna(0)
        return df
    except Exception:
        return pd.DataFrame(columns=["ds", "y"])


@cache.memoize(timeout=3600)
def get_saidas_diarias(tipo_residuo=TYPE_ALL, fill_gaps=True):
    params = {}
    where_clause = _apply_tipo_residuo_filter(
        """
        data_hora IS NOT NULL
        AND peso_embalagem_liquido_corrigido IS NOT NULL
        AND setor = 'CANDIOTA'
        """,
        params,
        tipo_residuo,
    )
    query = _build_daily_query(where_clause)
    try:
        df = pd.read_sql(query, engine, params=params)
        if not df.empty:
            df["ds"] = pd.to_datetime(df["ds"])
            df["y"] = pd.to_numeric(df["y"], errors="coerce").fillna(0)
            if fill_gaps:
                df = _fill_daily_gaps(df, ["y"])
        return df
    except Exception:
        return pd.DataFrame(columns=["ds", "y"])


@cache.memoize(timeout=3600)
def get_setor_volume_quinzenal(setor, tipo_residuo=TYPE_ALL):
    params = {"setor": setor}
    where_clause = _apply_tipo_residuo_filter(
        """
        data_hora IS NOT NULL
        AND peso_embalagem_liquido_corrigido IS NOT NULL
        AND setor = %(setor)s
        """,
        params,
        tipo_residuo,
    )
    query = _build_quinzenal_query(where_clause)
    try:
        df = pd.read_sql(query, engine, params=params)
        if not df.empty:
            df["ds"] = pd.to_datetime(df["ds"])
            df["y"] = pd.to_numeric(df["y"], errors="coerce").fillna(0)
        return df
    except Exception:
        return pd.DataFrame(columns=["ds", "y"])


@cache.memoize(timeout=3600)
def get_setor_volume_diario(setor, tipo_residuo=TYPE_ALL, fill_gaps=True):
    params = {"setor": setor}
    where_clause = _apply_tipo_residuo_filter(
        """
        data_hora IS NOT NULL
        AND peso_embalagem_liquido_corrigido IS NOT NULL
        AND setor = %(setor)s
        """,
        params,
        tipo_residuo,
    )
    query = _build_daily_query(where_clause)
    try:
        df = pd.read_sql(query, engine, params=params)
        if not df.empty:
            df["ds"] = pd.to_datetime(df["ds"])
            df["y"] = pd.to_numeric(df["y"], errors="coerce").fillna(0)
            if fill_gaps:
                df = _fill_daily_gaps(df, ["y"])
        return df
    except Exception:
        return pd.DataFrame(columns=["ds", "y"])


def get_volume_mensal(tipo_residuo=TYPE_ALL):
    return get_volume_quinzenal(tipo_residuo=tipo_residuo)


def get_entradas_mensais(tipo_residuo=TYPE_ALL):
    return get_entradas_quinzenais(tipo_residuo=tipo_residuo)


def get_saidas_mensais(tipo_residuo=TYPE_ALL):
    return get_saidas_quinzenais(tipo_residuo=tipo_residuo)


def get_setor_volume_mensal(setor, tipo_residuo=TYPE_ALL):
    return get_setor_volume_quinzenal(setor, tipo_residuo=tipo_residuo)

# --- 2. AUXILIARES (Usado em Gerenciar Eventos) ---

@cache.memoize(timeout=3600)
def get_list_setores():
    try:
        query = "SELECT DISTINCT setor FROM registro WHERE setor IS NOT NULL ORDER BY setor"
        df = pd.read_sql(query, engine)
        return df['setor'].tolist()
    except Exception:
        return []


def get_tipos_residuo_options():
    """Retorna apenas os tipos de resíduo realmente presentes na tabela registro."""
    try:
        query = """
            SELECT DISTINCT COALESCE(tipo_de_residuo, produto) AS tipo_residuo
            FROM registro
            WHERE COALESCE(tipo_de_residuo, produto) IS NOT NULL
            ORDER BY tipo_residuo
        """
        df = pd.read_sql(query, engine)
        tipos_presentes = [
            str(t) for t in df["tipo_residuo"].dropna().tolist() if str(t).strip()
        ]
    except Exception:
        return [{"label": "Todos os Resíduos", "value": TYPE_ALL}]

    options = [{"label": "Todos os Resíduos", "value": TYPE_ALL}]
    for tipo in tipos_presentes:
        options.append({
            "label": tipo,
            "value": tipo,
        })
    return options

# --- 3. ANÁLISE DE SETORES ---

@cache.memoize(timeout=3600)
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

@cache.memoize(timeout=3600)
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

@cache.memoize(timeout=3600)
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

@cache.memoize(timeout=3600)
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

@cache.memoize(timeout=3600)
def get_ranking_produtos():
    query = """
    SELECT produto, COUNT(*) as quantidade, SUM(peso_embalagem_liquido_corrigido) as peso_total
    FROM registro WHERE produto IS NOT NULL GROUP BY produto ORDER BY quantidade DESC LIMIT 50 
    """
    return pd.read_sql(query, engine)

@cache.memoize(timeout=3600)
def get_produtos_resumo():
    query = """
    SELECT 
        produto, 
        COUNT(*) as quantidade,
        SUM(peso_embalagem_liquido_corrigido) as peso_total
    FROM registro 
    WHERE produto IS NOT NULL
    GROUP BY produto 
    ORDER BY quantidade DESC
    """
    return pd.read_sql(query, engine)

@cache.memoize(timeout=3600)
def get_fornecedores_por_produto(produto, limit=20):
    query = """
    SELECT fornecedor_cliente, COUNT(*) as quantidade
    FROM registro
    WHERE produto = %(produto)s AND fornecedor_cliente IS NOT NULL
    GROUP BY fornecedor_cliente ORDER BY quantidade DESC
    """
    if limit:
        query += f" LIMIT {limit}"
        
    return pd.read_sql(query, engine, params={'produto': produto})

@cache.memoize(timeout=3600)
def get_produtos_por_setor(setor, limit=20):
    query = """
    SELECT produto, COUNT(*) as quantidade
    FROM registro
    WHERE setor = %(setor)s AND produto IS NOT NULL
    GROUP BY produto ORDER BY quantidade DESC
    """
    if limit:
        query += f" LIMIT {limit}"

    return pd.read_sql(query, engine, params={'setor': setor})

# --- 6. FLUXO DE CAIXA (CANDIOTA) ---

@cache.memoize(timeout=3600)
def get_fluxo_macro(tipo_residuo=TYPE_ALL):
    params = {}
    tipo_clause = ""
    if tipo_residuo and tipo_residuo != TYPE_ALL:
        params["tipo_residuo"] = tipo_residuo
        tipo_clause = " AND COALESCE(tipo_de_residuo, produto) = %(tipo_residuo)s"
    query = f"""
    SELECT 
        EXTRACT(YEAR FROM data_hora) as year,
        EXTRACT(MONTH FROM data_hora) as month,
        SUM(CASE WHEN setor = 'CANDIOTA' THEN peso_embalagem_liquido_corrigido ELSE 0 END) as saidas,
        SUM(CASE WHEN setor != 'CANDIOTA' AND setor != 'ACERTO DE PESO' THEN peso_embalagem_liquido_corrigido ELSE 0 END) as entradas
    FROM registro
    WHERE data_hora IS NOT NULL{tipo_clause}
    GROUP BY year, month
    ORDER BY year, month
    """
    try:
        df = pd.read_sql(query, engine, params=params)
        if not df.empty:
            df["ds"] = pd.to_datetime(df.assign(day=1)[["year", "month", "day"]])
            df = _fill_monthly_gaps(df, ["entradas", "saidas", "balanco"])
            df['balanco'] = (df['entradas'] - df['saidas']).round(2)
            df['entradas'] = df['entradas'].round(2)
            df['saidas'] = df['saidas'].round(2)
            df['year'] = df['ds'].dt.year
            df['month'] = df['ds'].dt.month
            df['periodo'] = df['ds'].dt.strftime('%Y-%m')
        return df
    except Exception:
        return pd.DataFrame()

@cache.memoize(timeout=3600)
def get_fluxo_micro(tipo_residuo=TYPE_ALL):
    params = {}
    tipo_clause = ""
    if tipo_residuo and tipo_residuo != TYPE_ALL:
        params["tipo_residuo"] = tipo_residuo
        tipo_clause = " AND COALESCE(tipo_de_residuo, produto) = %(tipo_residuo)s"
    query = f"""
    SELECT
        EXTRACT(YEAR FROM data_hora) as year,
        EXTRACT(MONTH FROM data_hora) as month,
        setor,
        COALESCE(tipo_de_residuo, produto) as tipo_residuo,
        SUM(peso_embalagem_liquido_corrigido) as peso_kg
    FROM registro
    WHERE setor != 'ACERTO DE PESO'{tipo_clause}
    GROUP BY year, month, setor, tipo_residuo
    ORDER BY year, month, setor, tipo_residuo
    """
    try:
        df = pd.read_sql(query, engine, params=params)
        if not df.empty:
            df['periodo'] = pd.to_datetime(df.assign(day=1)[['year', 'month', 'day']]).dt.strftime('%Y-%m')
        return df
    except Exception:
        return pd.DataFrame()

# --- 7. ANÁLISE DE HORÁRIOS ---

@cache.memoize(timeout=3600)
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

@cache.memoize(timeout=3600)
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

# --- 9. OPÇÕES E LISTAS (Para Dropdowns) ---

@cache.memoize(timeout=3600)
def get_produtos_options():
    try:
        df = pd.read_sql("SELECT DISTINCT produto FROM registro WHERE produto IS NOT NULL ORDER BY produto", engine)
        return [{'label': p, 'value': p} for p in df['produto']]
    except Exception:
        return []

@cache.memoize(timeout=3600)
def get_setores_options():
    try:
        query = "SELECT DISTINCT setor FROM registro WHERE setor IS NOT NULL AND setor != 'ACERTO DE PESO' AND setor != 'CANDIOTA' ORDER BY setor"
        df = pd.read_sql(query, engine)
        return [{'label': s, 'value': s} for s in df['setor']]
    except Exception:
        return []

@cache.memoize(timeout=3600)
def get_anos_options():
    try:
        anos_df = pd.read_sql("SELECT DISTINCT EXTRACT(YEAR FROM data_hora) AS ano FROM registro ORDER BY ano DESC", engine)
        options = [{'label': str(int(ano)), 'value': int(ano)} for ano in anos_df['ano']]
        valor_inicial = options[0]['value'] if options else None
        return options, valor_inicial
    except Exception as e:
        print(f"Erro ao buscar anos: {e}")
        return [{'label': '2024', 'value': 2024}], 2024 

# --- 10. TABELA REGISTROS (Sem Cache longo, pois tem muitos filtros) ---

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
