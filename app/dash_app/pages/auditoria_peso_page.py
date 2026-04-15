from dash import dcc, html, callback, dash_table
from dash.dependencies import Input, Output
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from app.application.analytics import engine
from app.services.dashboard_summaries import summarize_auditoria
from app.services.management_insights import render_management_insight


def get_entidades_options():
    query = """
    SELECT DISTINCT fornecedor_cliente
    FROM registro
    WHERE fornecedor_cliente IS NOT NULL AND peso_nota_fiscal > 0
    ORDER BY fornecedor_cliente;
    """
    df = pd.read_sql(query, engine)
    options = [{"label": t, "value": t} for t in df["fornecedor_cliente"]]
    options.insert(0, {"label": "Todas as Entidades", "value": "todas"})
    return options


entidades_options = get_entidades_options()


layout = html.Div([
    dmc.Title("Auditoria de Pesagem: Balanca vs Nota Fiscal", order=2),
    dmc.Text("Compare o peso medido na balanca com o peso declarado na nota fiscal.", c="dimmed", size="sm"),
    dmc.Divider(variant="solid", my="md"),
    dmc.Alert("Identifique divergencias significativas entre o peso declarado e o peso aferido.", title="Controle de Qualidade", color="ifsc-green", variant="light", icon=DashIconify(icon="akar-icons:triangle-alert"), mb="md"),
    dmc.Card(
        children=[
            dmc.Grid(
                gutter="md",
                children=[
                    dmc.GridCol(dmc.Select(label="Filtrar por Empresa/Entidade", id="filtro-entidade-auditoria", data=entidades_options, value="todas", leftSection=DashIconify(icon="domain")), span={"base": 12, "md": 6}),
                    dmc.GridCol([dmc.Text(id="label-slider-auditoria", children="Limite de discrepancia (%): 5%", size="sm", fw=500, mb=5), dmc.Slider(id="filtro-discrepancia-auditoria", min=0, max=20, step=1, value=5, updatemode="drag", marks=[{"value": 0, "label": "0%"}, {"value": 5, "label": "5%"}, {"value": 10, "label": "10%"}, {"value": 20, "label": "20%"}], color="red")], span={"base": 12, "md": 6}),
                ],
            )
        ],
        withBorder=True, shadow="sm", radius="md", mb="md"
    ),
    dmc.Card(dcc.Markdown(id="resumo-auditoria"), withBorder=True, shadow="sm", radius="md", p="md", mb="md"),
    html.Div(id="insight-auditoria-gerencial"),
    dmc.Card(
        children=[
            dmc.ScrollArea(
                dash_table.DataTable(
                    id="tabela-auditoria",
                    page_size=15,
                    sort_action="native",
                    filter_action="native",
                    style_table={"minWidth": "100%"},
                    style_header={"backgroundColor": "#f8f9fa", "color": "#000", "fontWeight": "bold", "fontFamily": "sans-serif"},
                    style_data={"backgroundColor": "#fff", "color": "#000", "fontFamily": "sans-serif"},
                    style_cell={"border": "1px solid #dee2e6", "padding": "10px", "textAlign": "left"},
                ),
                offsetScrollbars=True,
                type="auto",
            )
        ],
        withBorder=True, shadow="sm", radius="md", mb="md"
    ),
])


@callback(
    [Output("tabela-auditoria", "data"), Output("tabela-auditoria", "columns"), Output("tabela-auditoria", "style_data_conditional"), Output("label-slider-auditoria", "children"), Output("resumo-auditoria", "children"), Output("insight-auditoria-gerencial", "children")],
    [Input("filtro-entidade-auditoria", "value"), Input("filtro-discrepancia-auditoria", "value")],
)
def update_audit_table(selected_entidade, min_discrepancia):
    query = """
    SELECT ticket, to_char(data_hora, 'YYYY-MM-DD HH24:MI') as data_hora, fornecedor_cliente, produto,
           peso_embalagem_liquido_corrigido, peso_nota_fiscal,
           (peso_embalagem_liquido_corrigido - peso_nota_fiscal) as diferenca_kg,
           ((peso_embalagem_liquido_corrigido - peso_nota_fiscal) / peso_nota_fiscal) * 100 as diferenca_percentual
    FROM registro
    WHERE peso_nota_fiscal > 0 AND peso_embalagem_liquido_corrigido > 0
    """
    params = {}
    entidade_label = selected_entidade if selected_entidade != "todas" else "todas as entidades"
    if selected_entidade != "todas":
        query += " AND fornecedor_cliente = %(entidade)s"
        params["entidade"] = selected_entidade
    query += " ORDER BY diferenca_percentual DESC;"
    df_audit = pd.read_sql(query, engine, params=params)
    df_audit["diferenca_kg"] = pd.to_numeric(df_audit["diferenca_kg"], errors="coerce").round(2)
    df_audit["diferenca_percentual"] = pd.to_numeric(df_audit["diferenca_percentual"], errors="coerce").round(2)
    df_filtered = df_audit[(df_audit["diferenca_percentual"] > min_discrepancia) | (df_audit["diferenca_percentual"] < -min_discrepancia)]
    styles = [
        {"if": {"column_id": "diferenca_percentual", "filter_query": f"{{diferenca_percentual}} > {min_discrepancia}"}, "backgroundColor": "#fa5252", "color": "white"},
        {"if": {"column_id": "diferenca_percentual", "filter_query": f"{{diferenca_percentual}} < -{min_discrepancia}"}, "backgroundColor": "#fa5252", "color": "white"},
    ]
    summary = summarize_auditoria(df_filtered, min_discrepancia, entidade_label)
    return df_filtered.to_dict("records"), [{"name": i, "id": i} for i in df_filtered.columns], styles, f"Limite de discrepancia (%): {min_discrepancia}%", summary, render_management_insight(summary, "a relacao entre peso aferido e nota fiscal ajuda a priorizar auditoria, verificar falhas documentais e identificar risco de inconsistencias sistemicas")
