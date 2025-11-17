import requests
import json

URL = "https://online.turfinfo.api.pmu.fr/rest/client/61/programme/05112025/R1/C1/performances-detaillees/pretty"

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
    print(f"Téléchargement des performances détaillées : {URL}")
    resp = requests.get(URL)
    resp.raise_for_status()
    data = resp.json()

    # Selon l'API, la structure racine peut être:
    # - un dict avec clé "participants"
    # - directement une liste
    if isinstance(data, dict):
        participants = data.get("participants", [])
    elif isinstance(data, list):
        participants = data
    else:
        participants = []

    print(f"Nombre de participants (chevaux) dans le JSON 3 : {len(participants)}\n")

    # Champs au niveau course passée (coursesCourues[])
    course_fields = {
        "coursesCourues.date": "date",
        "coursesCourues.discipline": "discipline",
        "coursesCourues.allocation": "allocation",
        "coursesCourues.distance": "distance",
        "coursesCourues.tempsDuPremier": "tempsDuPremier",
    }

    # Champs au niveau participant dans la course passée
    participant_hist_fields = {
        "itsHim": "itsHim",
        "place.place": "place.place",
        "place.statusArrivee": "place.statusArrivee",
        "poidsJockey": "poidsJockey",
        "corde": "corde",
        "reductionKilometrique": "reductionKilometrique",
        "distanceParcourue": "distanceParcourue",
    }

    # Statistiques
    course_stats = {label: {"present": 0, "missing_or_null": 0} for label in course_fields}
    hist_participant_stats = {label: {"present": 0, "missing_or_null": 0} for label in participant_hist_fields}

    total_courses_courues = 0
    total_hist_participants = 0

    example_course = None
    example_hist_participant = None

    for p in participants:
        courses_courues = p.get("coursesCourues", [])
        for c in courses_courues:
            total_courses_courues += 1

            if example_course is None:
                example_course = c

            # Champs au niveau course passée
            for label, key in course_fields.items():
                value = c.get(key) if "." not in key else safe_get(c, key)
                if value is None:
                    course_stats[label]["missing_or_null"] += 1
                else:
                    course_stats[label]["present"] += 1

            # Champs au niveau participants dans la course passée
            hist_participants = c.get("participants", [])
            for hp in hist_participants:
                total_hist_participants += 1

                if example_hist_participant is None:
                    example_hist_participant = hp

                for label, path in participant_hist_fields.items():
                    value = safe_get(hp, path)
                    if value is None:
                        hist_participant_stats[label]["missing_or_null"] += 1
                    else:
                        hist_participant_stats[label]["present"] += 1

    # Résumé
    print("=== RÉSUMÉ COURSES PASSÉES (coursesCourues) ===")
    print(f"Total de coursesCourues (tous chevaux confondus) : {total_courses_courues}")
    for label, s in course_stats.items():
        print(
            f"- {label}: "
            f"{s['present']} présents, "
            f"{s['missing_or_null']} manquants/Null"
        )

    print("\n=== RÉSUMÉ PARTICIPANTS DANS LES COURSES PASSÉES ===")
    print(f"Total de 'participants' historiques (tous chevaux, toutes courses) : {total_hist_participants}")
    for label, s in hist_participant_stats.items():
        print(
            f"- {label}: "
            f"{s['present']} présents, "
            f"{s['missing_or_null']} manquants/Null"
        )

    # Exemples bruts pour inspection manuelle
    print("\n=== Exemple brut d'une courseCourue ===")
    if example_course is not None:
        print(json.dumps(example_course, indent=2, ensure_ascii=False))
    else:
        print("Aucune courseCourue trouvée.")

    print("\n=== Exemple brut d'un participant historique ===")
    if example_hist_participant is not None:
        print(json.dumps(example_hist_participant, indent=2, ensure_ascii=False))
    else:
        print("Aucun participant historique trouvé.")

if __name__ == "__main__":
    main()

# Téléchargement des performances détaillées : https://online.turfinfo.api.pmu.fr/rest/client/61/programme/05112025/R1/C1/performances-detaillees/pretty
# Nombre de participants (chevaux) dans le JSON 3 : 14

# === RÉSUMÉ COURSES PASSÉES (coursesCourues) ===
# Total de coursesCourues (tous chevaux confondus) : 70
# - coursesCourues.date: 70 présents, 0 manquants/Null
# - coursesCourues.discipline: 70 présents, 0 manquants/Null
# - coursesCourues.allocation: 70 présents, 0 manquants/Null
# - coursesCourues.distance: 70 présents, 0 manquants/Null
# - coursesCourues.tempsDuPremier: 37 présents, 33 manquants/Null

