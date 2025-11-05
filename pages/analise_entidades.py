from dash import dcc, html
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc

from database import engine

def fig_contagem_produtos():
    query = """
    SELECT 
        produto, 
        COUNT(*) as quantidade
    FROM registro 
    WHERE produto IS NOT NULL
    GROUP BY produto 
    ORDER BY quantidade DESC
    """
    df = pd.read_sql(query, engine)

    num_itens = len(df.index)
    dynamic_height = max(400, num_itens * 20)
    
    fig = px.bar(df, 
                 x='quantidade', 
                 y='produto',
                 orientation='h',
                 title="Volume de Registros por Produto")
    
    fig.update_layout(
        yaxis={'autorange': 'reversed'},
        height=dynamic_height
    )
    return fig


def fig_contagem_fornecedores():
    query = """
    SELECT 
        fornecedor_cliente, 
        COUNT(*) as quantidade
    FROM registro 
    WHERE fornecedor_cliente IS NOT NULL
    GROUP BY fornecedor_cliente 
    ORDER BY quantidade DESC
    """
    df = pd.read_sql(query, engine)

    num_itens = len(df.index)
    dynamic_height = max(400, num_itens * 20)
    
    fig = px.bar(df, 
                 x='quantidade', 
                 y='fornecedor_cliente', 
                 orientation='h',
                 title="Volume de Registros por Fornecedor/Cliente")
    
    fig.update_layout(
        yaxis={'autorange': 'reversed'},
        height=dynamic_height
    )
    return fig

layout = html.Div([
    html.H1('Análise de Produtos e Fornecedores'),
    html.P('Análises estáticas de volume por produto(aquilo que foi sendo coletado) e entidade(quem coletou).'),
    html.Hr(),
    
     dbc.Alert(
                [
                html.H5("O que estes gráficos respondem?", className="alert-heading"),
                html.P("Quais são nossos resíduos mais comuns e quais são os mais raros, em ordem? Quais empresas, entidades ou secretarias mais usam o nosso sistema de pesagem?")
                ],
            color="info", className="mb-3"
            ),

    dcc.Graph(
        id='grafico-contagem-produtos',
        figure=fig_contagem_produtos()
    ),
    
    html.Hr(),
    
    dcc.Graph(
        id='grafico-contagem-fornecedores',
        figure=fig_contagem_fornecedores()
    )
])