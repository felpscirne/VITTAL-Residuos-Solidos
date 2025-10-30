import dash
from dash import dcc, html

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "IFEsCS - Plataforma Web"
server = app.server

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    
    # menu lateral
    html.Div(className='sidebar', children=[
        html.H2("IFEsCS"),
        html.Hr(),
        dcc.Link('Visão Geral', href='/'),
        dcc.Link('Produtos e Fornecedores', href='/analise-entidades'),
        dcc.Link('Visão Geral Setores', href='/analise-setores'),
        dcc.Link('Média por Setor (Temporal)', href='/media-por-setor'),
        dcc.Link('Análise Por Mês', href='/qtde-por-mes'),

    ]),
    
    html.Div(id='page-content', className='content')
])