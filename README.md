# Mass Spectrometry Experiment Planner

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ms-experiment.streamlit.app/)

A Streamlit web application for planning and exporting mass spectrometry experiments end-to-end — from plate design to acquisition lists, SDRF metadata, and Skyline annotations.

---

## Overview

This tool covers the full experimental setup workflow for DIA, DDA, PRM, and SRM proteomics experiments. Starting from a plate layout, it generates all the files needed for instrument acquisition (Xcalibur, Evosep/Chronos), data repository submission (SDRF), and downstream analysis (Skyline).

All settings and outputs can be bundled into a single ZIP for reproducibility and sharing.

---

## Running Locally

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Launch the app
streamlit run web.py
```

Open the URL shown in the terminal (default: `http://localhost:8501`).

---

## Workflow

The app follows a sequential tab-based workflow. Complete each tab in order, as later tabs depend on outputs from earlier ones.

```
Sidebar → Plate Design → Xcalibur → Chronos → SDRF → Skyline → Download All
```

---

## Sidebar — Global Configuration

The sidebar is always visible and controls settings used across all tabs.

### Import Settings
Upload a previously saved `settings.json` to restore a full session — all sidebar fields, plate type, and sample annotation text are restored automatically, then the app reruns.

### Sample Information
| Field | Description |
|---|---|
| Project name | Used in all output file names |
| Organism | Human, Rat, Mouse, Cyanobacteria, E. coli |
| Sample type | Plasma, Serum, Tissue, Cell line, Cell culture |
| Plate ID (Barcode) | Plate identifier used in file names and SDRF |
| Cohort name | Name of the main sample cohort on the plate |

> Spaces in project name, plate ID, or cohort name will trigger a warning — avoid them for clean file names.

### MS Setup
| Field | Description |
|---|---|
| Instrument | Q Exactive HF, TSQ Altis, LIT Stellar |
| Acquisition method | DIA, DDA, PRM, SRM (filtered by instrument) |
| ProteomeEdge Lot number | Appears only for SRM/PRM experiments |
| Tryptic enzyme | Trypsin, Lys-C, Chymotrypsin (multi-select; default: Trypsin) |
| Dissociation method | ETD, CID, HCD (default: HCD) |

### Download All
Packages all generated files into a single ZIP:

| File | Description |
|---|---|
| `{proj}_{plate}_settings.json` | Full session configuration (always included) |
| `plate_heatmap.png` | Plate layout visualization |
| `sample_count.png` | Sample count bar chart |
| `plate_layout.csv` | Plate layout in long format |
| Xcalibur CSV | Sample injection order |
| Chronos CSV + XML | Evosep/Chronos method files |
| SDRF `.tsv` | Sample and data relationship file |
| Skyline CSV | Skyline document annotations |

---

## Tab 1 — Plate Design

Defines the physical layout of your microplate.

**Plate format:** Choose between **96-well** (rows A–H, columns 1–12) or **384-well** (rows A–P, columns 1–24).

### Sample Annotation

The main cohort fills the entire plate by default. Annotate exceptions using the text area — one entry per line, format `Label;Position`:

| Format | Example | Description |
|---|---|---|
| Single well | `Pool;A7` | Assign one well |
| Comma list | `Pool;A1,A2,A3` | Assign multiple wells at once |
| Full row | `Control;RowH` | Assign an entire row |
| Full column | `Control;Col12` | Assign an entire column |

Use `EMPTY` as a label to mark unused wells — these are excluded from all downstream steps (Xcalibur order, SDRF, etc.).

An AI assistant is available to help generate plate layouts from a natural language description (requires an OpenAI API key).

### Outputs
- **Plate layout plot** — realistic microplate visualization with color-coded wells, row/column labels, and a legend
- **Sample count chart** — horizontal bar chart ordered by count
- **`plate_layout.csv`** — long-format table (Row, Column, Sample)

---

## Tab 2 — Xcalibur

Generates the sample injection sequence for Thermo Xcalibur.

### Configuration
| Field | Description |
|---|---|
| Autosampler position | Red / Green / Blue tray with letter prefix |
| Injection volume | Slider (0.01–20 µL) with quick-select buttons, or manual input |
| Data directory | Path written into the CSV |
| Method file | `.meth` file path |
| Injection date | Used in the output file name |

### QC and Wash Injections
Three independent sections — each with its own path, method file, position, and volume:

| Section | Description |
|---|---|
| Wash | Solvent/blank injections between samples |
| QC Plasma | Pooled QC plasma injections |
| QC between samples | Optional QC rows inserted at a configurable interval |

### Sample Order
Toggle **Randomize** to randomize the injection sequence. A preview table is shown before download.

### Output
- **Xcalibur CSV** — `{date}_{proj_name}_Sample_Order_{plate_id}.csv`, UTF-8 BOM encoded, ready for direct Xcalibur import

