import dash
from dash import Dash, html, dcc, callback 
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime as dt
from datetime import date
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os
from dotenv import load_dotenv 

# register this as a page in the app
dash.register_page(__name__)

# set a try except clause to grab the online credentials keys and if not, grab them locally as environment variables
try:
    # set the key vault path
    KEY_VAULT_URL = "https://fsdh-swapit-dw1-poc-kv.vault.azure.net/"
    error_occur = False

    # Retrieve the secrets containing DB connection details
    credential = DefaultAzureCredential()
    secret_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)

    # Retrieve the secrets containing DB connection details
    DB_HOST = secret_client.get_secret("datahub-psql-server").value
    DB_NAME = secret_client.get_secret("datahub-psql-dbname").value
    DB_USER = secret_client.get_secret("datahub-psql-user").value
    DB_PASS = secret_client.get_secret("datahub-psql-password").value
    print ('Credentials loaded from FSDH')

except Exception as e:
    # declare FSDH keys exception
    error_occur = True
    print(f"An error occurred: {e}")

    # load the .env file using the dotenv module remove this when running a powershell script to confirue system environment vars
    load_dotenv() # default is relative local directory 
    env_path='.env'
    DB_HOST = os.getenv('DATAHUB_PSQL_SERVER')
    DB_NAME = os.getenv('DATAHUB_PSQL_DBNAME')
    DB_USER = os.getenv('DATAHUB_PSQL_USER')
    DB_PASS = os.getenv('DATAHUB_PSQL_PASSWORD')
    print ('Credentials loaded locally')

# set the sql engine string
sql_engine_string=('postgresql://{}:{}@{}/{}?sslmode=require').format(DB_USER,DB_PASS,DB_HOST,DB_NAME)
print ('sql engine string: ',sql_engine_string)
sql_engine=create_engine(sql_engine_string)


# sql query
sql_query="""
SET TIME ZONE 'GMT';
SELECT DISTINCT ON (datetime) * FROM (
	SELECT date_trunc('minute',datetime) AS datetime, co_r AS co, co2_r/1e3 AS co2, ch4_r AS ch4
	FROM cru__g2401m_v0
	WHERE co_r IS NOT NULL
	AND datetime >= '2024-03-01' AND datetime < '2024-03-01 01:00:00'
) AS g2401_
ORDER BY datetime;
"""
# create the dataframe from the sql query
g2401_output_df=pd.read_sql_query(sql_query, con=sql_engine)

# print (g2401_output_df)

g2401_output_df.set_index('datetime', inplace=True)
g2401_output_df.index=pd.to_datetime(g2401_output_df.index)
beginning_date=g2401_output_df.index[0]
ending_date=g2401_output_df.index[-1]
today=dt.today().strftime('%Y-%m-%d')
print(beginning_date, ending_date)
# use specs parameter in make_subplots function
# to create secondary y-axis


# plot a scatter chart by specifying the x and y values
# Use add_trace function to specify secondary_y axes.
def create_figure(g2401_output_df):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=g2401_output_df.index, y=g2401_output_df['co'], name="CO"),
        secondary_y=False)
    
    # Use add_trace function and specify secondary_y axes = True.
    fig.add_trace(
        go.Scatter(x=g2401_output_df.index, y=g2401_output_df['ch4'], name="CH4"),
        secondary_y=True,)

    # set axis titles
    fig.update_layout(
        template='simple_white',
        title='Cruiser G2401 Data',
        xaxis_title="Date",
        yaxis_title="CO",
        yaxis2_title="CH4",
        legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01
    )   
    )
    return fig

# set up the app layout
layout = html.Div(children=
                    [
                    html.H1(children=['SWAPIT Cruiser G2401 Dashboard']),
                    html.Div(children=['Cruiser G2401 plot display with date picker']),

                    dcc.DatePickerRange(
                        id='my-date-picker-range',
                        min_date_allowed=beginning_date,
                        max_date_allowed=ending_date
                    ),
                    dcc.Graph(id='cru-g2401-plot',figure=create_figure(g2401_output_df)),
                    
                    ] 
                    )

# @app.callback(
#     Output('graph_2', 'figure'),
#     [Input('date-picker', 'start_date'),
#     Input('date-picker', 'end_date')],
#     [State('submit_button', 'n_clicks')])

@callback(
    Output('cru-g2401-plot', 'figure'),
    Input('my-date-picker-range', 'start_date'),
    Input('my-date-picker-range', 'end_date'))

def update_output(start_date, end_date):
    print (start_date, end_date)
    if not start_date or not end_date:
        raise PreventUpdate
    else:
        output_selected_df = g2401_output_df.loc[
            (g2401_output_df.index >= start_date) & (g2401_output_df.index <= end_date), :
        ]
        return create_figure(output_selected_df)


# if __name__=='__main__':
#     app.run(debug=True)
