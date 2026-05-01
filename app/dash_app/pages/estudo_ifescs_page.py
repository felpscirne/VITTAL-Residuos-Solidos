from dash import callback, dcc, html
from dash.dependencies import Input, Output
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import plotly.express as px

from app.application.analytics import (
    get_kpis_gerais,
    get_qtde_por_ano,
    get_top_produtos_geral,
    get_volume_diario,
)
from app.services.temporal_charts import build_temporal_line_figure


def _create_highlight_card(title, value, icon, color):
    return dmc.Card(
        [
            dmc.Group(
                [
                    dmc.Text(title, size="xs", c="dimmed", fw=500, style={"textTransform": "uppercase"}),
                    dmc.ThemeIcon(
                        DashIconify(icon=icon, width=20),
                        color=color,
                        variant="light",
                        size="lg",
                        radius="md",
                    ),
                ],
                justify="space-between",
                mb="xs",
            ),
            dmc.Text(value, fw=700, size="xl"),
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        p="md",
    )


def _format_kg(value):
    return f"{float(value):,.0f} kg".replace(",", ".")


def _build_model_questions_markdown(df_volume, df_produtos, kpis):
    if df_volume.empty:
        return (
            "### Modelo de Melhoria\n"
            "- O que queremos alcançar? Organizar o acompanhamento do processo.\n"
            "- Como saber se houve melhoria? Monitorando indicadores periódicos.\n"
            "- Que mudança pode resultar em melhoria? Padronização de coleta e registro."
        )

    media_periodica = float(df_volume["y"].mean())
    pico_row = df_volume.loc[df_volume["y"].idxmax()]
    pico_periodo = pico_row["ds"].strftime("%d/%m/%Y")
    pico_valor = _format_kg(pico_row["y"])
    produto_lider = "Não identificado"
    if not df_produtos.empty:
        produto_lider = str(df_produtos.iloc[0]["produto"])

    return (
        "### Modelo de Melhoria aplicado ao IFEsCS\n"
        f"- O que queremos alcançar? Reduzir sobrecargas operacionais em dias acima da média histórica de **{_format_kg(media_periodica)}**.\n"
        f"- Como saber se houve melhoria? Comparando o comportamento atual com o pico recente de **{pico_valor}** registrado em **{pico_periodo}**, observando tendência, distribuição dos dados e estabilidade do processo.\n"
        f"- Que mudança pode resultar em melhoria? Reorganizar a operação com foco nos fluxos ligados ao item de maior recorrência, hoje identificado como **{produto_lider}**, e acompanhar o efeito dessa ação ao longo do tempo.\n"
        f"- Leitura IFEsCS: os dados cobrem o período entre **{kpis['inicio']}** e **{kpis['fim']}**, servindo como base para aprendizagem estatística aplicada e apoio à decisão."
    )


def _build_pdsa_markdown(df_volume, df_produtos):
    if df_volume.empty:
        return (
            "### Ciclo PDSA\n"
            "- Plan: definir um objetivo de melhoria.\n"
            "- Do: aplicar uma mudança em pequena escala.\n"
            "- Study: comparar os indicadores antes e depois.\n"
            "- Act: padronizar a mudança ou ajustar a estratégia."
        )

    media_periodica = float(df_volume["y"].mean())
    minimo = float(df_volume["y"].min())
    maximo = float(df_volume["y"].max())
    amplitude = maximo - minimo
    produto_lider = "Não identificado"
    if not df_produtos.empty:
        produto_lider = str(df_produtos.iloc[0]["produto"])

    return (
        "### Ciclo PDSA com leitura orientada por dados\n"
        f"- **Plan**: formular a meta de reduzir a amplitude operacional atual de **{_format_kg(amplitude)}** entre os períodos observados.\n"
        f"- **Do**: testar uma mudança localizada, como reorganização de rotina, reforço de equipe ou ação focada no fluxo de **{produto_lider}**.\n"
        f"- **Study**: verificar se a média periódica permanece abaixo ou próxima de **{_format_kg(media_periodica)}** com menor variação entre dias.\n"
        f"- **Act**: institucionalizar a mudança quando os indicadores mostrarem ganho, ou revisar a hipótese quando não houver melhora mensurável.\n"
        "- **Método IFEsCS**: o estudo parte de dados reais organizados, articulando ensino, pesquisa e extensão para gerar leitura estatística contextualizada."
    )


def _build_cause_effect_markdown(df_volume, df_produtos):
    if df_volume.empty:
        return (
            "### Causa e efeito\n"
            "- Um indicador isolado não explica o processo.\n"
            "- A leitura de causa e efeito exige observar contexto, sequência temporal e variação.\n"
            "- No IFEsCS, os dados devem apoiar perguntas, não apenas respostas prontas.\n"
            "- A prioridade é compreender o sistema antes de culpar pessoas ou eventos isolados."
        )

    pico = df_volume.loc[df_volume["y"].idxmax()]
    vale = df_volume.loc[df_volume["y"].idxmin()]
    produto_lider = "Não identificado"
    if not df_produtos.empty:
        produto_lider = str(df_produtos.iloc[0]["produto"])

    return (
        "### Leitura de causa e efeito\n"
        f"- O pico de **{_format_kg(pico['y'])}** em **{pico['ds'].strftime('%d/%m/%Y')}** não deve ser interpretado como causa por si só; ele é um sinal para investigação.\n"
        f"- Da mesma forma, o menor valor observado, **{_format_kg(vale['y'])}** em **{vale['ds'].strftime('%d/%m/%Y')}**, não prova melhora estrutural sem análise do processo.\n"
        f"- O papel do gestor é relacionar os sinais dos dados com hipóteses concretas, como alterações de rotina, sazonalidade, alocação de equipe ou concentração do fluxo em **{produto_lider}**.\n"
        "- No pensamento estatístico defendido pelo IFEsCS, dados ajudam a testar explicações plausíveis e a diferenciar percepção isolada de comportamento sistêmico.\n"
        "- Em termos didáticos, causa e efeito exigem sequência temporal, conhecimento do processo e comparação entre períodos, e não apenas uma coincidência visual no gráfico.\n"
        "- Essa leitura dialoga com Deming ao lembrar que um sistema gera resultados, e que agir sem entender a fonte da variação costuma produzir correções superficiais."
    )


def _build_variation_markdown(df_volume):
    if df_volume.empty:
        return (
            "### Variação, erro e média\n"
            "- A média resume o processo, mas não mostra sua instabilidade.\n"
            "- A variação entre períodos é essencial para compreender risco e previsibilidade.\n"
            "- O erro deve ser acompanhado continuamente.\n"
            "- Um processo pode ter média aceitável e ainda assim ser instável."
        )

    media = float(df_volume["y"].mean())
    desvio = float(df_volume["y"].std()) if len(df_volume) > 1 else 0.0
    amplitude = float(df_volume["y"].max() - df_volume["y"].min())
    coef_var = (desvio / media * 100) if media else 0.0

    return (
        "### Por que a média sozinha não basta\n"
        f"- A média observada é **{_format_kg(media)}**, mas a leitura do processo fica incompleta sem a variabilidade associada.\n"
        f"- O desvio padrão atual é **{_format_kg(desvio)}**, com amplitude total de **{_format_kg(amplitude)}** entre o menor e o maior período.\n"
        f"- O coeficiente de variação aproximado é **{coef_var:.2f}%**, mostrando quanto o processo oscila em relação ao centro da série.\n"
        "- Em melhoria de processos, acompanhar erro, dispersão e estabilidade costuma revelar mais do que observar apenas a média, pois são esses sinais que indicam previsibilidade, risco operacional e necessidade de intervenção.\n"
        "- A média descreve o centro do comportamento; o erro mostra o quanto a previsão ou a meta falham; e a variância mostra o quão confiável ou instável é o processo ao longo do tempo.\n"
        "- Em linguagem de gestão, um processo com média aceitável e alta variação segue sendo um processo arriscado, porque ele não entrega regularidade.\n"
        "- Box reforça esse ponto ao aproximar estatística de experimentação e aprendizagem: melhorar não é apenas deslocar a média, mas entender como reduzir a variação indesejada e aprender com o erro."
    )


def _build_chart_reading_markdown(df_volume, df_produtos):
    if df_volume.empty:
        return (
            "### Como ler os gráficos\n"
            "- Observe a distribuição temporal dos dados.\n"
            "- Identifique pontos de maior concentração.\n"
            "- Compare variações antes de formular hipóteses de melhoria."
        )

    ultimo_periodo = df_volume["ds"].max().strftime("%d/%m/%Y")
    primeiro_periodo = df_volume["ds"].min().strftime("%d/%m/%Y")
    variacao = float(df_volume["y"].max() - df_volume["y"].min())
    lider = "Não identificado"
    if not df_produtos.empty:
        lider = str(df_produtos.iloc[0]["produto"])

    return (
        "### Como interpretar esta pagina\n"
        f"- O gráfico de série mostra o comportamento do processo entre **{primeiro_periodo}** e **{ultimo_periodo}**.\n"
        f"- A amplitude entre o menor e o maior valor observado é de **{_format_kg(variacao)}**, o que ajuda a discutir estabilidade e variabilidade.\n"
        f"- O gráfico de categorias destaca quais itens concentram mais registros, com destaque atual para **{lider}**.\n"
        "- A leitura recomendada no IFEsCS parte da observação dos dados, passa pela formulação de hipóteses e chega a uma ação mensurável de melhoria."
    )


def _build_readings_markdown():
    return (
        "### Leituras fundamentais\n"
        "- **Base central do IFEsCS - Deming**: [*A nova economia para a indústria, o governo e a educação*](https://books.google.com/books/about/A_nova_economia_para_a_ind%C3%BAstria_o_gove.html?id=nZtYQCbqZO8C). Referência central para sistema, variação, previsibilidade, aprendizagem e responsabilidade gerencial.\n"
        "- **Base central do IFEsCS - Langley e IHI**: [Model for Improvement em português](https://www.ihi.org/pt-br/library/model-for-improvement). Sintetiza as três perguntas do Modelo de Melhoria e o uso do ciclo PDSA.\n"
        "- **Ferramenta em português**: [Planilha PDSA em português](https://www.ihi.org/pt-br/resources/tools/plan-do-study-act-pdsa-worksheet). Material prático para documentar testes de mudança e aprendizagem em ciclos curtos.\n"
        "- **Mediação e aprendizagem em português**: [Estabelecendo Medidas - IHI](https://www.ihi.org/index.php/pt-br/library/model-for-improvement/establishing-measures). Fonte importante para sustentar que medir melhoria não é apenas calcular média, mas acompanhar variação, tendência e aprendizagem ao longo do tempo.\n"
        "- **Apoio metodológico em estatística - Box, Hunter e Hunter**: [*Statistics for Experimenters*](https://www.wiley-vch.de/en/areas-interest/mathematics-statistics/statistics-for-experimenters-978-0-471-71813-0). Referência importante para erro, variação, experimentação e aprendizagem com dados.\n"
        "- **Aplicação em melhoria da qualidade**: [Lee et al. - redução de erro de medicação com melhoria contínua](https://pmc.ncbi.nlm.nih.gov/articles/PMC4129856/). Exemplo aplicado de observação sistemática, erro e intervenção em contexto assistencial.\n"
        "- **Observação metodológica**: quando não há fonte primária equivalente em português, mantém-se a referência internacional para preservar fidelidade conceitual."
    )


def _pdsa_step_card(title, subtitle, description, color):
    return dmc.Card(
        [
            dmc.Badge(title, color=color, variant="light", mb="sm"),
            dmc.Text(subtitle, fw=700, mb="xs"),
            dmc.Text(description, size="sm", c="dimmed"),
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        p="md",
    )


layout = dmc.Container(
    [
        dmc.Title("Ambiente de Estudo IFEsCS", order=2, mb="xs"),
        dmc.Text(
            "Espaço educacional para leitura de dados, aprendizagem do Modelo de Melhoria e aplicação do ciclo PDSA com base na metodologia do IFEsCS.",
            c="dimmed",
            mb="lg",
        ),
        dmc.Alert(
            children=[
                dmc.Title("Abordagem metodológica", order=5, mb="xs"),
                dmc.Text(
                    "A página transforma os dados do dashboard em suporte pedagógico para letramento estatístico, tomada de decisão e melhoria contínua."
                ),
            ],
            color="ifsc-green",
            icon=DashIconify(icon="radix-icons:reader"),
            variant="light",
            mb="xl",
        ),
        dmc.SimpleGrid(
            cols={"base": 1, "sm": 2, "lg": 4},
            spacing="md",
            mb="xl",
            children=[
                html.Div(id="estudo-kpi-total"),
                html.Div(id="estudo-kpi-periodo"),
                html.Div(id="estudo-kpi-media"),
                html.Div(id="estudo-kpi-pico"),
            ],
        ),
        dmc.SimpleGrid(
            cols={"base": 1, "xl": 2},
            spacing="md",
            mb="md",
            children=[
                dmc.Card(
                    [
                        dcc.Graph(id="estudo-grafico-serie"),
                    ],
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    p="md",
                ),
                dmc.Card(
                    [
                        dcc.Graph(id="estudo-grafico-produtos"),
                    ],
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    p="md",
                ),
            ],
        ),
        dmc.SimpleGrid(
            cols={"base": 1, "sm": 2, "xl": 4},
            spacing="md",
            mb="md",
            children=[
                html.Div(id="estudo-pdsa-plan"),
                html.Div(id="estudo-pdsa-do"),
                html.Div(id="estudo-pdsa-study"),
                html.Div(id="estudo-pdsa-act"),
            ],
        ),
        dmc.SimpleGrid(
            cols={"base": 1, "xl": 2},
            spacing="md",
            children=[
                dmc.Card(
                    dcc.Markdown(id="estudo-modelo-melhoria"),
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    p="md",
                ),
                dmc.Card(
                    dcc.Markdown(id="estudo-pdsa"),
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    p="md",
                ),
                dmc.Card(
                    dcc.Markdown(id="estudo-leitura-graficos"),
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    p="md",
                ),
                dmc.Card(
                    dcc.Markdown(id="estudo-causa-efeito"),
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    p="md",
                ),
                dmc.Card(
                    dcc.Markdown(id="estudo-variacao"),
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    p="md",
                ),
            ],
        ),
        dmc.Card(
            dcc.Markdown(id="estudo-leituras"),
            withBorder=True,
            shadow="sm",
            radius="md",
            p="md",
            mt="md",
        ),
    ],
    fluid=True,
    p=0,
)


@callback(
    [
        Output("estudo-kpi-total", "children"),
        Output("estudo-kpi-periodo", "children"),
        Output("estudo-kpi-media", "children"),
        Output("estudo-kpi-pico", "children"),
        Output("estudo-grafico-serie", "figure"),
        Output("estudo-grafico-produtos", "figure"),
        Output("estudo-modelo-melhoria", "children"),
        Output("estudo-pdsa", "children"),
        Output("estudo-leitura-graficos", "children"),
        Output("estudo-causa-efeito", "children"),
        Output("estudo-variacao", "children"),
        Output("estudo-leituras", "children"),
        Output("estudo-pdsa-plan", "children"),
        Output("estudo-pdsa-do", "children"),
        Output("estudo-pdsa-study", "children"),
        Output("estudo-pdsa-act", "children"),
    ],
    Input("mantine-provider", "forceColorScheme"),
)
def update_estudo_ifescs_page(color_scheme):
    template_name = "plotly_dark" if color_scheme == "dark" else "plotly_white"
    kpis = get_kpis_gerais()
    df_volume = get_volume_diario()
    df_produtos = get_top_produtos_geral()
    df_ano = get_qtde_por_ano()

    total_registros = kpis.get("total", "N/D")
    periodo = f"{kpis.get('inicio', 'N/D')} a {kpis.get('fim', 'N/D')}"
    media_label = "N/D"
    pico_label = "N/D"

    if not df_volume.empty:
        media_label = _format_kg(df_volume["y"].mean())
        pico_row = df_volume.loc[df_volume["y"].idxmax()]
        pico_label = f"{_format_kg(pico_row['y'])} em {pico_row['ds'].strftime('%d/%m/%Y')}"

    fig_serie = build_temporal_line_figure(
        df_volume,
        x="ds",
        y="y",
        title="Série Diária para Leitura de Variação e Melhoria",
        template=template_name,
        granularity="diaria",
        labels={"ds": "Dia", "y": "Volume (kg)"},
        xaxis_title="Dia",
        yaxis_title="Volume (kg)",
    )

    fig_produtos = px.bar(
        df_produtos,
        x="produto",
        y="qtde",
        title="Produtos mais frequentes para discussão pedagógica",
        labels={"produto": "Categoria", "qtde": "Registros"},
        template=template_name,
    ) if not df_produtos.empty else px.bar(template=template_name, title="Produtos mais frequentes para discussão pedagógica")
    fig_produtos.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 40, "r": 20, "t": 50, "b": 80},
        xaxis_tickangle=-30,
    )

    if not df_ano.empty:
        fig_produtos.add_annotation(
            text=f"Anos observados: {', '.join(df_ano['ano'].tolist())}",
            xref="paper",
            yref="paper",
            x=1,
            y=1.1,
            showarrow=False,
            xanchor="right",
        )

    return (
        _create_highlight_card("Total de Registros", total_registros, "radix-icons:stack", "ifsc-green"),
        _create_highlight_card("Período Observado", periodo, "radix-icons:calendar", "ifsc-green"),
        _create_highlight_card("Média Diária", media_label, "radix-icons:bar-chart", "ifsc-green"),
        _create_highlight_card("Maior Pico", pico_label, "radix-icons:activity-log", "ifsc-green"),
        fig_serie,
        fig_produtos,
        _build_model_questions_markdown(df_volume, df_produtos, kpis),
        _build_pdsa_markdown(df_volume, df_produtos),
        _build_chart_reading_markdown(df_volume, df_produtos),
        _build_cause_effect_markdown(df_volume, df_produtos),
        _build_variation_markdown(df_volume),
        _build_readings_markdown(),
        _pdsa_step_card(
            "Plan",
            "Definir o objetivo de melhoria",
            "Selecionar um problema observável nos dados, estabelecer uma meta e justificar por que ela é importante para o processo.",
            "blue",
        ),
        _pdsa_step_card(
            "Do",
            "Executar uma mudança em pequena escala",
            "Aplicar uma ação pontual e controlada, sem alterar todo o processo de uma vez.",
            "green",
        ),
        _pdsa_step_card(
            "Study",
            "Comparar o antes e o depois",
            "Observar se a ação gerou alteração nos indicadores, na variação do processo ou na estabilidade do comportamento diário.",
            "yellow",
        ),
        _pdsa_step_card(
            "Act",
            "Padronizar ou reajustar",
            "Se a mudança funcionou, incorporar a prática. Se não funcionou, revisar a hipótese e reiniciar o ciclo.",
            "grape",
        ),
    )
