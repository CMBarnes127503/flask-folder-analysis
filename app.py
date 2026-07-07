import os
import uuid
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")   # <-- MUST come immediately after importing matplotlib

import matplotlib.pyplot as plt

from flask import Flask, render_template, request
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import math

app = Flask(__name__)
app.secret_key = os.urandom(24)   # <-- ADD THIS LINE

from sss import sss_bp
app.register_blueprint(sss_bp)

from questions import questions_bp
app.register_blueprint(questions_bp)

from sports_participation import sports_bp
app.register_blueprint(sports_bp)


REGION_FOLDER = "region_folder"
COMPARE_FOLDER = "compare_folder"

# -------------------------------------------------
# Central plots folder (works in dev and in EXE)
# -------------------------------------------------
PLOTS_FOLDER = os.path.join(app.static_folder, "plots")
os.makedirs(PLOTS_FOLDER, exist_ok=True)


def save_plot(filename):
    """
    Save a plot into static/plots and return the browser path.
    """
    fs_path = os.path.join(PLOTS_FOLDER, filename)   # filesystem path
    web_path = f"static/plots/{filename}"            # what <img src="..."> should use
    return fs_path, web_path


# -------------------------------------------------
# Helper: Clear a folder safely
# -------------------------------------------------
def clear_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)
    for f in os.listdir(path):
        full = os.path.join(path, f)
        if os.path.isfile(full):
            os.remove(full)


# -------------------------------------------------
# Helper: List Excel files
# -------------------------------------------------
def list_valid_excels(path):
    if not os.path.exists(path):
        return []
    return [f for f in os.listdir(path) if f.lower().endswith(".xlsx")]


# -------------------------------------------------
# KPI plotting (Table 1 + Table 3)
# -------------------------------------------------
def plot_kpi(filepath, category="Gender"):
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import uuid
    import os

    # CATEGORY CONFIG
    config = {
        "Gender": {
            "groups": ["Boy", "Girl", "Pupils identifying as 'Other'", "I do not want to say"],
            "title": "Participation by Gender Category"
        },
        "Yeargroup": {
            "groups": ["Years 3 and 4", "Years 5 and 6", "Years 7 to 9", "Years 10 and 11"],
            "title": "Participation by Year Group"
        },
        "Ethnicity": {
            "groups": [
                "White",
                "Mixed / Multiple ethnic group",
                "Asian / Asian Welsh / Asian British",
                "Black / Black Welsh / Black British / Caribbean / African",
                "Other ethnic group"
            ],
            "title": "Participation by Ethnicity"
        },
        "Disabilityorimpairment": {
            "groups": ["Any disability or impairment", "No disability or impairment", "I don't want to say"],
            "title": "Participation by Disability or impairment"
        },
        "Learningdifficulty": {
            "groups": ["Any learning difficulty", "No learning difficulty", "I don't want to say"],
            "title": "Participation by Learning difficulty"
        },
        "FreeSchoolMealquartile": {
            "groups": ["FSM 1", "FSM 2", "FSM 3", "FSM 4"],
            "title": "Participation by Free School Meal quartile"
        },
        "Welshspeaker": {
            "groups": ["Speaks Welsh", "Does not speak Welsh"],
            "title": "Participation by Welsh speaker"
        }
    }

    group_names = config[category]["groups"]
    title_ = config[category]["title"]

    # READ TABLE 1
    df = pd.read_excel(filepath, sheet_name="Table 1")
    selected_cols = [1, 4, 5]

    labels = df.iloc[:, 0].astype(str).str.strip()
    mask = labels.isin(group_names)
    matched_labels = labels[mask]

    matching = df.loc[mask, df.columns[selected_cols]].copy()
    for col in matching.columns:
        matching[col] = pd.to_numeric(matching[col], errors="coerce").fillna(0)

    numeric = matching.to_numpy()

    # PLOT 1: 3D Scatter
    fig1 = plt.figure(figsize=(16, 14))
    ax1 = fig1.add_subplot(111, projection="3d")

    plt.subplots_adjust(left=0.22, right=0.90, top=0.92, bottom=0.22)

    unique_groups = matched_labels.unique()
    colors = plt.cm.tab10(np.linspace(0, 1, len(unique_groups)))

    for color, g in zip(colors, unique_groups):
        idx = matched_labels == g
        ax1.scatter(
            numeric[idx, 1],
            numeric[idx, 2],
            numeric[idx, 0],
            s=140,
            color=color,
            label=g
        )

    ax1.zaxis.set_rotate_label(False)
    ax1.text2D(
        0.98, 0.5, "% that participate ≥3x/week",
        transform=ax1.transAxes,
        rotation=90,
        fontsize=12,
        va='center'
    )

    ax1.set_xlabel("% that think PE lessons & sport help", labelpad=20)
    ax1.set_ylabel("% that feel listened to", labelpad=20)
    ax1.set_title(title_, pad=40)
    ax1.legend(loc="best")
    ax1.grid(True)

    scatter_name = f"kpi_scatter_{uuid.uuid4().hex}.png"
    scatter_fs, scatter_path = save_plot(scatter_name)
    plt.savefig(scatter_fs, bbox_inches="tight")
    plt.close(fig1)

    # READ TABLE 3 (Bar Chart)
    raw3 = pd.read_excel(filepath, sheet_name="Table 3", header=1)
    raw3.columns = raw3.columns.astype(str).str.strip().str.replace("\u00A0", "", regex=False)

    def find_col(possible_names):
        for col in raw3.columns:
            cleaned = col.lower().replace(" ", "")
            if cleaned in possible_names:
                return col
        return None

    boy_col = find_col(["boy"])
    girl_col = find_col(["girl"])
    all_col = find_col(["all"])

    countries = raw3.iloc[:, 0].astype(str)

    male_pct = pd.to_numeric(raw3[boy_col], errors="coerce").fillna(0)
    female_pct = pd.to_numeric(raw3[girl_col], errors="coerce").fillna(0)
    all_pct = pd.to_numeric(raw3[all_col], errors="coerce").fillna(0)

    # PLOT 2: Horizontal Bar Chart
    fig2, ax2 = plt.subplots(figsize=(30, len(countries) * 0.8))

    y = np.arange(len(countries))

    ax2.barh(y - 0.25, male_pct, height=0.25, label="Boy")
    ax2.barh(y,         female_pct, height=0.25, label="Girl")
    ax2.barh(y + 0.25, all_pct,     height=0.25, label="All")

    ax2.set_yticks(y)
    ax2.set_yticklabels(countries, fontsize=18)

    ax2.set_xlabel("Participation (%)", fontsize=22)
    ax2.set_title("Activity Participation (3+ times per week)", fontsize=26)

    ax2.legend(fontsize=20)
    ax2.grid(True)

    plt.tight_layout()

    bar_name = f"kpi_bar_{uuid.uuid4().hex}.png"
    bar_fs, bar_path = save_plot(bar_name)
    plt.savefig(bar_fs, bbox_inches="tight")
    plt.close(fig2)

    return scatter_path, bar_path


