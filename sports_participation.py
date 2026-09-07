from flask import Blueprint, request, render_template
import pandas as pd
import seaborn as sns
import io
import base64
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sports_bp = Blueprint("sports", __name__)

# ---------------------------------------------------------
# WIPAHS SOFT COLOUR PALETTE
# ---------------------------------------------------------
WIPAHS_COLORS = [
    "#4C78A8",  # blue
    "#F58518",  # orange
    "#E45756",  # red
    "#72B7B2",  # teal
    "#54A24B",  # green
    "#EECA3B",  # yellow
]

# ---------------------------------------------------------
# HARD‑WIRED GITHUB DATA URL
# ---------------------------------------------------------
SPORTS_DATA = "https://raw.githubusercontent.com/CMBarnes127503/flask-folder-analysis/main/data/Full%20Data%20Set_example4.xlsx?raw=1"

sports_df = None  # stored in memory


# ---------------------------------------------------------
# Helper: Convert Matplotlib figure to Base64
# ---------------------------------------------------------
def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"


# ---------------------------------------------------------
# Identify participation / latent demand columns
# ---------------------------------------------------------
def get_participation_cols(df):
    patterns = [
        "Sport - Fitness activities in last 4 weeks",
        "Sport - Games and sports in last 4 weeks",
        "Sport - Outdoor activities in last 4 weeks",
        "Sport - Participation - Last 4 weeks"
    ]
    return [c for c in df.columns if any(p in c for p in patterns)]


def get_latent_cols(df):
    return [c for c in df.columns if "Sport - Latent Demand" in c]


# ---------------------------------------------------------
# Plot 1: Participation Heatmap (rewritten)
# ---------------------------------------------------------
def plot_heatmap(df, year):

    # Clean column names
    df.columns = (
        df.columns.astype(str)
        .str.replace("\n", " ", regex=False)
        .str.replace("\r", " ", regex=False)
        .str.strip()
    )

    # Identify Year and Sex columns
    year_col = next((c for c in df.columns if c.lower() == "year"), None)
    sex_col  = next((c for c in df.columns if c.lower() in ["sex", "gender"]), None)

    if year_col is None or sex_col is None:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Year or Sex column missing", ha="center")
        return fig_to_base64(fig)

    # Participation columns
    part_cols = get_participation_cols(df)
    if not part_cols:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No participation columns found", ha="center")
        return fig_to_base64(fig)

    # Shorten activity names
    def shorten_activity(name):
        return name.split("-")[-1].strip()

    # Melt
    long_df = df.melt(
        id_vars=[year_col, sex_col],
        value_vars=part_cols,
        var_name="Activity",
        value_name="Percentage"
    )

    # Fix Sex codes
    sex_map = {
        1: "Male", 2: "Female", 3: "Other",
        "1": "Male", "2": "Female", "3": "Other"
    }
    long_df[sex_col] = long_df[sex_col].map(sex_map).fillna(long_df[sex_col])

    # Clean activity names
    long_df["Activity"] = long_df["Activity"].apply(shorten_activity)

    # Convert weird symbols → numeric
    long_df["Percentage"] = pd.to_numeric(long_df["Percentage"], errors="coerce").fillna(0)

    # Pivot
    pivot = long_df.pivot_table(
        index="Activity",
        columns=sex_col,
        values="Percentage",
        aggfunc="mean"
    )

    # Ensure all activities appear
    all_acts = long_df["Activity"].astype(str).unique()
    pivot = pivot.reindex(all_acts).fillna(0)

    # Auto-scale figure size
    fig_width = max(12, len(pivot.columns) * 0.4)
    fig_height = max(8, len(pivot.index) * 0.25)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    sns.heatmap(
        pivot,
        cmap=sns.color_palette(WIPAHS_COLORS, as_cmap=True),
        annot=True,
        fmt=".1f",
        annot_kws={"size": 8},
        ax=ax
    )

    ax.set_title(f"Participation Heatmap – {year}")
    ax.set_ylabel("Activity")
    ax.set_xlabel("Sex")

    plt.tight_layout()
    return fig_to_base64(fig)


