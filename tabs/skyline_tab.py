from datetime import datetime

import pandas as pd
import streamlit as st

from func.utils import build_download_name


def render(ms_info: dict, sample_info: dict) -> None:
    st.header("Skyline")
    st.markdown("Use SDRF file or Upload your SDRF file here to generate Skyline annotation file.")

    sdrf_upload = st.file_uploader("Upload SDRF file", type=["sdrf.tsv", "tsv"])
    anno_file = st.selectbox(
        "Select SDRF file to process",
        ["Use generated SDRF", "Upload SDRF file"],
        key="sdrf_choice",
    )

    if anno_file == "Upload SDRF file":
        if sdrf_upload is None:
            st.warning("Please upload an SDRF file.")
            st.stop()
        upload_sdrf_df = pd.read_csv(sdrf_upload, sep="\t", dtype=str)
        st.success("SDRF file uploaded successfully!")
    else:
        st.info("Using generated SDRF file from previous section.")
        sdrf_df = st.session_state.get("sdrf_df")
        if sdrf_df is None:
            st.warning("Please generate the SDRF file in the SDRF section first.")
            st.stop()
        upload_sdrf_df = sdrf_df.copy()

    char_cols = [col for col in upload_sdrf_df.columns if col.startswith("characteristics[")]
    skyline_anno = upload_sdrf_df[char_cols].copy()
    skyline_anno.columns = [
        col.replace("characteristics[", "").replace("]", "") for col in skyline_anno.columns
    ]

    st.subheader("Sample Annotations for Skyline")
    skyline_anno = st.data_editor(skyline_anno, use_container_width=True)

    filename = build_download_name(
        [
            datetime.now().strftime("%Y%m%d%H%M"),
            sample_info["proj_name"],
            "Skyline",
            "Annotations",
            sample_info["plate_id"],
        ],
        ".csv",
    )
    skyline_csv_bytes = skyline_anno.to_csv(index=False).encode("utf-8")
    st.session_state.dl_skyline = (skyline_csv_bytes, filename)

    st.download_button(
        label="Download Skyline Annotation",
        data=skyline_csv_bytes,
        file_name=filename,
        mime="text/csv; charset=utf-8",
    )
