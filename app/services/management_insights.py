from dash import dcc, html
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from flask_login import current_user


def user_can_view_management_insights():
    return getattr(current_user, "is_authenticated", False) and getattr(current_user, "role", None) in {"gestao", "superadmin"}


def _strip_summary_title(markdown_text):
    if not markdown_text:
        return ""
    return str(markdown_text).replace("### Resumo analitico\n", "", 1).strip()


def render_management_insight(markdown_text, relation_text):
    if not user_can_view_management_insights():
        return html.Div()

    summary_body = _strip_summary_title(markdown_text)
    content = (
        "### Apoio a decisao gerencial\n"
        f"- Relacao principal observada: {relation_text}\n"
        f"{summary_body}"
    ).strip()

    return dmc.Card(
        [
            dmc.Group(
                [
                    dmc.Text("Leitura Gerencial Dinamica", fw=700),
                    dmc.ThemeIcon(
                        DashIconify(icon="radix-icons:activity-log", width=18),
                        color="ifsc-green",
                        variant="light",
                        size="lg",
                        radius="md",
                    ),
                ],
                justify="space-between",
                mb="sm",
            ),
            dcc.Markdown(content),
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        p="md",
        mb="md",
    )
