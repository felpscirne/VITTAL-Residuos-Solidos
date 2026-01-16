from dash import dcc, html, callback, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify

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


layout = html.Div([
    dmc.Title('Auditoria de Pesagem: Balança vs Nota Fiscal', order=2),
    dmc.Text('Esta análise compara o peso medido em nossa balança com o peso declarado na Nota Fiscal.', c="dimmed", size="sm"),
    dmc.Divider(variant="solid", my="md"),

    dmc.Alert(
        children=[
            dmc.Title("Sobre Auditoria", order=5),
            dmc.Text("Identifique divergências significativas entre o peso declarado e o peso aferido."),
        ],
        title="Controle de Qualidade",
        color="red",
        variant="light",
        icon=DashIconify(icon="akar-icons:triangle-alert"),
        mb="md"
    ),

    # --- Filtros ---
    dmc.Card(
        children=[
            dmc.Grid(
                gutter="md",
                children=[
                    dmc.GridCol(
                        [
                            dmc.Select(
                                label="Filtrar por Empresa/Entidade",
                                placeholder="Selecione uma entidade",
                                id='filtro-entidade-auditoria',
                                data=entidades_options,
                                value='todas',
                                leftSection=DashIconify(icon="domain")
                            )
                        ], span={"base": 12, "md": 6}
                    ),
                    dmc.GridCol(
                        [
                            dmc.Text(id='label-slider-auditoria', children="Limite de discrepância (%): 5%", size="sm", fw=500, mb=5),
                            dmc.Slider(
                                id='filtro-discrepancia-auditoria',
                                min=0,
                                max=20,
                                step=1,
                                value=5,
                                updatemode='drag',
                                marks=[
                                    {'value': 0, 'label': '0%'},
                                    {'value': 5, 'label': '5%'},
                                    {'value': 10, 'label': '10%'},
                                    {'value': 20, 'label': '20%'},
                                ],
                                color="red"
                            )
                        ], span={"base": 12, "md": 6}
                    )
                ]
            )
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        mb="md"
    ),

    dmc.Button(
        "🤖 Auditar Discrepâncias", 
        id="btn-ia-auditoria", 
        n_clicks=0, 
        variant="outline", 
        color="indigo", 
        leftSection=DashIconify(icon="fluent:bot-24-regular")
    ),
    dcc.Loading(html.Div(id='ia-output-auditoria')), 

    dmc.Card(
        children=[
            dmc.ScrollArea(
                dash_table.DataTable(
                    id='tabela-auditoria',
                    page_size=15,
                    sort_action="native",
                    filter_action="native",
                    style_table={'minWidth': '100%'},
                    style_header={
                        "backgroundColor": "#f8f9fa", 
                        "color": "#000", 
                        "fontWeight": "bold", 
                        "fontFamily": "sans-serif"
                    },
                    style_data={
                        "backgroundColor": "#fff", 
                        "color": "#000",
                        "fontFamily": "sans-serif"
                    },
                    style_cell={'border': '1px solid #dee2e6', 'padding': '10px', 'textAlign': 'left'},
                ), 
                offsetScrollbars=True,
                type="auto"
            )
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        mb="md"
    )
])


@callback(
    [Output('tabela-auditoria', 'data'),
     Output('tabela-auditoria', 'columns'),
     Output('tabela-auditoria', 'style_data_conditional'),
     Output('label-slider-auditoria', 'children')],
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
            'backgroundColor': '#fa5252', 'color': 'white'
        },
        {
            'if': { 'column_id': 'diferenca_percentual',
                    'filter_query': f'{{diferenca_percentual}} < -{min_discrepancia}' },
            'backgroundColor': '#fa5252', 'color': 'white'
        },
    ]
    
    label_slider = f"Limite de discrepância (%): {min_discrepancia}%"

    return data, columns, dynamic_styles, label_slider

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
        return dmc.Alert(f"Nenhuma discrepância significativa (> {min_discrepancia}%) encontrada para {contexto_filtro}.", color="teal", variant="filled", className="mt-3")

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
