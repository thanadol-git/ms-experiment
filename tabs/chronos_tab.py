from datetime import datetime

import pandas as pd
import streamlit as st

from func.utils import (
    build_download_name,
    create_xml_from_dataframe,
    ensure_bom,
    sanitize_xml_columns,
)

EMPTY_WELL_LABEL = "EMPTY"


def render(ms_info: dict, sample_info: dict) -> None:
    st.header("Evosep method for " + ms_info["acq_tech"])

    evosep_sample_df = _get_sample_df()

    # Output and method paths
    evosep_output = st.text_input(
        "Enter the directory path to save Evosep method file", r"C:\data"
    )
    st.markdown(
        f"The data will be saved at: <span style='color:red'>{evosep_output}</span>",
        unsafe_allow_html=True,
    )

    evosep_method = st.text_input(
        "Enter the Evosep experiment machine file (.cam)", r"C:\data\Evosep\method.cam"
    )
    st.markdown(
        f"The Evosep method file is from: <span style='color:red'>{evosep_method}</span>",
        unsafe_allow_html=True,
    )

    xcalibur_sample_method = st.text_input(
        "Enter the Xcalibur method file (.meth)", r"C:\Xcalibur\methods.meth"
    )
    st.markdown(
        f"The Xcalibur method file is from: <span style='color:red'>{xcalibur_sample_method}</span>",
        unsafe_allow_html=True,
    )

    evosep_slot = "EvoSlot " + str(st.selectbox("Select Evosep slot", list(range(1, 7))))
    evosep_comment = st.text_input("Enter comment for Evosep", ms_info["srm_lot"] or "")

    evosep_sample_df["Source Tray"] = evosep_slot
    evosep_sample_df["Xcalibur Method"] = xcalibur_sample_method
    evosep_sample_df = evosep_sample_df[evosep_sample_df["Sample"] != EMPTY_WELL_LABEL]
    evosep_sample_df = evosep_sample_df[
        ["Source Tray", "Source Vial", "Sample Name", "Xcalibur Method"]
    ]

    randomize = st.checkbox("Randomize sample order", value=True)
    if randomize:
        evosep_sample_final = evosep_sample_df.sample(frac=1).reset_index(drop=True)
        st.success("Sample order randomized!")
    else:
        evosep_sample_final = evosep_sample_df.copy()

    # Pre-run iRT and post-run standby
    cols = st.columns(2)
    with cols[0]:
        st.markdown("### Pre-run: iRT calibration")
        include_irt, irt_df = _irt_section()

    with cols[1]:
        st.markdown("### Post-run: Standby and Prepare Commands")
        include_standby, standby_cmd, prepare_cmd = _standby_section()

    # Assemble final DataFrame
    if irt_df is not None:
        evosep_final_df = pd.concat([irt_df, evosep_sample_final], ignore_index=True)
    else:
        evosep_final_df = evosep_sample_final.copy()

    evosep_final_df.insert(0, "Analysis Method", evosep_method)
    evosep_final_df["Xcalibur Filename"] = evosep_final_df["Sample Name"]
    evosep_final_df["Xcalibur Post Acquisition Program"] = ""
    evosep_final_df["Xcalibur Output Dir"] = evosep_output
    evosep_final_df["Comment"] = evosep_comment
    evosep_final_df["Pump preparation"] = ""
    evosep_final_df["Align solvents"] = ""
    evosep_final_df["Flow to column / idle flow"] = ""

    if include_standby:
        evosep_final_df = _append_standby_rows(evosep_final_df, standby_cmd, prepare_cmd)

    st.subheader("Edit your data here:")
    evosep_final_df = st.data_editor(evosep_final_df, use_container_width=True)

    _download_section(evosep_final_df, sample_info)


def _get_sample_df() -> pd.DataFrame:
    """Load the sample DataFrame from session state."""
    xcal_df = st.session_state.get("xcalibur_plate_df")
    if xcal_df is not None:
        df = xcal_df.copy()
        if "File Name" in df.columns:
            df = df.rename(columns={"File Name": "Sample Name"})
        return df

    plate_df_long = st.session_state.get("plate_df_long")
    if plate_df_long is None:
        st.warning("Please go to the 'Plate Design' tab first to create the plate layout.")
        st.stop()

    df = plate_df_long.copy()
    df["Source Vial"] = list(range(1, df.shape[0] + 1))
    df["Sample Name"] = df["Sample"]
    return df


