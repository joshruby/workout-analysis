import streamlit as st
from streamlit_lottie import st_lottie
import requests
import pathlib
import pandas as pd
import fitdecode as fd

def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

    # Workout Analysis

# lottie_url = "https://assets7.lottiefiles.com/private_files/lf30_OTKlKD.json"
lottie_url = 'https://assets7.lottiefiles.com/datafiles/ogIQ10UnwnKiBZS/data.json'
lottie_json = load_lottieurl(lottie_url)

title_col1, title_col2, title_col3 = st.beta_columns([1,0.5,1])

with title_col1:
    st.markdown('# Workout Analysis')
with title_col2:
    st_lottie(st_lottie(lottie_json, height=75))