from dash import callback, dcc, html
from dash.dependencies import Input, Output
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import plotly.express as px

from app.application.analytics import (
    get_kpis_gerais,
    get_qtde_por_ano,
    get_top_produtos_geral,
    get_volume_mensal,
)


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
            "- O que queremos alcancar? Organizar o acompanhamento do processo.\n"
            "- Como saber se houve melhoria? Monitorando indicadores periodicos.\n"
            "- Que mudanca pode resultar em melhoria? Padronizacao de coleta e registro."
        )

    media_periodica = float(df_volume["y"].mean())
    pico_row = df_volume.loc[df_volume["y"].idxmax()]
    pico_periodo = pico_row["ds"].strftime("%d/%m/%Y")
    pico_valor = _format_kg(pico_row["y"])
    produto_lider = "Nao identificado"
    if not df_produtos.empty:
        produto_lider = str(df_produtos.iloc[0]["produto"])

    return (
        "### Modelo de Melhoria aplicado ao IFEsCS\n"
        f"- O que queremos alcancar? Reduzir sobrecargas operacionais em quinzenas acima da media historica de **{_format_kg(media_periodica)}**.\n"
        f"- Como saber se houve melhoria? Comparando o comportamento atual com o pico recente de **{pico_valor}** registrado em **{pico_periodo}**, observando tendencia, distribuicao dos dados e estabilidade do processo.\n"
        f"- Que mudanca pode resultar em melhoria? Reorganizar a operacao com foco nos fluxos ligados ao item de maior recorrencia, hoje identificado como **{produto_lider}**, e acompanhar o efeito dessa acao ao longo do tempo.\n"
        f"- Leitura IFEsCS: os dados cobrem o periodo entre **{kpis['inicio']}** e **{kpis['fim']}**, servindo como base para aprendizagem estatistica aplicada e apoio a decisao."
    )


def _build_pdsa_markdown(df_volume, df_produtos):
    if df_volume.empty:
        return (
            "### Ciclo PDSA\n"
            "- Plan: definir um objetivo de melhoria.\n"
            "- Do: aplicar uma mudanca em pequena escala.\n"
            "- Study: comparar os indicadores antes e depois.\n"
            "- Act: padronizar a mudanca ou ajustar a estrategia."
        )

    media_periodica = float(df_volume["y"].mean())
    minimo = float(df_volume["y"].min())
    maximo = float(df_volume["y"].max())
    amplitude = maximo - minimo
    produto_lider = "Nao identificado"
    if not df_produtos.empty:
        produto_lider = str(df_produtos.iloc[0]["produto"])

    return (
        "### Ciclo PDSA com leitura orientada por dados\n"
        f"- **Plan**: formular a meta de reduzir a amplitude operacional atual de **{_format_kg(amplitude)}** entre os periodos observados.\n"
        f"- **Do**: testar uma mudanca localizada, como reorganizacao de rotina, reforco de equipe ou acao focada no fluxo de **{produto_lider}**.\n"
        f"- **Study**: verificar se a media periodica permanece abaixo ou proxima de **{_format_kg(media_periodica)}** com menor variacao entre quinzenas.\n"
        f"- **Act**: institucionalizar a mudanca quando os indicadores mostrarem ganho, ou revisar a hipotese quando nao houver melhora mensuravel.\n"
        "- **Metodo IFEsCS**: o estudo parte de dados reais organizados, articulando ensino, pesquisa e extensao para gerar leitura estatistica contextualizada."
    )


def _build_cause_effect_markdown(df_volume, df_produtos):
    if df_volume.empty:
        return (
            "### Causa e efeito\n"
            "- Um indicador isolado nao explica o processo.\n"
            "- A leitura de causa e efeito exige observar contexto, sequencia temporal e variacao.\n"
            "- No IFEsCS, os dados devem apoiar perguntas, nao apenas respostas prontas.\n"
            "- A prioridade e compreender o sistema antes de culpar pessoas ou eventos isolados."
        )

    pico = df_volume.loc[df_volume["y"].idxmax()]
    vale = df_volume.loc[df_volume["y"].idxmin()]
    produto_lider = "Nao identificado"
    if not df_produtos.empty:
        produto_lider = str(df_produtos.iloc[0]["produto"])

    return (
        "### Leitura de causa e efeito\n"
        f"- O pico de **{_format_kg(pico['y'])}** em **{pico['ds'].strftime('%d/%m/%Y')}** nao deve ser interpretado como causa por si so; ele e um sinal para investigacao.\n"
        f"- Da mesma forma, o menor valor observado, **{_format_kg(vale['y'])}** em **{vale['ds'].strftime('%d/%m/%Y')}**, nao prova melhora estrutural sem analise do processo.\n"
        f"- O papel do gestor e relacionar os sinais dos dados com hipoteses concretas, como alteracoes de rotina, sazonalidade, alocacao de equipe ou concentracao do fluxo em **{produto_lider}**.\n"
        "- No pensamento estatistico defendido pelo IFEsCS, dados ajudam a testar explicacoes plausiveis e a diferenciar percepcao isolada de comportamento sistemico.\n"
        "- Em termos didaticos, causa e efeito exigem sequencia temporal, conhecimento do processo e comparacao entre periodos, e nao apenas uma coincidencia visual no grafico.\n"
        "- Essa leitura dialoga com Deming ao lembrar que um sistema gera resultados, e que agir sem entender a fonte da variacao costuma produzir correcoes superficiais."
    )


