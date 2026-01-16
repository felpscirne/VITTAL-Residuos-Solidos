from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from app.services.data_repository import get_kpis_gerais, get_qtde_por_ano, get_top_produtos_geral

# --- Carregar dados UMA VEZ ---
kpi_data = get_kpis_gerais()
df_ano = get_qtde_por_ano()
df_produtos = get_top_produtos_geral()

def create_kpi_card(title, value, icon, color):
    return dmc.Card(
        children=[
            dmc.Group(
                [
                    dmc.Text(title, size="xs", c="dimmed", fw=500, style={"textTransform": "uppercase"}),
                    dmc.ThemeIcon(
                        DashIconify(icon=icon, width=20),
                        color=color,
                        variant="light",
                        size="lg",
                        radius="md"
                    )
                ],
                justify="space-between",
                mb="xs"
            ),
            dmc.Text(value, fw=700, size="xl")
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        p="md"
    )

# --- Layout da Página ---
layout = dmc.Container(
    [
        dmc.Title('Visão Geral do Dashboard', order=2, mb="xs"),
        dmc.Text('Resumo dos principais indicadores de pesagem.', c="dimmed", mb="lg"),
        
        dmc.Alert(
            children=[
                dmc.Title("Contexto dos Dados", order=5, mb="xs"),
                dmc.Text(
                    "Estes números dão contexto sobre o 'tamanho' da amostra (registros). "
                    "Os gráficos abaixo mostram a tendência de longo prazo e o principal tipo de resíduo coletado."
                )
            ],
            title="Informação",
            color="ifsc-green",
            icon=DashIconify(icon="radix-icons:info-circled"),
            mb="xl",
            variant="light"
        ),

        # KPIs
        dmc.SimpleGrid(
            cols={"base": 1, "sm": 3},
            spacing="md",
            mb="xl",
            children=[
                create_kpi_card("Total de Registros", kpi_data['total'], "radix-icons:stack", "ifsc-green"),
                create_kpi_card("Data de Início", kpi_data['inicio'], "radix-icons:calendar", "ifsc-green"),
                create_kpi_card("Data de Fim", kpi_data['fim'], "radix-icons:calendar", "ifsc-green"),
            ]
        ),
        
        dmc.Divider(mb="xl"),
        
        # Gráficos
        dmc.SimpleGrid(
            cols={"base": 1, "md": 2},
            spacing="md",
            children=[
                dmc.Card(
                    dcc.Graph(id='overview-grafico-ano'),
                    withBorder=True, shadow="sm", radius="md", p="md"
                ),
                dmc.Card(
                    dcc.Graph(id='overview-grafico-produtos'),
                    withBorder=True, shadow="sm", radius="md", p="md"
                ),
            ]
        )
    ],
    fluid=True,
    p=0
)

@callback(
    [Output('overview-grafico-ano', 'figure'),
     Output('overview-grafico-produtos', 'figure')],
    [Input("mantine-provider", "forceColorScheme")]
)
def update_overview_graphs(color_scheme):
    is_dark = color_scheme == 'dark'
    template_name = "plotly_dark" if is_dark else "plotly_white"
    
    fig_ano = px.bar(
        df_ano, 
        x='ano', y='qtde', 
        title="Total de Registros por Ano", 
        template=template_name 
    )
    fig_ano.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 40, "r": 20, "t": 40, "b": 30}
    )

    fig_produtos = px.pie(
        df_produtos, 
        names='produto', values='qtde', 
        title="Top 10 Produtos (Volume)",
        template=template_name 
    )
    fig_produtos.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 20, "r": 20, "t": 40, "b": 20}
    )

    return fig_ano, fig_produtos