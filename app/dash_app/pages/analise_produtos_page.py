from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.express as px
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from app.application.analytics import (
    get_produtos_resumo,
    get_produtos_options,
    get_setores_options,
    get_fornecedores_por_produto,
    get_produtos_por_setor,
)
from app.services.dashboard_summaries import (
    summarize_produtos_ranking,
    summarize_produto_fornecedores,
    summarize_setor_produtos,
)
from app.services.management_insights import render_management_insight


df_produtos = get_produtos_resumo()
produtos_options = get_produtos_options()
setores_options = get_setores_options()


def fig_contagem_produtos(df, template):
    num_itens = len(df.index)
    dynamic_height = max(400, num_itens * 20)
    fig = px.bar(
        df,
        x="quantidade",
        y="produto",
        orientation="h",
        title="Volume (N de Registros) por Produto",
        template=template,
    )
    fig.update_layout(
        yaxis={"autorange": "reversed"},
        height=dynamic_height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


layout = dmc.Container([
    dmc.Title("Analise de Produtos", order=2),
    dmc.Text("Ranking geral dos tipos de residuos e analises cruzadas por fornecedor e setor.", c="dimmed", mb="lg"),
    dmc.Divider(mb="lg"),
    dmc.Title("Visao Geral: Ranking de Produtos", order=3, mb="md"),
    dmc.Alert(
        children=[
            dmc.Title("Contexto", order=5),
            dmc.Text("Identifique os residuos mais comuns e os mais raros para priorizar a gestao."),
        ],
        title="O que este grafico responde?",
        color="ifsc-green",
        variant="light",
        mb="md",
        icon=DashIconify(icon="radix-icons:question-mark-circled"),
    ),
    dmc.Card(dcc.Graph(id="grafico-contagem-produtos"), withBorder=True, shadow="sm", radius="md", p="md", mb="md"),
    dmc.Card(dcc.Markdown(id="resumo-produtos"), withBorder=True, shadow="sm", radius="md", p="md", mb="xl"),
    html.Div(id="insight-produtos-gerencial"),
    dmc.Title("Drill-Down: Fornecedores por Produto", order=3, mb="md"),
    dmc.Alert("Ao selecionar um produto, veja quem movimenta ele.", color="ifsc-green", variant="light", mb="md"),
    dmc.Grid(
        children=[
            dmc.GridCol(
                dmc.Select(
                    label="Selecione um Produto",
                    placeholder="Escolha um produto...",
                    id="filtro-produto-para-fornecedor",
                    data=produtos_options,
                    value=produtos_options[0]["value"] if produtos_options else None,
                ),
                span=6,
            )
        ],
        mb="md",
    ),
    dmc.Card(dcc.Graph(id="grafico-produto-fornecedores"), withBorder=True, shadow="sm", radius="md", p="md", mb="md"),
    dmc.Card(dcc.Markdown(id="resumo-produto-fornecedores"), withBorder=True, shadow="sm", radius="md", p="md", mb="xl"),
    html.Div(id="insight-produto-fornecedores-gerencial"),
    dmc.Title("Drill-Down: Produtos por Setor", order=3, mb="md"),
    dmc.Alert("Selecione um setor para ver o que e gerado la.", color="gray", variant="light", mb="md"),
    dmc.Grid(
        children=[
            dmc.GridCol(
                dmc.Select(
                    label="Selecione um Setor",
                    placeholder="Escolha um setor...",
                    id="filtro-setor-para-produto",
                    data=setores_options,
                    value=setores_options[0]["value"] if setores_options else None,
                ),
                span=6,
            )
        ],
        mb="md",
    ),
    dmc.Card(dcc.Graph(id="grafico-setor-produtos"), withBorder=True, shadow="sm", radius="md", p="md", mb="md"),
    dmc.Card(dcc.Markdown(id="resumo-setor-produtos"), withBorder=True, shadow="sm", radius="md", p="md"),
    html.Div(id="insight-setor-produtos-gerencial"),
], fluid=True, p=0)


@callback(
    [Output("grafico-contagem-produtos", "figure"), Output("resumo-produtos", "children"), Output("insight-produtos-gerencial", "children")],
    [Input("mantine-provider", "forceColorScheme")],
)
def update_product_graph_theme(color_scheme):
    template = "plotly_dark" if color_scheme == "dark" else "plotly_white"
    fig = fig_contagem_produtos(df_produtos, template)
    summary = summarize_produtos_ranking(df_produtos.head(10))
    return fig, summary, render_management_insight(summary, "o ranking mostra concentracao do mix de residuos e ajuda a decidir onde priorizar coleta, triagem e tratamento diferenciado")


@callback(
    [Output("grafico-produto-fornecedores", "figure"), Output("resumo-produto-fornecedores", "children"), Output("insight-produto-fornecedores-gerencial", "children")],
    [Input("filtro-produto-para-fornecedor", "value"), Input("mantine-provider", "forceColorScheme")],
)
def update_prod_forn_graph(selected_product, color_scheme):
    template = "plotly_dark" if color_scheme == "dark" else "plotly_white"
    df_drilldown = get_fornecedores_por_produto(selected_product, limit=None)
    fig = px.bar(
        df_drilldown,
        x="quantidade",
        y="fornecedor_cliente",
        orientation="h",
        title=f"Fornecedores que movimentaram: {selected_product}",
        template=template,
    )
    fig.update_layout(yaxis={"autorange": "reversed"}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    summary = summarize_produto_fornecedores(df_drilldown, selected_product)
    return fig, summary, render_management_insight(summary, f"a relacao entre produto e fornecedor mostra dependencia operacional, concentracao de origem e oportunidades de auditoria direcionada para {selected_product}")


@callback(
    [Output("grafico-setor-produtos", "figure"), Output("resumo-setor-produtos", "children"), Output("insight-setor-produtos-gerencial", "children")],
    [Input("filtro-setor-para-produto", "value"), Input("mantine-provider", "forceColorScheme")],
)
def update_setor_prod_graph(selected_setor, color_scheme):
    template = "plotly_dark" if color_scheme == "dark" else "plotly_white"
    df_drilldown = get_produtos_por_setor(selected_setor, limit=None)
    fig = px.bar(
        df_drilldown,
        x="quantidade",
        y="produto",
        orientation="h",
        title=f"Produtos encontrados no Setor: {selected_setor}",
        template=template,
    )
    fig.update_layout(yaxis={"autorange": "reversed"}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    summary = summarize_setor_produtos(df_drilldown, selected_setor)
    return fig, summary, render_management_insight(summary, f"a composicao de produtos do setor {selected_setor} ajuda a ajustar rota, frequencia de atendimento e necessidade de segregacao operacional")