---

## Tab 3 — Chronos (Evosep)

Generates method files for Evosep One liquid chromatography systems using the Chronos software format.

### Configuration
| Field | Description |
|---|---|
| Output directory | Evosep output path |
| Evosep method | `.cam` method file |
| Xcalibur method | `.meth` file |
| Evosep slot | Slot selector (1–6) |
| Comment | Free text, defaults to ProteomeEdge lot number if set |
| Randomize | Toggle to randomize sample order |

### iRT Pre-run (optional)
Add indexed retention time (iRT) standard injections before the main run:
- Slot, sample count (1–10), method file, and sample name

### Standby Post-run (optional)
Append standby and prepare commands at the end of the run sequence.

All rows — including iRT and standby — are shown in a fully editable table before export.

### Outputs
- **Chronos CSV** — `{date}_{proj_name}_Evosep_Order_{plate_id}.csv`
- **Chronos XML** — `{date}_{proj_name}_Evosep_Order_{plate_id}.xml`
- XML preview with a copy-to-clipboard button

---

## Tab 4 — SDRF

Builds a [Sample and Data Relationship Format (SDRF)](https://github.com/bigbio/proteomics-sample-metadata) file for proteomics data submission to public repositories.

### Configuration
| Field | Description |
|---|---|
| MS file format | `raw` or `mzML` |
| Collision Energy (NCE) | Default: 27 |
| Factor value column | Which sample characteristic to use as the experimental factor |

### Auto-populated Sample Characteristics
Derived from the plate design and sidebar:

| Characteristic | Source |
|---|---|
| Organism | Sidebar organism |
| Organism part | Derived from sample type (e.g. Plasma → blood plasma) |
| Plate / project | Sidebar plate ID and project name |
| Biological replicate | Fixed to 1 (editable) |
| Age, sex, disease, cell type, etc. | Pre-filled as "not available" (fully editable) |

### Auto-populated Data File Properties
Derived from the MS setup:

| Property | Source |
|---|---|
| Instrument | Sidebar instrument |
| Acquisition method | Sidebar acquisition |
| Dissociation method | Sidebar dissociation selection |
| Cleavage agent(s) | Sidebar enzyme selection (one column per enzyme) |
| MS1/MS2 scan ranges | Added automatically for DIA |
| ProteomeEdge lot | Added automatically for SRM/PRM |

The complete table is editable before download.

### Output
- **SDRF TSV** — `{date}_{proj_name}_{plate_id}.sdrf.tsv`, UTF-8 BOM encoded

> Duplicate `comment[cleavage agent details]` columns (one per enzyme) are renamed with a numeric suffix in-app and corrected to the proper SDRF column name in the downloaded file.

---

## Tab 5 — Skyline

Generates a Skyline document annotation file from SDRF sample characteristics.

### SDRF Source
- **Use generated SDRF** — uses the SDRF built in the SDRF tab (no upload needed)
- **Upload SDRF file** — upload an existing `.sdrf.tsv` or `.tsv` file

The annotation table is editable before download.

### Output
- **Skyline annotations CSV** — `{date}_{proj_name}_Skyline_Annotations_{plate_id}.csv`

---

## Settings Import / Export

All sidebar and plate configuration is captured in a structured JSON file that is always included in the Download All ZIP. Upload it via **Import settings** at the top of the sidebar to restore a previous session on any machine.

```json
{
  "sample": {
    "proj_name": "Project_X",
    "organism": "Human",
    "sample_type": "Plasma",
    "plate_id": "Plate001",
    "sample_name": "Cohort_1"
  },
  "ms": {
    "machine": "Q Exactive HF",
    "acq_tech": "DIA",
    "srm_lot": null,
    "digestion_enz": ["Trypsin"],
    "dissociation_method": "HCD"
  },
  "plate": {
    "plate_type": "96-well",
    "annotation_text": "Pool;A7,A8\nControl;H12\nEMPTY;A1"
  }
}
```

---

## Supported Instruments & Methods

| Instrument | Supported Acquisitions |
|---|---|
| Q Exactive HF | DIA, DDA, PRM |
| TSQ Altis | SRM |
| LIT Stellar | DIA, DDA, PRM, SRM |

---

## Dependencies

See `requirements.txt`. Key packages:

| Package | Purpose |
|---|---|
| `streamlit` | Web framework |
| `pandas` / `numpy` | Data handling |
| `matplotlib` / `seaborn` | Plate layout and count visualizations |
| `openpyxl` | Excel support |
| `hypha-rpc` | AI plate generation agent (optional, requires OpenAI API key) |

---

## Contributing

Contributions are welcome. See the [GitHub repository](https://github.com/thanadol-git/FE_MS_lab_web) for open issues and pull requests.
