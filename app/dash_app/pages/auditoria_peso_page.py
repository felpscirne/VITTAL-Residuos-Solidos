from dash import dcc, html, callback, dash_table
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from app.application.analytics import engine
from app.services.ai_analytics import get_audit_ai_analysis
from app.services.dashboard_summaries import summarize_auditoria
from app.services.management_insights import render_management_insight


def get_entidades_options():
    query = """
    SELECT DISTINCT fornecedor_cliente
    FROM registro
    WHERE fornecedor_cliente IS NOT NULL
      AND peso_nota_fiscal > 0
      AND UPPER(COALESCE(setor, '')) NOT LIKE 'ACERTO%%'
      AND UPPER(COALESCE(setor, '')) NOT LIKE 'CANDIOTA%%'
    ORDER BY fornecedor_cliente;
    """
    df = pd.read_sql(query, engine)
    options = [{"label": t, "value": t} for t in df["fornecedor_cliente"]]
    options.insert(0, {"label": "Todas as Entidades", "value": "todas"})
    return options


entidades_options = get_entidades_options()


layout = html.Div(
    [
        dmc.Title("Auditoria de pesagem: balança vs nota fiscal", order=2),
        dmc.Text("Compare o peso medido na balança com o peso declarado na nota fiscal.", c="dimmed", size="sm"),
        dmc.Divider(variant="solid", my="md"),
        dmc.Alert(
            "Identifique divergências significativas entre o peso declarado e o peso aferido.",
            title="Controle de qualidade",
            color="ifsc-green",
            variant="light",
            icon=DashIconify(icon="akar-icons:triangle-alert"),
            mb="md",
        ),
        dmc.Card(
            children=[
                dmc.Grid(
                    gutter="md",
                    children=[
                        dmc.GridCol(
                            dmc.Select(
                                label="Filtrar por empresa/entidade",
                                id="filtro-entidade-auditoria",
                                data=entidades_options,
                                value="todas",
                                leftSection=DashIconify(icon="domain"),
                            ),
                            span={"base": 12, "md": 6},
                        ),
                        dmc.GridCol(
                            [
                                dmc.Text(
                                    id="label-slider-auditoria",
                                    children="Limite de discrepância (%): 5%",
                                    size="sm",
                                    fw=500,
                                    mb=5,
                                ),
                                dmc.Slider(
                                    id="filtro-discrepancia-auditoria",
                                    min=0,
                                    max=20,
                                    step=1,
                                    value=5,
                                    updatemode="drag",
                                    marks=[
                                        {"value": 0, "label": "0%"},
                                        {"value": 5, "label": "5%"},
                                        {"value": 10, "label": "10%"},
                                        {"value": 20, "label": "20%"},
                                    ],
                                    color="red",
                                ),
                            ],
                            span={"base": 12, "md": 6},
                        ),
                    ],
                )
            ],
            withBorder=True,
            shadow="sm",
            radius="md",
            mb="md",
        ),
        dmc.Card(dcc.Markdown(id="resumo-auditoria"), withBorder=True, shadow="sm", radius="md", p="md", mb="md"),
        html.Div(id="insight-auditoria-gerencial"),
        dmc.SimpleGrid(
            cols={"base": 1, "xl": 2},
            spacing="md",
            mb="md",
            children=[
                dmc.Card([dcc.Graph(id="grafico-ia-auditoria")], withBorder=True, shadow="sm", radius="md", p="md"),
                dmc.Card(dcc.Markdown(id="resumo-ia-auditoria"), withBorder=True, shadow="sm", radius="md", p="md"),
            ],
        ),
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
            withBorder=True,
            shadow="sm",
            radius="md",
            mb="md",
        ),
    ]
)


