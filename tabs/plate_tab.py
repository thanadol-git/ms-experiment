import streamlit as st

from func.agent import create_agent_chat, init_plate_replace_text
from func.plate_plot import plate_dfplot, process_plate_positions

EXAMPLE_TEXT_96 = (
    "Pool;A7,A8,A12\nControl;G12\nControl;H12\n"
    "Cohort_2;C8\nEMPTY;A1\nCohort_2;RowD\n"
    "Cohort_2;RowE\nCohort_2;Col9\nCohort_2;Col8"
)

EXAMPLE_TEXT_384 = (
    "Pool;A1,A2,A3\nControl;P22\nControl;P23\n"
    "Cohort_2;C8\nEMPTY;A24\nCohort_2;RowD\n"
    "Cohort_2;RowE\nCohort_2;Col20\nCohort_2;Col21"
)


def render(ms_info: dict, sample_info: dict) -> None:
    st.header("Plate layout")

    st.subheader("A. Cohort name")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Main Cohort", value=sample_info["sample_name"])
    with col2:
        st.metric(label="Plate ID", value=sample_info["plate_id"])

    # Plate format selection
    st.markdown("**Select plate format**")
    if "settings_plate_type" not in st.session_state:
        st.session_state.settings_plate_type = "96-well"

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "96-well",
            use_container_width=True,
            type="primary" if st.session_state.settings_plate_type == "96-well" else "secondary",
        ):
            st.session_state.settings_plate_type = "96-well"
    with col2:
        if st.button(
            "384-well",
            use_container_width=True,
            type="primary" if st.session_state.settings_plate_type == "384-well" else "secondary",
        ):
            st.session_state.settings_plate_type = "384-well"

    plate_type = st.session_state.settings_plate_type

    # Reset example text when plate type changes
    if st.session_state.get("_last_plate_type") != plate_type:
        st.session_state.replace_pos_text = (
            EXAMPLE_TEXT_384 if plate_type == "384-well" else EXAMPLE_TEXT_96
        )
        st.session_state["_last_plate_type"] = plate_type

    st.subheader("B. Sample annotation")
    st.write(
        "Please annotate samples with other cohorts besides the main cohort in your plate, "
        "for example pool samples or control samples. "
        "Importantly, The 'EMPTY' wells will be removed in the later steps."
    )
    if plate_type == "96-well":
        st.caption("Format: Label;Position  (e.g. Pool;A7 | row shorthand: Cohort_2;RowA | col shorthand: Cohort_2;Col8 | comma list: Pool;A1,A2,A3)")
    else:
        st.caption("Format: Label;Position  (e.g. Pool;A7 | row shorthand: Cohort_2;RowA (A–P) | col shorthand: Cohort_2;Col8 (1–24) | comma list: Pool;A1,A2,A3)")
    st.markdown(
        "<span style='color:red'>⚠️ **Disclaimer:** Please ensure that the information you provide "
        "does not contain any sensitive or personally identifiable information.</span>",
        unsafe_allow_html=True,
    )

    init_plate_replace_text(EXAMPLE_TEXT_96)
    text_input = st.text_area(
        "Example: Control, Pool or another cohort", key="replace_pos_text", height=200
    )

    plate_df, _ = process_plate_positions(text_input, sample_info["sample_name"], plate_type)

    st.subheader("C. Layout of plate")
    plate_df_long = plate_dfplot(plate_df, sample_info["plate_id"])
    st.session_state.plate_df_long = plate_df_long
    st.session_state.plate_type = plate_type
    st.session_state.dl_plate_csv = plate_df_long.to_csv(index=False).encode("utf-8-sig")

    create_agent_chat()
