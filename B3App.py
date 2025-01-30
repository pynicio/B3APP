# -*- coding: utf-8 -*-
# @Author: Your name
# @Date:   2025-01-27 22:35:33
# @Last Modified by:   Your name
# @Last Modified time: 2025-01-29 15:55:46
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State
import dash  # Import the dash module for callback_context
import numpy as np
import dash_bootstrap_components as dbc

# Load the data from the CSV file
file_path = "b3.csv"
df = pd.read_csv(file_path, delimiter=";")

# Step 1: Clean and Reformat the Data

# A. Exclude unnecessary columns
columns_to_drop = [
    "DataReferencia", "AcaoAtualizacao", "CodigoIdentificadorNegocio",
    "TipoSessaoPregao", "CodigoParticipanteComprador", "CodigoParticipanteVendedor"
]
df = df.drop(columns=columns_to_drop)

# B. Exclude rows where 'CodigoInstrumento' has more than 5 characters
df = df[df["CodigoInstrumento"].str.len() <= 5]

# C. Reformat 'HoraFechamento' from xxxxxxxx to a proper time format
def reformat_hora_fechamento(hora):
    hora_str = str(hora).zfill(8)  # Ensure 8 digits (pad with leading zeros if necessary)
    # Extract hours, minutes, seconds, and milliseconds
    hours = int(hora_str[:2])
    minutes = int(hora_str[2:4])
    seconds = int(hora_str[4:6])
    milliseconds = int(hora_str[6:])
    
    # Validate time components
    if hours > 23 or minutes > 59 or seconds > 59:
        return None  # Invalid time, return None
    else:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:02d}"

df["HoraFechamento"] = df["HoraFechamento"].apply(reformat_hora_fechamento)

# Drop rows with invalid time values
df = df.dropna(subset=["HoraFechamento"])

# Convert 'HoraFechamento' to a datetime object for proper sorting and plotting
df["HoraFechamento"] = pd.to_datetime(df["HoraFechamento"], format="%H:%M:%S.%f")

# D. Reformat 'DataNegocio' from YYYY-MM-DD to DD-MM-YYYY
df["DataNegocio"] = pd.to_datetime(df["DataNegocio"]).dt.strftime("%d-%m-%Y")

# Fix the 'PrecoNegocio' column
# Replace commas with periods and convert to numeric
df["PrecoNegocio"] = df["PrecoNegocio"].str.replace(",", ".").astype(float)

# Step 2: Create a Dash Application

# Initialize the Dash app with Bootstrap
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # This line is crucial

# Calculate the mean price and count of transactions for each stock
mean_prices = df.groupby("CodigoInstrumento")["PrecoNegocio"].mean().round(2)
transaction_counts = df.groupby("CodigoInstrumento").size()

# Sort the stock codes by their mean price in ascending order
sorted_codigos_instrumento = mean_prices.sort_values().index.tolist()

# Layout of the app
app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Stock Price Analysis", className="text-center"))),
    dbc.Row([
        dbc.Col([
            html.Label("Select CodigoInstrumento:"),
            dcc.Dropdown(
                id="codigo-dropdown",
                options=[{"label": f"{codigo} (Mean: {mean_prices[codigo]}, Count: {transaction_counts[codigo]})", "value": codigo} for codigo in sorted_codigos_instrumento],
                value=None,  # No default value
                clearable=False,
            ),
            dbc.Button("Add Stock", id="add-stock-button", color="primary", className="mt-2"),
            dbc.Button("Clear All Stocks", id="clear-stocks-button", color="danger", className="mt-2"),
        ], width=4),
        dbc.Col([
            dcc.Checklist(
                id="stock-checklist",
                options=[],  # Will be populated dynamically
                value=[],  # No default value
                labelStyle={"display": "block"},  # Display checklist items vertically
            ),
        ], width=4),
    ]),
    dbc.Row(dbc.Col(dcc.Graph(id="price-plot"))),
])

# Callback to update the checklist and plot
@app.callback(
    [Output("stock-checklist", "options"),
     Output("stock-checklist", "value"),
     Output("price-plot", "figure")],
    [Input("add-stock-button", "n_clicks"),
     Input("clear-stocks-button", "n_clicks"),
     Input("stock-checklist", "value")],
    [State("codigo-dropdown", "value"),
     State("stock-checklist", "options")]
)
def update_plot(add_clicks, clear_clicks, selected_stocks, selected_codigo, checklist_options):
    # Initialize figure
    fig = px.line(title="PrecoNegocio vs HoraFechamento")

    # Initialize clicks if they are None
    if add_clicks is None:
        add_clicks = 0
    if clear_clicks is None:
        clear_clicks = 0

    # Use dash.callback_context to determine which button was clicked
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = None
    else:
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Clear all stocks if the clear button is clicked
    if button_id == "clear-stocks-button":
        checklist_options = []
        selected_stocks = []
    # Add stocks to the checklist when the "Add Stock" button is clicked
    elif button_id == "add-stock-button" and selected_codigo:
        # Add the selected stock to the checklist if it's not already there
        if selected_codigo not in [option["value"] for option in checklist_options]:
            checklist_options.append({"label": f"{selected_codigo} (Mean: {mean_prices[selected_codigo]}, Count: {transaction_counts[selected_codigo]})", "value": selected_codigo})
            selected_stocks.append(selected_codigo)

    # Plot the selected stocks
    for stock in selected_stocks:
        filtered_df = df[df["CodigoInstrumento"] == stock]
        # Sort by 'HoraFechamento' to ensure chronological order
        filtered_df = filtered_df.sort_values(by="HoraFechamento")
        fig.add_scatter(
            x=filtered_df["HoraFechamento"],
            y=filtered_df["PrecoNegocio"],
            mode="lines",
            name=f"{stock}",
        )

    # Ensure the time axis is continuous and shared
    fig.update_xaxes(
        title="HoraFechamento",
        type="date",  # Treat time as a continuous datetime axis
        tickformat="%H:%M:%S.%f",  # Format the time display
    )
    fig.update_yaxes(title="PrecoNegocio")

    # Add a vertical sliding axis (crosshair)
    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",  # Show hover information for all traces at the same x-value
    )

    return checklist_options, selected_stocks, fig

# Run the app
if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=int(os.environ.get('PORT', 8050)))

