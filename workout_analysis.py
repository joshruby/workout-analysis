import streamlit as st
from streamlit_lottie import st_lottie
import requests
from pathlib import Path
import json
import os
import time
import pandas as pd
import fitdecode as fd

'### Figure out how to handle the duplicate null speed and distance values from zwift rides and check if the same issue exists for rides uploaded from Wahoo Fitness'

'### Need to look at `data_message`s with names in `[record, activity, event, lap, session]`. Figure out what info is in each one and which names are relevant for Zwift, Wahoo Fitness, and outdoor rides'

'### Figure out how to best handle missing fields and None values'

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
    units = []
    for field in fields:
        units.append(simplified_ride[30][field]['units'])
    header = [fields, units]
    
    field_values = {}
    for field in fields:
        values = []
        for frame in simplified_ride:
            if field in list(frame.keys()):
                values.append(frame[field]['value'])
            else:
                values.append(None)
        field_values[field] = values

    df = pd.DataFrame.from_dict(field_values)
    # Add a second header row for units
    df.columns = header
    
    return df

# Workout Analysis

# lottie_url = "https://assets7.lottiefiles.com/private_files/lf30_OTKlKD.json"
lottie_url = 'https://assets7.lottiefiles.com/datafiles/ogIQ10UnwnKiBZS/data.json'
lottie_json = load_lottieurl(lottie_url)

title_col1, title_col2, title_col3 = st.beta_columns([1,0.3,1])

with title_col1:
    st.markdown('# Workout Analysis')
with title_col2:
    st_lottie(st_lottie(lottie_json, height=75))

f = st.file_uploader('Upload a .fit File', type=None, accept_multiple_files=False, key=None)

simplified_ride = None
if f:
    simplified_ride = record_fields_from_fit(f)
    
if simplified_ride:
    simplified_ride_df = df_from_simplfied_ride(simplified_ride)
    st.write(simplified_ride_df.head())







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