import dash
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template

def create_dash_app(server):
    
    # Modernizando o tema: MINTY é fresco e moderno.
    url_theme = dbc.themes.MINTY
    template_theme = "minty"
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
    
    app.title = "VITTAL Transbordo | IFEsCS"

    
    from . import layout
    from . import callbacks
    
    app.layout = layout.main_layout 
    
    callbacks.register_global_callbacks(app)
    
    return app