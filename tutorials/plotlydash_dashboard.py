"""
Create a dashboard using plotly dash open source version. It will generate the same dashboard
which is generated using voila notebook

Pre-requisite
    - dash
    - dash_flexbox_grid
    - dash-leaflet
    - dash_extensions
    - jsbeautifier
"""

import dash_flexbox_grid as dfx
import dash_html_components as html
import dash_core_components as dcc
import dash_leaflet as dl
from dash import Dash
from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
from dash_extensions.javascript import assign
import plotly.express as px
import pandas as pd
from dashboard.evdata import EVStation, TrafficMessage, get_partition_list, nearest_messages, empty_geojson

# initialize EV and traffic data
ev = EVStation()
traffic = TrafficMessage()

# Geojson layer style.
point_to_layer_traffic = assign("""function(feature, latlng, context) {
                           circle = L.circle(latlng, radius=3);
                           circle.setStyle({color: '#424344'});
                        return circle;}""")

# Geojson layer style.
point_to_layer_ev = assign("""function(feature, latlng, context) {
                           circle = L.circle(latlng, radius=20);
                           circle.setStyle({color: '#c20326'});
                        return circle;}""")

app = Dash('')
app.scripts.config.serve_locally = True


def get_info(feature=None):
    """
    Information panel for charging station

    :param feature:
    :return:
    """
    header = [html.H3("EV Charging Station Details"), html.P()]
    if not feature:
        return header + [html.P("Hoover over a Charging Station")]

    return header + [html.B("Station Name:{}".format(feature["properties"]["name"])), html.Br(), html.Br(),
                     "Language Code: {}".format(feature['properties']['description']), html.Br(), html.Br(),
                     "Operating Days:{}".format(feature['properties']['days']), html.Br(),
                     ]

# HTML element for information
info = html.Div(children=get_info(), id="info", className="info",
                style={"position": "absolute", "top": "10px", "right": "10px", "z-index": "1000"})

# Layout for map, and chart elements
app.layout = dfx.Grid(id='grid', fluid=True, children=[
    dfx.Row(children=[html.H3("EV Charging Station Demo Dashboard"), html.P()]),
    dfx.Row(children=[
        dfx.Col(xs=12, lg=24, children=[
            html.Div([
                # Setup a map with the edit control.
                dl.Map(center=[52.5, 13.3], zoom=14, children=[dl.TileLayer(),
                                                               dl.GeoJSON(id="geo_traffic", options=dict(
                                                                   pointToLayer=point_to_layer_traffic)),
                                                               dl.GeoJSON(id="geo_ev",
                                                                          options=dict(pointToLayer=point_to_layer_ev)),
                                                               info,
                                                               dl.FeatureGroup([
                                                                   dl.EditControl(id="edit_control")]),
                                                               ],
                       style={'width': '100%', 'height': '50vh', 'margin': "auto", "display": "inline-block"},
                       id="map"),

            ])
        ])
    ]),
    dfx.Row(children=[
        dfx.Col(xs=6, lg=6, children=html.P("Sum of Traffic Flow Messages/EV Station",
                                            style={'text-align': 'center', 'font-size': '25px'})),
        dfx.Col(xs=6, lg=6,
                children=html.P("EV Station Companies", style={'text-align': 'center', 'font-size': '25px'}))
    ]),
    dfx.Row(children=[
        dfx.Col(xs=6, lg=6, children=html.Div([dcc.Graph(id="bar-chart")])),
        dfx.Col(xs=6, lg=6, children=html.Div([dcc.Graph(id="pie-chart")]))
    ])
])


@app.callback(Output("info", "children"), [Input("geo_ev", "hover_feature")])
def info_hover(feature):
    """
    Generate Information Panel

    :param feature:
    :return:
    """
    return get_info(feature)


@app.callback([Output("geo_traffic", "data"),
               Output("geo_ev", "data"),
               Output("pie-chart", "figure"),
               Output("bar-chart", "figure")],
              [Input("edit_control", "geojson"), Input("edit_control", "action")])
def ev_station(geo, action):
    """
    This called after drawing a rectangle on the map, geo is geojson of the drawn control on the map
    and action is event generated e.g. drawstart of rectangle etc.

    :param geo:
    :param action:
    :return:
    """
    # clear map id delete action is taken
    if action and action['type'] == 'draw:deletestop':
        return clear_map()
    # if geojson is null or empty features, do not update
    elif not geo or len(geo['features']) == 0 or not action:
        raise PreventUpdate
    # if layer_type is not present, , do not update 
    elif action and not 'layer_type' in action:
        raise PreventUpdate
    # if rectangle drawn on the map then compute and draw data on the map and update charts
    elif action and action['layer_type'] == 'rectangle' and action['type'] == 'draw:drawstop':
        # compute coordinates of the rectangle
        x1 = geo['features'][0]['properties']['_bounds'][0]['lat']
        y1 = geo['features'][0]['properties']['_bounds'][0]['lng']
        x2 = geo['features'][0]['properties']['_bounds'][1]['lat']
        y2 = geo['features'][0]['properties']['_bounds'][1]['lng']

        p_list = get_partition_list(y1, x1, y2, x2)
        geo_ev = ev.get_geojson(p_list, y1, x1, y2, x2)
        pie_fig = pie_chart(ev.data)
        geo_tr = traffic.get_geojson(p_list, y1, x1, y2, x2)
        bar_fig = bar_chart(ev.data, traffic.data)

        return geo_tr, geo_ev, pie_fig, bar_fig

    else:
        raise PreventUpdate


def clear_map():
    """
    Clear map

    :return:
    """
    df_empty = pd.DataFrame({'name': [], 'values': []})
    pie_fig = px.pie(df_empty, values='values', names='name')
    fig = px.bar(df_empty, x="name", y="values", labels={
        "name": "",
        "values": "",
    },
                 )
    return empty_geojson(), empty_geojson(), pie_fig, fig


def pie_chart(df):
    """
    Generate a Pie Chart figure

    :param df:
    :return:
    """
    df_grp = pd.DataFrame(df.groupby(['name']).size().sort_values(ascending=False).reset_index(name="values"))
    pie_fig = px.pie(df_grp, values='values', names='name')

    return pie_fig


def bar_chart(ev_df, tf_df):
    """
    Create a bar chart figure

    :param ev_df:
    :param tf_df:
    :return:
    """
    df = nearest_messages(ev_df, tf_df)
    df_grp = pd.DataFrame(df.groupby(['name']).size().sort_values(ascending=False).reset_index(name="values"))
    fig = px.bar(df_grp, x="name", y="values", labels={
        "name": "",
        "values": "",
    },
                 )
    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