def plot_kpi_summary_3d():
    import os
    import uuid
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D

    folder = COMPARE_FOLDER
    files = [
        f for f in os.listdir(folder)
        if f.lower().endswith(".xlsx") and not f.startswith("~$")
    ]

    if not files:
        return None

    sheet = "Table 1"
    num_categories = 3
    rows_per_sheet = 3
    L = len(files)

    data_cube = np.zeros((rows_per_sheet, num_categories, L))
    region_labels_list = []
    category_labels = None

    # -----------------------------
    # Read all files
    # -----------------------------
    for i, fname in enumerate(files):
        fpath = os.path.join(folder, fname)
        df = pd.read_excel(fpath, sheet_name=sheet)

        # Extract category labels once
        if category_labels is None:
            category_labels = df.columns[1:4]

        # Region labels (first 3 rows)
        region_labels = df.iloc[0:3, 0].astype(str).values
        region_labels_list.append(region_labels)

        # Extract numeric data
        raw = df.iloc[0:3, 1:4].astype(str).replace(
            ["-", "nan", "NaN", ""], "0"
        )
        numeric = raw.apply(pd.to_numeric, errors="coerce").fillna(0).values

        data_cube[:, :, i] = numeric

    # -----------------------------
    # Build 3D bar chart
    # -----------------------------
    fig = plt.figure(figsize=(16, 12))
    ax = fig.add_subplot(111, projection="3d")

    bar_width = 0.2
    group_spacing = 1.5

    # Unique region names across all files
    all_regions = np.concatenate(region_labels_list)
    unique_regions = pd.unique(all_regions)

    # Assign colors
    cmap = plt.cm.get_cmap("tab10", len(unique_regions))
    region_color_map = {
        region: cmap(idx) for idx, region in enumerate(unique_regions)
    }

    legend_handles = []
    legend_names = []

    # -----------------------------
    # Draw bars
    # -----------------------------
    for sheet_idx in range(L):
        for cat_idx in range(num_categories):
            for reg_idx in range(rows_per_sheet):

                value = data_cube[reg_idx, cat_idx, sheet_idx]
                region_name = region_labels_list[sheet_idx][reg_idx]
                color = region_color_map[region_name]

                x = cat_idx + (reg_idx - 1) * bar_width
                y = sheet_idx * group_spacing
                z = 0
                dx = bar_width
                dy = bar_width
                dz = value

                ax.bar3d(x, y, z, dx, dy, dz, color=color, alpha=0.95)

                # Legend entry
                if region_name not in legend_names:
                    h = ax.bar3d(0, 0, 0, 0, 0, 0, color=color)
                    legend_handles.append(h)
                    legend_names.append(region_name)

    # -----------------------------
    # Axes & labels
    # -----------------------------
    ax.set_xlabel("Category")
    ax.set_ylabel("File Index")
    ax.set_zlabel("Percentage (%)")
    ax.set_title("3D Grouped Bar Chart: Regions × Categories × Files")

    ax.set_xticks(range(num_categories))
    ax.set_xticklabels(category_labels, rotation=30)

    ax.set_yticks([i * group_spacing for i in range(L)])
    ax.set_yticklabels([f"File {i+1}" for i in range(L)])

    ax.view_init(30, 45)
    ax.grid(True)

    # -----------------------------
    # Save plot
    # -----------------------------
    outname = f"compare_3d_{uuid.uuid4().hex}.png"
    out_fs, out_path = save_plot(outname)
    plt.savefig(out_fs, bbox_inches="tight")
    plt.close(fig)

    return out_path


