# =====================================================
# Imports
# =====================================================

from flask import Blueprint, render_template, request
import pandas as pd
import seaborn as sns
import os
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# =====================================================
# WIPAHS SOFT COLOUR PALETTE
# =====================================================

WIPAHS_COLORS = [
    "#4C78A8",  # blue
    "#F58518",  # orange
    "#E45756",  # red
    "#72B7B2",  # teal
    "#54A24B",  # green
    "#EECA3B",  # yellow
]

# =====================================================
# Blueprint
# =====================================================

sss_bp = Blueprint(
    "sss",
    __name__,
    template_folder="templates"
)

# =====================================================
# HARD‑WIRED GITHUB DATA URL
# =====================================================

SSS_DATA = "https://raw.githubusercontent.com/CMBarnes127503/flask-folder-analysis/main/data/Data%20Set_SSS.xlsx?raw=1"

# =====================================================
# Helper Functions
# =====================================================

def load_sss_data():
    try:
        df = pd.read_excel(SSS_DATA, sheet_name="SSS (WW)", header=None)
    except Exception as e:
        print("DEBUG: Failed to load SSS dataset:", e)
        return None

    df = df.astype(str).apply(lambda col: col.str.strip())
    return df


def get_table(df, table_name):
    df_str = df.astype(str).apply(lambda col: col.str.strip())

    patterns = [
        table_name,
        "Table 3:",
        "Three or more occasions",
        "FG Indicator 38",
        "Indicator 38",
        "FG38",
        "Three or more",
    ]

    matches = []
    for p in patterns:
        mask = df_str.apply(lambda col: col.str.contains(p, case=False, regex=False))
        rows = df.index[mask.any(axis=1)].tolist()
        matches.extend(rows)

    if not matches:
        return None

    start = matches[0] + 1
    while start < len(df) and df.iloc[start].isna().all():
        start += 1

    end = start
    while end < len(df) and not df.iloc[end].isna().all():
        end += 1

    table = df.iloc[start:end].copy()
    table = table.reset_index(drop=True)
    return table


