TYPE_ALL = "todos"

TYPE_OPTIONS = [
    {"label": "Todos os residuos", "value": TYPE_ALL},
    {"label": "Domiciliar", "value": "DOMICILIAR"},
    {"label": "Hospitalar", "value": "HOSPITALAR"},
    {"label": "Reciclavel", "value": "RECICLAVEL"},
    {"label": "Poda e vegetais", "value": "PODA_VEGETAIS"},
    {"label": "Entulho e construcao", "value": "ENTULHO_CONSTRUCAO"},
    {"label": "Volumoso e inservivel", "value": "VOLUMOSO_INSERVIVEL"},
    {"label": "Outros", "value": "OUTROS"},
]


def get_tipo_residuo_case_sql(produto_column: str = "produto") -> str:
    upper_col = f"UPPER(COALESCE({produto_column}, ''))"
    return f"""
        CASE
            WHEN {upper_col} LIKE '%HOSP%'
              OR {upper_col} LIKE '%RSS%'
              OR {upper_col} LIKE '%INFECT%'
              OR {upper_col} LIKE '%SAUDE%'
              OR {upper_col} LIKE '%AMBULAT%'
                THEN 'HOSPITALAR'
            WHEN {upper_col} LIKE '%DOMIC%'
              OR {upper_col} LIKE '%REJEITO%'
              OR {upper_col} LIKE '%ORGANIC%'
                THEN 'DOMICILIAR'
            WHEN {upper_col} LIKE '%RECIC%'
              OR {upper_col} LIKE '%SELET%'
              OR {upper_col} LIKE '%PAPEL%'
              OR {upper_col} LIKE '%PLASTIC%'
              OR {upper_col} LIKE '%VIDRO%'
              OR {upper_col} LIKE '%METAL%'
                THEN 'RECICLAVEL'
            WHEN {upper_col} LIKE '%PODA%'
              OR {upper_col} LIKE '%GALHO%'
              OR {upper_col} LIKE '%VEGET%'
                THEN 'PODA_VEGETAIS'
            WHEN {upper_col} LIKE '%ENTULHO%'
              OR {upper_col} LIKE '%CONSTRU%'
              OR {upper_col} LIKE '%RCD%'
                THEN 'ENTULHO_CONSTRUCAO'
            WHEN {upper_col} LIKE '%VOLUM%'
              OR {upper_col} LIKE '%INSERV%'
              OR {upper_col} LIKE '%MOVEI%'
              OR {upper_col} LIKE '%MOVEL%'
                THEN 'VOLUMOSO_INSERVIVEL'
            ELSE 'OUTROS'
        END
    """
