from typing import Protocol


class AnalyticsRepositoryPort(Protocol):
    def get_engine(self):
        ...

    def get_kpis_gerais(self):
        ...

    def get_qtde_por_ano(self):
        ...

    def get_top_produtos_geral(self):
        ...

    def get_volume_mensal(self):
        ...

    def get_entradas_mensais(self):
        ...

    def get_saidas_mensais(self):
        ...

    def get_setor_volume_mensal(self, setor):
        ...

    def get_list_setores(self):
        ...

    def get_dados_setores_macro(self):
        ...

    def get_dados_setor_temporal(self, setor, ano):
        ...

    def get_ranking_empresas(self):
        ...

    def get_empresa_temporal(self, empresa, ano):
        ...

    def get_ranking_produtos(self):
        ...

    def get_produtos_resumo(self):
        ...

    def get_fornecedores_por_produto(self, produto, limit=20):
        ...

    def get_produtos_por_setor(self, setor, limit=20):
        ...

    def get_fluxo_macro(self):
        ...

    def get_fluxo_micro(self):
        ...

    def get_heatmap_data(self):
        ...

    def get_frota_data(self):
        ...

    def get_produtos_options(self):
        ...

    def get_setores_options(self):
        ...

    def get_anos_options(self):
        ...

    def get_registros_filtrados(self, ano, mes, ticket):
        ...


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepositoryPort):
        self._repository = repository

    def get_engine(self):
        return self._repository.get_engine()

    def get_kpis_gerais(self):
        return self._repository.get_kpis_gerais()

    def get_qtde_por_ano(self):
        return self._repository.get_qtde_por_ano()

    def get_top_produtos_geral(self):
        return self._repository.get_top_produtos_geral()

    def get_volume_mensal(self):
        return self._repository.get_volume_mensal()

    def get_entradas_mensais(self):
        return self._repository.get_entradas_mensais()

    def get_saidas_mensais(self):
        return self._repository.get_saidas_mensais()

    def get_setor_volume_mensal(self, setor):
        return self._repository.get_setor_volume_mensal(setor)

    def get_list_setores(self):
        return self._repository.get_list_setores()

    def get_dados_setores_macro(self):
        return self._repository.get_dados_setores_macro()

    def get_dados_setor_temporal(self, setor, ano):
        return self._repository.get_dados_setor_temporal(setor, ano)

    def get_ranking_empresas(self):
        return self._repository.get_ranking_empresas()

    def get_empresa_temporal(self, empresa, ano):
        return self._repository.get_empresa_temporal(empresa, ano)

    def get_ranking_produtos(self):
        return self._repository.get_ranking_produtos()

    def get_produtos_resumo(self):
        return self._repository.get_produtos_resumo()

    def get_fornecedores_por_produto(self, produto, limit=20):
        return self._repository.get_fornecedores_por_produto(produto, limit)

    def get_produtos_por_setor(self, setor, limit=20):
        return self._repository.get_produtos_por_setor(setor, limit)

    def get_fluxo_macro(self):
        return self._repository.get_fluxo_macro()

    def get_fluxo_micro(self):
        return self._repository.get_fluxo_micro()

    def get_heatmap_data(self):
        return self._repository.get_heatmap_data()

    def get_frota_data(self):
        return self._repository.get_frota_data()

    def get_produtos_options(self):
        return self._repository.get_produtos_options()

    def get_setores_options(self):
        return self._repository.get_setores_options()

    def get_anos_options(self):
        return self._repository.get_anos_options()

    def get_registros_filtrados(self, ano, mes, ticket):
        return self._repository.get_registros_filtrados(ano, mes, ticket)


def build_default_analytics_service():
    from app.infrastructure.analytics_repository import SqlAnalyticsRepositoryAdapter

    return AnalyticsService(repository=SqlAnalyticsRepositoryAdapter())


_default_analytics_service = build_default_analytics_service()
engine = _default_analytics_service.get_engine()


def get_kpis_gerais():
    return _default_analytics_service.get_kpis_gerais()


def get_qtde_por_ano():
    return _default_analytics_service.get_qtde_por_ano()


def get_top_produtos_geral():
    return _default_analytics_service.get_top_produtos_geral()


def get_volume_mensal():
    return _default_analytics_service.get_volume_mensal()


def get_entradas_mensais():
    return _default_analytics_service.get_entradas_mensais()


def get_saidas_mensais():
    return _default_analytics_service.get_saidas_mensais()


def get_setor_volume_mensal(setor):
    return _default_analytics_service.get_setor_volume_mensal(setor)


def get_list_setores():
    return _default_analytics_service.get_list_setores()


def get_dados_setores_macro():
    return _default_analytics_service.get_dados_setores_macro()


def get_dados_setor_temporal(setor, ano):
    return _default_analytics_service.get_dados_setor_temporal(setor, ano)


def get_ranking_empresas():
    return _default_analytics_service.get_ranking_empresas()


def get_empresa_temporal(empresa, ano):
    return _default_analytics_service.get_empresa_temporal(empresa, ano)


def get_ranking_produtos():
    return _default_analytics_service.get_ranking_produtos()


def get_produtos_resumo():
    return _default_analytics_service.get_produtos_resumo()


def get_fornecedores_por_produto(produto, limit=20):
    return _default_analytics_service.get_fornecedores_por_produto(produto, limit)


def get_produtos_por_setor(setor, limit=20):
    return _default_analytics_service.get_produtos_por_setor(setor, limit)


def get_fluxo_macro():
    return _default_analytics_service.get_fluxo_macro()


def get_fluxo_micro():
    return _default_analytics_service.get_fluxo_micro()


def get_heatmap_data():
    return _default_analytics_service.get_heatmap_data()


def get_frota_data():
    return _default_analytics_service.get_frota_data()


def get_produtos_options():
    return _default_analytics_service.get_produtos_options()


def get_setores_options():
    return _default_analytics_service.get_setores_options()


def get_anos_options():
    return _default_analytics_service.get_anos_options()


def get_registros_filtrados(ano, mes, ticket):
    return _default_analytics_service.get_registros_filtrados(ano, mes, ticket)