# ---------------------------------------------------------
# Simple Activity Categories
# ---------------------------------------------------------
def get_simple_categories():
    return {
        "Fitness": [
            "Sport - Fitness activities in last 4 weeks - Worked out/exercised at home",
            "Sport - Fitness activities in last 4 weeks - Fitness classes",
            "Sport - Fitness activities in last 4 weeks - Gone to gym (not for fitness class)",
            "Sport - Fitness activities in last 4 weeks - Dance classes",
        ],
        "Team Sports": [
            "Sport - Games and sports in last 4 weeks - Team sports",
        ],
        "Outdoor Pursuits": [
            "Sport - Outdoor activities in last 4 weeks - Mountain sports like climbing or sk",
            "Sport - Outdoor activities in last 4 weeks - Fishing or angling",
            "Sport - Outdoor activities in last 4 weeks - Horse riding",
        ],
        "Cycling": [
            "Sport - Fitness activities in last 4 weeks - Cycling",
        ],
        "Swimming": [
            "Sport - Fitness activities in last 4 weeks - Swimming or diving",
        ],
        "Martial Arts": [
            "Sport - Games and sports in last 4 weeks - Combat sports and martial arts",
        ],
        "Indoor Games": [
            "Sport - Games and sports in last 4 weeks - Indoor games",
        ],
        "Watersports": [
            "Sport - Outdoor activities in last 4 weeks - Watersport (kayaking, surfing, sail",
        ],
        "Other Activities": [
            "Sport - Fitness activities in last 4 weeks - Walking over 2 miles",
            "Sport - Fitness activities in last 4 weeks - Jogging or running",
        ],
    }


# ---------------------------------------------------------
# Plot 2: Activity Category Bar Chart
# ---------------------------------------------------------
def plot_categories(df, year):
    cats = get_simple_categories()
    results = {}

    for cat, cols in cats.items():
        valid = [c for c in cols if c in df.columns]
        if valid:
            numeric_df = df[valid].apply(pd.to_numeric, errors="coerce").fillna(0)
            results[cat] = numeric_df.mean().mean() * 100

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(results.keys(), results.values(), color=WIPAHS_COLORS[0])
    ax.set_ylabel("Participation (%)")
    ax.set_title(f"Activity Category Summary – {year}")
    plt.xticks(rotation=45, ha="right")

    return fig_to_base64(fig)


