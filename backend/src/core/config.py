import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DB_URL = os.getenv("DB_URL")
MAX_WORKERS = 4
FAILURES_DIR = "failures"

PROGRAMME_URL_TEMPLATE = "https://online.turfinfo.api.pmu.fr/rest/client/1/programme/{date_code}"
PARTICIPANTS_URL_TEMPLATE = "https://online.turfinfo.api.pmu.fr/rest/client/61/programme/{date}/R{meeting}/C{race}/participants"
PERF_URL_TEMPLATE = "https://online.turfinfo.api.pmu.fr/rest/client/61/programme/{date}/R{meeting}/C{race}/performances-detaillees/pretty"
REPORTS_URL_TEMPLATE = "https://online.turfinfo.api.pmu.fr/rest/client/1/programme/{date}/R{meeting}/C{race}/rapports-definitifs"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.pmu.fr/",
    "Origin": "https://www.pmu.fr"
}

STATUS_MAP = {
    "ARRIVEE_DEFINITIVE_COMPLETE": "FIN",
    "ARRIVEE_DEFINITIVE_C": "FIN",
    "FIN_COURSE": "FIN",
    "COURSE_ANNULEE": "ANN",
    "A_PARTIR": "FUT",
    "EN_COURS": "LIVE",
    "ARRIVEE_PROVISOIRE": "PROV"
}

TRACK_MAP = {
    "SABLE": "S",
    "POUZZOLANE": "P",
    "HERBE": "H",
    "CENDREE": "C",
    "MACHEFER": "M"
}

INCIDENT_MAP = {
    "DISQUALIFIE_POUR_ALLURE_IRREGULIERE": "DAI",
    "DISQUALIFIE_POTEAU_GALOP": "DPG",
    "NON_PARTANT": "NP",
    "DISTANCE": "DIST",
    "ARRETE": "ARR",
    "TOMBE": "T",
    "RESTE_AU_POTEAU": "RP",
    "DISQUALIFIE": "DAI",
    "RETROGRADE": "RET"
}

SHOE_MAP = {
    "DEFERRE_ANTERIEURS_POSTERIEURS": "D4",
    "PROTEGE_ANTERIEURS_DEFERRRE_POSTERIEURS": "PADP",
    "DEFERRE_POSTERIEURS": "DP",
    "DEFERRE_ANTERIEURS": "DA",
    "PROTEGE_ANTERIEURS": "PA",
    "PROTEGE_ANTERIEURS_POSTERIEURS": "P4",
    "DEFERRE_ANTERIEURS_PROTEGE_POSTERIEURS": "DAPP",
    "REFERRE_ANTERIEURS_POSTERIEURS": "R4",
    "PROTEGE_POSTERIEURS": "PP"
}

BET_TYPE_MAP = {
    "SIMPLE_GAGNANT": "SG",
    "SIMPLE_PLACE": "SP",
    "COUPLE_GAGNANT": "CG",
    "COUPLE_PLACE": "CP",
    "COUPLE_ORDRE": "CO",
    "TRIO": "TRIO",
    "TRIO_ORDRE": "TRIOO",
    "DEUX_SUR_QUATRE": "2S4",
    "MULTI": "MULTI",
    "MINI_MULTI": "MM",
    "TIERCE": "TIERCE",
    "QUARTE_PLUS": "QUARTE",
    "QUINTE_PLUS": "QUINTE",
    "PICK5": "PICK5",
    "SUPER_QUATRE": "SUP4"
}