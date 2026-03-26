import xml.etree.ElementTree as ET
from xml.dom import minidom

import pandas as pd


def ensure_bom(text: str) -> str:
    """Add UTF-8 BOM to text if not already present (for Windows compatibility)."""
    if text.startswith("\ufeff"):
        return text
    return "\ufeff" + text


def build_file_name(row, ms_info: dict, sample_info: dict, date_injection: str) -> str:
    """Build a standardized MS file name from row metadata."""
    parts = [
        ms_info["acq_tech"],
        date_injection,
        sample_info["proj_name"],
        sample_info["plate_id"],
        row["Position"],
    ]
    return "_".join(parts)


def build_download_name(parts: list, suffix: str) -> str:
    """Build a download file name from parts and suffix."""
    return "_".join(parts) + suffix


def chunk_df(df: pd.DataFrame, size: int) -> list:
    """Split a DataFrame into chunks of given size."""
    return [df[i: i + size] for i in range(0, len(df), size)]


def insert_wash_after_chunks(df: pd.DataFrame, wash_df: pd.DataFrame, size: int) -> pd.DataFrame:
    """Insert wash rows after every N sample rows."""
    chunks = chunk_df(df, size)
    return pd.concat(
        [pd.concat([chunk, wash_df], ignore_index=True) for chunk in chunks],
        ignore_index=True,
    )


def sanitize_xml_columns(columns) -> list:
    """Replace characters invalid in XML tag names."""
    return [
        col.replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        for col in columns
    ]


def create_xml_from_dataframe(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a pretty-printed XML string."""
    root = ET.Element("data")
    for _, row in df.iterrows():
        row_elem = ET.SubElement(root, "row")
        for col_name, value in row.items():
            col_elem = ET.SubElement(row_elem, col_name)
            col_elem.text = str(value)
    return minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
