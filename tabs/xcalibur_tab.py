from datetime import datetime

import pandas as pd
import streamlit as st

from func.utils import build_download_name, build_file_name, ensure_bom, insert_wash_after_chunks

EMPTY_WELL_LABEL = "EMPTY"
INJECTION_POS_COLORS = {"Red": "red", "Green": "green", "Blue": "blue"}
INJECTION_POS_LETTERS = {"Red": "R", "Green": "G", "Blue": "B"}


def render(ms_info: dict, sample_info: dict) -> None:
    st.header(ms_info["acq_tech"] + " Injection")

    plate_df_long = st.session_state.get("plate_df_long")
    if plate_df_long is None:
        st.warning("Please go to the 'Plate Design' tab first to create the plate layout.")
        st.stop()

    plate_df_long = plate_df_long.copy()
    plate_df_long["Source Vial"] = list(range(1, plate_df_long.shape[0] + 1))
    plate_df_long = plate_df_long[plate_df_long["Sample"] != EMPTY_WELL_LABEL]

    # 1. Injection position
    injection_pos = st.selectbox(
        "1. Select your Autosampler injection position", ["Red", "Green", "Blue"]
    )
    load_color = INJECTION_POS_COLORS[injection_pos]
    injection_pos_letter = INJECTION_POS_LETTERS[injection_pos]
    st.write(
        f"The selected injection position is <span style='color:{load_color}'>{injection_pos}</span> "
        f"with corresponding letter <span style='color:{load_color}'>{injection_pos_letter}</span>.",
        unsafe_allow_html=True,
    )

    # 2. Injection volume
    injection_vol = st.slider("2. Select your injection volume", 0.01, 20.0, 0.1, 0.01)
    vol_col, text_col = st.columns(2)
    with vol_col:
        btns = st.columns(5)
        for btn_col, vol in zip(btns, [0.01, 0.1, 5.0, 10.0, 15.0]):
            if btn_col.button(f"{vol} ul", use_container_width=True):
                injection_vol = vol
    with text_col:
        injection_vol = st.text_input("Enter your injection volume (ul)", str(injection_vol))
    st.markdown(
        f"Selected injection volume (ul): <span style='color:red'>{injection_vol}</span>",
        unsafe_allow_html=True,
    )

    # 3. Data directory
    uploaded_dir = st.text_input("3. Enter the directory path to the data", r"C:\data\yourdir")
    st.markdown(
        f"The data will be saved at: <span style='color:red'>{uploaded_dir}</span>",
        unsafe_allow_html=True,
    )

    # 4. Method file
    method_file = st.text_input(
        "4. Enter the directory path to the method file", r"C:\Xcalibur\methods\method1"
    )
    st.markdown(
        f"The method file for MS is from: <span style='color:red'>{method_file}</span>",
        unsafe_allow_html=True,
    )

    # 5. Date of injection
    date_injection = st.date_input("5. Date of injection", pd.Timestamp("today"))
    date_injection = date_injection.strftime("%Y%m%d")
    st.markdown(
        f"Date of injection: <span style='color:red'>{date_injection}</span>",
        unsafe_allow_html=True,
    )

    # Build file metadata columns
    plate_df_long["Position"] = plate_df_long["Row"] + plate_df_long["Column"].astype(str)
    plate_df_long["Inj Vol"] = injection_vol
    plate_df_long["Instrument Method"] = method_file
    plate_df_long["Path"] = uploaded_dir
    plate_df_long["File Name"] = plate_df_long.apply(
        build_file_name, axis=1,
        ms_info=ms_info, sample_info=sample_info, date_injection=date_injection,
    )
    plate_df_long["Position"] = injection_pos_letter + plate_df_long["Position"]

    output_order_df = plate_df_long[
        ["File Name", "Path", "Instrument Method", "Position", "Inj Vol"]
    ].copy()

    # Wash, QC Plasma, and QC between samples
    cols = st.columns(3)
    with cols[0]:
        st.markdown("### Wash")
        wash_df = _build_run_df(
            name="wash",
            path=st.text_input("Enter the path to the washes", r"C:\data\wash"),
            method=st.text_input("Enter the method file for washes", r"C:\Xcalibur\methods\wash"),
            pos=st.text_input("Enter the position for washes", "G3"),
            vol=st.text_input("Modify your 'Wash' injection volume (ul)", str(injection_vol)),
        )

    with cols[1]:
        st.markdown("### QC Plasma")
        qc_base = _build_run_df(
            name="QC_Plasma",
            path=st.text_input("Enter the path to the QC standard", r"C:\data\QC"),
            method=st.text_input("Enter the method file for QC standard", r"C:\Xcalibur\methods\QC"),
            pos=st.text_input("Enter the position for QC standard", "GE1"),
            vol=st.text_input("Modify your 'QC' injection volume (ul)", str(injection_vol)),
        )
        qc_df = pd.concat([qc_base, wash_df], ignore_index=True)

    with cols[2]:
        st.markdown("### QC between samples")
        qcb_base = _build_run_df(
            name="QC_" + date_injection,
            path=st.text_input("Enter the path to the between QC standard", r"C:\data\QC_between"),
            method=st.text_input(
                "Enter the method file for between QC standard", r"C:\Xcalibur\methods\QC_between"
            ),
            pos=st.text_input("Enter the position for between QC standard", "GE2"),
            vol=st.text_input(
                "Modify your 'QC between' injection volume (ul)", str(injection_vol)
            ),
        )
        include_qc_between = st.checkbox("Include QC between samples", value=True)
        qcb_pre = pd.concat(
            [wash_df, qcb_base.assign(**{"File Name": qcb_base["File Name"] + "_1"})],
            ignore_index=True,
        )
        qcb_post = pd.concat(
            [qcb_base.assign(**{"File Name": qcb_base["File Name"] + "_2"}), wash_df],
            ignore_index=True,
        )

    # Randomize and assemble final injection sequence
    st.markdown("### Download data")
    randomize = st.checkbox("Randomize sample order", key="randomize_xcalibur", value=True)
    if randomize:
        st.success("Sample order randomized!")
        output_order_rand = output_order_df.sample(frac=1).reset_index(drop=True)
    else:
        output_order_rand = output_order_df.copy()

    if ms_info["acq_tech"] in ["SRM", "PRM"]:
        output_with_wash = output_order_rand
    else:
        output_with_wash = insert_wash_after_chunks(output_order_rand, wash_df, 8)

    output_with_wash = pd.concat([wash_df, qc_df, output_with_wash, qc_df], ignore_index=True)
    if include_qc_between:
        output_with_wash = pd.concat([qcb_pre, output_with_wash, qcb_post], ignore_index=True)

    # Save for downstream tabs
    st.session_state.output_order_df = output_order_df
    st.session_state.xcalibur_plate_df = plate_df_long

    csv_data = ensure_bom("Bracket Type=4,,,,\n" + output_with_wash.to_csv(index=False, encoding="utf-8-sig"))

    st.markdown(
        "The data below is an example for sample order in Xcalibur. "
        "The injection order will be randomized and added with wash and qc standard. "
        "Be sure with SRM injection."
    )
    st.write(output_order_rand)
    st.markdown("Click below to download the data.")

    filename = build_download_name(
        [
            datetime.now().strftime("%Y%m%d%H%M"),
            sample_info["proj_name"],
            "Sample",
            "Order",
            sample_info["plate_id"],
        ],
        ".csv",
    )
    st.download_button(
        label="Download sample order",
        data=csv_data.encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv; charset=utf-8",
    )


def _build_run_df(name: str, path: str, method: str, pos: str, vol: str) -> pd.DataFrame:
    """Helper to build a single-row run DataFrame (wash/QC)."""
    return pd.DataFrame({
        "File Name": [name],
        "Path": [path],
        "Instrument Method": [method],
        "Position": [pos],
        "Inj Vol": [vol],
    })
