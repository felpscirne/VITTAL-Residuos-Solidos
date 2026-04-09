import dash_bootstrap_components as dbc
from dash import dcc


def generate_analysis_component(prompt):
    message = (
        "### Modulo em transicao\n"
        "- A integracao com Gemini foi descontinuada neste projeto.\n"
        "- O dashboard esta sendo migrado para analises baseadas em metricas e previsao temporal com Prophet.\n"
        "- Esta secao ainda nao foi convertida para o novo formato.\n\n"
        "Trecho de contexto recebido:\n\n"
        f"```text\n{prompt[:1200]}\n```"
    )
    return dbc.Card(dbc.CardBody(dcc.Markdown(message)), className="mt-3")
