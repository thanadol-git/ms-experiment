import streamlit as st

from sidebar import create_sidebar
from tabs.intro_tab import intro_detail
from tabs import plate_tab, xcalibur_tab, chronos_tab, sdrf_tab, skyline_tab


ms_info, sample_info = create_sidebar()

intro, plate, xcalibur, chronos, sdrf, skyline = st.tabs(
    ["Intro", "Plate Design", "Xcalibur", "Chronos", "SDRF", "Skyline"]
)

with intro:
    intro_detail()

with plate:
    plate_tab.render(ms_info, sample_info)

with xcalibur:
    xcalibur_tab.render(ms_info, sample_info)

with chronos:
    chronos_tab.render(ms_info, sample_info)

with sdrf:
    sdrf_tab.render(ms_info, sample_info)

with skyline:
    skyline_tab.render(ms_info, sample_info)