# -------------------------------------------------
# Frequency
# -------------------------------------------------
def plot_frequency(filepath):
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import uuid
    import os

    df = pd.read_excel(filepath, sheet_name="Table 3", header=1)

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace("\u00A0", "", regex=False)
    )

    countries = df.iloc[:, 0].astype(str)

    male_pct = pd.to_numeric(df["Boy"], errors="coerce").fillna(0)
    female_pct = pd.to_numeric(df["Girl"], errors="coerce").fillna(0)

    countries = countries[:62]
    male_pct = male_pct[:62]
    female_pct = female_pct[:62]

    total_pct = male_pct + female_pct
    sort_idx = np.argsort(-total_pct)

    countries = countries.iloc[sort_idx]
    male_pct = male_pct.iloc[sort_idx]
    female_pct = female_pct.iloc[sort_idx]

    fig1, ax1 = plt.subplots(figsize=(28, len(countries) * 0.35))

    y = np.arange(len(countries))

    ax1.barh(y - 0.2, male_pct, height=0.4, label="Boy", color="#3A86FF")
    ax1.barh(y + 0.2, female_pct, height=0.4, label="Girl", color="#FF006E")

    ax1.set_yticks(y)
    ax1.set_yticklabels(countries, fontsize=14)

    ax1.set_xlabel("Participation (%)", fontsize=18)
    ax1.set_title("Activity Participation (3+ times per week)", fontsize=22, pad=20)

    ax1.legend(fontsize=16)
    ax1.grid(True, axis="x", linestyle="--", alpha=0.6)

    plt.tight_layout()

    bar_name = f"freq_bar_{uuid.uuid4().hex}.png"
    bar_fs, bar_path = save_plot(bar_name)
    plt.savefig(bar_fs, bbox_inches="tight")
    plt.close(fig1)

    # Heatmap
    sport_cols = df.columns[5:]
    sports = list(sport_cols)

    matrix = []
    for col in sport_cols:
        col_data = df[col]
        if col_data.dtype == object:
            numeric = pd.to_numeric(col_data, errors="coerce").fillna(0)
        else:
            numeric = col_data.fillna(0)
        matrix.append(numeric)

    matrix = np.array(matrix).T
    matrix = matrix[:62, :]

    fig2, ax2 = plt.subplots(figsize=(30, 20))

    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list(
        "custom_rYG",
        [(1, 0, 0), (1, 1, 0), (0, 1, 0)],
        N=256
    )

    im = ax2.imshow(matrix, cmap=cmap, aspect="auto")

    ax2.set_xticks(np.arange(len(sports)))
    ax2.set_xticklabels(sports, rotation=45, ha="right", fontsize=14)

    ax2.set_yticks(np.arange(len(countries)))
    ax2.set_yticklabels(countries, fontsize=14)

    ax2.set_title("Participation in the last year by sport, by school", fontsize=18, pad=20)
    ax2.set_xlabel("Sport", fontsize=14)
    ax2.set_ylabel("School", fontsize=14)

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax2.text(
                j, i, f"{matrix[i, j]:.1f}%",
                ha="center", va="center",
                fontsize=10, color="black"
            )

    plt.tight_layout()

    heat_name = f"freq_heat_{uuid.uuid4().hex}.png"
    heat_fs, heat_path = save_plot(heat_name)
    plt.savefig(heat_fs, bbox_inches="tight")
    plt.close(fig2)

    return bar_path, heat_path


