import dash
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template

def create_dash_app(server):
    
    url_theme = dbc.themes.COSMO
    template_theme = "cosmo"
    load_figure_template([template_theme])
    dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"

    app = dash.Dash(
        __name__,
        server=server, 
        url_base_pathname='/', 
        suppress_callback_exceptions=True,
        external_stylesheets=[url_theme, dbc.icons.BOOTSTRAP, dbc_css],
        assets_folder='assets' 
    )
    
    app.title = "IFEsCS - Plataforma Web"

    
    from . import layout
    from . import callbacks
    
    app.layout = layout.main_layout 
    
    callbacks.register_global_callbacks(app)
    
    return app