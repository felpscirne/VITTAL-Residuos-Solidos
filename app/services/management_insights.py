import unicodedata

from dash import dcc, html
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from flask_login import current_user


def user_can_view_management_insights():
    return getattr(current_user, "is_authenticated", False) and getattr(current_user, "role", None) == "management"


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


def _infer_domain(markdown_text):
    text = _normalize(markdown_text)
    if any(term in text for term in ["frota", "viagem", "placa", "kg/viagem"]):
        return "frota"
    if any(term in text for term in ["setor", "setorial"]):
        return "setor"
    if any(term in text for term in ["empresa", "entidade", "fornecedor", "cliente"]):
        return "empresa"
    if any(term in text for term in ["produto", "residuo", "mix"]):
        return "produto"
    if any(term in text for term in ["discrepancia", "nota fiscal", "auditoria", "ticket"]):
        return "auditoria"
    if any(term in text for term in ["hora", "heatmap", "pico operacional", " dia "]):
        return "horario"
    if any(term in text for term in ["balanco", "entrada", "saida", "candiota", "fluxo"]):
        return "fluxo"
    if any(term in text for term in ["previsao", "horizonte", "intervalo"]):
        return "previsao"
    return "geral"


def _domain_messages(domain):
    mapping = {
        "frota": (
            "Priorizar revisão da alocação de veículos e das rotas com menor aproveitamento.",
            "Manter o padrão atual pode ampliar custo operacional por viagem e gerar ociosidade de parte da frota.",
            "Comparar capacidade transportada, frequência de uso e necessidade de redistribuição logística.",
        ),
        "setor": (
            "Redefinir prioridade operacional entre setores com maior pressão de volume e maior carga média.",
            "Se a diferença entre setores não for tratada, a operação tende a ficar desequilibrada em equipe e atendimento.",
            "Usar o perfil setorial para ajustar frequência, capacidade e ordem de atendimento.",
        ),
        "empresa": (
            "Concentrar atenção gerencial nas empresas com maior participação ou comportamento mais sensível.",
            "Dependência excessiva de poucas entidades pode ampliar risco operacional e institucional.",
            "Acompanhar concentração, regularidade e possíveis desvios por empresa para orientar negociação e auditoria.",
        ),
        "produto": (
            "Priorizar os resíduos mais recorrentes para organizar coleta, segregação e tratamento.",
            "Sem essa diferenciação, produtos dominantes podem continuar pressionando a operação sem resposta proporcional.",
            "Relacionar frequência, peso e origem dos materiais para direcionar capacidade e tratamento especializado.",
        ),
        "horario": (
            "Ajustar escala e janela de atendimento nos horários com maior densidade operacional.",
            "Ignorar os picos observados tende a manter filas, sobrecarga da balança e perda de fluidez.",
            "Distribuir equipe e apoio operacional conforme os dias e horas de maior pressão.",
        ),
        "auditoria": (
            "Auditar primeiro os registros com maior sinal de risco ou anomalia.",
            "Sem resposta rápida, divergências recorrentes podem permanecer invisíveis no fluxo operacional.",
            "Cruzar discrepância, recorrência e entidade responsável para priorizar investigação.",
        ),
        "fluxo": (
            "Monitorar o equilíbrio entre entrada e saída para evitar acúmulo ou descompasso de escoamento.",
            "Desequilíbrios persistentes podem indicar pressão operacional, retenção de material ou limitação de destino.",
            "Comparar balanço, participação setorial e ritmo de saída para orientar capacidade e programação.",
        ),
        "previsao": (
            "Antecipar ajustes de capacidade, equipe e resposta operacional antes do horizonte projetado.",
            "Se a tendência prevista se confirmar sem reação, a pressão sobre a operação pode crescer rapidamente.",
            "Usar tendência, erro retrospectivo e intervalo preditivo como apoio ao planejamento, não como valor absoluto.",
        ),
        "geral": (
            "Transformar o principal sinal observado em prioridade operacional concreta.",
            "Sem atuação direcionada, a leitura tende a virar apenas monitoramento passivo.",
            "Ler os dados como apoio à priorização, definição de foco e revisão de processo.",
        ),
    }
    return mapping[domain]


def render_management_insight(markdown_text, relation_text=None):
    if not user_can_view_management_insights():
        return html.Div()

    summary_body = _strip_summary_title(markdown_text)
    bullets = _extract_bullets(summary_body)
    domain = _infer_domain(summary_body)
    acao, risco, leitura = _domain_messages(domain)

    principal = bullets[0] if bullets else "Os dados ainda não trouxeram um sinal suficientemente claro para destacar uma prioridade específica."
    metric_reference = bullets[1] if len(bullets) > 1 else "Acompanhar o comportamento ao longo do tempo ajuda a diferenciar variação natural de mudança real."

    content = (
        "### Apoio à decisão gerencial\n"
        f"- O que merece ação agora: {acao}\n"
        f"- Risco de manter o cenário atual: {risco}\n"
        f"- Evidência que sustenta a decisão: {principal}\n"
        f"- Leitura complementar para gestão: {metric_reference}\n"
        f"- Como usar este achado: {leitura}"
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
