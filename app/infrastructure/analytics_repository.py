from app.database import engine
from app.services import data_repository


class SqlAnalyticsRepositoryAdapter:
    def get_engine(self):
        return engine

    def get_kpis_gerais(self):
        return data_repository.get_kpis_gerais()

    def get_qtde_por_ano(self):
        return data_repository.get_qtde_por_ano()

    def get_top_produtos_geral(self):
        return data_repository.get_top_produtos_geral()

    def get_volume_quinzenal(self, tipo_residuo="todos"):
        return data_repository.get_volume_quinzenal(tipo_residuo=tipo_residuo)

    def get_volume_mensal(self, tipo_residuo="todos"):
        return self.get_volume_quinzenal(tipo_residuo=tipo_residuo)

    def get_entradas_quinzenais(self, tipo_residuo="todos"):
        return data_repository.get_entradas_quinzenais(tipo_residuo=tipo_residuo)

    def get_entradas_mensais(self, tipo_residuo="todos"):
        return self.get_entradas_quinzenais(tipo_residuo=tipo_residuo)

    def get_saidas_quinzenais(self, tipo_residuo="todos"):
        return data_repository.get_saidas_quinzenais(tipo_residuo=tipo_residuo)

    def get_saidas_mensais(self, tipo_residuo="todos"):
        return self.get_saidas_quinzenais(tipo_residuo=tipo_residuo)

    def get_setor_volume_quinzenal(self, setor, tipo_residuo="todos"):
        return data_repository.get_setor_volume_quinzenal(setor, tipo_residuo=tipo_residuo)

    def get_setor_volume_mensal(self, setor, tipo_residuo="todos"):
        return self.get_setor_volume_quinzenal(setor, tipo_residuo=tipo_residuo)

    def get_list_setores(self):
        return data_repository.get_list_setores()

    def get_tipos_residuo_options(self):
        return data_repository.get_tipos_residuo_options()

    def get_dados_setores_macro(self):
        return data_repository.get_dados_setores_macro()

    def get_dados_setor_temporal(self, setor, ano):
        return data_repository.get_dados_setor_temporal(setor, ano)

    def get_ranking_empresas(self):
        return data_repository.get_ranking_empresas()

    def get_empresa_temporal(self, empresa, ano):
        return data_repository.get_empresa_temporal(empresa, ano)

    def get_ranking_produtos(self):
        return data_repository.get_ranking_produtos()

    def get_produtos_resumo(self):
        return data_repository.get_produtos_resumo()

    def get_fornecedores_por_produto(self, produto, limit=20):
        return data_repository.get_fornecedores_por_produto(produto, limit)

    def get_produtos_por_setor(self, setor, limit=20):
        return data_repository.get_produtos_por_setor(setor, limit)

    def get_fluxo_macro(self, tipo_residuo="todos"):
        return data_repository.get_fluxo_macro(tipo_residuo=tipo_residuo)

    def get_fluxo_micro(self, tipo_residuo="todos"):
        return data_repository.get_fluxo_micro(tipo_residuo=tipo_residuo)

    def get_heatmap_data(self):
        return data_repository.get_heatmap_data()

    def get_frota_data(self):
        return data_repository.get_frota_data()

    def get_produtos_options(self):
        return data_repository.get_produtos_options()

    def get_setores_options(self):
        return data_repository.get_setores_options()

    def get_anos_options(self):
        return data_repository.get_anos_options()

    def get_registros_filtrados(self, ano, mes, ticket):
        return data_repository.get_registros_filtrados(ano, mes, ticket)


_default_adapter = SqlAnalyticsRepositoryAdapter()


def get_engine():
    return _default_adapter.get_engine()


def get_kpis_gerais():
    return _default_adapter.get_kpis_gerais()


def get_qtde_por_ano():
    return _default_adapter.get_qtde_por_ano()


def get_top_produtos_geral():
    return _default_adapter.get_top_produtos_geral()


def get_volume_mensal(tipo_residuo="todos"):
    return _default_adapter.get_volume_mensal(tipo_residuo=tipo_residuo)


def get_entradas_mensais(tipo_residuo="todos"):
    return _default_adapter.get_entradas_mensais(tipo_residuo=tipo_residuo)


def get_saidas_mensais(tipo_residuo="todos"):
    return _default_adapter.get_saidas_mensais(tipo_residuo=tipo_residuo)


def get_setor_volume_mensal(setor, tipo_residuo="todos"):
    return _default_adapter.get_setor_volume_mensal(setor, tipo_residuo=tipo_residuo)


def get_list_setores():
    return _default_adapter.get_list_setores()


def get_tipos_residuo_options():
    return _default_adapter.get_tipos_residuo_options()


def get_dados_setores_macro():
    return _default_adapter.get_dados_setores_macro()


def get_dados_setor_temporal(setor, ano):
    return _default_adapter.get_dados_setor_temporal(setor, ano)


def get_ranking_empresas():
    return _default_adapter.get_ranking_empresas()


def get_empresa_temporal(empresa, ano):
    return _default_adapter.get_empresa_temporal(empresa, ano)


def get_ranking_produtos():
    return _default_adapter.get_ranking_produtos()


def get_produtos_resumo():
    return _default_adapter.get_produtos_resumo()


def get_fornecedores_por_produto(produto, limit=20):
    return _default_adapter.get_fornecedores_por_produto(produto, limit)


def get_produtos_por_setor(setor, limit=20):
    return _default_adapter.get_produtos_por_setor(setor, limit)


def get_fluxo_macro(tipo_residuo="todos"):
    return _default_adapter.get_fluxo_macro(tipo_residuo=tipo_residuo)


def get_fluxo_micro(tipo_residuo="todos"):
    return _default_adapter.get_fluxo_micro(tipo_residuo=tipo_residuo)


def get_heatmap_data():
    return _default_adapter.get_heatmap_data()


def get_frota_data():
    return _default_adapter.get_frota_data()


def get_produtos_options():
    return _default_adapter.get_produtos_options()


def get_setores_options():
    return _default_adapter.get_setores_options()


def get_anos_options():
    return _default_adapter.get_anos_options()


def get_registros_filtrados(ano, mes, ticket):
    return _default_adapter.get_registros_filtrados(ano, mes, ticket)
