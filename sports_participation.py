from flask import Blueprint, request, render_template
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import os

sports_bp = Blueprint("sports", __name__)

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
    return [
        c for c in df.columns
        if "Sport - Fitness activities in last 4 weeks" in c
        or "Sport - Games and sports in last 4 weeks" in c
        or "Sport - Outdoor activities in last 4 weeks" in c
        or "Sport - Participation - Last 4 weeks" in c
    ]


def get_latent_cols(df):
    return [c for c in df.columns if "Sport - Latent Demand" in c]


# ---------------------------------------------------------
# Plot 1: Participation Heatmap
# ---------------------------------------------------------
def plot_heatmap(df, year):
    cols = get_participation_cols(df)

    long_df = df.melt(
        id_vars=["Year", "Sex"],
        value_vars=cols,
        var_name="Activity",
        value_name="Percentage"
    )

    sex_map = {
        1: "Male",
        2: "Female",
        3: "Other",
        "1": "Male",
        "2": "Female",
        "3": "Other"
    }
    long_df["Sex"] = long_df["Sex"].map(sex_map).fillna(long_df["Sex"])

    long_df["Activity"] = (
        long_df["Activity"]
        .str.replace("Sport - Fitness activities in last 4 weeks - ", "", regex=False)
        .str.replace("Sport - Games and sports in last 4 weeks - ", "", regex=False)
        .str.replace("Sport - Outdoor activities in last 4 weeks - ", "", regex=False)
        .str.replace("Sport - Participation - Last 4 weeks - ", "", regex=False)
        .str.strip()
    )

    long_df["Percentage"] = pd.to_numeric(long_df["Percentage"], errors="coerce").fillna(0)

    pivot = long_df.pivot_table(
        index="Activity",
        columns="Sex",
        values="Percentage",
        aggfunc="mean"
    )

    fig, ax = plt.subplots(figsize=(14, 18))
    sns.heatmap(pivot, cmap="viridis", ax=ax)

    ax.set_title(f"Participation Heatmap – {year}")
    ax.set_ylabel("Activity")
    ax.set_xlabel("Sex")

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
    ax.bar(results.keys(), results.values(), color="steelblue")
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
    ax.barh(means.index, means.values, color="darkgreen")
    ax.set_title(f"Top 10 Activities – {year}")
    ax.set_xlabel("Participation (%)")
    plt.gca().invert_yaxis()

    return fig_to_base64(fig)


# ---------------------------------------------------------
# Plot 4: Latent Demand Scatter
# ---------------------------------------------------------
def plot_latent(df, year):
    latent_cols = get_latent_cols(df)
    part_cols = get_participation_cols(df)

    if not latent_cols or not part_cols:
        fig, ax = plt.subplots()
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
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No matching activities between participation and latent demand", ha="center")
        return fig_to_base64(fig)

    part_vals   = []
    latent_vals = []

    for act in common_activities:
        part_vals.append(part_df[part_map[act]].mean() * 100)
        latent_vals.append(latent_df[latent_map[act]].mean() * 100)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(part_vals, latent_vals)

    for i, act in enumerate(common_activities):
        ax.text(part_vals[i], latent_vals[i], act, fontsize=8)

    ax.set_xlabel("Participation (%)")
    ax.set_ylabel("Latent Demand (%)")
    ax.set_title(f"Latent Demand vs Participation – {year}")

    return fig_to_base64(fig)


# ---------------------------------------------------------
# Plot 5: Demographic Comparison
# ---------------------------------------------------------
def plot_demographic(df, year):
    part_cols = get_participation_cols(df)
    numeric_df = df[part_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

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
        groups = df[demo].dropna().unique()

        means = []
        labels = []

        for g in groups:
            subset = numeric_df[df[demo] == g]
            means.append(subset.mean().mean() * 100)
            labels.append(str(g))

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(labels, means, color="purple")
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

    fig, ax = plt.subplots(figsize=(14, 10))

    x = range(len(combined))
    width = 0.4

    ax.bar([i - width/2 for i in x], combined["2022"], width=width, label="2022", color="steelblue")
    ax.bar([i + width/2 for i in x], combined["2023"], width=width, label="2023", color="darkorange")

    ax.set_xticks(x)
    ax.set_xticklabels(combined.index, rotation=45, ha="right", fontsize=8)

    ax.set_ylabel("Participation (%)")
    ax.set_title("Participation Comparison: 2022 vs 2023")
    ax.legend()

    return fig_to_base64(fig)


# ---------------------------------------------------------
# ROUTES — UPDATED TO USE HARD‑WIRED GITHUB DATA
# ---------------------------------------------------------

@sports_bp.route("/sports", methods=["GET", "POST"])
def sports_home():
    return render_template("index.html")


@sports_bp.route("/sports/load", methods=["POST"])
def sports_load():
    global sports_df

    # Load sports dataset from GitHub (raw Excel)
    sports_df = pd.read_excel(SPORTS_DATA, engine="openpyxl")

    return render_template("index.html", sports_loaded=True)


@sports_bp.route("/sports/participation", methods=["POST"])
def sports_participation():
    global sports_df

    if sports_df is None:
        return render_template("index.html", message="Sports data not loaded — click Load Dataset")

    year = request.form.get("year")
    analysis_type = request.form.get("analysis_type")

    # Select correct year subset
    df = pd.read_excel(SPORTS_DATA, engine="openpyxl")

    if year == "2022":
        df = df[df["Year"] == 2022]
    elif year == "2023":
        df = df[df["Year"] == 2023]

    # Decide which plot to generate
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

    elif analysis_type == "year_compare":
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
