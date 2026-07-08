# =====================================================
# Imports
# =====================================================

from flask import Blueprint, render_template, request
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import io
import base64

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
    """Load SSS dataset directly from GitHub."""
    try:
        df = pd.read_excel(SSS_DATA, sheet_name="SSS (WW)", header=None)
    except Exception as e:
        print("DEBUG: Failed to load SSS dataset:", e)
        return None

    df = df.astype(str).apply(lambda col: col.str.strip())
    return df


def get_table(df, table_name):
    print("\n\n==================== DEBUG: get_table() ====================")
    print(f"Looking for table: {table_name}\n")

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
        if rows:
            print(f"Pattern '{p}' matched rows: {rows}")
        matches.extend(rows)

    if not matches:
        print("DEBUG: No table match found. First 200 rows:")
        print(df_str.head(200))
        return None

    start = matches[0] + 1
    print(f"DEBUG: Initial start row: {start}")

    while start < len(df) and df.iloc[start].isna().all():
        print(f"DEBUG: Skipping blank row at index {start}")
        start += 1

    print(f"DEBUG: Real table starts at row index: {start}")

    end = start
    while end < len(df) and not df.iloc[end].isna().all():
        end += 1

    print(f"DEBUG: Table ends at row index: {end}")

    table = df.iloc[start:end].copy()
    table = table.reset_index(drop=True)

    print("\nDEBUG: Extracted table preview:")
    print(table.head(15))

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
    print("\n\n==================== DEBUG: simple_summary() ====================")
    print(f"Summary requested for: {table_name}")

    table = get_table(df, table_name)
    if table is None:
        return f"{title} could not be found."

    numeric_cols = []
    for col in range(1, table.shape[1]):
        series = pd.to_numeric(table.iloc[:, col], errors="coerce")
        if series.notna().sum() > 0:
            numeric_cols.append(col)

    print(f"DEBUG: Numeric columns detected: {numeric_cols}")

    if not numeric_cols:
        return f"No numeric columns found in {title}."

    if table_name == "Table 6" and len(numeric_cols) > 1:
        first_numeric = numeric_cols[1]
        print(f"DEBUG: Table 6 special rule applied. Using numeric column: {first_numeric}")
    else:
        first_numeric = numeric_cols[0]
        print(f"DEBUG: Using numeric column: {first_numeric}")

    wales_row = table[table.iloc[:, 0] == "Wales"]
    print("DEBUG: Wales row:")
    print(wales_row)

    if wales_row.empty:
        return f"Wales row missing in {title}."

    value = pd.to_numeric(wales_row.iloc[0, first_numeric], errors="coerce")
    print(f"DEBUG: Wales value extracted: {value}")

    lines = [title + ":", ""]
    lines.append(f"Wales: {value:.1f}%")

    return "\n".join(lines)


def summary_table_4(df):
    table = get_table(df, "Table 4")
    if table is None:
        return "Weekly Activity Breakdown could not be found."

    wales_row = table[table.iloc[:, 0] == "Wales"]
    if wales_row.empty:
        return "Wales row missing in Weekly Activity Breakdown."

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
    print("\n\n==================== DEBUG: bar_plot() ====================")
    print(f"Plot requested for: {table_name}")

    table = get_table(df, table_name)
    if table is None:
        return None

    areas = table.iloc[:, 0].astype(str).tolist()
    print(f"DEBUG: Areas: {areas}")

    numeric_cols = []
    for col in range(1, table.shape[1]):
        series = pd.to_numeric(table.iloc[:, col], errors="coerce")
        if series.notna().sum() > 0:
            numeric_cols.append(col)

    print(f"DEBUG: Numeric columns detected: {numeric_cols}")

    if not numeric_cols:
        return None

    if table_name == "Table 6" and len(numeric_cols) > 1:
        first_numeric = numeric_cols[1]
        print(f"DEBUG: Table 6 special rule applied. Using numeric column: {first_numeric}")
    else:
        first_numeric = numeric_cols[0]
        print(f"DEBUG: Using numeric column: {first_numeric}")

    values = pd.to_numeric(table.iloc[:, first_numeric], errors="coerce").tolist()
    print(f"DEBUG: Values used for bar plot: {values}")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(areas, values)
    ax.set_title(title)
    ax.set_ylabel("Percentage")
    plt.xticks(rotation=45)

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
    clean.plot(kind="bar", stacked=True, ax=ax)
    ax.set_title("Weekly Activity Breakdown")
    ax.set_ylabel("Percentage")

    return save_plot(fig)


def heatmap_plot(df, table_name, title):
    table = get_table(df, table_name)
    if table is None:
        return None

    table = table.rename(columns={table.columns[0]: "Sport"})

    numeric_cols = []
    for col in table.columns[1:]:
        series = pd.to_numeric(table[col], errors="coerce")
        if series.notna().sum() > 0:
            numeric_cols.append(col)
            table[col] = series

    clean = table[["Sport"] + numeric_cols].copy()
    clean = clean.set_index("Sport")

    real_names = [
        "Wales",
        "RSP West Wales",
        "Pembrokeshire",
        "Carmarthenshire",
        "Swansea",
        "Neath Port Talbot"
    ]

    clean.columns = real_names[:len(clean.columns)]

    fig, ax = plt.subplots(figsize=(14, 10))
    sns.heatmap(clean, cmap="viridis", annot=True, fmt=".1f", ax=ax)
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

        print("\n\nDEBUG: FIRST 200 ROWS OF DATAFRAME\n")
        print(df.head(200))

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
            plot_url = heatmap_plot(df, "Table 9c", "Community Club Participation by Sport – Annual")

        return render_template(
            "analysis.html",
            analysis_type=analysis,
            text_summary=text_summary,
            plot_url=plot_url
        )

    return render_template("index.html")