# === RÉSUMÉ PARTICIPANTS DANS LES COURSES PASSÉES ===
# Total de 'participants' historiques (tous chevaux, toutes courses) : 392
# - itsHim: 392 présents, 0 manquants/Null
# - place.place: 370 présents, 22 manquants/Null
# - place.statusArrivee: 392 présents, 0 manquants/Null
# - poidsJockey: 0 présents, 392 manquants/Null
# - corde: 0 présents, 392 manquants/Null
# - reductionKilometrique: 196 présents, 196 manquants/Null
# - distanceParcourue: 392 présents, 0 manquants/Null

# === Exemple brut d'une courseCourue ===
# {
#   "date": 1761951600000,
#   "timezoneOffset": 3600000,
#   "hippodrome": "Pontchâteau",
#   "nomPrix": "PRIX JEAN-MARIE DAVID (Grp A)",
#   "discipline": "ATTELE",
#   "allocation": 15500,
#   "distance": 2800,
#   "nbParticipants": 13,
#   "tempsDuPremier": 21567,
#   "participants": [
#     {
#       "numPmu": null,
#       "place": {
#         "place": 1,
#         "rawValue": null,
#         "statusArrivee": "PLACE"
#       },
#       "nomCheval": "KILIADO BELLO",
#       "nomJockey": "PH. BOUTIN",
#       "poidsJockey": null,
#       "corde": null,
#       "distanceAvecPrecedent": null,
#       "itsHim": false,
#       "reductionKilometrique": 7700,
#       "distanceParcourue": 2800,
#       "oeillere": null
#     },
#     {
#       "numPmu": null,
#       "place": {
#         "place": 2,
#         "rawValue": null,
#         "statusArrivee": "PLACE"
#       },
#       "nomCheval": "KANDJAR RANAIS",
#       "nomJockey": "H. MARIE",
#       "poidsJockey": null,
#       "corde": null,
#       "distanceAvecPrecedent": null,
#       "itsHim": false,
#       "reductionKilometrique": 7710,
#       "distanceParcourue": 2800,
#       "oeillere": null
#     },
#     {
#       "numPmu": null,
#       "place": {
#         "place": 3,
#         "rawValue": null,
#         "statusArrivee": "PLACE"
#       },
#       "nomCheval": "KALINE DU LEVANT",
#       "nomJockey": "M. HAMELIN",
#       "poidsJockey": null,
#       "corde": null,
#       "distanceAvecPrecedent": null,
#       "itsHim": false,
#       "reductionKilometrique": 7720,
#       "distanceParcourue": 2800,
#       "oeillere": null
#     },
#     {
#       "numPmu": null,
#       "place": {
#         "place": 4,
#         "rawValue": null,
#         "statusArrivee": "PLACE"
#       },
#       "nomCheval": "KOPERNIK DE GODREL",
#       "nomJockey": "N. BRIDAULT",
#       "poidsJockey": null,
#       "corde": null,
#       "distanceAvecPrecedent": null,
#       "itsHim": false,
#       "reductionKilometrique": 7740,
#       "distanceParcourue": 2800,
#       "oeillere": null
#     },
#     {
#       "numPmu": null,
#       "place": {
#         "place": 5,
#         "rawValue": null,
#         "statusArrivee": "PLACE"
#       },
#       "nomCheval": "KEL AMOUR BARBES",
#       "nomJockey": "D. HEON",
#       "poidsJockey": null,
#       "corde": null,
#       "distanceAvecPrecedent": null,
#       "itsHim": false,
#       "reductionKilometrique": 7740,
#       "distanceParcourue": 2800,
#       "oeillere": null
#     },
#     {
#       "numPmu": null,
#       "place": {
#         "place": 6,
#         "rawValue": null,
#         "statusArrivee": "PLACE"
#       },
#       "nomCheval": "KING DU PLESSIS",
#       "nomJockey": "CH. BOISNARD",
#       "poidsJockey": null,
#       "corde": null,
#       "distanceAvecPrecedent": null,
#       "itsHim": true,
#       "reductionKilometrique": 7750,
#       "distanceParcourue": 2800,
#       "oeillere": null
#     }
#   ]
# }

# === Exemple brut d'un participant historique ===
# {
#   "numPmu": null,
#   "place": {
#     "place": 1,
#     "rawValue": null,
#     "statusArrivee": "PLACE"
#   },
#   "nomCheval": "KILIADO BELLO",
#   "nomJockey": "PH. BOUTIN",
#   "poidsJockey": null,
#   "corde": null,
#   "distanceAvecPrecedent": null,
#   "itsHim": false,
#   "reductionKilometrique": 7700,
#   "distanceParcourue": 2800,
#   "oeillere": null
# }