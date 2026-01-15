from dash import dcc, html, clientside_callback, Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify

# --- Header ---
header = dmc.AppShellHeader(
    px=25,
    children=[
        dmc.Group(
            justify="space-between",
            align="center",
            h="100%",
            children=[
                dmc.Group(
                    h="100%",
                    children=[
                        dmc.Burger(id="burger-button", hiddenFrom="sm"),
                        dmc.Text("IFEsCS Dashboard", size="xl", fw=700, c="blue"),
                    ],
                ),
                dmc.Group(
                    children=[
                       dmc.ActionIcon(
                            DashIconify(icon="radix-icons:moon", width=20),
                            size="lg",
                            variant="subtle",
                            id="color-scheme-toggle",
                            n_clicks=0,
                        ), 
                    ]
                )
            ],
        )
    ],
)

# --- Navbar (Sidebar) ---
navbar = dmc.AppShellNavbar(
    p="md",
    children=[
        html.Div(id="sidebar-content")
    ],
)

# --- Main Layout ---
main_layout = dmc.MantineProvider(
    id="mantine-provider",
    forceColorScheme="light",
    theme={
        "primaryColor": "blue",
        "fontFamily": "'Inter', sans-serif",
        "components": {
            "Button": {"defaultProps": {"fw": 400}},
            "Container": {"defaultProps": {"size": "xl"}},
        },
    },
    children=[
        dcc.Location(id='url', refresh='callback'),
        dcc.Store(id='sidebar-state', data='open', storage_type='session'),
        
        dmc.AppShell(
            [
                header,
                navbar,
                dmc.AppShellMain(children=[html.Div(id='page-content-dynamic')]),
            ],
            header={"height": 60},
            navbar={
                "width": 300,
                "breakpoint": "sm",
                "collapsed": {"mobile": True},
            },
            padding="md",
            id="app-shell",
        ),
        
        html.Div(id='dummy-theme-output', style={'display': 'none'}) 
    ]
)

clientside_callback(
    """
    function(n_clicks) {
        return (n_clicks % 2 === 0) ? "light" : "dark";
    }
    """,
    Output("mantine-provider", "forceColorScheme"),
    Input("color-scheme-toggle", "n_clicks"),
)

clientside_callback(
    """
    function(n_clicks, collapsed) {
        return !collapsed;
    }
    """,
    Output("app-shell", "navbar"),
    Input("burger-button", "n_clicks"),
    State("app-shell", "navbar"),
)