@callback(
    [
        Output("tabela-auditoria", "data"),
        Output("tabela-auditoria", "columns"),
        Output("tabela-auditoria", "style_data_conditional"),
        Output("label-slider-auditoria", "children"),
        Output("resumo-auditoria", "children"),
        Output("insight-auditoria-gerencial", "children"),
        Output("grafico-ia-auditoria", "figure"),
        Output("resumo-ia-auditoria", "children"),
    ],
    [Input("filtro-entidade-auditoria", "value"), Input("filtro-discrepancia-auditoria", "value")],
)
def update_audit_table(selected_entidade, min_discrepancia):
    query = """
    SELECT ticket, to_char(data_hora, 'YYYY-MM-DD HH24:MI') as data_hora, fornecedor_cliente, produto,
           peso_embalagem_liquido_corrigido, peso_nota_fiscal,
           (peso_embalagem_liquido_corrigido - peso_nota_fiscal) as diferenca_kg,
           ((peso_embalagem_liquido_corrigido - peso_nota_fiscal) / peso_nota_fiscal) * 100 as diferenca_percentual
    FROM registro
    WHERE peso_nota_fiscal > 0
      AND peso_embalagem_liquido_corrigido > 0
      AND UPPER(COALESCE(setor, '')) NOT LIKE 'ACERTO%%'
      AND UPPER(COALESCE(setor, '')) NOT LIKE 'CANDIOTA%%'
    """
    params = {}
    entidade_label = selected_entidade if selected_entidade != "todas" else "todas as entidades"
    if selected_entidade != "todas":
        query += " AND fornecedor_cliente = %(entidade)s"
        params["entidade"] = selected_entidade
    query += " ORDER BY ABS(((peso_embalagem_liquido_corrigido - peso_nota_fiscal) / peso_nota_fiscal) * 100) DESC;"

    df_audit = pd.read_sql(query, engine, params=params)
    if df_audit.empty:
        empty_fig = px.bar(title="IA aplicada à auditoria")
        empty_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        empty_fig.add_annotation(
            text="A base atual não possui registros com peso de nota fiscal preenchido para comparação.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        summary = (
            "### Resumo analítico\n"
            "- A base atual não possui registros com `peso_nota_fiscal` preenchido e maior que zero.\n"
            "- Sem esse campo, a auditoria balança vs nota fiscal não pode ser calculada de forma fiel.\n"
            "- Próximo passo: importar registros que tragam peso de nota fiscal para ativar esta análise."
        )
        return (
            [],
            [
                {"name": "ticket", "id": "ticket"},
                {"name": "data_hora", "id": "data_hora"},
                {"name": "fornecedor_cliente", "id": "fornecedor_cliente"},
                {"name": "produto", "id": "produto"},
                {"name": "peso_embalagem_liquido_corrigido", "id": "peso_embalagem_liquido_corrigido"},
                {"name": "peso_nota_fiscal", "id": "peso_nota_fiscal"},
                {"name": "diferenca_kg", "id": "diferenca_kg"},
                {"name": "diferenca_percentual", "id": "diferenca_percentual"},
            ],
            [],
            f"Limite de discrepância (%): {min_discrepancia}%",
            summary,
            render_management_insight(summary),
            empty_fig,
            "### IA aplicada à auditoria\n- A camada de IA depende da existência de peso de nota fiscal para comparar o valor aferido com o declarado.",
        )
    df_audit["diferenca_kg"] = pd.to_numeric(df_audit["diferenca_kg"], errors="coerce").round(2)
    df_audit["diferenca_percentual"] = pd.to_numeric(df_audit["diferenca_percentual"], errors="coerce").round(2)
    df_filtered = df_audit[
        (df_audit["diferenca_percentual"] > min_discrepancia) | (df_audit["diferenca_percentual"] < -min_discrepancia)
    ].copy()

    ai_result = get_audit_ai_analysis(selected_entidade, float(min_discrepancia))
    ai_df = ai_result.get("data", pd.DataFrame())
    display_note = ""

    if not ai_df.empty:
        ai_filtered = ai_df[
            (pd.to_numeric(ai_df["diferenca_percentual"], errors="coerce") > min_discrepancia)
            | (pd.to_numeric(ai_df["diferenca_percentual"], errors="coerce") < -min_discrepancia)
        ].copy()
        if ai_filtered.empty:
            df_filtered = ai_df.head(20).copy()
            display_note = f"\n- Como não houve registros acima de **{min_discrepancia}%**, a tabela mostra os casos mais relevantes segundo a IA."
        else:
            df_filtered = ai_filtered.copy()

        df_filtered["probabilidade_risco_operacional"] = pd.to_numeric(
            df_filtered["probabilidade_risco_operacional"], errors="coerce"
        ).round(1)

        chart_df = df_filtered.head(15).copy()
        chart_df["ticket"] = chart_df["ticket"].astype(str)
        fig_ai = px.bar(
            chart_df.sort_values("probabilidade_risco_operacional", ascending=True),
            x="probabilidade_risco_operacional",
            y="ticket",
            color="classificacao_anomalia_ia",
            orientation="h",
            title="Prioridade de auditoria por IA",
            labels={
                "probabilidade_risco_operacional": "Probabilidade de risco (%)",
                "ticket": "Ticket",
                "classificacao_anomalia_ia": "Anomalia por IA",
            },
        )
        fig_ai.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin={"l": 20, "r": 20, "t": 50, "b": 20},
        )
        ai_summary = ai_result.get("summary", "")
    else:
        if df_filtered.empty and not df_audit.empty:
            df_filtered = (
                df_audit.assign(diferenca_percentual_abs=df_audit["diferenca_percentual"].abs())
                .sort_values("diferenca_percentual_abs", ascending=False)
                .drop(columns=["diferenca_percentual_abs"])
                .head(20)
            )
            display_note = f"\n- Como não houve registros acima de **{min_discrepancia}%**, a tabela mostra as maiores divergências observadas."

        fig_ai = px.bar(title="IA aplicada à auditoria")
        fig_ai.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        fig_ai.add_annotation(
            text=ai_result.get("message", "Ainda não há dados suficientes para a análise de IA."),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        ai_summary = ai_result.get("summary", ai_result.get("message", ""))

    styles = [
        {"if": {"column_id": "diferenca_percentual", "filter_query": f"{{diferenca_percentual}} > {min_discrepancia}"}, "backgroundColor": "#fa5252", "color": "white"},
        {"if": {"column_id": "diferenca_percentual", "filter_query": f"{{diferenca_percentual}} < -{min_discrepancia}"}, "backgroundColor": "#fa5252", "color": "white"},
        {"if": {"column_id": "classificacao_risco_operacional", "filter_query": "{classificacao_risco_operacional} = 'Muito alto'"}, "backgroundColor": "#c92a2a", "color": "white"},
        {"if": {"column_id": "classificacao_anomalia_ia", "filter_query": "{classificacao_anomalia_ia} = 'Muito anômalo'"}, "backgroundColor": "#862e9c", "color": "white"},
    ]

    summary = summarize_auditoria(df_filtered, min_discrepancia, entidade_label)
    if display_note:
        summary += display_note

    return (
        df_filtered.to_dict("records"),
        [{"name": i, "id": i} for i in df_filtered.columns],
        styles,
        f"Limite de discrepância (%): {min_discrepancia}%",
        summary,
        render_management_insight(summary),
        fig_ai,
        ai_summary,
    )
