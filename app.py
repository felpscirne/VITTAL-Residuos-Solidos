import dash
from dash import dcc, html, Input, Output, ClientsideFunction
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
import plotly.io as pio 

url_theme = dbc.themes.COSMO
template_theme = "cosmo"

load_figure_template([template_theme])

dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"

app = dash.Dash(__name__, 
                suppress_callback_exceptions=True,
                external_stylesheets=[url_theme, dbc.icons.BOOTSTRAP, dbc_css])

app.title = "IFEsCS - Plataforma Web"
server = app.server

theme_switch = html.Div(
    [
        html.I(className="bi bi-moon-fill me-2"), 
        dbc.Switch(
            id="theme-switch",
            value=True, # Começa no modo claro
            persistence=True,
            persistence_type="session",
            className="dbc_no_label"
        ),
        html.I(className="bi bi-sun-fill ms-1"),
    ],
    className="d-flex align-items-center"
)

sidebar_toggle_button = dbc.Button(
    html.I(className="bi bi-list", style={'fontSize': '1.5rem'}),
    id='btn-collapse',
    n_clicks=0,
    outline=True,
    color="secondary",
)

sidebar = html.Div(
    id='sidebar',
   
    className='sidebar navbar-primary bg-primary',
    
    children=[
        html.Div([
            html.H2("IFEsCS", className="text-white"),
            html.Hr(className="text-white"),
            dbc.Nav(
                [
                    dbc.NavLink('Visão Geral', href='/', active="exact"),
                    dbc.NavLink('Análise por Mês', href='/analise-por-mes', active="exact"),
                    dbc.NavLink('Média por Setor (Temporal)', href='/media-por-setor', active="exact"), 
                    dbc.NavLink('Visão Geral Setores', href='/analise-setores', active="exact"),
                    dbc.NavLink('Produtos e Fornecedores', href='/analise-entidades', active="exact"),
                    dbc.NavLink('Buscar Registros', href='/registros', active="exact"),
                ],
                vertical=True,
                pills=True,
            )
        ], className="flex-grow-1"),
        
        html.Div(
            theme_switch,
            className="w-100 d-flex justify-content-center"
        )
    ]
)

content = html.Div(
    id='page-content',
    className='content',
    children=[
        html.Div(id='page-content-dynamic') 
    ]
)

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='sidebar-state', data='open', storage_type='session'), 
    sidebar_toggle_button,
    sidebar,
    content,
    html.Div(id='dummy-theme-output', style={'display': 'none'}) 
])


app.clientside_callback(
    """
    function(switch_on) {
        // 'switch_on' é True para claro, False para escuro
        var theme = switch_on ? 'light' : 'dark';
        // Define o atributo no <html> tag
        document.documentElement.setAttribute('data-bs-theme', theme);
        return window.dash_clientside.no_update;
    }
    """,
    Output('dummy-theme-output', 'children'), 
    Input("theme-switch", "value")
)