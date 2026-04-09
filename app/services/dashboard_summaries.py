import pandas as pd


def _safe_top_label(df, column):
    if df is None or df.empty or column not in df.columns:
        return "N/D"
    return str(df.iloc[0][column])


def _safe_top_value(df, column):
    if df is None or df.empty or column not in df.columns:
        return 0
    value = pd.to_numeric(pd.Series([df.iloc[0][column]]), errors="coerce").iloc[0]
    return 0 if pd.isna(value) else float(value)


def summarize_produtos_ranking(df):
    if df is None or df.empty:
        return "### Resumo analitico\n- Nao ha dados de produtos disponiveis."
    top_produto = _safe_top_label(df, "produto")
    top_qtde = _safe_top_value(df, "quantidade")
    total_top10 = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0).sum()
    participacao = (top_qtde / total_top10 * 100) if total_top10 else 0
    return (
        "### Resumo analitico\n"
        f"- Produto lider: **{top_produto}** com {top_qtde:.0f} registros.\n"
        f"- Participacao no top 10: **{participacao:.1f}%**.\n"
        "- Leitura gerencial: produtos dominantes devem orientar priorizacao de coleta, alocacao operacional e tratamento diferenciado quando necessario."
    )


def summarize_produto_fornecedores(df, produto):
    if df is None or df.empty:
        return f"### Resumo analitico\n- Nao ha movimentacao registrada para **{produto}**."
    top_fornecedor = _safe_top_label(df, "fornecedor_cliente")
    top_qtde = _safe_top_value(df, "quantidade")
    total = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0).sum()
    participacao = (top_qtde / total * 100) if total else 0
    return (
        "### Resumo analitico\n"
        f"- Principal movimentador de **{produto}**: **{top_fornecedor}**.\n"
        f"- Participacao no volume analisado: **{participacao:.1f}%**.\n"
        "- Leitura gerencial: alta concentracao em poucos atores sugere dependencia operacional e facilita auditoria dirigida."
    )


def summarize_setor_produtos(df, setor):
    if df is None or df.empty:
        return f"### Resumo analitico\n- Nao ha produtos registrados para o setor **{setor}**."
    top_produto = _safe_top_label(df, "produto")
    top_qtde = _safe_top_value(df, "quantidade")
    total = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0).sum()
    participacao = (top_qtde / total * 100) if total else 0
    return (
        "### Resumo analitico\n"
        f"- Produto predominante no setor **{setor}**: **{top_produto}**.\n"
        f"- Participacao no mix do setor: **{participacao:.1f}%**.\n"
        "- Leitura gerencial: a composicao setorial ajuda a definir rota, frequencia de coleta e necessidade de tratamento especializado."
    )


def summarize_setores_overview(df):
    if df is None or df.empty:
        return "### Resumo analitico\n- Nao ha dados setoriais disponiveis."
    maior_volume = df.sort_values("quantidade", ascending=False).iloc[0]
    maior_peso = df.sort_values("Média de Peso (kg)", ascending=False).iloc[0]
    return (
        "### Resumo analitico\n"
        f"- Setor com maior volume: **{maior_volume['setor']}** ({float(maior_volume['quantidade']):.0f} registros).\n"
        f"- Setor com maior peso medio: **{maior_peso['setor']}** ({float(maior_peso['Média de Peso (kg)']):.2f} kg).\n"
        "- Leitura gerencial: diferencas entre lideranca em volume e peso medio indicam perfis operacionais distintos entre os setores."
    )


def summarize_setor_temporal(df, setor, ano):
    if df is None or df.empty:
        return f"### Resumo analitico\n- Nao ha historico mensal para o setor **{setor}** em **{ano}**."
    serie = pd.to_numeric(df["media_peso"], errors="coerce").fillna(0)
    pico_idx = serie.idxmax()
    vale_idx = serie.idxmin()
    crescimento = serie.iloc[-1] - serie.iloc[0] if len(serie) >= 2 else 0
    return (
        "### Resumo analitico\n"
        f"- Pico mensal de peso medio: **mes {int(df.loc[pico_idx, 'mes'])}** com {serie.loc[pico_idx]:.2f} kg.\n"
        f"- Menor valor mensal: **mes {int(df.loc[vale_idx, 'mes'])}** com {serie.loc[vale_idx]:.2f} kg.\n"
        f"- Variacao do inicio ao fim da serie: **{crescimento:.2f} kg**.\n"
        "- Leitura gerencial: a evolucao mensal ajuda a identificar sazonalidade, eventos operacionais e necessidade de replanejamento."
    )


def summarize_empresas_ranking(df):
    if df is None or df.empty:
        return "### Resumo analitico\n- Nao ha dados de empresas disponiveis."
    lider = df.iloc[0]
    total = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0).sum()
    participacao = (float(lider["quantidade"]) / total * 100) if total else 0
    return (
        "### Resumo analitico\n"
        f"- Entidade lider: **{lider['fornecedor_cliente']}** com {float(lider['quantidade']):.0f} registros.\n"
        f"- Participacao no conjunto analisado: **{participacao:.1f}%**.\n"
        "- Leitura gerencial: concentracao alta em poucas entidades indica pontos-chave para coordenacao institucional e auditoria."
    )


