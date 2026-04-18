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
        return "### Resumo analítico\n- Não há dados de produtos disponíveis."
    top_produto = _safe_top_label(df, "produto")
    top_qtde = _safe_top_value(df, "quantidade")
    total_top10 = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0).sum()
    participacao = (top_qtde / total_top10 * 100) if total_top10 else 0
    return (
        "### Resumo analítico\n"
        f"- Produto líder: **{top_produto}** com {top_qtde:.0f} registros.\n"
        f"- Participação no top 10: **{participacao:.1f}%**.\n"
    )


def summarize_produto_fornecedores(df, produto):
    if df is None or df.empty:
        return f"### Resumo analítico\n- Não há movimentação registrada para **{produto}**."
    top_fornecedor = _safe_top_label(df, "fornecedor_cliente")
    top_qtde = _safe_top_value(df, "quantidade")
    total = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0).sum()
    participacao = (top_qtde / total * 100) if total else 0
    return (
        "### Resumo analítico\n"
        f"- Principal movimentador de **{produto}**: **{top_fornecedor}**.\n"
        f"- Participação no volume analisado: **{participacao:.1f}%**.\n"
    )


def summarize_setor_produtos(df, setor):
    if df is None or df.empty:
        return f"### Resumo analítico\n- Não há produtos registrados para o setor **{setor}**."
    top_produto = _safe_top_label(df, "produto")
    top_qtde = _safe_top_value(df, "quantidade")
    total = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0).sum()
    participacao = (top_qtde / total * 100) if total else 0
    return (
        "### Resumo analítico\n"
        f"- Produto predominante no setor **{setor}**: **{top_produto}**.\n"
        f"- Participação no mix do setor: **{participacao:.1f}%**.\n"
    )


def summarize_setores_overview(df):
    if df is None or df.empty:
        return "### Resumo analítico\n- Não há dados setoriais disponíveis."
    maior_volume = df.sort_values("quantidade", ascending=False).iloc[0]
    maior_peso = df.sort_values("Média de Peso (kg)", ascending=False).iloc[0]
    return (
        "### Resumo analítico\n"
        f"- Setor com maior volume: **{maior_volume['setor']}** ({float(maior_volume['quantidade']):.0f} registros).\n"
        f"- Setor com maior peso médio: **{maior_peso['setor']}** ({float(maior_peso['Média de Peso (kg)']):.2f} kg).\n"
    )


def summarize_setor_temporal(df, setor, ano):
    if df is None or df.empty:
        return f"### Resumo analítico\n- Não há histórico mensal para o setor **{setor}** em **{ano}**."
    serie = pd.to_numeric(df["media_peso"], errors="coerce").fillna(0)
    pico_idx = serie.idxmax()
    vale_idx = serie.idxmin()
    crescimento = serie.iloc[-1] - serie.iloc[0] if len(serie) >= 2 else 0
    return (
        "### Resumo analítico\n"
        f"- Pico mensal de peso médio: **mês {int(df.loc[pico_idx, 'mes'])}** com {serie.loc[pico_idx]:.2f} kg.\n"
        f"- Menor valor mensal: **mês {int(df.loc[vale_idx, 'mes'])}** com {serie.loc[vale_idx]:.2f} kg.\n"
        f"- Variação do início ao fim da série: **{crescimento:.2f} kg**.\n"
    )


def summarize_empresas_ranking(df):
    if df is None or df.empty:
        return "### Resumo analítico\n- Não há dados de empresas disponíveis."
    lider = df.iloc[0]
    total = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0).sum()
    participacao = (float(lider["quantidade"]) / total * 100) if total else 0
    return (
        "### Resumo analítico\n"
        f"- Entidade líder: **{lider['fornecedor_cliente']}** com {float(lider['quantidade']):.0f} registros.\n"
        f"- Participação no conjunto analisado: **{participacao:.1f}%**.\n"
    )


