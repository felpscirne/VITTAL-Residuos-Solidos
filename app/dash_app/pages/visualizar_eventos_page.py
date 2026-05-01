import dash
from dash import dcc, html, callback, dash_table
from dash.dependencies import Input, Output
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from app.models import Event

# --- Layout ---
layout = html.Div([
    dmc.Title('Mural de Eventos Operacionais', order=2),
    dmc.Text('Quadro geral de avisos, manutenções e paradas.', c="dimmed", size="sm"),
    dmc.Divider(variant="solid", my="md"),

    dmc.Card(
        children=[
            dmc.Text("Histórico de Eventos", size="lg", fw=500, mb="sm"),
            dmc.ScrollArea(
                dash_table.DataTable(
                    id='view-table-events',
                    columns=[
                        {'name': 'Data Início', 'id': 'start'},
                        {'name': 'Data Fim', 'id': 'end'},
                        {'name': 'Título', 'id': 'title'},
                        {'name': 'Tipo', 'id': 'type'},
                        {'name': 'Descrição', 'id': 'description'},
                        {'name': 'Setores Afetados', 'id': 'sectors'},
                    ],
                    data=[],
                    row_selectable=False, # Não selecionável, apenas leitura
                    style_table={'minWidth': '100%'},
                    style_header={
                        "backgroundColor": "#f8f9fa", 
                        "color": "#000", 
                        "fontWeight": "bold", 
                        "fontFamily": "sans-serif"
                    },
                    style_data={
                        "backgroundColor": "#fff", 
                        "color": "#000",
                        "fontFamily": "sans-serif",
                        "whiteSpace": "normal",
                        "height": "auto",
                    },
                    style_cell={'textAlign': 'left', 'padding': '10px', 'border': '1px solid #dee2e6'},
                ),
                offsetScrollbars=True,
                type="auto"
            )
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        mb="md"
    ),
    
    # Auto-refresh interval (opcional, para ser um mural vivo)
    dcc.Interval(id='view-interval-events', interval=30000, n_intervals=0) # 30s
])

@callback(
    Output('view-table-events', 'data'),
    [Input('url', 'pathname'),
     Input('view-interval-events', 'n_intervals')]
)
def update_view_events(pathname, n):
    try:
        events = Event.query.order_by(Event.start_date.desc()).all()  
        data = []
        for e in events:
            data.append({
                'start': e.start_date.strftime('%d/%m/%Y'),          
                'end': e.end_date.strftime('%d/%m/%Y'),               
                'title': e.title,
                'type': e.event_type,                                 
                'description': e.description or "",
                'sectors': e.affected_sectors or "Geral"              
            })
        return data
    except Exception as e:
        print(f"Erro ao carregar eventos: {e}")
        return []