def summarize_empresas_temporal(df_volume, df_media, empresa, ano):
    if df_volume is None or df_volume.empty:
        return f"### Resumo analitico\n- Nao ha serie temporal para **{empresa}** em **{ano}**."
    vol = pd.to_numeric(df_volume.iloc[:, 1], errors="coerce").fillna(0)
    pico_idx = vol.idxmax()
    texto = (
        "### Resumo analitico\n"
        f"- Maior volume mensal de **{empresa}** em **{ano}**: **{df_volume.loc[pico_idx, 'mes_nome']}** com {vol.loc[pico_idx]:.0f} registros.\n"
    )
    if df_media is not None and not df_media.empty:
        med = pd.to_numeric(df_media.iloc[:, 1], errors="coerce").fillna(0)
        melhor_idx = med.idxmax()
        texto += f"- Melhor media de peso no ano: **{df_media.loc[melhor_idx, 'mes_nome']}** com {med.loc[melhor_idx]:.2f} kg.\n"
    texto += "- Leitura gerencial: volume e peso medio devem ser acompanhados em conjunto para distinguir carga operacional de eficiencia."
    return texto


def summarize_frota(df):
    if df is None or df.empty:
        return "### Resumo analitico\n- Nenhum veiculo atende aos filtros atuais."
    melhor = df.sort_values("peso_medio_por_viagem", ascending=False).iloc[0]
    pior = df.sort_values("peso_medio_por_viagem", ascending=True).iloc[0]
    return (
        "### Resumo analitico\n"
        f"- Veiculo mais eficiente: **{melhor['placa_veiculo']}** com media de {float(melhor['peso_medio_por_viagem']):.2f} kg/viagem.\n"
        f"- Veiculo com menor media: **{pior['placa_veiculo']}** com {float(pior['peso_medio_por_viagem']):.2f} kg/viagem.\n"
        "- Leitura gerencial: diferencas acentuadas sugerem revisao de rota, carga, manutencao ou alocacao da frota."
    )


def summarize_heatmap(df_grouped):
    if df_grouped is None or df_grouped.empty:
        return "### Resumo analitico\n- Nao ha registros para os filtros selecionados."
    pico = df_grouped.sort_values("numero_de_registros", ascending=False).iloc[0]
    vale = df_grouped.sort_values("numero_de_registros", ascending=True).iloc[0]
    return (
        "### Resumo analitico\n"
        f"- Pico operacional: **{pico['dia_semana']}** as **{int(pico['hora_do_dia'])}h** com {float(pico['numero_de_registros']):.0f} registros.\n"
        f"- Menor carga observada: **{vale['dia_semana']}** as **{int(vale['hora_do_dia'])}h**.\n"
        "- Leitura gerencial: janelas de pico devem orientar escala, atendimento e distribuicao do trabalho na balanca."
    )


def summarize_auditoria(df, limite, entidade):
    if df is None or df.empty:
        return f"### Resumo analitico\n- Nenhuma discrepancia acima de **{limite}%** para **{entidade}**."
    maior = df.iloc[0]
    media_abs = pd.to_numeric(df["diferenca_percentual"], errors="coerce").abs().mean()
    return (
        "### Resumo analitico\n"
        f"- Total de ocorrencias acima do limite: **{len(df)}**.\n"
        f"- Maior discrepancia: ticket **{maior['ticket']}** com **{float(maior['diferenca_percentual']):.2f}%**.\n"
        f"- Media absoluta das discrepancias: **{media_abs:.2f}%**.\n"
        "- Leitura gerencial: casos extremos devem ser auditados primeiro para verificar falha documental, balanca ou processo."
    )


def summarize_fluxo_macro(df):
    if df is None or df.empty:
        return "### Resumo analitico\n- Nao ha dados de fluxo disponiveis."
    media_balanco = pd.to_numeric(df["balanco"], errors="coerce").fillna(0).mean()
    maior = df.sort_values("balanco", ascending=False).iloc[0]
    menor = df.sort_values("balanco", ascending=True).iloc[0]
    return (
        "### Resumo analitico\n"
        f"- Balanco medio mensal: **{media_balanco:.2f} kg**.\n"
        f"- Maior excesso de entrada: **{maior['periodo']}** com {float(maior['balanco']):.2f} kg.\n"
        f"- Maior deficit relativo: **{menor['periodo']}** com {float(menor['balanco']):.2f} kg.\n"
        "- Leitura gerencial: desvios persistentes entre entrada e saida merecem verificacao de estoque temporario, umidade, material agregado ou medicao."
    )


def summarize_fluxo_setor(total_setor, total_saida, percentual, setor):
    return (
        "### Resumo analitico\n"
        f"- Participacao de **{setor}** no total de saida: **{percentual:.2f}%**.\n"
        f"- Volume acumulado do setor: **{total_setor:,.2f} kg**.\n"
        f"- Volume acumulado de saida para Candiota: **{total_saida:,.2f} kg**.\n"
        "- Leitura gerencial: a participacao do setor ajuda a priorizar redimensionamento, rota e recursos de coleta."
    )
