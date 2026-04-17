from dash import dcc, html, clientside_callback, Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify

# --- Header Content ---
header_content = dmc.Group(
    justify="space-between",
    align="center",
    h="100%",
    px="md",
    children=[
        dmc.Group(
            children=[
                dmc.Burger(id="burger-button", hiddenFrom="sm"),
                dcc.Link(
                    dmc.Group(
                        gap="xs",
                        children=[
                            html.Img(src="/assets/favicon.ico", style={"height": "30px", "objectFit": "contain"}),
                            dmc.Stack(
                                gap=0,
                                children=[
                                    dmc.Text("VITTAL Transbordo", size="md", fw=700, c="ifsc-green", lh=1.2),
                                    dmc.Text("IFEsCS · IFRS Campus Rio Grande", size="xs", c="dimmed", lh=1.2),
                                ]
                            )
                        ]
                    ),
                    href="/",
                    style={"textDecoration": "none", "color": "inherit"}
                ),
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

# --- Navbar (Sidebar) ---
navbar = dmc.AppShellNavbar(
    p="md",
    children=[
        html.Div(id="sidebar-content")
    ],
    withBorder=True,
    zIndex=100
)

# --- Header Shell ---
header = dmc.AppShellHeader(
    children=header_content,
    zIndex=101
)

# --- Main Layout ---
main_layout = dmc.MantineProvider(
    id="mantine-provider",
    forceColorScheme="light",
    theme={
        "primaryColor": "ifsc-green",
        "colors": {
            "ifsc-green": [
                "#e8f5e9",
                "#c8e6c9",
                "#a5d6a7",
                "#81c784",
                "#66bb6a",
                "#4caf50",
                "#43a047",
                "#2e7d32",
                "#1b5e20",
                "#1b5e20"
            ]
        },
        "fontFamily": "'Inter', sans-serif",
        "components": {
            "Button": {"defaultProps": {"fw": 400}},
            "Container": {"defaultProps": {"size": "xl"}},
        },
    },
    children=[
        dcc.Location(id='url', refresh='callback'),
        dcc.Store(id='theme-store', data='light', storage_type='local'),
        
        dmc.AppShell(
            children=[
                header,
                navbar,
                dmc.AppShellMain(children=[
                    html.Div(id='page-content-dynamic')
                ]),
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
        html.Div(
            id="mobile-nav-overlay",
            n_clicks=0,
            style={"display": "none"},
        ),
        html.Div(
            id="mobile-nav-panel",
            children=[
                dmc.Group(
                    justify="space-between",
                    align="center",
                    mb="md",
                    children=[
                        dmc.Text("Menu", fw=700, size="lg", c="ifsc-green"),
                        dmc.ActionIcon(
                            DashIconify(icon="radix-icons:cross-1", width=18),
                            id="mobile-nav-close",
                            variant="subtle",
                            color="gray",
                            n_clicks=0,
                        ),
                    ],
                ),
                html.Div(id="mobile-sidebar-content"),
            ],
            style={"display": "none"},
        ),
        
        html.Div(id='dummy-theme-output', style={'display': 'none'}) 
    ]
)

clientside_callback(
    """
    function(data) {
        return data || 'light';
    }
    """,
    Output("mantine-provider", "forceColorScheme"),
    Input("theme-store", "data"),
)

clientside_callback(
    """
    function(n_clicks, data) {
        return data === "dark" ? "light" : "dark";
    }
    """,
    Output("theme-store", "data"),
    Input("color-scheme-toggle", "n_clicks"),
    State("theme-store", "data"),
    prevent_initial_call=True,
)

