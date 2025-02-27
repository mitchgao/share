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

# Clientside Callback
app.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks) return [{"base": 250}, ["tabler-chevron-left"]];
        return (n_clicks % 2 === 1) 
            ? [{"base": 0}, ["tabler-chevron-right"]] 
            : [{"base": 250}, ["tabler-chevron-left"]];
    }
    """,
    Output("navbar", "width"),
    Output("toggle-button", "icon"),
    Input("toggle-button", "n_clicks"),
)

if __name__ == "__main__":
    app.run_server(debug=True)
