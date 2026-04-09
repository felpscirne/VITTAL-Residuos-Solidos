from dash import dcc, html, callback, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify

# Service imports
from app.application.analytics import get_anos_options, get_registros_filtrados

anos_options_raw, ano_inicial = get_anos_options()
# Garantindo que as opções sejam string para o dmc.Select
anos_options = [{'label': str(opt['label']), 'value': str(opt['value'])} for opt in anos_options_raw]


layout = html.Div([
    dmc.Title('Visualizador de Registros', order=2),
    dmc.Text('Use os filtros para buscar nos registros brutos.', c="dimmed", size="sm"),
    dmc.Divider(variant="solid", my="md"),
    
    dmc.Card(
        children=[
            dmc.Grid(
                gutter="md",
                children=[
                    dmc.GridCol(
                        [
                            dmc.Select(
                                label='Selecione o Ano',
                                placeholder="Selecione um ano",
                                id='filtro-ano-tabela',
                                data=anos_options,
                                value=str(ano_inicial),
                                leftSection=DashIconify(icon="uil:calender")
                            )
                        ], span={"base": 12, "md": 3}
                    ),
                    dmc.GridCol(
                        [
                            dmc.NumberInput(
                                label='Mês (1-12)',
                                placeholder="Ex: 5",
                                id='filtro-mes-tabela', 
                                min=1, 
                                max=12,
                                leftSection=DashIconify(icon="uil:calendar-slash")
                            )
                        ], span={"base": 12, "md": 3}
                    ),
                    dmc.GridCol(
                        [
                            dmc.TextInput(
                                label='Ticket',
                                placeholder="Nº do Ticket",
                                id='filtro-ticket-tabela',
                                leftSection=DashIconify(icon="iot:ticket")
                            )
                        ], span={"base": 12, "md": 3}
                    ),
                    dmc.GridCol(
                        [
                            dmc.Button(
                            "Filtrar",
                            id='btn-filtrar-tabela',
                            n_clicks=0,
                            variant="filled",
                            color="blue",
                            leftSection=DashIconify(icon="fluent:search-24-regular"),
                            fullWidth=True
                        ),  
                        ], span={"base": 12, "md": 3}
                    )
                ]
            )
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        mb="md"
    ),

    dcc.Loading(
        dmc.Card(
            children=[
                dmc.ScrollArea(
                    dash_table.DataTable(
                        id='tabela-registros-brutos',
                        page_size=20,
                        sort_action='native',
                        filter_action='native',
                        style_table={'minWidth': '100%'},
                        style_header={
                            'backgroundColor': '#f8f9fa',
                            'fontWeight': 'bold',
                            'textAlign': 'left',
                            'fontFamily': 'sans-serif'
                        },
                        style_data={
                            'whiteSpace': 'normal',
                            'height': 'auto',
                            'fontFamily': 'sans-serif',
                            'fontSize': '14px'
                        },
                        style_cell={
                            'border': '1px solid #dee2e6',
                            'padding': '10px'
                        },
                    ), offsetScrollbars=True, type="auto"
                )
            ],
            withBorder=True,
            shadow="sm",
            radius="md",
            mb="md"
        )
    )
])

@callback(
    [Output('tabela-registros-brutos', 'data'),
     Output('tabela-registros-brutos', 'columns')],
    [Input('btn-filtrar-tabela', 'n_clicks')],
    [State('filtro-ano-tabela', 'value'),
     State('filtro-mes-tabela', 'value'),
     State('filtro-ticket-tabela', 'value')]
)
def update_table(n_clicks, ano, mes, ticket):
    # Remove initial check to allow loading on start
    # if n_clicks == 0: return [], []
    
    try:
        # Convertendo o ano de volta para int se necessario, dependendo de como o get_registros_filtrados espera.
        # Geralmente args de SQL sao strings ou ints, mas vamos garantir.
        ano_int = int(ano) if ano else None
        
        # dmc.TextInput retorna string. dmc.NumberInput retorna number (int/float) ou None.
        
        df = get_registros_filtrados(ano_int, mes, ticket)
        data_tabela = df.to_dict('records')
        cols_tabela = [{"name": i, "id": i} for i in df.columns]
        return data_tabela, cols_tabela
    except Exception as e:
        print(f"Erro ao buscar na tabela: {e}")
        return [], []