def summarize_empresas_temporal(df_volume, df_media, empresa, ano):
    if df_volume is None or df_volume.empty:
        return f"### Resumo analítico\n- Não há série temporal para **{empresa}** em **{ano}**."
    vol = pd.to_numeric(df_volume.iloc[:, 1], errors="coerce").fillna(0)
    pico_idx = vol.idxmax()
    texto = (
        "### Resumo analítico\n"
        f"- Maior volume mensal de **{empresa}** em **{ano}**: **{df_volume.loc[pico_idx, 'mes_nome']}** com {vol.loc[pico_idx]:.0f} registros.\n"
    )
    if df_media is not None and not df_media.empty:
        med = pd.to_numeric(df_media.iloc[:, 1], errors="coerce").fillna(0)
        melhor_idx = med.idxmax()
        texto += f"- Melhor média de peso no ano: **{df_media.loc[melhor_idx, 'mes_nome']}** com {med.loc[melhor_idx]:.2f} kg.\n"
   
    return texto


def summarize_frota(df):
    if df is None or df.empty:
        return "### Resumo analítico\n- Nenhum veículo atende aos filtros atuais."
    melhor = df.sort_values("peso_medio_por_viagem", ascending=False).iloc[0]
    pior = df.sort_values("peso_medio_por_viagem", ascending=True).iloc[0]
    return (
        "### Resumo analítico\n"
        f"- Veículo mais eficiente: **{melhor['placa_veiculo']}** com média de {float(melhor['peso_medio_por_viagem']):.2f} kg/viagem.\n"
        f"- Veículo com menor média: **{pior['placa_veiculo']}** com {float(pior['peso_medio_por_viagem']):.2f} kg/viagem.\n"
    )


def summarize_heatmap(df_grouped):
    if df_grouped is None or df_grouped.empty:
        return "### Resumo analítico\n- Não há registros para os filtros selecionados."
    pico = df_grouped.sort_values("numero_de_registros", ascending=False).iloc[0]
    vale = df_grouped.sort_values("numero_de_registros", ascending=True).iloc[0]
    return (
        "### Resumo analítico\n"
        f"- Pico operacional: **{pico['dia_semana']}** às **{int(pico['hora_do_dia'])}h** com {float(pico['numero_de_registros']):.0f} registros.\n"
        f"- Menor carga observada: **{vale['dia_semana']}** às **{int(vale['hora_do_dia'])}h**.\n"
    )


def summarize_auditoria(df, limite, entidade):
    if df is None or df.empty:
        return f"### Resumo analítico\n- Nenhuma discrepância acima de **{limite}%** para **{entidade}**."
    maior = df.iloc[0]
    media_abs = pd.to_numeric(df["diferenca_percentual"], errors="coerce").abs().mean()
    return (
        "### Resumo analítico\n"
        f"- Total de ocorrências acima do limite: **{len(df)}**.\n"
        f"- Maior discrepância: ticket **{maior['ticket']}** com **{float(maior['diferenca_percentual']):.2f}%**.\n"
        f"- Média absoluta das discrepâncias: **{media_abs:.2f}%**.\n"
    )


def summarize_fluxo_macro(df):
    if df is None or df.empty:
        return "### Resumo analítico\n- Não há dados de fluxo disponíveis."
    media_balanco = pd.to_numeric(df["balanco"], errors="coerce").fillna(0).mean()
    maior = df.sort_values("balanco", ascending=False).iloc[0]
    menor = df.sort_values("balanco", ascending=True).iloc[0]
    return (
        "### Resumo analítico\n"
        f"- Balanço médio mensal: **{media_balanco:.2f} kg**.\n"
        f"- Maior excesso de entrada: **{maior['periodo']}** com {float(maior['balanco']):.2f} kg.\n"
        f"- Maior déficit relativo: **{menor['periodo']}** com {float(menor['balanco']):.2f} kg.\n"
    )


def summarize_fluxo_setor(total_setor, total_saida, percentual, setor):
    return (
        "### Resumo analítico\n"
        f"- Participação de **{setor}** no total de saída: **{percentual:.2f}%**.\n"
        f"- Volume acumulado do setor: **{total_setor:,.2f} kg**.\n"
        f"- Volume acumulado de saída para Candiota: **{total_saida:,.2f} kg**.\n"
    )