# -------------------------------------------------
# Participation setting
# -------------------------------------------------
def plot_participation_setting(filepath):
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import uuid
    import os

    df = pd.read_excel(filepath, sheet_name="Table 7b", header=1)

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace("\u00A0", "", regex=False)
    )

    sports = df.iloc[:, 0].astype(str)

    all_pupils = pd.to_numeric(df.iloc[:, 1], errors="coerce").fillna(0)
    boys       = pd.to_numeric(df.iloc[:, 4], errors="coerce").fillna(0)
    girls      = pd.to_numeric(df.iloc[:, 7], errors="coerce").fillna(0)

    fig, ax = plt.subplots(figsize=(28, len(sports) * 0.35))

    y = np.arange(len(sports))
    bar_height = 0.25

    ax.barh(y - bar_height, all_pupils, height=bar_height, label="All pupils", color="#6A4C93")
    ax.barh(y,             boys,       height=bar_height, label="Boy",        color="#3A86FF")
    ax.barh(y + bar_height, girls,     height=bar_height, label="Girl",       color="#FF006E")

    ax.set_yticks(y)
    ax.set_yticklabels(sports, fontsize=14)

    ax.set_xlabel("Participation (%)", fontsize=18)
    ax.set_title("Participation in the last year by setting (Table 7b)", fontsize=22, pad=20)

    ax.legend(fontsize=16)
    ax.grid(True, axis="x", linestyle="--", alpha=0.6)

    plt.tight_layout()

    plot_name = f"setting_bar_{uuid.uuid4().hex}.png"
    plot_fs, plot_path = save_plot(plot_name)
    plt.savefig(plot_fs, bbox_inches="tight")
    plt.close(fig)

    return plot_path


# -------------------------------------------------
# Disability support
# -------------------------------------------------
def plot_disability_support(filepath):
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import uuid
    import os

    # Table 11a
    df = pd.read_excel(filepath, sheet_name="Table 11a", header=1)

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace("\u00A0", "", regex=False)
    )

    schools = df.iloc[:, 0].astype(str)

    wales_pct  = pd.to_numeric(df.iloc[:, 1], errors="coerce").fillna(0)
    region_pct = pd.to_numeric(df.iloc[:, 2], errors="coerce").fillna(0)
    area_pct   = pd.to_numeric(df.iloc[:, 3], errors="coerce").fillna(0)

    schools = schools[:62]
    wales_pct = wales_pct[:62]
    region_pct = region_pct[:62]
    area_pct = area_pct[:62]

    fig1, ax1 = plt.subplots(figsize=(28, len(schools) * 0.35))

    y = np.arange(len(schools))
    bar_h = 0.25

    ax1.barh(y - bar_h, wales_pct,  height=bar_h, label="Wales", color="#6A4C93")
    ax1.barh(y,         region_pct, height=bar_h, label="Regional Sport Partnership", color="#3A86FF")
    ax1.barh(y + bar_h, area_pct,   height=bar_h, label="Specific Region", color="#FF006E")

    ax1.set_yticks(y)
    ax1.set_yticklabels(schools, fontsize=14)

    ax1.set_xlabel("Percentage of participation of pupils with disability", fontsize=18)
    ax1.set_title("Participation support for those with a disability (Table 11a)", fontsize=22, pad=20)

    ax1.legend(fontsize=16)
    ax1.grid(True, axis="x", linestyle="--", alpha=0.6)

    plt.tight_layout()

    plot1_name = f"disability_11a_{uuid.uuid4().hex}.png"
    plot1_fs, plot1_path = save_plot(plot1_name)
    plt.savefig(plot1_fs, bbox_inches="tight")
    plt.close(fig1)

    # Table 11b
    df2 = pd.read_excel(filepath, sheet_name="Table 11b", header=1)

    df2.columns = (
        df2.columns.astype(str)
        .str.strip()
        .str.replace("\u00A0", "", regex=False)
    )

    support_labels = df2.iloc[1:14, 0].astype(str)

    colA = pd.to_numeric(df2.iloc[1:14, 1], errors="coerce").fillna(0)
    colB = pd.to_numeric(df2.iloc[1:14, 2], errors="coerce").fillna(0)
    colC = pd.to_numeric(df2.iloc[1:14, 3], errors="coerce").fillna(0)

    fig2, ax2 = plt.subplots(figsize=(24, len(support_labels) * 0.6))

    y2 = np.arange(len(support_labels))
    bar_h2 = 0.25

    ax2.barh(y2 - bar_h2, colA, height=bar_h2, label=df2.columns[1], color="#6A4C93")
    ax2.barh(y2,          colB, height=bar_h2, label=df2.columns[2], color="#3A86FF")
    ax2.barh(y2 + bar_h2, colC, height=bar_h2, label=df2.columns[3], color="#FF006E")

    ax2.set_yticks(y2)
    ax2.set_yticklabels(support_labels, fontsize=14)

    ax2.set_xlabel("Participation (%)", fontsize=18)
    ax2.set_title("Support needed for activity participation (Table 11b)", fontsize=22, pad=20)

    ax2.legend(fontsize=16)
    ax2.grid(True, axis="x", linestyle="--", alpha=0.6)

    plt.tight_layout()

    plot2_name = f"disability_11b_{uuid.uuid4().hex}.png"
    plot2_fs, plot2_path = save_plot(plot2_name)
    plt.savefig(plot2_fs, bbox_inches="tight")
    plt.close(fig2)

    return plot1_path, plot2_path


