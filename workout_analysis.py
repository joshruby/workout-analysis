import streamlit as st
import SessionState
from streamlit_lottie import st_lottie
import requests
from pathlib import Path
import json
import os
import time
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import scipy as sp
from scipy import signal
import numpy as np
import matplotlib.pyplot as plt
import fitdecode as fd

st.set_page_config(page_title='Workout Analysis', page_icon=None, layout='wide', initial_sidebar_state='auto')

'''
## Todo

* Figure out how to handle the duplicate null speed and distance values from zwift rides and check if the same issue exists for rides uploaded from Wahoo Fitness'

* Need to look at `data_message`s with names in `[record, activity, event, lap, session]`. Figure out what info is in each one and which names are relevant for Zwift, Wahoo Fitness, and outdoor rides'

* Figure out how to best handle missing fields and None values'

* Figure out optimal smoothing params'
'''

def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

def convert_fit_to_json(dict, selected_keys):
    for k in selected_keys:
        destination_stem = dict[k].parent.joinpath(dict[k].stem)

        os.system('fitjson "{}" -o "{}".json'.format(str(dict[k]), destination_stem))

def dict_for_file_type(directory, suffix):
    paths = sorted(directory.rglob("*{}".format(suffix)))
    stems = [path.stem for path in paths]

    return dict(zip(stems, paths))

def record_fields_from_fit(fit_file):
    with fd.FitReader(fit_file) as fit:
        simplified_ride = []
        simplified_frame = {}

        for frame in fit:
            # The yielded frame object is of one of the following types:
            # * fd.FitHeader
            # * fd.FitDefinitionMessage
            # * fd.FitDataMessage
            # * fd.FitCRC

            if isinstance(frame, fd.FitDataMessage) and frame.name == 'record':
                # Here, frame is a FitDataMessage object.
                # A FitDataMessage object contains decoded values that
                # are directly usable in your script logic.
                for field in frame.fields:
                    simplified_frame[field.name] = {
                        'value': field.value,
                        'raw_value': field.raw_value,
                        'units': field.units
                    }
                simplified_ride.append(simplified_frame)
                simplified_frame = {}
    return simplified_ride
    
def df_from_simplfied_ride(simplified_ride):
    # Get the available keys from an element that's not near the beginning of the list since the first several records have limited fields for some rides
    fields = list(simplified_ride[30].keys())
    
    field_values = {}
    for field in fields:
        values = []
        for frame in simplified_ride:
            if field in list(frame.keys()):
                values.append(frame[field]['value'])
            else:
                values.append(None)
        field_values[field] = values

    # Create df
    df = pd.DataFrame.from_dict(field_values)

    # Make a multiIndex to track the units of each column
    units = []
    for field in fields:
        field_units = simplified_ride[30][field]['units']
        # Clean up unit names
        if field_units == None:
            # This will make selecting columns from the df that have NaN units possible without any funny business later on
            # Leaving the NaN units as None no worky
            field_units = np.nan
        elif field_units == '%':
            field_units = 'percent'
        units.append(field_units)
    arrays = [fields, units]
    header_tuples = list(zip(*arrays))
    header = pd.MultiIndex.from_tuples(header_tuples, names=['Fields','Units'])
    df.columns = header

    # Drop columns that only contain NaN vales
    df.dropna(axis=1, how='all', inplace=True)
    
    return df

# State vars
session_state = SessionState.get(f=None)

# lottie_url = "https://assets7.lottiefiles.com/private_files/lf30_OTKlKD.json"
lottie_url = 'https://assets7.lottiefiles.com/datafiles/ogIQ10UnwnKiBZS/data.json'
lottie_json = load_lottieurl(lottie_url)

st_lottie(lottie_json, height=300)

session_state.f = st.file_uploader('Upload a .fit File', type=None, accept_multiple_files=False, key=None)

simplified_ride = None
if session_state.f:
    simplified_ride = record_fields_from_fit(session_state.f)
    
