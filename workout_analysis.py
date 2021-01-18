import streamlit as st
from streamlit_lottie import st_lottie
import requests
from pathlib import Path
import json
import os
import time
import pandas as pd
import fitdecode as fd

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
    

# Workout Analysis

# lottie_url = "https://assets7.lottiefiles.com/private_files/lf30_OTKlKD.json"
lottie_url = 'https://assets7.lottiefiles.com/datafiles/ogIQ10UnwnKiBZS/data.json'
lottie_json = load_lottieurl(lottie_url)

title_col1, title_col2, title_col3 = st.beta_columns([1,0.3,1])

with title_col1:
    st.markdown('# Workout Analysis')
with title_col2:
    st_lottie(st_lottie(lottie_json, height=75))

# f = st.file_uploader('Upload a .fit File', type=None, accept_multiple_files=False, key=None)

fit_dict = dict_for_file_type(Path.cwd(), '.fit')
selected_fit_dict_keys = st.multiselect('Select .fit Files to Convert to JSON', list(fit_dict.keys()))

if st.button('Convert selected .fit files into JSON files'):
    convert_fit_to_json(fit_dict, selected_fit_dict_keys)
    st.success('Finished')

json_dict = dict_for_file_type(Path.cwd(), '.json')
selected_json_dict_keys = st.multiselect('Select .json Files to Inspect', list(json_dict.keys()))

if st.button('Inspect JSON(s)'):
    simplified_json_ride_lists = {}
    for json_stem in selected_json_dict_keys:
        with open(json_dict[json_stem], 'r') as f:
            f_json = json.load(f)

            simplified_json_ride_lists[json_stem] = []
            for frame in f_json:
                if frame['frame_type'] == 'data_message' and frame['name'] == 'record':
                    payload = {
                        'timestamp': frame['fields'][0],
                        'position_lat': frame['fields'][1],
                        'position_long': frame['fields'][2],
                        'distance': frame['fields'][2],
                        'heart_rate': frame['fields'][8],
                        'altitude': frame['fields'][10],
                        'speed': frame['fields'][12],
                        'power': frame['fields'][13],
                        'grade': frame['fields'][14],
                        'cycle_length': frame['fields'][17],
                        'temperature': frame['fields'][17],
                        'chunk': frame['chunk'],
                    }
                    simplified_json_ride_lists[json_stem].append(payload)

    for k, v in simplified_json_ride_lists.items():
        st.write(k, len(v))
        for itm in v[:4]:
            st.write([itm['timestamp']['value'], itm['heart_rate']['value'], itm['power']['value']])
