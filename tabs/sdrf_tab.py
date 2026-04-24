import subprocess
import sys
import tempfile
import os
import shutil
from datetime import datetime

import pandas as pd
import streamlit as st

from func.utils import build_download_name, ensure_bom

EMPTY_WELL_LABEL = "EMPTY"

SAMPLE_TO_PART = {
    "plasma": "blood plasma",
    "serum": "blood serum",
}


def render(ms_info: dict, sample_info: dict) -> None:
    st.header("SDRF")

    ms_file = st.selectbox("MS file output", ["mzML", "raw"])
    collision_energy = st.text_input("Collision Energy (NCE)", "27")

    output_order_df = st.session_state.get("output_order_df")
    if output_order_df is None:
        st.warning("Please go to the 'Xcalibur' tab first to create the sample order.")
        st.stop()

    plate_df = _get_filtered_plate_df()

    sample_prop = _build_sample_prop(plate_df, sample_info, output_order_df)
    sample_prop_columns = [
        c.replace("characteristics[", "").replace("]", "")
        for c in sample_prop.columns
        if c.startswith("characteristics[")
    ]

    data_file_prop = _build_data_file_prop(ms_info, output_order_df, ms_file, collision_energy)

    sdrf_df = pd.concat([sample_prop, data_file_prop], axis=1)

    factor_col = st.selectbox(
        "Select column for factor value",
        sample_prop_columns,
        index=sample_prop_columns.index("Sample") if "Sample" in sample_prop_columns else 0,
    )
    sdrf_df[f"factor value[{factor_col}]"] = sdrf_df[f"characteristics[{factor_col}]"]

    st.subheader("Edit your SDRF data here:")
    sdrf_df = st.data_editor(sdrf_df, use_container_width=True)

    sdrf_filename = build_download_name(
        [datetime.now().strftime("%Y%m%d"), sample_info["proj_name"], sample_info["plate_id"]],
        ".sdrf.tsv",
    )
    sdrf_tsv = ensure_bom(sdrf_df.to_csv(sep="\t", index=False))
    for i in range(len(ms_info["enz_accession_list"])):
        sdrf_tsv = sdrf_tsv.replace(
            f"comment[cleavage agent details{i}]", "comment[cleavage agent details]"
        )

    # Save for Skyline tab and Download All
    st.session_state.sdrf_df = sdrf_df
    st.session_state.dl_sdrf = (sdrf_tsv.encode("utf-8"), sdrf_filename)

    st.subheader("Step 1: Validate SDRF")
    if st.button("Validate before download"):
        with tempfile.NamedTemporaryFile(suffix=".sdrf.tsv", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp_path = tmp.name
            tmp.write(sdrf_tsv)
        try:
            parse_sdrf_bin = (
                shutil.which("parse_sdrf")
                or os.path.join(os.path.dirname(sys.executable), "parse_sdrf")
            )
            result = subprocess.run(
                [parse_sdrf_bin, "validate-sdrf", "--sdrf_file", tmp_path, "--skip-ontology"],
                capture_output=True,
                text=True,
            )
            output = result.stdout + result.stderr
            st.code(output if output.strip() else "(no output)", language="text")
        except FileNotFoundError:
            st.error("`parse_sdrf` not found. Please install sdrf-pipelines: `pip install sdrf-pipelines`")
        finally:
            os.unlink(tmp_path)

    st.subheader("Step 2: Download SDRF")
    st.download_button(
        label="Download SDRF",
        data=sdrf_tsv.encode("utf-8"),
        file_name=sdrf_filename,
        mime="text/tab-separated-values; charset=utf-8",
    )

    url = "https://www.github.com/thanadol-git/quantms_example/"
    st.markdown(
        "comment[cleavage agent details] will be fixed with the downloaded file. "
        "Pandas cannot handle two columns with the same name. "
        "check out this [link](%s)" % url
    )


def _get_filtered_plate_df() -> pd.DataFrame:
    """Return plate DataFrame with EMPTY wells removed."""
    xcal_df = st.session_state.get("xcalibur_plate_df")
    if xcal_df is not None:
        df = xcal_df[["Row", "Column", "Sample"]].copy()
    else:
        df = st.session_state.get("plate_df_long", pd.DataFrame()).copy()
    return df[df["Sample"] != EMPTY_WELL_LABEL]


def _build_sample_prop(plate_df: pd.DataFrame, sample_info: dict, output_order_df: pd.DataFrame) -> pd.DataFrame:
    """Build the sample properties (characteristics) section of SDRF."""
    n = len(output_order_df)
    df = plate_df.copy()

    df["organism"] = sample_info["organism_species"]
    df["organism part"] = SAMPLE_TO_PART.get(sample_info["sample"].lower(), "not available")
    df["plate"] = sample_info["plate_id"]
    df["project"] = sample_info["proj_name"]
    for col in ["age", "developmental stage", "sex", "ancestry category",
                "cell type", "cell line", "disease", "individual"]:
        df[col] = "not available"
    df["biological replicate"] = "1"

    df.columns = "characteristics[" + df.columns + "]"
    df.insert(0, "source name", output_order_df["File Name"].values)
    df["Material type"] = sample_info["sample"].lower()
    df["assay name"] = [f"run {i}" for i in range(1, n + 1)]
    df["technology type"] = "proteomic profiling by mass spectrometry"
    return df


def _build_data_file_prop(ms_info: dict, output_order_df: pd.DataFrame, ms_file: str, collision_energy: str) -> pd.DataFrame:
    """Build the data file properties (comments) section of SDRF."""
    n = len(output_order_df)
    df = pd.DataFrame({
        "data file": output_order_df["File Name"] + "." + ms_file,
        "file uri": output_order_df["File Name"] + "." + ms_file,
        "proteomics data acquisition method": ms_info["sdrf_acquisition"],
        "label": "AC=MS:1002038;NT=label free sample",
        "fraction identifier": "1",
        "fractionation method": "NT=High-performance liquid chromatography;AC=PRIDE:0000565",
        "technical replicate": "1",
        "ms2 mass analyzer": "not available",
        "instrument": ms_info["sdrf_ms"],
        "modification parameters": "NT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed",
        "dissociation method": ms_info["dissociation_accession"],
        "collision energy": collision_energy + " NCE",
        "precursor mass tolerance": "40 ppm",
        "fragment mass tolerance": "0.05 Da",
    })

    for i, enz in enumerate(ms_info["enz_accession_list"]):
        df[f"cleavage agent details{i}"] = enz

    # Insert cleavage columns right after "technical replicate"
    cleavage_cols = [c for c in df.columns if c.startswith("cleavage agent details")]
    other_cols = [c for c in df.columns if not c.startswith("cleavage agent details")]
    insert_after = other_cols.index("technical replicate") if "technical replicate" in other_cols else 6
    df = df[other_cols[: insert_after + 1] + cleavage_cols + other_cols[insert_after + 1:]]

    if ms_info["acq_tech"] == "DIA":
        df["MS1 scan range"] = "400-1250 m/z"
        df["MS2 scan range"] = "100-2000 m/z"
    if ms_info["acq_tech"] in ["SRM", "PRM"]:
        df["ProteomEdge"] = ms_info["srm_lot"]

    df.columns = "comment[" + df.columns + "]"
    return df
