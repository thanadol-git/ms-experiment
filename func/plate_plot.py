import io

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import streamlit as st


PLATE_CONFIGS = {
    "96-well": {
        "rows": list("ABCDEFGH"),
        "n_cols": 12,
    },
    "384-well": {
        "rows": list("ABCDEFGHIJKLMNOP"),
        "n_cols": 24,
    },
}


def create_plate_df_long(plate_df):
    long_format = plate_df.stack().reset_index()
    long_format.columns = ["Row", "Column", "Sample"]
    return long_format


def _draw_plate(plate_df, plate_id, ax):
    """Draw a realistic microplate layout on the given axes."""
    n_rows, n_cols = plate_df.shape
    rows = list(plate_df.index)

    is_384 = n_cols > 12
    well_spacing = 1.0
    well_radius = 0.46
    margin_left = 1.2
    margin_top = 1.0
    margin_right = 0.8
    margin_bottom = 0.8

    plate_w = margin_left + n_cols * well_spacing + margin_right
    plate_h = margin_top + n_rows * well_spacing + margin_bottom

    ax.set_xlim(-0.2, plate_w + 0.2)
    ax.set_ylim(-0.2, plate_h + 0.2)
    ax.set_aspect("equal")
    ax.axis("off")

    plate_rect = mpatches.FancyBboxPatch(
        (0, 0), plate_w, plate_h,
        boxstyle="round,pad=0.25",
        linewidth=2.5, edgecolor="#555555", facecolor="white", zorder=0,
    )
    ax.add_patch(plate_rect)

    unique_labels = sorted(plate_df.stack().unique())
    palette = dict(zip(unique_labels, sns.color_palette("colorblind", len(unique_labels))))
    if "EMPTY" in palette:
        palette["EMPTY"] = "white"

    max_len = max(len(str(v)) for v in plate_df.values.flatten())
    label_fs = max(3, min(6, 30 // max_len)) if is_384 else max(4, min(9, 42 // max_len))
    tick_fs = 6 if is_384 else 9

    for j in range(n_cols):
        cx = margin_left + j * well_spacing + well_spacing / 2
        cy = plate_h - margin_top / 2
        ax.text(cx, cy, str(j + 1), ha="center", va="center",
                fontsize=tick_fs, fontweight="bold", color="#333333")

    for i, row_label in enumerate(rows):
        cx = margin_left / 2
        cy = plate_h - margin_top - i * well_spacing - well_spacing / 2
        ax.text(cx, cy, row_label, ha="center", va="center",
                fontsize=tick_fs, fontweight="bold", color="#333333")

    for i in range(n_rows):
        for j in range(n_cols):
            value = plate_df.iloc[i, j]
            color = palette.get(value, (1, 1, 1))
            cx = margin_left + j * well_spacing + well_spacing / 2
            cy = plate_h - margin_top - i * well_spacing - well_spacing / 2

            is_empty = str(value) == "EMPTY"
            ring_color = "#dddddd" if is_empty else "#bbbbbb"
            fill_color = "white" if is_empty else color
            text_color = "black" if is_empty else "white"

            ax.add_patch(plt.Circle((cx, cy), well_radius, color=ring_color, zorder=1))
            ax.add_patch(plt.Circle((cx, cy), well_radius * 0.94, color=fill_color, zorder=2))
            ax.text(cx, cy, str(value), ha="center", va="center",
                    color=text_color, fontsize=label_fs, zorder=3, fontweight="bold")


@st.cache_data
def _build_plate_pngs(plate_df: pd.DataFrame, plate_id: str) -> tuple:
    """Render plate and count figures to PNG bytes. Cached so reruns skip redrawing."""
    n_rows, n_cols = plate_df.shape
    is_384 = n_cols > 12

    well_inch = 0.42 if is_384 else 0.72
    fig_w = n_cols * well_inch + 2.0
    fig_h = n_rows * well_inch + 2.0
    label_fs = 10

    unique_labels = sorted(plate_df.stack().unique())
    palette = dict(zip(unique_labels, sns.color_palette("colorblind", len(unique_labels))))
    if "EMPTY" in palette:
        palette["EMPTY"] = "white"

    # Plate heatmap
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), facecolor="white")
    _draw_plate(plate_df, plate_id, ax)
    ax.set_title(plate_id, fontsize=14, fontweight="bold")
    legend_handles = [
        mpatches.Patch(facecolor=palette[lbl], edgecolor="#555555", label=lbl)
        for lbl in unique_labels
    ]
    ax.legend(
        handles=legend_handles,
        loc="center right",
        bbox_to_anchor=(-0.18, 0.5),
        bbox_transform=ax.transAxes,
        ncol=1,
        fontsize=label_fs + 2,
        framealpha=0.85,
        title=plate_id,
        title_fontsize=label_fs + 3,
    )
    fig.subplots_adjust(left=0.25, right=0.98)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    heatmap_bytes = buf.getvalue()

    # Count plot
    plate_df_long = create_plate_df_long(plate_df)
    order = plate_df_long["Sample"].value_counts().sort_values().index
    fig2, ax2 = plt.subplots(figsize=(5, max(3, len(unique_labels) * 0.6)))
    sns.countplot(data=plate_df_long, y="Sample", ax=ax2, order=order, palette=palette)
    for p in ax2.patches:
        p.set_edgecolor("black")
        p.set_linewidth(0.8)
    ax2.set_title(f"Sample count — {plate_id}")
    ax2.set_xlabel("Count")
    ax2.set_ylabel(None)
    for p in ax2.patches:
        ax2.text(
            p.get_width() + 0.3,
            p.get_y() + p.get_height() / 2.0,
            int(p.get_width()),
            ha="left", va="center", fontsize=10, color="black",
        )
    fig2.tight_layout()
    buf2 = io.BytesIO()
    fig2.savefig(buf2, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig2)
    count_bytes = buf2.getvalue()

    return heatmap_bytes, count_bytes


