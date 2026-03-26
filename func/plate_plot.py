import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
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


def plate_dfplot(plate_df, plate_id):
    plate_df_long = create_plate_df_long(plate_df)

    unique_labels = sorted(plate_df_long["Sample"].unique())
    custom_palette = dict(zip(unique_labels, sns.color_palette("colorblind", len(unique_labels))))

    n_rows, n_cols = plate_df.shape
    figsize = (max(12, n_cols * 0.7), max(6, n_rows * 0.6))
    font_size = 3 if n_cols > 12 else 4

    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        plate_df.isnull(), cbar=False, cmap="coolwarm",
        ax=ax, linewidths=1, linecolor="darkgrey", alpha=0.1,
    )
    ax.xaxis.tick_top()
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
    ax.set_title(plate_id)

    for i in range(n_rows):
        for j in range(n_cols):
            value = plate_df.iloc[i, j]
            color = custom_palette.get(value, (1, 1, 1))
            ax.add_patch(plt.Circle((j + 0.5, i + 0.5), 0.4, color=color, fill=True))
            ax.text(j + 0.5, i + 0.5, str(value), ha="center", va="center", color="white", fontsize=font_size)

    ax.set_yticklabels(plate_df.index, rotation=0)
    st.pyplot(fig)

    fig2, ax2 = plt.subplots()
    sns.countplot(
        data=plate_df_long,
        x="Sample",
        ax=ax2,
        order=plate_df_long["Sample"].value_counts().index,
        palette=custom_palette,
    )
    ax2.set_title(f"Sample count in plate {plate_id}")
    ax2.set_xlabel(None)
    ax2.set_ylabel("Count")
    for p in ax2.patches:
        ax2.text(
            p.get_x() + p.get_width() / 2.0,
            p.get_height() + 1,
            int(p.get_height()),
            ha="center", va="center", fontsize=10, color="black",
        )
    st.pyplot(fig2)

    return plate_df_long


def process_plate_positions(text_input, sample_name, plate_type="96-well"):
    """
    Process plate positions from text input and create a plate DataFrame.

    Args:
        text_input (str): Text area input with position specifications ('Label;Position')
        sample_name (str): Default sample name to fill the plate
        plate_type (str): '96-well' (A-H, 1-12) or '384-well' (A-P, 1-24)

    Returns:
        tuple: (plate_df, replace_pos)
    """
    config = PLATE_CONFIGS[plate_type]
    rows = config["rows"]
    n_cols = config["n_cols"]
    valid_rows = "".join(rows)

    replace_pos = [item for item in text_input.split("\n") if item.strip()]

    # Basic format validation
    invalid_chars = set('?!@#$%^&*()+={[]}|\\:"\'<>./~`')
    for item in replace_pos:
        if item.count(";") != 1 or any(c in item for c in invalid_chars):
            st.warning(f"Invalid format: {item}. It should be like 'Cohort_2;Col8'.")
            break

    # Separate Row/Col shorthand entries from individual well entries
    colrow_label = [item for item in replace_pos if "Col" in item or "Row" in item]
    replace_pos = [item for item in replace_pos if "Col" not in item and "Row" not in item]

    # Expand Row/Col shorthand into individual well entries
    for item in colrow_label:
        if ";" not in item:
            st.warning(f"Invalid format: {item}. It should be like 'Cohort_2;Col8'.")
            continue
        label, pos = item.split(";")
        if pos.startswith("Row") and len(pos) == 4 and pos[-1] in valid_rows:
            for col_num in range(1, n_cols + 1):
                replace_pos.insert(0, f"{label};{pos[-1]}{col_num}")
        elif pos.startswith("Col") and pos[3:].isdigit() and 1 <= int(pos[3:]) <= n_cols:
            for row_letter in rows:
                replace_pos.insert(0, f"{label};{row_letter}{pos[3:]}")
        else:
            st.warning(
                f"Invalid position format: {item}. "
                f"Expected 'Label;RowX' (X in {valid_rows[0]}-{valid_rows[-1]}) "
                f"or 'Label;ColN' (N in 1-{n_cols})."
            )

    # Expand comma-separated positions, e.g. "Sample1;A1,A3,A5"
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
                    st.warning(f"Invalid position: {label};{p}. Expected e.g. 'Sample1;A1'.")
        else:
            expanded.append(item)
    replace_pos = expanded

    # Warn on duplicate entries
    if len(replace_pos) != len(set(replace_pos)):
        st.warning("Some positions are mentioned more than once. Please check your input.")

    pos_list = [item.split(";")[1] for item in set(replace_pos) if ";" in item]
    if len(pos_list) != len(set(pos_list)):
        st.warning(
            "A position is assigned to more than one label (possibly via Row/Col shorthand). "
            "Please check your input."
        )

    # Build the plate DataFrame
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

    return plate_df, replace_pos
