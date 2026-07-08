# =====================================================
# Imports
# =====================================================

from flask import Blueprint, render_template, request, session
import pandas as pd
import matplotlib.pyplot as plt
import os
import io
import base64

# =====================================================
# Blueprint
# =====================================================

questions_bp = Blueprint(
    "questions",
    __name__,
    template_folder="templates"
)

# =====================================================
# HARD‑WIRED GITHUB DATA URL
# =====================================================

QUESTIONS_DATA = "https://raw.githubusercontent.com/CMBarnes127503/flask-folder-analysis/main/data/Full%20Data%20Set_example3__.xlsx?raw=1"



# =====================================================
# Helper Functions
# =====================================================

def load_dataset():
    """Load the long-format SHRN dataset safely from GitHub."""
    try:
        df = pd.read_excel(QUESTIONS_DATA)
    except Exception as e:
        print("DEBUG: Failed to load GitHub dataset:", e)
        return None

    df.columns = df.columns.astype(str).str.strip()

    # Convert key columns to strings
    for col in ["Question", "Variable", "Characteristic", "Gender", "Breakdown"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    print("DEBUG: Dataset loaded with columns:", df.columns.tolist())
    return df


def save_plot(fig):
    """Convert Matplotlib figure to base64 for inline HTML."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"

# =====================================================
# Plot Function (ALL GENDERS TOGETHER)
# =====================================================

def plot_question(df, question, characteristic):
    """Generate grouped bar chart showing ALL genders for each Breakdown."""

    print("DEBUG: plot_question called with:")
    print("  Question:", question)
    print("  Characteristic:", characteristic)

    # Map long Question → short Variable
    try:
        variable = df.loc[df["Question"] == question, "Variable"].iloc[0]
    except Exception:
        print("DEBUG: Could not map Question to Variable")
        return None

    print("DEBUG: Mapped Question to Variable:", variable)

    # Filter using Variable instead of Question
    filtered = df[
        (df["Variable"] == variable) &
        (df["Characteristic"] == characteristic)
    ]

    print("DEBUG: Filtered rows:", len(filtered))

    if filtered.empty:
        print("DEBUG: No matching rows found.")
        return None

    # Sort breakdowns for cleaner charts
    filtered = filtered.sort_values("Breakdown")

    breakdowns = filtered["Breakdown"].unique()

    genders = ["Persons", "Boy", "Girl", "Neither word describes me"]

    # Build matrix: rows = breakdowns, columns = genders
    data = []
    for b in breakdowns:
        row = []
        for g in genders:
            match = filtered[
                (filtered["Breakdown"] == b) &
                (filtered["Gender"] == g)
            ]
            if not match.empty:
                row.append(float(match["Percentage"].iloc[0]))
            else:
                row.append(0.0)
        data.append(row)

    fig, ax = plt.subplots(figsize=(12, 6))

    x = range(len(breakdowns))
    width = 0.2

    for i, g in enumerate(genders):
        ax.bar(
            [xi + i * width for xi in x],
            [row[i] for row in data],
            width=width,
            label=g
        )

    ax.set_xticks([xi + width for xi in x])
    ax.set_xticklabels(breakdowns, rotation=45, ha="right")

    ax.set_ylabel("Percentage (%)")
    ax.set_title(f"{variable} ({characteristic})")

    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    return save_plot(fig)

# =====================================================
# Routes
# =====================================================

@questions_bp.route("/questions", methods=["GET", "POST"])
def questions():
    df = load_dataset()
    plot = None
    message = None

    # ---------------------------------------------------------
    # RUN ANALYSIS (no upload needed anymore)
    # ---------------------------------------------------------
    if request.method == "POST" and "selected_question" in request.form:
        question = request.form.get("selected_question")
        characteristic = request.form.get("breakdown")

        print("DEBUG: Analysis POST with:")
        print("  selected_question:", question)
        print("  characteristic:", characteristic)

        df = load_dataset()

        if df is not None:
            plot = plot_question(df, question, characteristic)

            return render_template(
                "analysis.html",
                analysis_type=f"Question Analysis – {question}",
                plot_file=plot
            )

    # ---------------------------------------------------------
    # GET REQUEST — dataset loads automatically
    # ---------------------------------------------------------
    questions_list = None

    df = load_dataset()
    if df is not None:
        questions_list = sorted(df["Question"].dropna().unique())

    return render_template(
        "index.html",
        questions_list=questions_list
    )

