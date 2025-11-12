from dash import dcc, html
import dash_bootstrap_components as dbc
from flask_login import current_user


theme_switch = html.Div(
    [
        html.I(className="bi bi-moon-fill text-white me-2"), 
        dbc.Switch(
            id="theme-switch",
            value=True, 
            persistence=True,
            persistence_type="session",
            className="dbc_no_label"
        ),
        html.I(className="bi bi-sun-fill text-white ms-1"),
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
    className='sidebar navbar-dark bg-dark', 
    
    children=[
        html.Div(id='sidebar-content'), 
        
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


main_layout = html.Div([
    dcc.Location(id='url', refresh='callback'), 
    dcc.Store(id='sidebar-state', data='open', storage_type='session'), 
    
    sidebar_toggle_button,
    sidebar,
    content,
    
    
    html.Div(id='dummy-theme-output', style={'display': 'none'}) 
])