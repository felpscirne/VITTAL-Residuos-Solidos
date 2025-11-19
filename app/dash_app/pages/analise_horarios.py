from dash import dcc, html, callback
from dash.dependencies import Input, Output, State # Adicionamos 'State'
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc

from app.database import engine, get_anos_options 
from app.services.ai_service import generate_analysis_component
template_theme_light = "cosmo" 
template_theme_dark = "plotly_dark"

dias_map = {
    0: 'Domingo',
    1: 'Segunda-feira',
    2: 'Terça-feira',
    3: 'Quarta-feira',
    4: 'Quinta-feira',
    5: 'Sexta-feira',
    6: 'Sábado'
}
dias_completos = list(dias_map.values())
horas_completas = list(range(24))

anos_options, _ = get_anos_options()
anos_options.insert(0, {'label': 'Todos os Anos', 'value': 'todos'})

meses_options = [
    {'label': 'Ano Inteiro', 'value': 'todos'},
    {'label': 'Janeiro', 'value': 1},
    {'label': 'Fevereiro', 'value': 2},
    {'label': 'Março', 'value': 3},
    {'label': 'Abril', 'value': 4},
    {'label': 'Maio', 'value': 5},
    {'label': 'Junho', 'value': 6},
    {'label': 'Julho', 'value': 7},
    {'label': 'Agosto', 'value': 8},
    {'label': 'Setembro', 'value': 9},
    {'label': 'Outubro', 'value': 10},
    {'label': 'Novembro', 'value': 11},
    {'label': 'Dezembro', 'value': 12},
]


def load_heatmap_data():
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
    df = pd.read_sql(query, engine)
    
    df['dia_semana'] = df['dia_semana_num'].map(dias_map)
    return df

df_heatmap_raw = load_heatmap_data()

def create_heatmap_graph(df_grouped, template):
    
    
    # Pivota a tabela para preencher com zeros
    df_pivot = df_grouped.pivot_table(
        values='numero_de_registros',
        index='dia_semana',
        columns='hora_do_dia',
        fill_value=0
    )
    df_pivot = df_pivot.reindex(
        index=dias_completos, 
        columns=horas_completas, 
        fill_value=0
    )

    # Converte de volta para formato longo
    df_final = df_pivot.stack().reset_index(name='numero_de_registros')

    fig = px.density_heatmap(
        df_final,
        x='hora_do_dia',
        y='dia_semana',
        z='numero_de_registros',
        title="Mapa de Calor: Carga de Trabalho da Balança",
        labels={
            'hora_do_dia': 'Hora do Dia (0-23h)',
            'dia_semana': 'Dia da Semana',
            'numero_de_registros': 'Nº de Registros'
        },
        template=template,
        category_orders={
            'dia_semana': dias_completos,
            'hora_do_dia': horas_completas
        },
        color_continuous_scale="Viridis"
    )
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_nticks=24
    )
    return fig

layout = html.Div([
    html.H1('Análise de Horário de Pico'),
    html.P('Esta análise mostra os "pontos quentes" da operação da balança, cruzando o dia da semana com a hora do dia.'),
    html.Hr(),
    
    dbc.Alert(
        [
            html.H5("O que este gráfico responde?", className="alert-heading"),
            html.P("Quais são os dias e horários de maior movimento? Onde estão nossos gargalos? "
                   "E quais são os horários mais ociosos? As áreas mais escuras/vermelhas são os horários de pico."),
        ], color="info", className="mb-3"
    ),

    dbc.Row(
        [
            dbc.Col(
                [
                    html.Label("Selecione o Ano:"),
                    dcc.Dropdown(
                        id='filtro-ano-heatmap',
                        options=anos_options,
                        value='todos' 
                    )
                ], md=6
            ),
            dbc.Col(
                [
                    html.Label("Selecione o Mês:"),
                    dcc.Dropdown(
                        id='filtro-mes-heatmap',
                        options=meses_options,
                        value='todos' 
                    )
                ], md=6
            )
        ], className="dbc mb-3"
    ),

    

    dbc.Card(
        dbc.CardBody([
            dcc.Graph(id='grafico-heatmap') 
        ]),
        className="mb-3"
    ),

    dbc.Button("🤖 Analisar Horários de Pico", id="btn-ia-heatmap", n_clicks=0, color="primary", outline=True, size="sm", className="mb-3"),
    dcc.Loading(html.Div(id='ia-output-heatmap'))
])