if simplified_ride:
    df = df_from_simplfied_ride(simplified_ride)
    st.write(df.head())

    # Make a dict of the column tuples where the keys are the first multiIndex label of each pair
    col_selections = {col_tuple[0]: col_tuple for col_tuple in df.columns}
    
    # Find the index of the timestamp and power fields so they can be set as the default selections of the selectboxes
    timestamp_index = [col_tuple[0] for col_tuple in df.columns].index('timestamp')
    try:
        primary_y_index = [col_tuple[0] for col_tuple in df.columns].index('power')
    except:
        try:
            primary_y_index = [col_tuple[0] for col_tuple in df.columns].index('power')
        except:
           primary_y_index = 1 
    try:
        secondary_y_index = [col_tuple[0] for col_tuple in df.columns].index('heart_rate')
    except:
        try:
            secondary_y_index = [col_tuple[0] for col_tuple in df.columns].index('heart_rate')
        except:
            secondary_y_index = [col_tuple[0] for col_tuple in df.columns].index('speed')
    
    # Use the keys of the dict as simplified selection options in the selectboxes
    # This removes the units from the selection items and makes them simple, clean strings
    x_axis_selection, primary_y_axis_selection, secondary_y_axis_selection = st.beta_columns(3)
    with x_axis_selection:
        x_axis_selection = st.selectbox('x-axis Field', list(col_selections.keys()), index=timestamp_index)
    with primary_y_axis_selection:
        primary_y_axis_selection = st.selectbox('Primary y-axis Field', list(col_selections.keys()), index=primary_y_index)
    with secondary_y_axis_selection:
        secondary_y_axis_selection = st.selectbox('Secondary y-axis Field', list(col_selections.keys()), index=secondary_y_index)

    # The actual column labels can be references in the dict
    x_axis_selection = col_selections[x_axis_selection]
    primary_y_axis_selection = col_selections[primary_y_axis_selection]
    secondary_y_axis_selection = col_selections[secondary_y_axis_selection]

    win_size, std = st.beta_columns(2)
    with win_size:
        win_size = st.slider('Gaussian Rolling Average Window Size', min_value=1, max_value=100, value=1, step=1)
    with std:
        std = st.slider('Gaussian Rolling Average Std', min_value=1, max_value=10, value=3, step=1)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=df[x_axis_selection], 
        y=df[primary_y_axis_selection].rolling(win_size, min_periods=win_size, win_type='gaussian', center=True).mean(std=std).round(),
        name=primary_y_axis_selection[0]
        ),
        secondary_y=False
    )
    fig.add_trace(go.Scatter(
        x=df[x_axis_selection], 
        y=df[secondary_y_axis_selection].rolling(win_size, min_periods=win_size, win_type='gaussian', center=True).mean(std=std).round(),
        name=secondary_y_axis_selection[0]
        ),
        secondary_y=True
    )
    # Set x-axis title
    fig.update_xaxes(title_text='{} [{}]'.format(x_axis_selection[0], x_axis_selection[1]))
    # Set y-axes titles
    fig.update_yaxes(title_text='{} [{}]'.format(primary_y_axis_selection[0], primary_y_axis_selection[1]), secondary_y=False)
    fig.update_yaxes(title_text='{} [{}]'.format(secondary_y_axis_selection[0], secondary_y_axis_selection[1]), secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)


    # c = alt.Chart(df).mark_line().transform_fold(
    #     fold=['power', 'power_smoothed_gaus'],
    #     as_=['category', 'y']
    # ).encode(
    #     x='timestamp:T',
    #     y='y:Q',
    #     color='category:N',
    #     ).interactive()
    # st.altair_chart(c, use_container_width=True)

    # c = alt.Chart(df).mark_line().transform_fold(
    #     fold=['power_smoothed_exp'],
    #     as_=['category', 'y']
    # ).encode(
    #     x='timestamp:T',
    #     y='y:Q',
    #     color='category:N',
    #     ).interactive()
    # st.altair_chart(c, use_container_width=True)


fit_dict = dict_for_file_type(Path.cwd(), '.fit')
selected_fit_dict_keys = st.multiselect('Select .fit Files to Convert to JSON', list(fit_dict.keys()))

if st.button('Convert selected .fit files into JSON files'):
    convert_fit_to_json(fit_dict, selected_fit_dict_keys)
    st.success('Finished')

json_dict = dict_for_file_type(Path.cwd(), '.json')
selected_json_dict_keys = st.multiselect('Select .json Files to Inspect', list(json_dict.keys()))

if st.button('Inspect JSON(s)'):
    simplified_rides = {}

    for json_stem in selected_json_dict_keys:
        with open(json_dict[json_stem], 'r') as f:
            f_json = json.load(f)
            st.write(json_stem, len(f_json))

            simplified_rides[json_stem] = []

            for frame in f_json:
                # st.write(frame)
                if frame['frame_type'] == 'data_message' and frame['name'] == 'record':
                    simplified_frame = {}
                    stats_of_interest = [
                        'timestamp',
                        'position_lat',
                        'position_long',
                        'distance',
                        'speed',
                        'altitude',
                        'ascent',
                        'heart_rate',
                        'power',
                        'left_right_balance',
                        'left_pedal_smoothness',
                        'right_pedal_smoothness',
                        'left_torque_effectiveness',
                        'right_torque_effectiveness',
                        'grade',
                        'cadence',
                        'temperature'
                    ]
                    for stat in stats_of_interest:
                        for field in frame['fields']:
                            if field['name'] == stat:
                                if field['value'] != None:
                                    simplified_frame[stat] = {
                                        'value': field['value'],
                                        'units': field['units']
                                    }
                    simplified_frame['chunk'] = frame['chunk']
                    simplified_rides[json_stem].append(simplified_frame)
            
            st.write(simplified_rides[json_stem][:2])