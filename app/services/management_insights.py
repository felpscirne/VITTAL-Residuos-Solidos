import re
import unicodedata

from dash import dcc, html
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from flask_login import current_user


def user_can_view_management_insights():
    return getattr(current_user, "is_authenticated", False) and getattr(current_user, "role", None) in {"management", "superadmin"}


def _strip_summary_title(markdown_text):
    if not markdown_text:
        return ""
    return str(markdown_text).replace("### Resumo analítico\n", "", 1).replace("### Resumo analitico\n", "", 1).strip()


def _extract_bullets(markdown_text):
    lines = []
    for raw_line in str(markdown_text or "").splitlines():
        line = raw_line.strip()
        if line.startswith("- "):
            lines.append(line[2:].strip())
    return lines


def _normalize(text):
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    return normalized.lower()


def _infer_decision_guidance(markdown_text):
    text = _normalize(markdown_text)
    if any(term in text for term in ["frota", "viagem", "placa", "kg/viagem"]):
        return "Os dados sugerem revisar distribuição de rotas, aproveitamento dos veículos e equilíbrio entre frequência de viagens e carga transportada."
    if any(term in text for term in ["setor", "mix do setor", "setorial"]):
        return "A leitura ajuda a redistribuir equipe, frequência de atendimento e priorização operacional entre os setores com maior pressão ou maior peso médio."
    if any(term in text for term in ["empresa", "entidade", "fornecedor", "cliente"]):
        return "O resultado apoia negociação institucional, auditoria direcionada e planejamento sobre dependência de poucas entidades ou origens principais."
    if any(term in text for term in ["produto", "residuo", "mix"]):
        return "O gestor pode priorizar coleta, segregação e tratamento a partir dos tipos mais recorrentes ou mais concentrados no conjunto analisado."
    if any(term in text for term in ["hora", "dia", "heatmap", "pico operacional"]):
        return "A decisão mais útil aqui é ajustar escala, reforço de equipe e janela de atendimento conforme os horários e dias de maior concentração."
    if any(term in text for term in ["discrepancia", "nota fiscal", "auditoria", "ticket"]):
        return "Os achados ajudam a priorizar auditoria, revisar documentação e atuar primeiro nas ocorrências com maior risco de inconsistência."
    if any(term in text for term in ["balanco", "entrada", "saida", "candiota", "fluxo"]):
        return "A leitura orienta capacidade operacional, ritmo de escoamento e monitoramento de acúmulo temporário ao comparar entradas e saídas."
    if any(term in text for term in ["previsao", "previsão", "horizonte", "intervalo"]):
        return "A projeção apoia planejamento antecipado de capacidade, insumos e resposta operacional, sempre considerando a incerteza indicada pelo intervalo preditivo."
    return "A síntese destaca onde concentrar atenção gerencial, permitindo transformar sinais dos dados em priorização operacional e revisão de processo."


def _build_management_narrative(markdown_text):
    bullets = _extract_bullets(markdown_text)
    primary_signal = bullets[0] if bullets else "Os dados ainda não trouxeram um sinal suficientemente claro para destacar uma prioridade específica."
    attention_point = bullets[1] if len(bullets) > 1 else "Vale acompanhar a série ao longo do tempo para diferenciar variação natural de mudança real no processo."
    decision_guidance = _infer_decision_guidance(markdown_text)
    return primary_signal, attention_point, decision_guidance


def render_management_insight(markdown_text, relation_text=None):
    if not user_can_view_management_insights():
        return html.Div()

    summary_body = _strip_summary_title(markdown_text)
    primary_signal, attention_point, decision_guidance = _build_management_narrative(summary_body)
    content = (
        "### Apoio à decisão gerencial\n"
        f"- Sinal principal identificado: {primary_signal}\n"
        f"- Ponto que merece atenção: {attention_point}\n"
        f"- Como isso apoia a decisão: {decision_guidance}"
    ).strip()

    return dmc.Card(
        [
            dmc.Group(
                [
                    dmc.Text("Leitura gerencial dinâmica", fw=700),
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
