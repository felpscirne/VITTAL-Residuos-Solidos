from dash import dcc, html, callback, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc

from app.database import engine
from app.services.ai_service import generate_analysis_component

template_theme_light = "cosmo" 
template_theme_dark = "plotly_dark"

def get_entidades_options():
    query = """
    SELECT DISTINCT fornecedor_cliente 
    FROM registro 
    WHERE 
        fornecedor_cliente IS NOT NULL 
        AND peso_nota_fiscal > 0
    ORDER BY fornecedor_cliente;
    """
    df = pd.read_sql(query, engine)
    options = [{'label': t, 'value': t} for t in df['fornecedor_cliente']]
    options.insert(0, {'label': 'Todas as Entidades', 'value': 'todas'})
    return options

entidades_options = get_entidades_options()


table_header_style = {
    "backgroundColor": "var(--bs-tertiary-bg)",
    "color": "var(--bs-body-color)",
    "fontWeight": "bold",
    "border": "1px solid var(--bs-border-color)"
}
table_data_style = {
    "backgroundColor": "var(--bs-body-bg)",
    "color": "var(--bs-body-color)",
}
table_cell_style = {'border': '1px solid var(--bs-border-color)', 'textAlign': 'left'}


layout = html.Div([
    html.H1('Auditoria de Peso (Real vs. Nota Fiscal)'),
    html.P('Esta análise compara o peso medido em nossa balança com o peso declarado na Nota Fiscal.'),
    html.Hr(),
    
    dbc.Alert(
        [
            html.H5("O que esta análise responde?", className="alert-heading"),
            html.P("O peso que as empresas estão declarando confere com o que estamos medindo? "
                   "Uma diferença grande pode indicar erro de registro, problema na balança da empresa ou, em casos extremos, fraude."),
        ], color="info", className="mb-3"
    ),

    # --- Filtros ---
    dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Filtrar por Empresa/Entidade:"),
                    dcc.Dropdown(
                        id='filtro-entidade-auditoria',
                        options=entidades_options,
                        value='todas'
                    )
                ], md=6),
                dbc.Col([
                    html.Label("Limite de discrepância (%):"),
                    dcc.Slider(
                        id='filtro-discrepancia-auditoria',
                        min=0,
                        max=20,
                        step=1,
                        value=5,
                        marks={i: f'{i}%' for i in range(0, 21, 5)},
                        tooltip={"placement": "bottom", "always_visible": False}
                    )
                ], md=6)
            ])
        ]),
        className="dbc mb-3"
    ),

    dbc.Button("🤖 Analisar Discrepâncias", id="btn-ia-auditoria", n_clicks=0, color="primary", outline=True, size="sm", className="mb-3"),
    dcc.Loading(html.Div(id='ia-output-auditoria')), 

    dbc.Card(
        dbc.CardBody(
            dash_table.DataTable(
                id='tabela-auditoria',
                page_size=15,
                sort_action="native",
                filter_action="native",
                style_table={'overflowX': 'auto'},
                
              
                style_header=table_header_style,
                style_data=table_data_style,
                style_cell=table_cell_style,
            )
        ),
        className="dbc mb-3"
    )
])


