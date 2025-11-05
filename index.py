import dash  
from dash import html
from dash.dependencies import Input, Output, State
from app import app, server

from pages import (
    analise_empresas,
    analise_produtos,
    overview, 
    analise_setores, 
    registros,
    fluxo_de_caixa
)


@app.callback(
    [Output('sidebar', 'className'),
     Output('page-content', 'className'),
     Output('sidebar-state', 'data')],
    [Input('btn-collapse', 'n_clicks')],
    [State('sidebar-state', 'data')]
)
def toggle_sidebar_collapse(n, current_state):
    
    ctx = dash.callback_context 
    if not ctx.triggered:
        if current_state == 'collapsed':
            return 'sidebar navbar-dark bg-dark collapsed', 'content collapsed', 'collapsed'
        else:
            return 'sidebar navbar-dark bg-dark', 'content', 'open'

    if current_state == 'open':
        return 'sidebar navbar-dark bg-dark collapsed', 'content collapsed', 'collapsed'
    else: 
        return 'sidebar navbar-dark bg-dark', 'content', 'open'
        
        
@app.callback(
    Output('page-content-dynamic', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == '/analise-empresas':
        return analise_empresas.layout
    
    elif pathname == '/analise-setores':
        return analise_setores.layout
    
    elif pathname == '/analise-produtos':
        return analise_produtos.layout
        
    elif pathname == '/registros':
        return registros.layout
    elif pathname == '/fluxo-de-caixa':
        return fluxo_de_caixa.layout
    
    elif pathname == '/':
        return overview.layout
    
    else:
        return html.Div([
            html.H1('404: Página não encontrada'),
            html.P(f'O caminho "{pathname}" não foi reconhecido.')
        ])

if __name__ == '__main__':
    app.run(debug=True)