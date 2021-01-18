import streamlit as st
from streamlit_lottie import st_lottie
import requests
import pandas as pd
import fitdecode as fd

def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

    # Workout Analysis

lottie_url = "https://assets5.lottiefiles.com/packages/lf20_V9t630.json"
lottie_json = load_lottieurl(lottie_url)
st_lottie(lottie_json)