def plate_dfplot(plate_df, plate_id):
    heatmap_png, count_png = _build_plate_pngs(plate_df, plate_id)
    st.image(heatmap_png)
    st.image(count_png)
    st.session_state.dl_plate_heatmap = heatmap_png
    st.session_state.dl_plate_count = count_png
    return create_plate_df_long(plate_df)


@st.cache_data
def _process_plate_positions_pure(text_input: str, sample_name: str, plate_type: str) -> tuple:
    """Pure computation for plate position parsing. Returns (plate_df, replace_pos, warnings)."""
    config = PLATE_CONFIGS[plate_type]
    rows = config["rows"]
    n_cols = config["n_cols"]
    valid_rows = "".join(rows)
    warnings = []

    replace_pos = [item for item in text_input.split("\n") if item.strip()]

    invalid_chars = set('?!@#$%^&*()+={[]}|\\:"\'<>./~`')
    for item in replace_pos:
        if item.count(";") != 1 or any(c in item for c in invalid_chars):
            warnings.append(f"Invalid format: {item}. It should be like 'Cohort_2;Col8'.")
            break

    colrow_label = [item for item in replace_pos if "Col" in item or "Row" in item]
    replace_pos = [item for item in replace_pos if "Col" not in item and "Row" not in item]

    for item in colrow_label:
        if ";" not in item:
            warnings.append(f"Invalid format: {item}. It should be like 'Cohort_2;Col8'.")
            continue
        label, pos = item.split(";")
        if pos.startswith("Row") and len(pos) == 4 and pos[-1] in valid_rows:
            for col_num in range(1, n_cols + 1):
                replace_pos.insert(0, f"{label};{pos[-1]}{col_num}")
        elif pos.startswith("Col") and pos[3:].isdigit() and 1 <= int(pos[3:]) <= n_cols:
            for row_letter in rows:
                replace_pos.insert(0, f"{label};{row_letter}{pos[3:]}")
        else:
            warnings.append(
                f"Invalid position format: {item}. "
                f"Expected 'Label;RowX' (X in {valid_rows[0]}-{valid_rows[-1]}) "
                f"or 'Label;ColN' (N in 1-{n_cols})."
            )

    expanded = []
    for item in replace_pos:
        if ";" not in item:
            expanded.append(item)
            continue
        label, pos = item.split(";")
        parts = [p.strip() for p in pos.split(",") if p.strip()]
        if len(parts) > 1:
            for p in parts:
                if p[0] in valid_rows and p[1:].isdigit() and 1 <= int(p[1:]) <= n_cols:
                    expanded.append(f"{label};{p}")
                else:
                    warnings.append(f"Invalid position: {label};{p}. Expected e.g. 'Sample1;A1'.")
        else:
            expanded.append(item)
    replace_pos = expanded

    if len(replace_pos) != len(set(replace_pos)):
        warnings.append("Some positions are mentioned more than once. Please check your input.")

    pos_list = [item.split(";")[1] for item in set(replace_pos) if ";" in item]
    if len(pos_list) != len(set(pos_list)):
        warnings.append(
            "A position is assigned to more than one label (possibly via Row/Col shorthand). "
            "Please check your input."
        )

    data = np.resize(sample_name, (len(rows), n_cols))
    plate_df = pd.DataFrame(
        data,
        columns=[str(i) for i in range(1, n_cols + 1)],
        index=rows,
    )
    for item in replace_pos:
        if ";" in item:
            label, pos = item.split(";")
            row = pos[0]
            col = int(pos[1:])
            plate_df.at[row, str(col)] = label

    return plate_df, replace_pos, warnings


def process_plate_positions(text_input, sample_name, plate_type="96-well"):
    plate_df, replace_pos, warnings = _process_plate_positions_pure(text_input, sample_name, plate_type)
    for w in warnings:
        st.warning(w)
    return plate_df, replace_pos