def _build_variation_markdown(df_volume):
    if df_volume.empty:
        return (
            "### Variacao, erro e media\n"
            "- A media resume o processo, mas nao mostra sua instabilidade.\n"
            "- A variacao entre periodos e essencial para compreender risco e previsibilidade.\n"
            "- O erro deve ser acompanhado continuamente.\n"
            "- Um processo pode ter media aceitavel e ainda assim ser instavel."
        )

    media = float(df_volume["y"].mean())
    desvio = float(df_volume["y"].std()) if len(df_volume) > 1 else 0.0
    amplitude = float(df_volume["y"].max() - df_volume["y"].min())
    coef_var = (desvio / media * 100) if media else 0.0

    return (
        "### Por que a media sozinha nao basta\n"
        f"- A media observada e **{_format_kg(media)}**, mas a leitura do processo fica incompleta sem a variabilidade associada.\n"
        f"- O desvio padrao atual e **{_format_kg(desvio)}**, com amplitude total de **{_format_kg(amplitude)}** entre o menor e o maior periodo.\n"
        f"- O coeficiente de variacao aproximado e **{coef_var:.2f}%**, mostrando quanto o processo oscila em relacao ao centro da serie.\n"
        "- Em melhoria de processos, acompanhar erro, dispersao e estabilidade costuma revelar mais do que observar apenas a media, pois sao esses sinais que indicam previsibilidade, risco operacional e necessidade de intervencao.\n"
        "- A media descreve o centro do comportamento; o erro mostra o quanto a previsao ou a meta falham; e a variancia mostra o quao confiavel ou instavel e o processo ao longo do tempo.\n"
        "- Em linguagem de gestao, um processo com media aceitavel e alta variacao segue sendo um processo arriscado, porque ele nao entrega regularidade.\n"
        "- Box reforca esse ponto ao aproximar estatistica de experimentacao e aprendizagem: melhorar nao e apenas deslocar a media, mas entender como reduzir a variacao indesejada e aprender com o erro."
    )


def _build_chart_reading_markdown(df_volume, df_produtos):
    if df_volume.empty:
        return (
            "### Como ler os graficos\n"
            "- Observe a distribuicao temporal dos dados.\n"
            "- Identifique pontos de maior concentracao.\n"
            "- Compare variacoes antes de formular hipoteses de melhoria."
        )

    ultimo_periodo = df_volume["ds"].max().strftime("%d/%m/%Y")
    primeiro_periodo = df_volume["ds"].min().strftime("%d/%m/%Y")
    variacao = float(df_volume["y"].max() - df_volume["y"].min())
    lider = "Nao identificado"
    if not df_produtos.empty:
        lider = str(df_produtos.iloc[0]["produto"])

    return (
        "### Como interpretar esta pagina\n"
        f"- O grafico de serie mostra o comportamento do processo entre **{primeiro_periodo}** e **{ultimo_periodo}**.\n"
        f"- A amplitude entre o menor e o maior valor observado e de **{_format_kg(variacao)}**, o que ajuda a discutir estabilidade e variabilidade.\n"
        f"- O grafico de categorias destaca quais itens concentram mais registros, com destaque atual para **{lider}**.\n"
        "- A leitura recomendada no IFEsCS parte da observacao dos dados, passa pela formulacao de hipoteses e chega a uma acao mensuravel de melhoria."
    )