# -------------------------------------------------
# Demand
# -------------------------------------------------
def plot_demand(filepath):
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import uuid
    import os

    df = pd.read_excel(filepath, sheet_name="Table 12a", header=1)

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace("\u00A0", "", regex=False)
    )

    schools = df.iloc[:, 0].astype(str)
    boys = pd.to_numeric(df["Boy"], errors="coerce").fillna(0)
    girls = pd.to_numeric(df["Girl"], errors="coerce").fillna(0)

    schools = schools[:62]
    boys = boys[:62]
    girls = girls[:62]

    fig, ax = plt.subplots(figsize=(28, len(schools) * 0.35))

    y = np.arange(len(schools))
    bar_h = 0.25

    ax.barh(y - bar_h/2, boys,  height=bar_h, label="Boy",  color="#3A86FF")
    ax.barh(y + bar_h/2, girls, height=bar_h, label="Girl", color="#FF006E")

    ax.set_yticks(y)
    ax.set_yticklabels(schools, fontsize=14)

    ax.set_xlabel("Demand (%)", fontsize=18)
    ax.set_title("Latent demand by Gender (Table 12a)", fontsize=22, pad=20)

    ax.legend(fontsize=16)
    ax.grid(True, axis="x", linestyle="--", alpha=0.6)

    plt.tight_layout()

    plot_name = f"demand_bar_{uuid.uuid4().hex}.png"
    plot_fs, plot_path = save_plot(plot_name)
    plt.savefig(plot_fs, bbox_inches="tight")
    plt.close(fig)

    return plot_path