# ---------------------------------------------------------
# Plot 3: Top 10 Activities
# ---------------------------------------------------------
def plot_top10(df, year):
    cols = get_participation_cols(df)
    numeric_df = df[cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    means = numeric_df.mean().sort_values(ascending=False).head(10) * 100

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(means.index, means.values, color=WIPAHS_COLORS[2])
    ax.set_title(f"Top 10 Activities – {year}")
    ax.set_xlabel("Participation (%)")
    plt.gca().invert_yaxis()

    return fig_to_base64(fig)


# ---------------------------------------------------------
# Plot 4: Latent vs Participation
# ---------------------------------------------------------
def plot_latent(df, year):
    latent_cols = get_latent_cols(df)
    part_cols = get_participation_cols(df)

    if not latent_cols or not part_cols:
        fig, ax = plt.subplots(figsize=(20, 16))
        ax.text(0.5, 0.5, "Latent demand columns not found", ha="center")
        return fig_to_base64(fig)

    latent_df = df[latent_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    part_df   = df[part_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    def extract_activity(col):
        return col.split("-")[-1].strip().lower()

    latent_map = {extract_activity(c): c for c in latent_cols}
    part_map   = {extract_activity(c): c for c in part_cols}

    common_activities = [a for a in latent_map.keys() if a in part_map.keys()]

    if not common_activities:
        fig, ax = plt.subplots(figsize=(14, 10))
        ax.text(0.5, 0.5, "No matching activities between participation and latent demand", ha="center")
        return fig_to_base64(fig)

    part_vals   = []
    latent_vals = []

    for act in common_activities:
        part_vals.append(part_df[part_map[act]].mean() * 100)
        latent_vals.append(latent_df[latent_map[act]].mean() * 100)

    fig, ax = plt.subplots(figsize=(14, 10))
    ax.scatter(part_vals, latent_vals, color=WIPAHS_COLORS[3], s=120, alpha=0.85)

    # Selective labeling
    scores = [(act, part_vals[i] + latent_vals[i]) for i, act in enumerate(common_activities)]
    scores.sort(key=lambda x: x[1], reverse=True)
    TOP_N = 10
    label_set = {act for act, _ in scores[:TOP_N]}

    for i, act in enumerate(common_activities):
        if act in label_set:
            ax.annotate(
                act,
                (part_vals[i], latent_vals[i]),
                fontsize=10,
                xytext=(6, 6),
                textcoords="offset points"
            )

    ax.set_xlabel("Participation (%)")
    ax.set_ylabel("Latent Demand (%)")
    ax.set_title(f"Latent Demand vs Participation – {year}")

    plt.tight_layout()
    return fig_to_base64(fig)


# ---------------------------------------------------------
# Plot 5: Demographic Comparison
# ---------------------------------------------------------
def plot_demographic(df, year):
    part_cols = get_participation_cols(df)
    numeric_df = df[part_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    demo_map = {
        1: "Male", 2: "Female", 3: "Other",
        "1": "Male", "2": "Female", "3": "Other"
    }

    possible = ["gender", "Gender", "sex", "Sex",
                "ethnicity", "Ethnicity",
                "FSM", "fsm", "fsm_quartile", "FreeSchoolMealquartile",
                "WelshSpeaker", "welsh_speaker", "Welsh speaker"]

    demo_cols = [c for c in df.columns if c in possible]

    if not demo_cols:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No demographic columns found", ha="center")
        return fig_to_base64(fig)

    figs = []

    for demo in demo_cols:
        df[demo] = df[demo].map(demo_map).fillna(df[demo])
        groups = df[demo].dropna().unique()

        means = []
        labels = []

        for g in groups:
            subset = numeric_df[df[demo] == g]
            means.append(subset.mean().mean() * 100)
            labels.append(str(g))

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(labels, means, color=WIPAHS_COLORS[4])
        ax.set_title(f"Participation by {demo} – {year}")
        ax.set_ylabel("Participation (%)")
        plt.xticks(rotation=45, ha="right")

        figs.append(fig_to_base64(fig))

    return figs


# ---------------------------------------------------------
# Plot 6: Year Comparison
# ---------------------------------------------------------
def plot_year_compare(df_2022, df_2023):
    cols = get_participation_cols(df_2022)

    df22 = df_2022[cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    df23 = df_2023[cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    m22 = df22.mean() * 100
    m23 = df23.mean() * 100

    combined = pd.DataFrame({
        "2022": m22,
        "2023": m23
    })

    combined.index = (
        combined.index
        .str.replace("Sport - Fitness activities in last 4 weeks - ", "", regex=False)
        .str.replace("Sport - Games and sports in last 4 weeks - ", "", regex=False)
        .str.replace("Sport - Outdoor activities in last 4 weeks - ", "", regex=False)
        .str.replace("Sport - Participation - Last 4 weeks - ", "", regex=False)
        .str.strip()
    )

    fig, ax = plt.subplots(figsize=(22, 12))

    x = range(len(combined))
    width = 0.4

    ax.bar([i - width/2 for i in x], combined["2022"], width=width, label="2022", color=WIPAHS_COLORS[0])
    ax.bar([i + width/2 for i in x], combined["2023"], width=width, label="2023", color=WIPAHS_COLORS[1])

    ax.set_xticks(x)
    ax.set_xticklabels(combined.index, rotation=75, ha="right", fontsize=9)

    ax.set_ylabel("Participation (%)")
    ax.set_title("Participation Comparison: 2022 vs 2023")
    ax.legend()

    plt.tight_layout()

    return fig_to_base64(fig)


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

@sports_bp.route("/sports", methods=["GET", "POST"])
def sports_home():
    return render_template("index.html")


@sports_bp.route("/sports/load", methods=["POST"])
def sports_load():
    global sports_df
    sports_df = pd.read_excel(SPORTS_DATA, engine="openpyxl")
    return render_template("index.html", sports_loaded=True)


@sports_bp.route("/sports/participation", methods=["POST"])
def sports_participation():
    global sports_df

    if sports_df is None:
        return render_template("index.html", message="Sports data not loaded — click Load Dataset")

    year = request.form.get("year")
    analysis_type = request.form.get("analysis_type")

    df = pd.read_excel(SPORTS_DATA, engine="openpyxl")

    if year == "2022":
        df = df[df["Year"] == 2022]
    elif year == "2023":
        df = df[df["Year"] == 2023]

    # Analysis routing
    if analysis_type == "heatmap":
        plot_file = plot_heatmap(df, year)
        plot_file2 = None

    elif analysis_type == "categories":
        plot_file = plot_categories(df, year)
        plot_file2 = None

    elif analysis_type == "top10":
        plot_file = plot_top10(df, year)
        plot_file2 = None

    elif analysis_type == "latent":
        plot_file = plot_latent(df, year)
        plot_file2 = None

    elif analysis_type == "demographic":
        plot_file = plot_demographic(df, year)
        plot_file2 = None

    # ⭐ FIXED COMPARISON OPTION
    elif analysis_type in ["year_compare", "comparison"]:
        full_df = pd.read_excel(SPORTS_DATA, engine="openpyxl")
        df22 = full_df[full_df["Year"] == 2022]
        df23 = full_df[full_df["Year"] == 2023]
        plot_file = plot_year_compare(df22, df23)
        plot_file2 = None

    else:
        return render_template("index.html", message="Invalid sports analysis type")

    return render_template(
        "index.html",
        plot_file=plot_file,
        plot_file2=plot_file2,
        sports_loaded=True
    )