def _build_readings_markdown():
    return (
        "### Leituras fundamentais\n"
        "- **Base central do IFEsCS - Deming**: [*A nova economia para a industria, o governo e a educacao*](https://books.google.com/books/about/A_nova_economia_para_a_ind%C3%BAstria_o_gove.html?id=nZtYQCbqZO8C). Referencia central para sistema, variacao, previsibilidade, aprendizagem e responsabilidade gerencial.\n"
        "- **Base central do IFEsCS - Langley e IHI**: [Model for Improvement em portugues](https://www.ihi.org/pt-br/library/model-for-improvement). Sintetiza as tres perguntas do Modelo de Melhoria e o uso do ciclo PDSA.\n"
        "- **Ferramenta em portugues**: [Planilha PDSA em portugues](https://www.ihi.org/pt-br/resources/tools/plan-do-study-act-pdsa-worksheet). Material pratico para documentar testes de mudanca e aprendizagem em ciclos curtos.\n"
        "- **Mediacao e aprendizagem em portugues**: [Estabelecendo Medidas - IHI](https://www.ihi.org/index.php/pt-br/library/model-for-improvement/establishing-measures). Fonte importante para sustentar que medir melhoria nao e apenas calcular media, mas acompanhar variacao, tendencia e aprendizagem ao longo do tempo.\n"
        "- **Apoio metodologico em estatistica - Box, Hunter e Hunter**: [*Statistics for Experimenters*](https://www.wiley-vch.de/en/areas-interest/mathematics-statistics/statistics-for-experimenters-978-0-471-71813-0). Referencia importante para erro, variacao, experimentacao e aprendizagem com dados.\n"
        "- **Aplicacao em melhoria da qualidade**: [Lee et al. - reducao de erro de medicacao com melhoria continua](https://pmc.ncbi.nlm.nih.gov/articles/PMC4129856/). Exemplo aplicado de observacao sistematica, erro e intervencao em contexto assistencial.\n"
        "- **Observacao metodologica**: quando nao ha fonte primaria equivalente em portugues, mantem-se a referencia internacional para preservar fidelidade conceitual."
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
            "Espaco educacional para leitura de dados, aprendizagem do Modelo de Melhoria e aplicacao do ciclo PDSA com base na metodologia do IFEsCS.",
            c="dimmed",
            mb="lg",
        ),
        dmc.Alert(
            children=[
                dmc.Title("Abordagem metodologica", order=5, mb="xs"),
                dmc.Text(
                    "A pagina transforma os dados do dashboard em suporte pedagogico para letramento estatistico, tomada de decisao e melhoria continua."
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
            ],
        ),
        dmc.SimpleGrid(
            cols={"base": 1, "xl": 2},
            spacing="md",
            mt="md",
            children=[
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
    df_volume = get_volume_mensal()
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

    fig_serie = px.line(
        df_volume,
        x="ds",
        y="y",
        markers=True,
        title="Serie Historica para Leitura de Variacao e Melhoria",
        labels={"ds": "Periodo", "y": "Volume (kg)"},
        template=template_name,
    ) if not df_volume.empty else px.line(template=template_name, title="Serie Historica para Leitura de Variacao e Melhoria")
    fig_serie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 40, "r": 20, "t": 50, "b": 30},
    )

    fig_produtos = px.bar(
        df_produtos,
        x="produto",
        y="qtde",
        title="Produtos mais frequentes para discussao pedagogica",
        labels={"produto": "Categoria", "qtde": "Registros"},
        template=template_name,
    ) if not df_produtos.empty else px.bar(template=template_name, title="Produtos mais frequentes para discussao pedagogica")
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
        _create_highlight_card("Periodo Observado", periodo, "radix-icons:calendar", "ifsc-green"),
        _create_highlight_card("Media por Periodo", media_label, "radix-icons:bar-chart", "ifsc-green"),
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
            "Selecionar um problema observavel nos dados, estabelecer uma meta e justificar por que ela e importante para o processo.",
            "blue",
        ),
        _pdsa_step_card(
            "Do",
            "Executar uma mudanca em pequena escala",
            "Aplicar uma acao pontual e controlada, sem alterar todo o processo de uma vez.",
            "green",
        ),
        _pdsa_step_card(
            "Study",
            "Comparar o antes e o depois",
            "Observar se a acao gerou alteracao nos indicadores, na variacao do processo ou na estabilidade das quinzenas.",
            "yellow",
        ),
        _pdsa_step_card(
            "Act",
            "Padronizar ou reajustar",
            "Se a mudanca funcionou, incorporar a pratica. Se nao funcionou, revisar a hipotese e reiniciar o ciclo.",
            "grape",
        ),
    )