def _irt_section() -> tuple:
    """Render the iRT pre-run section. Returns (include_irt, irt_df or None)."""
    include_irt = st.checkbox("Include iRT standards", value=False)
    if not include_irt:
        return False, None

    irt_slot = "EvoSlot " + str(
        st.selectbox("Select iRT slot", list(range(1, 7)), key="irt_slot")
    )
    irt_count = st.number_input("Number of iRT samples", min_value=1, max_value=10, value=2, step=1)
    irt_method = st.text_input("Enter the Xcalibur iRT method file", r"C:\Xcalibur\methods\iRT.meth")
    st.markdown(
        f"The Xcalibur iRT method file is from: <span style='color:red'>{irt_method}</span>",
        unsafe_allow_html=True,
    )
    irt_name = st.text_input("Enter iRT sample name", "iRT_Tag_unscheduled")

    irt_df = pd.DataFrame({
        "Source Vial": list(range(1, irt_count + 1)),
        "Sample Name": [f"{irt_name}_{i}" for i in range(1, irt_count + 1)],
        "Xcalibur Method": [irt_method] * irt_count,
    })
    irt_df.insert(0, "Source Tray", irt_slot)
    return True, irt_df


def _standby_section() -> tuple:
    """Render the standby/prepare post-run section. Returns (include, standby_cmd, prepare_cmd)."""
    include_standby = st.checkbox("Include Standby and Prepare commands", value=False)
    if not include_standby:
        return False, "", ""

    standby_cmd = st.text_input("Enter the standby command", r"C:\Xcalibur MS standby.cam")
    prepare_cmd = st.text_input("Enter the prepare command", r"C:\Xcalibur MS prepare.cam")
    return True, standby_cmd, prepare_cmd


def _append_standby_rows(df: pd.DataFrame, standby_cmd: str, prepare_cmd: str) -> pd.DataFrame:
    """Append two standby/prepare command rows to the Evosep DataFrame."""
    standby_df = df.copy()
    standby_df.loc[:, :] = ""
    standby_df.iloc[0, 0] = standby_cmd
    standby_df.iloc[1, 0] = prepare_cmd
    standby_df.iloc[1, -3] = "none"
    standby_df.iloc[1, -2] = "False"
    standby_df.iloc[1, -1] = "Idle flow (250 nl/min)"
    standby_df = standby_df.iloc[:2, :12]
    return pd.concat([df, standby_df], ignore_index=True)


def _download_section(df: pd.DataFrame, sample_info: dict) -> None:
    """Render CSV, XML download buttons and XML preview."""
    base_parts = [
        datetime.now().strftime("%Y%m%d%H%M"),
        sample_info["proj_name"],
        "Evosep",
        "Order",
        sample_info["plate_id"],
    ]
    csv_data = ensure_bom(df.to_csv(index=True, sep=",", encoding="utf-8-sig"))

    xml_df = df.copy()
    xml_df.columns = sanitize_xml_columns(xml_df.columns)
    xml_data = create_xml_from_dataframe(xml_df)

    csv_name = build_download_name(base_parts, ".csv")
    xml_name = build_download_name(base_parts, ".xml")
    st.session_state.dl_chronos_csv = (csv_data.encode("utf-8"), csv_name)
    st.session_state.dl_chronos_xml = (xml_data.encode("utf-8"), xml_name)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_data.encode("utf-8-sig"),
            file_name=csv_name,
            mime="text/csv; charset=utf-8; separator=semicolon",
        )
    with col2:
        st.download_button(
            label="⬇️ Download XML",
            data=xml_data.encode("utf-8"),
            file_name=xml_name,
            mime="application/xml",
        )
    with col3:
        if st.button("📋 Copy XML to Clipboard"):
            st.write(
                "<script>navigator.clipboard.writeText(`"
                + xml_data.replace("`", "\\`")
                + "`);</script>",
                unsafe_allow_html=True,
            )
            st.success("XML copied to clipboard!")

    st.markdown("### XML Preview")
    with st.expander("View XML (click to expand)"):
        st.code(xml_data, language="xml")
