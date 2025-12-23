from flask import Blueprint, render_template
import pandas as pd

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    # Exemple : résultats ML
    results = [
        {"race": "Vincennes R1", "horse": "Bold Eagle", "score": 0.87},
        {"race": "Chantilly R3", "horse": "Enable", "score": 0.81},
    ]

    return render_template("index.html", results=results)