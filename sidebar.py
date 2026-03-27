import io
import json
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


def _upload_settings() -> None:
    """Sidebar upload box to restore all settings from a previously saved JSON."""
    uploaded = st.sidebar.file_uploader(
        "Import settings (JSON)", type="json", key="settings_upload"
    )
    if uploaded is not None:
        try:
            cfg = json.load(uploaded)
            s = cfg.get("sample", {})
            m = cfg.get("ms", {})
            p = cfg.get("plate", {})

            # Sample settings
            for key, val in [
                ("settings_proj_name", s.get("proj_name")),
                ("settings_organism", s.get("organism")),
                ("settings_sample", s.get("sample_type")),
                ("settings_plate_id", s.get("plate_id")),
                ("settings_sample_name", s.get("sample_name")),
            ]:
                if val is not None:
                    st.session_state[key] = val

            # MS settings
            for key, val in [
                ("settings_machine", m.get("machine")),
                ("settings_acq_tech", m.get("acq_tech")),
                ("settings_srm_lot", m.get("srm_lot")),
                ("settings_digestion_enz", m.get("digestion_enz")),
                ("settings_dissociation_method", m.get("dissociation_method")),
            ]:
                if val is not None:
                    st.session_state[key] = val

            # Plate settings — also sync _last_plate_type to prevent annotation reset
            if "plate_type" in p:
                st.session_state["settings_plate_type"] = p["plate_type"]
                st.session_state["_last_plate_type"] = p["plate_type"]
            if "annotation_text" in p:
                st.session_state["replace_pos_text"] = p["annotation_text"]

            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Failed to load settings: {e}")


def sample_info() -> dict:
    proj_name = st.sidebar.text_input(
        "Enter your project name", "Project_X", key="settings_proj_name"
    )
    organism = st.sidebar.selectbox(
        "Select your organism", list(ORGANISM_SPECIES.keys()), key="settings_organism"
    )
    sample = st.sidebar.selectbox(
        "Select your sample type",
        ["Plasma", "Serum", "Tissue", "Cell line", "Cell culture"],
        key="settings_sample",
    )
    plate_id = st.sidebar.text_input(
        "Enter your plate ID (Barcode)", "", key="settings_plate_id"
    )
    sample_name = st.sidebar.text_input(
        "Main cohort name/abbreviation", "Cohort_1", key="settings_sample_name"
    )

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

    machine = st.sidebar.selectbox(
        "Select your instrument", list(MS_OPTIONS.keys()), key="settings_machine"
    )
    # Reset acq_tech if the stored value is not valid for the current machine
    if st.session_state.get("settings_acq_tech") not in MS_OPTIONS[machine]:
        st.session_state["settings_acq_tech"] = MS_OPTIONS[machine][0]
    acq_tech = st.sidebar.selectbox(
        "Select your acquisition", MS_OPTIONS[machine], key="settings_acq_tech"
    )

    srm_lot = None
    if acq_tech in ["SRM", "PRM"]:
        srm_lot = st.sidebar.text_input(
            "ProteomeEdge Lot number: Lot ", "23233", key="settings_srm_lot"
        )
        if srm_lot:
            st.sidebar.markdown(
                f"The ProteomEdge Lot <span style='color:red'>{srm_lot}</span>",
                unsafe_allow_html=True,
            )

    digestion_enz = st.sidebar.multiselect(
        "Select your tryptic enzyme",
        list(ENZ_ACCESSION.keys()),
        default=["Trypsin"],
        key="settings_digestion_enz",
    )
    dissociation_method = st.sidebar.selectbox(
        "Select your dissociation method",
        list(DISSOCIATION_ACCESSION.keys()),
        key="settings_dissociation_method",
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


def _build_settings_json() -> str:
    """Build a JSON string of all current sidebar and plate settings."""
    cfg = {
        "sample": {
            "proj_name": st.session_state.get("settings_proj_name", ""),
            "organism": st.session_state.get("settings_organism", "Human"),
            "sample_type": st.session_state.get("settings_sample", "Plasma"),
            "plate_id": st.session_state.get("settings_plate_id", ""),
            "sample_name": st.session_state.get("settings_sample_name", ""),
        },
        "ms": {
            "machine": st.session_state.get("settings_machine", "Q Exactive HF"),
            "acq_tech": st.session_state.get("settings_acq_tech", "DIA"),
            "srm_lot": st.session_state.get("settings_srm_lot"),
            "digestion_enz": st.session_state.get("settings_digestion_enz", ["Trypsin"]),
            "dissociation_method": st.session_state.get("settings_dissociation_method", "HCD"),
        },
        "plate": {
            "plate_type": st.session_state.get("settings_plate_type", "96-well"),
            "annotation_text": st.session_state.get("replace_pos_text", ""),
        },
    }
    return json.dumps(cfg, indent=2)


def _download_all_button(sample_info: dict) -> None:
    """Sidebar button that zips all available results into one file."""
    st.sidebar.divider()
    st.sidebar.subheader("Download All")

    # Collect files: {zip_path: bytes}
    files = {}

    # Always include settings JSON
    settings_json = _build_settings_json()
    settings_filename = f"{sample_info['proj_name']}_{sample_info['plate_id']}_settings.json"
    files[settings_filename] = settings_json.encode("utf-8")

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


def _init_defaults() -> None:
    """Set initial defaults for widgets that don't default to index 0."""
    defaults = {"settings_dissociation_method": "HCD"}
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def create_sidebar() -> tuple:
    st.sidebar.image("images/logo.png")
    _init_defaults()
    st.sidebar.header("Import settings")
    _upload_settings()
    st.sidebar.header("Sample information")
    st.sidebar.write("This part is needed for every file that we are creating.")
    ms = ms_info()
    sample = sample_info()
    _download_all_button(sample)
    return ms, sample
