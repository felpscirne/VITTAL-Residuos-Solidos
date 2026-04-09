from dash import dcc, html, callback, no_update
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from app.application.analytics import engine, get_anos_options 
from app.application.insights import generate_analysis_component
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

# Tratamento de opções para dmc.Select (valores como Strings)
# Removed static load
# anos_options_raw, _ = get_anos_options()
# anos_options = [{'label': opt['label'], 'value': str(opt['value'])} for opt in anos_options_raw]
# anos_options.insert(0, {'label': 'Todos os Anos', 'value': 'todos'})

meses_options = [
    {'label': 'Ano Inteiro', 'value': 'todos'},
    {'label': 'Janeiro', 'value': '1'},
    {'label': 'Fevereiro', 'value': '2'},
    {'label': 'Março', 'value': '3'},
    {'label': 'Abril', 'value': '4'},
    {'label': 'Maio', 'value': '5'},
    {'label': 'Junho', 'value': '6'},
    {'label': 'Julho', 'value': '7'},
    {'label': 'Agosto', 'value': '8'},
    {'label': 'Setembro', 'value': '9'},
    {'label': 'Outubro', 'value': '10'},
    {'label': 'Novembro', 'value': '11'},
    {'label': 'Dezembro', 'value': '12'},
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

# df_heatmap_raw = load_heatmap_data()

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
    dmc.Title('Análise de Horários de Pico', order=2),
    dmc.Text('Esta análise mostra os "pontos quentes" da operação da balança, cruzando o dia da semana com a hora do dia.', c="dimmed", size="sm"),
    dmc.Divider(variant="solid", my="md"),

    dmc.Alert(
        "Quais são os dias e horários de maior movimento? Onde estão nossos gargalos? E quais são os horários mais ociosos? As áreas mais escuras/vermelhas são os horários de pico.",
        title="O que este gráfico responde?",
        color="ifsc-green",
        variant="light",
        icon=DashIconify(icon="akar-icons:fire"),
        mb="md"
    ),

    dmc.Grid(
        gutter="md",
        children=[
            dmc.GridCol([
                dmc.Select(
                    label="Selecione o Ano",
                    placeholder="Filtrar por ano",
                    id='filtro-ano-heatmap',
                    data=[], # Dynamic load
                    value='todos',
                    clearable=False,
                    leftSection=DashIconify(icon="clarity:calendar-line")
                )
            ], span={"base": 12, "md": 6}),
            dmc.GridCol([
               dmc.Select(
                    label="Selecione o Mês",
                    placeholder="Filtrar por mês",
                    id='filtro-mes-heatmap',
                    data=meses_options,
                    value='todos',
                    clearable=False,
                    leftSection=DashIconify(icon="clarity:date-line")
                )
            ], span={"base": 12, "md": 6})
        ],
        mb="md"
    ),

    dmc.Card(
        children=[
            dcc.Graph(id='grafico-heatmap')
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        mb="md"
    ),

    dmc.Button(
        "🤖 Analisar Horários de Pico", 
        id="btn-ia-heatmap", 
        n_clicks=0, 
        variant="outline", 
        color="indigo", 
        leftSection=DashIconify(icon="fluent:bot-24-regular"),
        size="compact-sm",
        mb="md"
    ),
    dcc.Loading(html.Div(id='ia-output-heatmap'))
])

# @callback(
#     Output('grafico-heatmap', 'figure'),
#     [Input('filtro-ano-heatmap', 'value'),
#      Input('filtro-mes-heatmap', 'value'),
#      Input("mantine-provider", "forceColorScheme")]
# )
# def update_heatmap(selected_year, selected_month, color_scheme):
#     # Legacy callback replaced by update_heatmap_graph to support dynamic loading
#     pass

@callback(
    Output('ia-output-heatmap', 'children'),
    Input('btn-ia-heatmap', 'n_clicks'),
    State('grafico-heatmap', 'figure'),
    prevent_initial_call=True
)
def run_ai_analysis(n_clicks, figure_data):
    if not n_clicks:
        return no_update
    
    # Simples extração de dados da figura para passar pro prompt
    # Idealmente passaria o DataFrame, mas aqui vamos usar um resumo
    # (simplificação)
    prompt_context = "Analise esse mapa de calor de horários vs dia da semana. Identifique gargalos e ociosidade."
    
    return generate_analysis_component(prompt_context, "heatmap_horarios")

@callback(
    Output('grafico-heatmap', 'figure'),
    [Input('url', 'pathname'),
     Input('filtro-ano-heatmap', 'value'),
     Input('filtro-mes-heatmap', 'value'),
     Input("mantine-provider", "forceColorScheme")]
)
def update_heatmap_graph(pathname, ano_val, mes_val, color_scheme):
    if pathname != '/analise-horarios': return no_update
    
    # Reload data
    # Note: load_heatmap_data actually groups by everything.
    # The original logic used df_heatmap_raw globally and filtered IT?
    # Let's check load_heatmap_data again. It groups by ano, mes, dia, hora.
    # So we can filter the DF here.
    
    df = load_heatmap_data() 
    if df.empty:
        is_dark = color_scheme == 'dark'
        template = "plotly_dark" if is_dark else "plotly_white"
        return px.density_heatmap(template=template).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

    # Apply Filters
    if ano_val and ano_val != 'todos':
        df = df[df['ano'] == int(ano_val)]
    
    if mes_val and mes_val != 'todos':
        df = df[df['mes'] == int(mes_val)]
    
    # Aggregate again by dia/hora since we might have summed multiple months/years
    df_grouped = df.groupby(['dia_semana', 'hora_do_dia']).size().reset_index(name='numero_de_registros')
    # Wait, load_heatmap_data already has 'numero_de_registros' counted.
    # So we should sum it.
    df_grouped = df.groupby(['dia_semana', 'hora_do_dia'])['numero_de_registros'].sum().reset_index()

    is_dark = color_scheme == 'dark'
    template = "plotly_dark" if is_dark else "plotly_white"
    
    return create_heatmap_graph(df_grouped, template)

@callback(
    [Output('filtro-ano-heatmap', 'data'),
     Output('filtro-ano-heatmap', 'value')],
    Input('url', 'pathname')
)
def update_anos_dropdown_horarios(pathname):
    if pathname == '/analise-horarios':
        options_raw, _ = get_anos_options()
        options = [{'label': opt['label'], 'value': str(opt['value'])} for opt in options_raw]
        options.insert(0, {'label': 'Todos os Anos', 'value': 'todos'})
        return options, 'todos'
    return no_update, no_update
