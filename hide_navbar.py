import dash
from dash import dcc, html, Input, Output, ClientsideFunction
import dash_mantine_components as dmc

app = dash.Dash(__name__, suppress_callback_exceptions=True)

app.layout = dmc.MantineProvider(
    children=dmc.AppShell(
        navbar=dmc.AppShellNavbar(
            id="navbar",
            width={"base": 250},  # Default width
            style={"position": "relative", "transition": "width 0.3s ease"},
            children=[
                dmc.Text("Navigation Menu", size="lg", align="center"),
                dmc.Space(h=20),
                dmc.Button("Dashboard", fullWidth=True),
                dmc.Button("Settings", fullWidth=True, mt=10),
                
                # Floating Toggle Button
                dmc.ActionIcon(
                    id="toggle-button",
                    icon=[dmc.Icon("tabler-chevron-left", size=20)],
                    size="lg",
                    variant="light",
                    style={
                        "position": "absolute",
                        "top": "50%",
                        "right": "-15px",  # Moves outside the navbar
                        "transform": "translateY(-50%)",
                        "zIndex": 10, 
                        "backgroundColor": "white",
                        "border": "1px solid #ddd",
                        "borderRadius": "50%",
                        "boxShadow": "0px 0px 5px rgba(0,0,0,0.2)"
                    },
                ),
            ],
        ),
        children=dmc.Container(
            dmc.Text("Main Content Area", size="xl"), fluid=True
        ),
    )
)

@app.callback(
    Output("app-shell", "navbar"),
    Output("toggle-button", "children"),
    Input("toggle-button", "n_clicks"),
    State("app-shell", "navbar"),  # Get the current navbar dict
    prevent_initial_call=True,
)
def toggle_navbar(n_clicks, navbar):
    """ Updates the original navbar dictionary instead of creating a new one """
    navbar["collapsed"] = not navbar.get("collapsed", False)  # Toggle collapsed state
    icon = dmc.Icon("tabler-chevron-right" if navbar["collapsed"] else "tabler-chevron-left", size=20)
    return navbar, icon

if __name__ == "__main__":
    app.run_server(debug=True)
