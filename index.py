from dash import html
from dash.dependencies import Input, Output


from app import app, server 

from pages import overview, qtde_por_ano, media_por_setor, produtos
# from pages import media_por_setor, produtos 


@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == '/qtde-por-ano':
        return qtde_por_ano.layout
    
    elif pathname == '/media-por-setor':
        return media_por_setor.layout
    elif pathname == '/produtos':
        return produtos.layout
    
    elif pathname == '/':
        return overview.layout 
    
    else:
        return html.Div([
            html.H1('404: Página não encontrada'),
            html.P(f'O caminho "{pathname}" não foi reconhecido.')
        ])

if __name__ == '__main__':
    app.run(debug=True)


    # run
    #  python3.12 -m venv .venv
    # . .venv/bin/activate    //  .venv\Scripts\activate
    # pip3 install -r requirements.txt
    # python index.py