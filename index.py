from dash import html
from dash.dependencies import Input, Output


from app import app, server 

from pages import overview, qtde_por_mes
# from pages import media_por_setor, produtos 


@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == '/qtde-por-mes':
        return qtde_por_mes.layout
    
    # elif pathname == '/media-por-setor':
    #     return media_por_setor.layout 
    
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
    # . .venv/bin/activate
    # pip3 install -r requirements.txt
    # python index.py