# -------------------------------------------------
# Motivation
# -------------------------------------------------
def plot_motivation(filepath):
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import uuid
    import os

    print(">>> plot_motivation called with:", filepath)

    try:
        df = pd.read_excel(filepath, sheet_name="Table 14a", header=0)
    except Exception as e:
        print("❌ Error reading Table 14a:", e)
        return None

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace("\u00A0", "", regex=False)
    )

    first_col = df.iloc[:, 0].astype(str)

    questions = [
        "How much do you think PE lessons and sport help you to have a healthy lifestyle?",
        "How often do you feel your ideas about PE and school sport are listened to?",
        "How much do you enjoy PE lessons?",
        "How much do you enjoy doing sport at after-school or lunchtime clubs?",
        "How much do you enjoy doing sport in a community club, when you are not at school?",
        "How much do you enjoy doing sport somewhere else that is outside of school and community clubs?",
        "How confident are you in trying new sports?"
    ]

    output_paths = []

    for q_index, question in enumerate(questions, start=1):
        print(f"🔍 Processing Q{q_index}: {question}")

        row_start = first_col[first_col.str.contains(question, na=False)].index
        if len(row_start) == 0:
            print(f"⚠️ No match found for Q{q_index}")
            continue

        row_start = row_start[0]

        try:
            subset = df.iloc[row_start + 1: row_start + 5, :].copy()
        except Exception as e:
            print(f"❌ Error extracting rows for Q{q_index}: {e}")
            continue

        responses = subset.iloc[:, 0].astype(str)
        groups = subset.columns[1:]

        numeric = subset.iloc[:, 1:].apply(
            lambda col: pd.to_numeric(col, errors="coerce").fillna(0)
        )

        row_sums = numeric.sum(axis=1)
        row_sums = row_sums.replace(0, 1)
        pct = (numeric.T / row_sums).T * 100
        pct = pct.round(1)

        fig, ax = plt.subplots(figsize=(14, 8))

        from matplotlib.colors import LinearSegmentedColormap
        cmap = LinearSegmentedColormap.from_list(
            "custom_rYG",
            [(1, 0, 0), (1, 1, 0), (0, 1, 0)],
            N=256
        )

        im = ax.imshow(pct.values, cmap=cmap, aspect="auto")

        ax.set_xticks(np.arange(len(groups)))
        ax.set_xticklabels(groups, rotation=45, ha="right", fontsize=12)

        ax.set_yticks(np.arange(len(responses)))
        ax.set_yticklabels(responses, fontsize=12)

        ax.set_title(question, fontsize=14, pad=20)
        ax.set_xlabel("Group")
        ax.set_ylabel("Response Category")

        for i in range(pct.shape[0]):
            for j in range(pct.shape[1]):
                ax.text(
                    j, i, f"{pct.iloc[i, j]:.1f}%",
                    ha="center", va="center", color="black", fontsize=10
                )

        plt.tight_layout()

        filename = f"motivation_q{q_index}_{uuid.uuid4().hex}.png"
        fs_path, web_path = save_plot(filename)
        plt.savefig(fs_path, bbox_inches="tight")
        plt.close(fig)

        output_paths.append(web_path)

    return output_paths


# -------------------------------------------------
# School provision
# -------------------------------------------------
def plot_school_provision(filepath):
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import uuid
    import os

    print(">>> plot_school_provision called with:", filepath)

    def make_chart(df, title_text):
        countries = df.iloc[2:, 0].astype(str).values
        male_pct = pd.to_numeric(df.iloc[2:, 1], errors="coerce").fillna(0).values
        female_pct = pd.to_numeric(df.iloc[2:, 2], errors="coerce").fillna(0).values
        final_pct = pd.to_numeric(df.iloc[2:, 3], errors="coerce").fillna(0).values

        countries = countries[:10]
        data = np.column_stack([male_pct[:10], female_pct[:10], final_pct[:10]])

        fig, ax = plt.subplots(figsize=(18, 10))

        x = np.arange(len(countries))
        width = 0.25

        ax.bar(x - width, data[:, 0], width, label="Wales")
        ax.bar(x,         data[:, 1], width, label="Regional Sport Partnership")
        ax.bar(x + width, data[:, 2], width, label="Your region")

        ax.set_xticks(x)
        ax.set_xticklabels(countries, rotation=45, ha="right")
        ax.set_ylabel("Percentage of schools")
        ax.set_title(title_text)
        ax.legend()
        ax.grid(True, axis="y", linestyle="--", alpha=0.6)
        ax.tick_params(labelsize=12)

        plt.tight_layout()

        filename = f"school_provision_{uuid.uuid4().hex}.png"
        fs_path, web_path = save_plot(filename)
        plt.savefig(fs_path, bbox_inches="tight")
        plt.close(fig)

        return web_path

    try:
        df_primary = pd.read_excel(filepath, sheet_name="Table P4", header=0)
    except Exception as e:
        print("❌ Error reading Table P4:", e)
        return None

    try:
        df_secondary = pd.read_excel(filepath, sheet_name="Table S4", header=0)
    except Exception as e:
        print("❌ Error reading Table S4:", e)
        return None

    plot_primary = make_chart(df_primary, "Activity Participation by Gender (Primary)")
    plot_secondary = make_chart(df_secondary, "Activity Participation by Gender (Secondary)")

    return plot_primary, plot_secondary


