from flask import Blueprint, jsonify, request
from datetime import date
import datetime as dt

from src.pmu_prediction.db.connection import get_connection
from src.pmu_prediction.queries.races import (
    get_races_for_date,
    get_race_id,
)
from src.pmu_prediction.queries.participants import (
    get_participants_for_race_id,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


# =======================
# RACES DU JOUR
# =======================
@api_bp.route("/races", methods=["GET"])
def get_races():
    conn = get_connection()
    try:
        today = date.today()
        races = get_races_for_date(conn, today)
        return jsonify(races)
    finally:
        conn.close()


# =======================
# PARTICIPANTS D'UNE COURSE
# =======================
@api_bp.route("/races/<race_code>/participants", methods=["GET"])
def race_participants(race_code):
    # race_code ex: "R3C2"
    try:
        meeting_number = int(race_code.split("C")[0][1:])
        race_number = int(race_code.split("C")[1])
    except Exception:
        return jsonify({"error": "Invalid race code"}), 400

    program_date = date.today()  # pour l'instant : aujourd'hui

    conn = get_connection()
    try:
        race_id = get_race_id(conn, meeting_number, race_number, program_date)
        if not race_id:
            return jsonify([])

        participants = get_participants_for_race_id(conn, race_id)
        return jsonify(participants)
    finally:
        conn.close()


# =======================
# MOCK PREDICTION (TEMPORAIRE)
# =======================
@api_bp.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()

    course_id = data.get("course_id")
    bet_type = data.get("bet_type")

    # réponse fictive (pour l'instant)
    return jsonify([
        {
            "horse": "Cheval 7",
            "p_win": 0.28,
            "p_place": 0.55,
            "odds": 6.4,
            "comment": f"Mock prediction pour {course_id} / {bet_type}"
        }
    ])


