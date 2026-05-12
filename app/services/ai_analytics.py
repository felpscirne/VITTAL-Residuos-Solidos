from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from app.database import engine
from app.extensions import cache

try:
    from sklearn.cluster import KMeans
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
    SKLEARN_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover
    KMeans = None
    IsolationForest = None
    RandomForestClassifier = None
    StandardScaler = None
    SKLEARN_AVAILABLE = False
    SKLEARN_IMPORT_ERROR = str(exc)


def _unavailable_result(message: str) -> dict[str, Any]:
    return {"available": False, "message": message, "data": pd.DataFrame(), "summary": message}


def _normalize_0_100(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").fillna(0)
    min_value = float(numeric.min()) if not numeric.empty else 0.0
    max_value = float(numeric.max()) if not numeric.empty else 0.0
    if math.isclose(min_value, max_value):
        return pd.Series(np.full(len(numeric), 50.0), index=numeric.index)
    return ((numeric - min_value) / (max_value - min_value) * 100).clip(lower=0, upper=100)


def _risk_band(probability: float) -> str:
    if probability >= 0.75:
        return "Muito alto"
    if probability >= 0.55:
        return "Alto"
    if probability >= 0.35:
        return "Moderado"
    return "Baixo"


def _anomaly_band(score: float) -> str:
    if score >= 80:
        return "Muito anômalo"
    if score >= 60:
        return "Anômalo"
    if score >= 40:
        return "Atenção"
    return "Dentro do padrão"


def _prepare_audit_dataframe(selected_entidade: str) -> pd.DataFrame:
    query = """
    SELECT
        ticket,
        data_hora,
        fornecedor_cliente,
        produto,
        setor,
        peso_entrada,
        peso_saida,
        peso_liquido,
        peso_embalagem_liquido_corrigido,
        peso_nota_fiscal,
        (peso_embalagem_liquido_corrigido - peso_nota_fiscal) AS diferenca_kg,
        ABS(((peso_embalagem_liquido_corrigido - peso_nota_fiscal) / NULLIF(peso_nota_fiscal, 0)) * 100) AS diferenca_percentual_abs
    FROM registro
    WHERE peso_nota_fiscal > 0
      AND peso_embalagem_liquido_corrigido > 0
      AND UPPER(COALESCE(setor, '')) NOT LIKE 'ACERTO%%'
      AND UPPER(COALESCE(setor, '')) NOT LIKE 'CANDIOTA%%'
    """
    params: dict[str, Any] = {}
    if selected_entidade and selected_entidade != "todas":
        query += " AND fornecedor_cliente = %(entidade)s"
        params["entidade"] = selected_entidade
    query += " ORDER BY data_hora DESC"
    df = pd.read_sql(query, engine, params=params)
    if df.empty:
        return df

    for column in [
        "peso_entrada",
        "peso_saida",
        "peso_liquido",
        "peso_embalagem_liquido_corrigido",
        "peso_nota_fiscal",
        "diferenca_kg",
        "diferenca_percentual_abs",
    ]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    df["fornecedor_cliente"] = df["fornecedor_cliente"].fillna("Não informado")
    df["produto"] = df["produto"].fillna("Não informado")
    df["setor"] = df["setor"].fillna("Não informado")
    return df


def _build_risk_features(df: pd.DataFrame) -> pd.DataFrame:
    feature_df = df.copy()
    feature_df["peso_bruto_relativo"] = feature_df["peso_entrada"] - feature_df["peso_saida"]
    feature_df["relacao_nota_balanca"] = (
        feature_df["peso_embalagem_liquido_corrigido"] / feature_df["peso_nota_fiscal"].replace(0, np.nan)
    ).replace([np.inf, -np.inf], np.nan).fillna(1.0)

    setor_risk = feature_df.groupby("setor")["diferenca_percentual_abs"].transform("mean")
    entidade_risk = feature_df.groupby("fornecedor_cliente")["diferenca_percentual_abs"].transform("mean")
    produto_risk = feature_df.groupby("produto")["diferenca_percentual_abs"].transform("mean")

    feature_df["historico_setor"] = setor_risk.fillna(setor_risk.median() if not setor_risk.empty else 0)
    feature_df["historico_entidade"] = entidade_risk.fillna(entidade_risk.median() if not entidade_risk.empty else 0)
    feature_df["historico_produto"] = produto_risk.fillna(produto_risk.median() if not produto_risk.empty else 0)
    return feature_df[
        [
            "peso_entrada",
            "peso_saida",
            "peso_liquido",
            "peso_embalagem_liquido_corrigido",
            "peso_nota_fiscal",
            "peso_bruto_relativo",
            "historico_setor",
            "historico_entidade",
            "historico_produto",
        ]
    ].fillna(0)


@cache.memoize(timeout=900)
def get_audit_ai_analysis(selected_entidade: str = "todas", min_discrepancia: float = 5.0) -> dict[str, Any]:
    df = _prepare_audit_dataframe(selected_entidade)
    if df.empty:
        return _unavailable_result("Ainda não há dados suficientes para treinar a detecção de anomalias e o risco operacional.")

    features = _build_risk_features(df)
    target_threshold = max(float(min_discrepancia), 5.0)

    if SKLEARN_AVAILABLE and len(df) >= 12:
        anomaly_model = IsolationForest(
            n_estimators=200,
            contamination=min(0.12, max(0.03, 12 / len(df))),
            random_state=42,
        )
        anomaly_model.fit(features)
        anomaly_score = -anomaly_model.score_samples(features)
        df["score_anomalia_ia"] = _normalize_0_100(pd.Series(anomaly_score, index=df.index)).round(1)
        df["classificacao_anomalia_ia"] = df["score_anomalia_ia"].apply(_anomaly_band)

        target = (df["diferenca_percentual_abs"] >= target_threshold).astype(int)
        if target.nunique() > 1:
            risk_model = RandomForestClassifier(
                n_estimators=180,
                max_depth=6,
                min_samples_leaf=4,
                random_state=42,
                class_weight="balanced_subsample",
            )
            risk_model.fit(features, target)
            risk_probability = risk_model.predict_proba(features)[:, 1]
        else:
            risk_probability = (df["score_anomalia_ia"] / 100.0).to_numpy()
    else:
        heuristic_anomaly = (
            (_normalize_0_100(df["diferenca_percentual_abs"]) * 0.7)
            + (_normalize_0_100(df["diferenca_kg"].abs()) * 0.3)
        )
        df["score_anomalia_ia"] = heuristic_anomaly.round(1)
        df["classificacao_anomalia_ia"] = df["score_anomalia_ia"].apply(_anomaly_band)
        risk_probability = (
            (
                (_normalize_0_100(df["diferenca_percentual_abs"]) * 0.5)
                + (_normalize_0_100(df["diferenca_kg"].abs()) * 0.2)
                + (_normalize_0_100(df["score_anomalia_ia"]) * 0.3)
            ) / 100.0
        ).clip(lower=0, upper=1).to_numpy()

    df["probabilidade_risco_operacional"] = (risk_probability * 100).round(1)
    df["classificacao_risco_operacional"] = (risk_probability.astype(float)).tolist()
    df["classificacao_risco_operacional"] = [
        _risk_band(probability) for probability in risk_probability
    ]

    df["diferenca_percentual"] = pd.to_numeric(df["diferenca_kg"] / df["peso_nota_fiscal"].replace(0, np.nan) * 100, errors="coerce")
    df["diferenca_percentual"] = df["diferenca_percentual"].replace([np.inf, -np.inf], np.nan).fillna(0).round(2)
    df["diferenca_kg"] = df["diferenca_kg"].round(2)
    df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")

    filtered = df[
        (df["diferenca_percentual"] > min_discrepancia) |
        (df["diferenca_percentual"] < -min_discrepancia)
    ].copy()
    filtered = filtered.sort_values(
        by=["probabilidade_risco_operacional", "score_anomalia_ia", "diferenca_percentual_abs"],
        ascending=False,
    )

    top_setor = "Não informado"
    top_entidade = "Não informado"
    if not filtered.empty:
        top_setor = (
            filtered.groupby("setor")["probabilidade_risco_operacional"]
            .mean()
            .sort_values(ascending=False)
            .index[0]
        )
        top_entidade = (
            filtered.groupby("fornecedor_cliente")["probabilidade_risco_operacional"]
            .mean()
            .sort_values(ascending=False)
            .index[0]
        )

    high_risk_count = int((filtered["probabilidade_risco_operacional"] >= 75).sum()) if not filtered.empty else 0
    anomaly_count = int((filtered["score_anomalia_ia"] >= 60).sum()) if not filtered.empty else 0
    summary = (
        "### IA aplicada à auditoria\n"
        f"- Registros analisados pelo modelo: **{len(df)}**.\n"
        f"- Registros acima do limite atual: **{len(filtered)}**.\n"
        f"- Casos classificados com risco operacional alto ou muito alto: **{high_risk_count}**.\n"
        f"- Casos marcados como anômalos ou muito anômalos: **{anomaly_count}**.\n"
        f"- Setor com maior risco médio: **{top_setor}**.\n"
        f"- Entidade com maior risco médio: **{top_entidade}**.\n"
        "- Leitura gerencial: a detecção de anomalias prioriza registros fora do padrão histórico, enquanto a classificação de risco estima a chance de discrepância operacional relevante."
    )

    display_columns = [
        "ticket",
        "data_hora",
        "fornecedor_cliente",
        "produto",
        "setor",
        "peso_embalagem_liquido_corrigido",
        "peso_nota_fiscal",
        "diferenca_kg",
        "diferenca_percentual",
        "score_anomalia_ia",
        "classificacao_anomalia_ia",
        "probabilidade_risco_operacional",
        "classificacao_risco_operacional",
    ]
    return {
        "available": True,
        "message": "",
        "data": filtered[display_columns],
        "summary": summary,
    }


def _cluster_name(quantity: float, secondary: float, quantity_median: float, secondary_median: float) -> str:
    high_quantity = quantity >= quantity_median
    high_secondary = secondary >= secondary_median
    if high_quantity and high_secondary:
        return "Alta demanda e maior carga"
    if high_quantity:
        return "Alta demanda e carga moderada"
    if high_secondary:
        return "Baixa demanda e carga elevada"
    return "Perfil operacional intermediário"


def _fit_cluster_result(df: pd.DataFrame, entity_col: str, feature_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    if not SKLEARN_AVAILABLE or len(df) < 3:
        df["cluster"] = "Sem agrupamento suficiente"
        return df

    matrix = df[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(matrix)
    cluster_count = min(3, len(df))
    if cluster_count < 2:
        df["cluster"] = "Sem agrupamento suficiente"
        return df

    model = KMeans(n_clusters=cluster_count, n_init=10, random_state=42)
    df["cluster_id"] = model.fit_predict(scaled)

    quantity_median = float(pd.to_numeric(df[feature_cols[0]], errors="coerce").median())
    secondary_median = float(pd.to_numeric(df[feature_cols[1]], errors="coerce").median())
    cluster_labels: dict[int, str] = {}
    for cluster_id in sorted(df["cluster_id"].unique()):
        subset = df[df["cluster_id"] == cluster_id]
        cluster_labels[cluster_id] = _cluster_name(
            float(pd.to_numeric(subset[feature_cols[0]], errors="coerce").mean()),
            float(pd.to_numeric(subset[feature_cols[1]], errors="coerce").mean()),
            quantity_median,
            secondary_median,
        )

    df["cluster"] = df["cluster_id"].map(cluster_labels)
    return df.drop(columns=["cluster_id"])


@cache.memoize(timeout=1800)
def get_setor_clustering_analysis() -> dict[str, Any]:
    query = """
    SELECT
        setor,
        COUNT(*) AS quantidade,
        AVG(peso_embalagem_liquido_corrigido) AS media_peso,
        SUM(peso_embalagem_liquido_corrigido) AS peso_total,
        AVG(ABS(((peso_embalagem_liquido_corrigido - peso_nota_fiscal) / NULLIF(peso_nota_fiscal, 0)) * 100)) AS discrepancia_media_abs
    FROM registro
    WHERE setor IS NOT NULL
      AND UPPER(COALESCE(setor, '')) NOT LIKE 'ACERTO%%'
      AND UPPER(COALESCE(setor, '')) NOT LIKE 'CANDIOTA%%'
    GROUP BY setor
    ORDER BY quantidade DESC
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return _unavailable_result("Ainda não há dados suficientes para agrupar setores.")

    for column in ["quantidade", "media_peso", "peso_total", "discrepancia_media_abs"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    clustered = _fit_cluster_result(df.copy(), "setor", ["quantidade", "media_peso", "peso_total", "discrepancia_media_abs"])
    summary = (
        "### IA aplicada aos setores\n"
        f"- Setores agrupados: **{len(clustered)}**.\n"
        f"- Perfis identificados: **{', '.join(sorted(clustered['cluster'].dropna().unique()))}**.\n"
        f"- Setor com maior peso total no agrupamento atual: **{clustered.sort_values('peso_total', ascending=False).iloc[0]['setor']}**.\n"
        "- Leitura gerencial: o clustering aproxima setores com comportamento parecido e ajuda a planejar atendimento, prioridade e frequência de operação por perfil."
    )
    return {"available": True, "message": "", "data": clustered, "summary": summary}


@cache.memoize(timeout=1800)
def get_empresa_clustering_analysis() -> dict[str, Any]:
    query = """
    SELECT
        fornecedor_cliente AS empresa,
        COUNT(*) AS quantidade,
        AVG(peso_embalagem_liquido_corrigido) AS media_peso,
        SUM(peso_embalagem_liquido_corrigido) AS peso_total,
        AVG(ABS(((peso_embalagem_liquido_corrigido - peso_nota_fiscal) / NULLIF(peso_nota_fiscal, 0)) * 100)) AS discrepancia_media_abs
    FROM registro
    WHERE fornecedor_cliente IS NOT NULL
      AND UPPER(COALESCE(setor, '')) NOT LIKE 'ACERTO%%'
      AND UPPER(COALESCE(setor, '')) NOT LIKE 'CANDIOTA%%'
    GROUP BY fornecedor_cliente
    ORDER BY quantidade DESC
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return _unavailable_result("Ainda não há dados suficientes para agrupar empresas.")

    for column in ["quantidade", "media_peso", "peso_total", "discrepancia_media_abs"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    clustered = _fit_cluster_result(df.copy(), "empresa", ["quantidade", "media_peso", "peso_total", "discrepancia_media_abs"])
    summary = (
        "### IA aplicada às empresas\n"
        f"- Empresas agrupadas: **{len(clustered)}**.\n"
        f"- Perfis identificados: **{', '.join(sorted(clustered['cluster'].dropna().unique()))}**.\n"
        f"- Empresa com maior peso total no agrupamento atual: **{clustered.sort_values('peso_total', ascending=False).iloc[0]['empresa']}**.\n"
        "- Leitura gerencial: o agrupamento separa empresas com padrões parecidos de volume, peso e discrepância, facilitando priorização institucional e auditoria dirigida."
    )
    return {"available": True, "message": "", "data": clustered, "summary": summary}