# -------------------------------------------------
# Comparative overall (heatmap + map)
# -------------------------------------------------
def plot_overall():
    import os
    import uuid
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt

    folder = COMPARE_FOLDER

    files = [
        f for f in os.listdir(folder)
        if f.lower().endswith(".xlsx") and not f.startswith("~$")
    ]

    if not files:
        print("❌ No comparative Excel files found in", folder)
        return None, None

    region_names = []
    results = {i: [] for i in range(1, 20)}

    labels = [
        "Boy",
        "Girl",
        "Years 3 to 6",
        "Years 7 to 11",
        "White",
        "Mixed / Multiple ethnic group",
        "Asian / Asian Welsh / Asian British",
        "Black / Black Welsh / Black British / Caribbean / African",
        "Other ethnic group",
        "Any disability or impairment",
        "No disability or impairment",
        "Any learning difficulty",
        "No learning difficulty",
        "FSM 1",
        "FSM 2",
        "FSM 3",
        "FSM 4",
        "Speaks Welsh",
        "Does not speak Welsh",
    ]

    for fname in files:
        fpath = os.path.join(folder, fname)
        print(">>> Reading comparative file:", fpath)

        region_name, _ = os.path.splitext(fname)
        region_names.append(region_name)

        df = pd.read_excel(fpath, sheet_name="Table 1", header=0)
        row_labels = df.iloc[:, 0].astype(str).str.strip()
        value_col = df.columns[1]

        for idx, label in enumerate(labels, start=1):
            match = df.loc[row_labels == label, value_col]
            if not match.empty:
                val = pd.to_numeric(match.iloc[0], errors="coerce")
            else:
                val = np.nan
            results[idx].append(val)

    data_matrix = np.column_stack([results[i] for i in range(1, 20)])

    metric_labels = [
        "Boy", "Girl", "Years 3 to 6", "Years 7 to 11", "White",
        "Mixed Ethnicity", "Asian", "Black", "Other Ethnicity",
        "Disability", "No Disability", "Learning Difficulty", "No Learning Difficulty",
        "FSM 1", "FSM 2", "FSM 3", "FSM 4", "Speaks Welsh", "Does Not Speak Welsh"
    ]

    from matplotlib.colors import LinearSegmentedColormap

    fig, ax = plt.subplots(figsize=(18, 10))

    cmap = LinearSegmentedColormap.from_list(
        "custom_rYG",
        [(1, 0, 0), (1, 1, 0), (0, 1, 0)],
        N=256
    )

    im = ax.imshow(data_matrix, aspect="auto", cmap=cmap)

    ax.set_xticks(np.arange(len(metric_labels)))
    ax.set_xticklabels(metric_labels, rotation=45, ha="right", fontsize=10)

    ax.set_yticks(np.arange(len(region_names)))
    ax.set_yticklabels(region_names, fontsize=10)

    ax.set_title("Participation Metrics by Region", fontsize=16, pad=20)
    ax.set_xlabel("Metrics")
    ax.set_ylabel("Regions")

    for i in range(data_matrix.shape[0]):
        for j in range(data_matrix.shape[1]):
            val = data_matrix[i, j]
            if not np.isnan(val):
                ax.text(
                    j, i, f"{val:.1f}",
                    ha="center", va="center", color="black", fontsize=8
                )

    plt.tight_layout()

    heat_name = f"overall_heat_{uuid.uuid4().hex}.png"
    heat_fs, heat_path = save_plot(heat_name)
    plt.savefig(heat_fs, bbox_inches="tight")
    plt.close(fig)

    # Static Wales map image (already in static/)
    map_path = "static/wales-councils-map-1417540885.gif"

    return map_path, heat_path


# -------------------------------------------------
# Extract region metrics (for clickable map)
# -------------------------------------------------
def extract_region_metrics(filepath):
    import pandas as pd
    import numpy as np

    df = pd.read_excel(filepath, sheet_name="Table 1")

    # Clean both label and value columns
    labels = df.iloc[:, 0].astype(str).str.strip()
    values = df.iloc[:, 1].astype(str).str.strip()

    def get(label):
        match = values[labels == label]

        if match.empty:
            return np.nan

        raw = match.iloc[0]

        # Treat all non-numeric placeholders as missing
        if raw in ["-", "--", "—", "", "NA", "N/A", "n/a", None]:
            return np.nan

        # Try converting to float safely
        try:
            return float(raw)
        except Exception:
            return np.nan

    return {
        "Boy": get("Boy"),
        "Girl": get("Girl"),
        "Years_3_6": get("Years 3 to 6"),
        "Years_7_11": get("Years 7 to 11"),
        "White": get("White"),
        "Mixed": get("Mixed / Multiple ethnic group"),
        "Asian": get("Asian / Asian Welsh / Asian British"),
        "Black": get("Black / Black Welsh / Black British / Caribbean / African"),
        "Other": get("Other ethnic group"),
        "Disability": get("Any disability or impairment"),
        "No_Disability": get("No disability or impairment"),
        "Learning_Difficulty": get("Any learning difficulty"),
        "No_Learning_Difficulty": get("No learning difficulty"),
        "FSM1": get("FSM 1"),
        "FSM2": get("FSM 2"),
        "FSM3": get("FSM 3"),
        "FSM4": get("FSM 4"),
        "Welsh": get("Speaks Welsh"),
        "Not_Welsh": get("Does not speak Welsh"),
    }