def save_plot(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"

# =====================================================
# TEXT SUMMARY FUNCTIONS
# =====================================================

def simple_summary(df, table_name, title):
    table = get_table(df, table_name)
    if table is None:
        return f"{title} could not be found."

    numeric_cols = []
    for col in range(1, table.shape[1]):
        series = pd.to_numeric(table.iloc[:, col], errors="coerce")
        if series.notna().sum() > 0:
            numeric_cols.append(col)

    if not numeric_cols:
        return f"No numeric columns found in {title}."

    if table_name == "Table 6" and len(numeric_cols) > 1:
        first_numeric = numeric_cols[1]
    else:
        first_numeric = numeric_cols[0]

    wales_row = table[table.iloc[:, 0] == "Wales"]
    if wales_row.empty:
        return f"Wales row missing in {title}."

    value = pd.to_numeric(wales_row.iloc[0, first_numeric], errors="coerce")

    lines = [title + ":", ""]
    lines.append(f"Wales: {value:.1f}%")

    return "\n".join(lines)


def summary_table_4(df):
    table = get_table(df, "Table 4")
    if table is None:
        return "Weekly Activity Breakdown could not be found."

    wales_row = table[table.iloc[:, 0] == "Wales"]
    if wales_row.empty:
        return "Wales row missing."

    numeric_cols = []
    for col in range(1, table.shape[1]):
        series = pd.to_numeric(table.iloc[:, col], errors="coerce")
        if series.notna().sum() > 0:
            numeric_cols.append(col)

    numeric_cols = numeric_cols[:4]

    labels = [
        "No frequent activity",
        "Once per week",
        "Twice per week",
        "Three times a week or more"
    ]

    values = [pd.to_numeric(wales_row.iloc[0, col], errors="coerce") for col in numeric_cols]

    lines = ["Weekly Activity Breakdown:", ""]
    for label, val in zip(labels, values):
        lines.append(f"{label}: {val:.1f}%")

    return "\n".join(lines)

# =====================================================
# UNIVERSAL PLOT FUNCTIONS
# =====================================================

def bar_plot(df, table_name, title):
    table = get_table(df, table_name)
    if table is None:
        return None

    areas = table.iloc[:, 0].astype(str).tolist()

    numeric_cols = []
    for col in range(1, table.shape[1]):
        series = pd.to_numeric(table.iloc[:, col], errors="coerce")
        if series.notna().sum() > 0:
            numeric_cols.append(col)

    if not numeric_cols:
        return None

    if table_name == "Table 6" and len(numeric_cols) > 1:
        first_numeric = numeric_cols[1]
    else:
        first_numeric = numeric_cols[0]

    values = pd.to_numeric(table.iloc[:, first_numeric], errors="coerce").tolist()

    fig, ax = plt.subplots(figsize=(10, 5))

    # ⭐ Plot bars at numeric positions
    x = range(len(areas))
    ax.bar(x, values, color=WIPAHS_COLORS[0])

    # ⭐ Explicitly set tick positions AND labels
    ax.set_xticks(x)
    ax.set_xticklabels(areas, rotation=45, ha="right")

    ax.set_title(title)
    ax.set_ylabel("Percentage")

    return save_plot(fig)



def stacked_bar_plot(df):
    table = get_table(df, "Table 4")
    if table is None:
        return None

    area = table.iloc[:, 0]

    numeric_cols = []
    for col in range(1, table.shape[1]):
        series = pd.to_numeric(table.iloc[:, col], errors="coerce")
        if series.notna().sum() > 0:
            numeric_cols.append(col)

    numeric_cols = numeric_cols[:4]

    labels = [
        "No frequent activity",
        "Once per week",
        "Twice per week",
        "Three times a week or more"
    ]

    clean = pd.DataFrame({"Area": area})

    for label, col in zip(labels, numeric_cols):
        clean[label] = pd.to_numeric(table.iloc[:, col], errors="coerce")

    clean = clean.set_index("Area")

    fig, ax = plt.subplots(figsize=(10, 6))

    # ⭐ Apply WIPAHS colours
    clean.plot(kind="bar", stacked=True, ax=ax, color=WIPAHS_COLORS[:4])

    ax.set_title("Weekly Activity Breakdown")
    ax.set_ylabel("Percentage")

    return save_plot(fig)


def heatmap_plot(df, table_name, title):
    table = get_table(df, table_name)
    if table is None:
        return None

    # Rename first column to "Sport"
    table = table.rename(columns={table.columns[0]: "Sport"})

    # Identify numeric columns
    numeric_cols = []
    for col in table.columns[1:]:
        series = pd.to_numeric(table[col], errors="coerce")
        if series.notna().sum() > 0:
            numeric_cols.append(col)
            table[col] = series

    # Build clean table
    clean = table[["Sport"] + numeric_cols].copy()
    clean = clean.set_index("Sport")

    # ⭐ FIX: Ensure ALL sports appear on the heatmap
    all_sports = table["Sport"].astype(str).unique()
    clean = clean.reindex(all_sports).fillna(0)

    # Plot
    fig, ax = plt.subplots(figsize=(14, 10))

    sns.heatmap(
        clean,
        cmap=sns.color_palette(WIPAHS_COLORS, as_cmap=True),
        annot=True,
        fmt=".1f",
        ax=ax
    )

    ax.set_title(title)

    return save_plot(fig)


# =====================================================
# ROUTING LOGIC
# =====================================================

@sss_bp.route("/sss_ww", methods=["GET", "POST"])
def sss_ww():
    message = None
    text_summary = None
    plot_url = None

    df = load_sss_data()

    if df is None:
        return render_template("index.html", message="Could not load SSS dataset from GitHub.")

    if request.method == "POST":

        analysis = request.form.get("wales_analysis")

        if analysis == "Frequent Weekly Activity (Table 3)":
            text_summary = simple_summary(df, "Table 3", "Frequent Weekly Activity (3+ times)")
            plot_url = bar_plot(df, "Table 3", "Frequent Weekly Activity")

        elif analysis == "Weekly Activity Breakdown (Table 4)":
            text_summary = summary_table_4(df)
            plot_url = stacked_bar_plot(df)

        elif analysis == "Extracurricular Sport – Weekly (Table 5)":
            text_summary = simple_summary(df, "Table 5", "Extracurricular Sport – Weekly")
            plot_url = bar_plot(df, "Table 5", "Extracurricular Sport – Weekly")

        elif analysis == "Community Sport – Weekly (Table 6)":
            text_summary = simple_summary(df, "Table 6", "Community Sport – Weekly")
            plot_url = bar_plot(df, "Table 6", "Community Sport – Weekly")

        elif analysis == "Any Sport Participation – Annual (Table 7a)":
            text_summary = simple_summary(df, "Table 7a", "Any Sport Participation – Annual")
            plot_url = bar_plot(df, "Table 7a", "Any Sport Participation – Annual")

        elif analysis == "Sport Participation by Sport – Annual (Table 7c)":
            text_summary = "Sport participation by sport (annual)."
            plot_url = heatmap_plot(df, "Table 7c", "Sport Participation by Sport – Annual")

        elif analysis == "Extracurricular Sport – Annual (Table 8a)":
            text_summary = simple_summary(df, "Table 8a", "Extracurricular Sport – Annual")
            plot_url = bar_plot(df, "Table 8a", "Extracurricular Sport – Annual")

        elif analysis == "Extracurricular Sport by Sport – Annual (Table 8c)":
            text_summary = "Extracurricular sport participation by sport (annual)."
            plot_url = heatmap_plot(df, "Table 8c", "Extracurricular Sport by Sport – Annual")

        elif analysis == "Community Club Participation – Annual (Table 9a)":
            text_summary = simple_summary(df, "Table 9a", "Community Club Participation – Annual")
            plot_url = bar_plot(df, "Table 9a", "Community Club Participation – Annual")

        elif analysis == "Community Club Participation by Sport – Annual (Table 9c)":
            text_summary = "Community club participation by sport (annual)."
            plot_url = heatmap_plot(df, "Table 9c", "Community Club Participation – Annual")

        return render_template(
            "analysis.html",
            analysis_type=analysis,
            text_summary=text_summary,
            plot_url=plot_url
        )

    return render_template("index.html")
