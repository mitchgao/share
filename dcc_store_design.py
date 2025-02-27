import dash
import dash_mantine_components as dmc
import dash_ag_grid as dag
import plotly.express as px
import pandas as pd
import psycopg2
import os
import json
from dash import dcc, html, Input, Output, ctx
from flask import Flask, session
from flask_session import Session
from datetime import datetime

# Flask App for session management
server = Flask(__name__)
server.config["SESSION_TYPE"] = "filesystem"
server.config["SECRET_KEY"] = os.urandom(24)
Session(server)

# Dash App
app = dash.Dash(__name__, server=server, suppress_callback_exceptions=True)
app.title = "PostgreSQL Caching Demo"

# PostgreSQL Connection (Replace with your DB credentials)
DB_CONFIG = {
    "dbname": "your_db",
    "user": "your_user",
    "password": "your_password",
    "host": "your_host",
    "port": "your_port"
}

# Function to load data from PostgreSQL
def fetch_data():
    conn = psycopg2.connect(**DB_CONFIG)
    query = "SELECT * FROM your_table"  # Adjust query as needed
    df = pd.read_sql(query, conn)
    conn.close()
    return df.to_dict("records")

# Layout
app.layout = dmc.Container([
    dcc.Store(id="cached-data", storage_type="local"),  # Store data in localStorage
    dcc.Store(id="cache-date", storage_type="local"),   # Store cache date
    
    dmc.Title("PostgreSQL Data with Caching", order=1),
    dmc.Space(h=20),

    dmc.Text("Filter Data:"),
    dmc.TextInput(id="filter-text", placeholder="Type something to filter..."),
    
    dmc.Space(h=10),
    dag.AgGrid(
        id="data-table",
        columnDefs=[{"headerName": "Column1", "field": "column1"}, {"headerName": "Column2", "field": "column2"}],  
        rowData=[],
        dashGridOptions={"pagination": True, "paginationPageSize": 10},
    ),
    
    dmc.Space(h=20),
    dcc.Graph(id="data-chart")
])

# Callbacks
@app.callback(
    Output("cached-data", "data"),
    Output("cache-date", "data"),
    Input("cached-data", "data"),
    Input("cache-date", "data"),
    prevent_initial_call=True  # Ensures data is only fetched when needed
)
def load_data(cached_data, cache_date):
    today = datetime.now().strftime("%Y-%m-%d")

    if cache_date == today and cached_data:
        return cached_data, cache_date  # Use existing cache

    # Otherwise, fetch new data
    data = fetch_data()
    return data, today

@app.callback(
    Output("data-table", "rowData"),
    Output("data-chart", "figure"),
    Input("cached-data", "data"),
    Input("filter-text", "value")
)
def update_display(data, filter_text):
    if not data:
        return [], px.scatter()  # Return empty table and chart if no data

    df = pd.DataFrame(data)

    # Apply filtering
    if filter_text:
        df = df[df["column1"].astype(str).str.contains(filter_text, case=False, na=False)]

    # Update table and chart
    fig = px.scatter(df, x="column1", y="column2", title="Filtered Data")
    return df.to_dict("records"), fig

if __name__ == "__main__":
    app.run(debug=True)
