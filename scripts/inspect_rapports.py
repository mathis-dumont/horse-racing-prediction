import requests
import json

URL = "https://online.turfinfo.api.pmu.fr/rest/client/1/programme/05112025/R1/C1/rapports-definitifs"

def safe_get(obj, path, default=None):
    """
    Récupère une valeur dans un dict imbriqué avec une notation 'a.b.c'.
    Retourne default si une des clés manque.
    """
    keys = path.split(".")
    cur = obj
    for k in keys:
        if not isinstance(cur, dict):
            return default
        if k not in cur:
            return default
        cur = cur[k]
    return cur

def main():
    print(f"Téléchargement des rapports définitifs : {URL}")
    resp = requests.get(URL)
    resp.raise_for_status()
    data = resp.json()

    # Selon l'API, les rapports peuvent être un tableau ou un objet contenant un tableau.
    if isinstance(data, list):
        bets = data
    elif isinstance(data, dict):
        # Si jamais l'API change légèrement et encapsule dans une clé
        # on essaie de deviner une clé probable, sinon on met liste vide.
        bets = data.get("rapportsDefinitifs", [])
    else:
        bets = []

    print(f"Nombre de types de pari (entries dans la liste) : {len(bets)}\n")

    # Champs au niveau pari (un élément de la liste)
    bet_fields = {
        "typePari": "typePari",
        "famillePari": "famillePari",
        "miseBase": "miseBase",
        "rembourse": "rembourse",
    }

    # Champs au niveau rapport individuel (dans [].rapports[])
    report_fields = {
        "dividende": "dividende",
        "dividendePourUnEuro": "dividendePourUnEuro",
        "combinaison": "combinaison",
        "nombreGagnants": "nombreGagnants",
    }

    bet_stats = {label: {"present": 0, "missing_or_null": 0} for label in bet_fields}
    report_stats = {label: {"present": 0, "missing_or_null": 0} for label in report_fields}

    total_reports = 0
    example_bet = None
    example_report = None

    for bet in bets:
        if example_bet is None:
            example_bet = bet

        # Statistiques au niveau pari
        for label, path in bet_fields.items():
            value = safe_get(bet, path)
            if value is None:
                bet_stats[label]["missing_or_null"] += 1
            else:
                bet_stats[label]["present"] += 1

        # Rapports individuels
        rapports = bet.get("rapports", [])
        for r in rapports:
            total_reports += 1

            if example_report is None:
                example_report = r

            for label, path in report_fields.items():
                value = safe_get(r, path)
                if value is None:
                    report_stats[label]["missing_or_null"] += 1
                else:
                    report_stats[label]["present"] += 1

    # Résumé
    print("=== RÉSUMÉ NIVEAU PARI (JSON 4 root list) ===")
    print(f"Total de types de pari : {len(bets)}")
    for label, s in bet_stats.items():
        print(
            f"- {label}: "
            f"{s['present']} présents, "
            f"{s['missing_or_null']} manquants/Null"
        )

    print("\n=== RÉSUMÉ NIVEAU RAPPORT (rapports[]) ===")
    print(f"Total de rapports individuels : {total_reports}")
    for label, s in report_stats.items():
        print(
            f"- {label}: "
            f"{s['present']} présents, "
            f"{s['missing_or_null']} manquants/Null"
        )

    # Exemples bruts pour inspection manuelle
    print("\n=== Exemple brut d'un pari ===")
    if example_bet is not None:
        print(json.dumps(example_bet, indent=2, ensure_ascii=False))
    else:
        print("Aucun pari dans la réponse.")

    print("\n=== Exemple brut d'un rapport ===")
    if example_report is not None:
        print(json.dumps(example_report, indent=2, ensure_ascii=False))
    else:
        print("Aucun rapport dans la réponse.")

if __name__ == "__main__":
    main()

# Téléchargement des rapports définitifs : https://online.turfinfo.api.pmu.fr/rest/client/1/programme/05112025/R1/C1/rapports-definitifs
# Nombre de types de pari (entries dans la liste) : 7

# === RÉSUMÉ NIVEAU PARI (JSON 4 root list) ===
# Total de types de pari : 7
# - typePari: 7 présents, 0 manquants/Null
# - famillePari: 7 présents, 0 manquants/Null
# - miseBase: 7 présents, 0 manquants/Null
# - rembourse: 7 présents, 0 manquants/Null

# === RÉSUMÉ NIVEAU RAPPORT (rapports[]) ===
# Total de rapports individuels : 19
# - dividende: 19 présents, 0 manquants/Null
# - dividendePourUnEuro: 19 présents, 0 manquants/Null
# - combinaison: 19 présents, 0 manquants/Null
# - nombreGagnants: 19 présents, 0 manquants/Null

# === Exemple brut d'un pari ===
# {
#   "typePari": "SIMPLE_GAGNANT",
#   "miseBase": 200,
#   "rembourse": false,
#   "rapports": [
#     {
#       "libelle": "Simple gagnant",
#       "dividende": 310,
#       "dividendePourUnEuro": 310,
#       "combinaison": "7",
#       "nombreGagnants": 21294.6,
#       "dividendePourUneMiseDeBase": 620,
#       "dividendeUnite": "PourUnEuro"
#     }
#   ],
#   "audience": "NATIONAL",
#   "famillePari": "Simple",
#   "dividendeUnite": "PourUnEuro"
# }

# === Exemple brut d'un rapport ===
# {
#   "libelle": "Simple gagnant",
#   "dividende": 310,
#   "dividendePourUnEuro": 310,
#   "combinaison": "7",
#   "nombreGagnants": 21294.6,
#   "dividendePourUneMiseDeBase": 620,
#   "dividendeUnite": "PourUnEuro"
# }