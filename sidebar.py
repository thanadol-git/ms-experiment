import io
import zipfile

import streamlit as st


ORGANISM_SPECIES = {
    "Human": "Homo sapiens",
    "Rat": "Rattus norvegicus",
    "Mouse": "Mus musculus",
    "Cyanobacteria": "Cyanobacteria",
    "E.coli": "Escherichia coli",
}

MS_OPTIONS = {
    "Q Exactive HF": ["DIA", "DDA", "PRM"],
    "TSQ Altis": ["SRM"],
    "LIT Stellar": ["DIA", "DDA", "PRM", "SRM"],
}

MS_ACCESSION = {
    "Q Exactive HF": "NT=Q Exactive HF;AC=MS:1002523",
    "TSQ Altis": "NT=TSQ Altis;AC=MS:1002874",
    "LIT Stellar": "NT=Stellar;AC=MS:1003409",
}

MS_ACQUISITION = {
    "DIA": "NT=Data-Independent Acquisition;AC=NCIT:C161786",
    "DDA": "NT=Data-Dependent Acquisition;AC=NCIT:C161785",
    "PRM": "NT=Parallel Reaction Monitoring;AC=MS:1002956",
    "SRM": "NT=Selected Reaction Monitoring;AC=MS:1000423",
}

ENZ_ACCESSION = {
    "Trypsin": "AC=MS:1001251;NT=Trypsin",
    "Lys-C": "AC=MS:1001309;NT=Lys-C",
    "Chymotrypsin": "AC=MS:1001306;NT=Chymotrypsin",
}

DISSOCIATION_ACCESSION = {
    "ETD": "NT=Electron Transfer Dissociation;AC=MS:1002592",
    "CID": "NT=Collision-Induced Dissociation;AC=MS:1000132",
    "HCD": "NT=Higher-energy Collisional Dissociation;AC=MS:1000422",
}


def sample_info() -> dict:
    proj_name = st.sidebar.text_input("Enter your project name", "Project_X")
    organism = st.sidebar.selectbox("Select your organism", list(ORGANISM_SPECIES.keys()), index=0)
    sample = st.sidebar.selectbox(
        "Select your sample type", ["Plasma", "Serum", "Tissue", "Cell line", "Cell culture"], index=0
    )
    plate_id = st.sidebar.text_input("Enter your plate ID (Barcode)", "")
    sample_name = st.sidebar.text_input("Main cohort name/abbreviation", "Cohort_1")

    if not plate_id:
        plate_id = sample_name

    warnings = [
        label
        for label, val in [("Project name", proj_name), ("Plate ID", plate_id), ("Cohort name", sample_name)]
        if " " in val
    ]
    if warnings:
        st.sidebar.warning(f"Warning: {'/'.join(warnings)} should not contain spaces.")

    return {
        "proj_name": proj_name,
        "organism_species": ORGANISM_SPECIES[organism],
        "sample": sample,
        "plate_id": plate_id,
        "sample_name": sample_name,
    }


def ms_info() -> dict:
    st.sidebar.header("MS setup")

    machine = st.sidebar.selectbox("Select your instrument", list(MS_OPTIONS.keys()))
    acq_tech = st.sidebar.selectbox("Select your acquisition", MS_OPTIONS[machine])

    srm_lot = None
    if acq_tech in ["SRM", "PRM"]:
        srm_lot = st.sidebar.text_input("ProteomeEdge Lot number: Lot ", "23233")
        if srm_lot:
            st.sidebar.markdown(
                f"The ProteomEdge Lot <span style='color:red'>{srm_lot}</span>",
                unsafe_allow_html=True,
            )

    digestion_enz = st.sidebar.multiselect(
        "Select your tryptic enzyme", list(ENZ_ACCESSION.keys()), default=["Trypsin"]
    )
    dissociation_method = st.sidebar.selectbox(
        "Select your dissociation method", list(DISSOCIATION_ACCESSION.keys()), index=2
    )

    return {
        "machine": machine,
        "srm_lot": srm_lot,
        "sdrf_ms": MS_ACCESSION[machine],
        "acq_tech": acq_tech,
        "digestion_enz": digestion_enz,
        "dissociation_method": dissociation_method,
        "dissociation_accession": DISSOCIATION_ACCESSION[dissociation_method],
        "enz_accession_list": [ENZ_ACCESSION[e] for e in digestion_enz],
        "sdrf_acquisition": MS_ACQUISITION[acq_tech],
    }


def _download_all_button(sample_info: dict) -> None:
    """Sidebar button that zips all available results into one file."""
    st.sidebar.divider()
    st.sidebar.subheader("Download All")

    # Collect files: {zip_path: bytes}
    files = {}

    if "dl_plate_heatmap" in st.session_state:
        files["plate_heatmap.png"] = st.session_state.dl_plate_heatmap
    if "dl_plate_count" in st.session_state:
        files["sample_count.png"] = st.session_state.dl_plate_count
    if "dl_plate_csv" in st.session_state:
        files["plate_layout.csv"] = st.session_state.dl_plate_csv
    for key in ("dl_xcalibur", "dl_chronos_csv", "dl_chronos_xml", "dl_sdrf", "dl_skyline"):
        if key in st.session_state:
            data, name = st.session_state[key]
            files[name] = data

    if not files:
        st.sidebar.caption("Complete the Plate Design tab to enable download.")
        return

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)

    zip_name = f"{sample_info['proj_name']}_{sample_info['plate_id']}_results.zip"
    st.sidebar.download_button(
        label=f"⬇️ Download All ({len(files)} files)",
        data=buf.getvalue(),
        file_name=zip_name,
        mime="application/zip",
    )


def create_sidebar() -> tuple:
    st.sidebar.image("images/logo.png")
    st.sidebar.header("Sample information")
    st.sidebar.write("This part is needed for every file that we are creating.")
    ms = ms_info()
    sample = sample_info()
    _download_all_button(sample)
    return ms, sample