@callback(
    [Output('tabela-auditoria', 'data'),
     Output('tabela-auditoria', 'columns'),
     Output('tabela-auditoria', 'style_data_conditional')],
    [Input('filtro-entidade-auditoria', 'value'),
     Input('filtro-discrepancia-auditoria', 'value'),
     Input("theme-switch", "value")] 
)
def update_audit_table(selected_entidade, min_discrepancia, switch_is_light):
    
    query = """
    SELECT 
        ticket,
        to_char(data_hora, 'YYYY-MM-DD HH24:MI') as data_hora,
        fornecedor_cliente,
        produto,
        peso_embalagem_liquido_corrigido,
        peso_nota_fiscal,
        (peso_embalagem_liquido_corrigido - peso_nota_fiscal) as diferenca_kg,
        ((peso_embalagem_liquido_corrigido - peso_nota_fiscal) / peso_nota_fiscal) * 100 as diferenca_percentual
    FROM registro
    WHERE 
        peso_nota_fiscal > 0 
        AND peso_embalagem_liquido_corrigido > 0
    """
    params = {}
    
    if selected_entidade != 'todas':
        query += " AND fornecedor_cliente = %(entidade)s"
        params['entidade'] = selected_entidade
        
    query += " ORDER BY diferenca_percentual DESC;"

    df_audit = pd.read_sql(query, engine, params=params)
    

    df_audit['diferenca_kg'] = pd.to_numeric(df_audit['diferenca_kg'], errors='coerce')
    df_audit['diferenca_percentual'] = pd.to_numeric(df_audit['diferenca_percentual'], errors='coerce')

    df_audit['diferenca_kg'] = df_audit['diferenca_kg'].round(2)
    df_audit['diferenca_percentual'] = df_audit['diferenca_percentual'].round(2)
    
    df_filtered = df_audit[
        (df_audit['diferenca_percentual'] > min_discrepancia) |
        (df_audit['diferenca_percentual'] < -min_discrepancia)
    ]
    
    data = df_filtered.to_dict('records')
    columns = [{"name": i, "id": i} for i in df_filtered.columns]
    
    # 3. estilos para diferenças significativas
    dynamic_styles = [
        {
            'if': { 'column_id': 'diferenca_percentual',
                    'filter_query': f'{{diferenca_percentual}} > {min_discrepancia}' },
            'backgroundColor': '#FF4136', 'color': 'white'
        },
        {
            'if': { 'column_id': 'diferenca_percentual',
                    'filter_query': f'{{diferenca_percentual}} < -{min_discrepancia}' },
            'backgroundColor': '#FF4136', 'color': 'white'
        },
    ]
    

    return data, columns, dynamic_styles

@callback(
    Output('ia-output-auditoria', 'children'),
    [Input('btn-ia-auditoria', 'n_clicks')],
    [State('filtro-entidade-auditoria', 'value'),
     State('filtro-discrepancia-auditoria', 'value')],
    prevent_initial_call=True
)
def get_ia_audit_analysis(n_clicks, selected_entidade, min_discrepancia):
    
            
    query = """
    SELECT 
        ticket, fornecedor_cliente, produto,
        peso_embalagem_liquido_corrigido as peso_real,
        peso_nota_fiscal as peso_declarado,
        ((peso_embalagem_liquido_corrigido - peso_nota_fiscal) / peso_nota_fiscal) * 100 as diferenca_percentual
    FROM registro
    WHERE 
        peso_nota_fiscal > 0 
        AND peso_embalagem_liquido_corrigido > 0
    """
    params = {}
    
    contexto_filtro = "de todas as entidades"
    if selected_entidade != 'todas':
        query += " AND fornecedor_cliente = %(entidade)s"
        params['entidade'] = selected_entidade
        contexto_filtro = f"da entidade '{selected_entidade}'"
        
    query += " ORDER BY diferenca_percentual DESC"

    df_audit = pd.read_sql(query, engine, params=params)
    df_audit['diferenca_percentual'] = pd.to_numeric(df_audit['diferenca_percentual'], errors='coerce').round(2)
    
    df_discrepancias = df_audit[
        (df_audit['diferenca_percentual'] > min_discrepancia) |
        (df_audit['diferenca_percentual'] < -min_discrepancia)
    ]
    
    if df_discrepancias.empty:
        return dbc.Alert(f"Nenhuma discrepância significativa (> {min_discrepancia}%) encontrada para {contexto_filtro}.", color="success", className="mt-3")

    dados_em_texto = df_discrepancias.to_markdown(index=False)

    prompt = f"""
    Você é um auditor sênior da prefeitura de Rio Grande - RS.
    Sua tarefa é analisar as discrepâncias de pesagem {contexto_filtro} 
    onde a diferença entre o peso real (medido) e o peso declarado (nota fiscal) 
    foi maior que {min_discrepancia}%.

    Aqui estão os registros encontrados:
    {dados_em_texto}

    Por favor, gere uma análise em markdown respondendo:
    1.  O que a existência dessas discrepâncias significa?
    2.  Qual é a discrepância mais grave (maior %)?
    3.  Qual a sua principal recomendação de auditoria para o gestor? (Ex: "Investigar o Ticket X", "Verificar a balança da Empresa Y", etc.)
    
    Responda em um texto organizado e de linguagem clara. Não fale as perguntas. Não se apresente.
    """
    
    return generate_analysis_component(prompt)