# -------------------------------------------------
# Region statistics route (for clickable map)
# -------------------------------------------------
@app.route("/region/<region_name>")
def region_stats(region_name):
    # Normalise the incoming region name
    key = region_name.lower().replace("_eng", "").replace("_", " ")

    # Search for ANY file that contains the region name in any reasonable form
    files = [
        f for f in os.listdir(COMPARE_FOLDER)
        if key in f.lower().replace("_", " ").replace(".xlsx", "")
    ]

    if not files:
        return {"error": f"No matching file for region '{region_name}'"}, 404

    filepath = os.path.join(COMPARE_FOLDER, files[0])
    metrics = extract_region_metrics(filepath)

    # Convert NaN → 0 safely
    cleaned = {}
    for k, v in metrics.items():
        try:
            num = float(v)
            cleaned[k] = 0 if math.isnan(num) else num
        except Exception:
            cleaned[k] = 0

    return cleaned


# -------------------------------------------------
# Main route
# -------------------------------------------------




@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        clear_folder(REGION_FOLDER)
        clear_folder(COMPARE_FOLDER)

    message = ""
    plot_file = None
    plot_file2 = None

    region_files = list_valid_excels(REGION_FOLDER)
    compare_files = list_valid_excels(COMPARE_FOLDER)

    if request.method == "POST":
        action = request.form.get("action")
        print(">>> ACTION:", action)

        if action == "upload_region":
            uploaded = request.files.getlist("region_files")
            clear_folder(REGION_FOLDER)
            for f in uploaded:
                if f.filename.lower().endswith(".xlsx"):
                    save_path = os.path.join(REGION_FOLDER, f.filename)
                    f.save(save_path)
            message = "Region files uploaded."
            region_files = list_valid_excels(REGION_FOLDER)

        elif action == "upload_compare":
            uploaded = request.files.getlist("compare_files")
            clear_folder(COMPARE_FOLDER)
            for f in uploaded:
                if f.filename.lower().endswith(".xlsx"):
                    save_path = os.path.join(COMPARE_FOLDER, f.filename)
                    f.save(save_path)
            message = "Comparative files uploaded."
            compare_files = list_valid_excels(COMPARE_FOLDER)

        elif action == "analyze":
            source = request.form["source"]
            filename = request.form["selected_file"]
            analysis = request.form["analysis"]

            folder = REGION_FOLDER if source == "region" else COMPARE_FOLDER
            filepath = os.path.join(folder, filename)

            # Default: no plots
            plot_file = None
            plot_file2 = None

            if analysis == "KPI":
                category = request.form.get("kpi_category", "Gender")
                print(">>> KPI category selected:", category)
                scatter_path, bar_path = plot_kpi(filepath, category)
                # Send BOTH as normal plots (no map layout)
                plot_file = [scatter_path, bar_path]
                plot_file2 = None

            elif analysis == "Overall" and source == "compare":
                # Comparative overall: ONLY here we use the map layout
                map_path, heat_path = plot_overall()
                plot_file = map_path      # used as the map
                plot_file2 = heat_path    # shown as Plot 2 (normal plot)

            elif analysis == "KPI_Summary" and source == "compare":
                plot_path = plot_kpi_summary_3d()
                plot_file = [plot_path]
                plot_file2 = None

            elif analysis == "Frequency":
                bar_path, heat_path = plot_frequency(filepath)
                plot_file = [bar_path, heat_path]
                plot_file2 = None

            elif analysis == "ParticipationSetting":
                setting_path = plot_participation_setting(filepath)
                plot_file = [setting_path]
                plot_file2 = None

            elif analysis == "DisabilitySupport":
                plot1_path, plot2_path = plot_disability_support(filepath)
                plot_file = [plot1_path, plot2_path]
                plot_file2 = None

            elif analysis == "Demand":
                demand_path = plot_demand(filepath)
                plot_file = [demand_path]
                plot_file2 = None

            elif analysis == "Motivation":
                # Already returns a list of images
                plot_file = plot_motivation(filepath)
                plot_file2 = None

            elif analysis == "School":
                primary_path, secondary_path = plot_school_provision(filepath)
                plot_file = [primary_path, secondary_path]
                plot_file2 = None

            message = "Analysis complete."

    return render_template(
        "index.html",
        message=message,
        plot_file=plot_file,
        plot_file2=plot_file2,
        region_files=region_files,
        compare_files=compare_files
    )


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)