@callback(
    Output('grafico-heatmap', 'figure'),
    [Input('filtro-ano-heatmap', 'value'),
     Input('filtro-mes-heatmap', 'value'),
     Input("theme-switch", "value")]
)
def update_heatmap(selected_year, selected_month, switch_is_light):
    template = template_theme_light if switch_is_light else template_theme_dark
    
    df_filtered = df_heatmap_raw.copy()
    if selected_year != 'todos':
        df_filtered = df_filtered[df_filtered['ano'] == selected_year]
    if selected_month != 'todos':
        df_filtered = df_filtered[df_filtered['mes'] == selected_month]
        
  
    df_grouped = df_filtered.groupby(
        ['dia_semana', 'hora_do_dia']
    )['numero_de_registros'].sum().reset_index()

    fig = create_heatmap_graph(df_grouped, template)
    return fig

@callback(
    Output('ia-output-heatmap', 'children'),
    [Input('btn-ia-heatmap', 'n_clicks')],
    [State('filtro-ano-heatmap', 'value'), 
     State('filtro-mes-heatmap', 'value')],
    prevent_initial_call=True
)
def get_ia_heatmap_analysis(n_clicks, selected_year, selected_month):
            
    df_filtered = df_heatmap_raw.copy()
    
    contexto_tempo = "de todo o período"
    if selected_year != 'todos' and selected_month != 'todos':
        df_filtered = df_filtered[
            (df_filtered['ano'] == selected_year) & 
            (df_filtered['mes'] == selected_month)
        ]
        contexto_tempo = f"de {meses_options[selected_month]['label']}/{selected_year}"
    elif selected_year != 'todos':
        df_filtered = df_filtered[df_filtered['ano'] == selected_year]
        contexto_tempo = f"do ano de {selected_year}"
    elif selected_month != 'todos':
        df_filtered = df_filtered[df_filtered['mes'] == selected_month]
        contexto_tempo = f"de todos os meses de {meses_options[selected_month]['label']}"

    df_grouped = df_filtered.groupby(
        ['dia_semana', 'hora_do_dia']
    )['numero_de_registros'].sum().reset_index()

    df_pico = df_grouped.nlargest(5, 'numero_de_registros')
    df_ocioso = df_grouped[df_grouped['numero_de_registros'] > 0].nsmallest(5, 'numero_de_registros')

    dados_pico_texto = df_pico.to_markdown(index=False)
    dados_ocioso_texto = df_ocioso.to_markdown(index=False)


    # Prompt Horarios
    prompt = f"""
    Você é um gerente de operações da prefeitura de Rio Grande - RS.
    Sua tarefa é analisar os horários de pico e ociosos da balança de pesagem
    para o período filtrado: {contexto_tempo}.
    (Hora 0 = 00:00, Hora 14 = 14:00)

    Aqui estão os dados:
    
    TOP 5 HORÁRIOS DE PICO (Mais Registros) {contexto_tempo}:
    {dados_pico_texto}

    TOP 5 HORÁRIOS OCIOSOS (Menos Registros, >0) {contexto_tempo}:
    {dados_ocioso_texto}

    Por favor, gere uma análise em markdown respondendo:
    1.  Qual é o padrão de pico claro para {contexto_tempo}?
    2.  Qual é o padrão de ociosidade para {contexto_tempo}?
    3.  Qual a sua principal recomendação para um gestor de logística sobre alocação de equipe com base nesses dados específicos?
    
    Responda em um texto organizado e de linguagem clara. Não fale as perguntas. Não se apresente.
    """
    
    return generate_analysis_component(prompt)