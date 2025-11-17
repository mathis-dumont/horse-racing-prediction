import requests
import json

URL = "https://online.turfinfo.api.pmu.fr/rest/client/1/programme/05112025"

def safe_get(obj, path, default=None):
    """Utility to safely get nested JSON keys using a.b.c notation."""
    keys = path.split(".")
    for k in keys:
        if not isinstance(obj, dict) or k not in obj:
            return default
        obj = obj[k]
    return obj

def main():
    print(f"Téléchargement du programme : {URL}")
    resp = requests.get(URL)
    data = resp.json()

    print(data.keys())  # pour vérifier la structure racine

    programme = data.get("programme", {})
    print(programme.keys())

    # -------------------------
    # PROGRAMME.DATE
    # -------------------------
    program_date = programme.get("date")
    print(f"Date du programme trouvée : {program_date}")
    print()

    # -------------------------
    # RÉUNIONS
    # -------------------------
    reunions = programme.get("reunions", [])
    print(f"Nombre de réunions : {len(reunions)}")
    print()

    meeting_stats = {
        "numOfficiel": 0,
        "nature": 0,
        "hippodrome.code": 0,
        "meteo.temperature": 0,
        "meteo.directionVent": 0
    }

    race_stats = {
        "typePiste": 0,
        "categorieParticularite": 0,
        "conditionAge": 0,
        "nombreDeclaresPartants": 0,
        "conditions": 0,
        "penetrometre.valeurMesure": 0,
        "penetrometre.intitule": 0,
        "ordreArrivee": 0,
        "dureeCourse": 0,
        "statut": 0,
        "categorieStatut": 0,
        "paris[].codePari": 0
    }

    total_races = 0

    example_race = None

    # -------------------------
    # LOOP MEETINGS + RACES
    # -------------------------
    for reunion in reunions:

        if reunion.get("numOfficiel") is not None:
            meeting_stats["numOfficiel"] += 1

        if reunion.get("nature") is not None:
            meeting_stats["nature"] += 1

        if safe_get(reunion, "hippodrome.code") is not None:
            meeting_stats["hippodrome.code"] += 1

        if safe_get(reunion, "meteo.temperature") is not None:
            meeting_stats["meteo.temperature"] += 1

        if safe_get(reunion, "meteo.directionVent") is not None:
            meeting_stats["meteo.directionVent"] += 1

        # Courses
        courses = reunion.get("courses", [])
        total_races += len(courses)

        for course in courses:

            # Save an example
            if example_race is None:
                example_race = course

            # Count all fields presence
            for key in race_stats.keys():

                if key == "paris[].codePari":
                    paris = course.get("paris", [])
                    if any(p.get("codePari") is not None for p in paris):
                        race_stats[key] += 1
                else:
                    if safe_get(course, key) is not None:
                        race_stats[key] += 1

    # -------------------------
    # SUMMARY OUTPUT
    # -------------------------
    print("=== RÉSUMÉ RÉUNIONS ===")
    print(f"Total réunions : {len(reunions)}")
    for k, v in meeting_stats.items():
        print(f"- {k}: {v} présents, {len(reunions) - v} manquants/Null")
    print()

    print("=== RÉSUMÉ COURSES ===")
    print(f"Total courses : {total_races}")
    for k, v in race_stats.items():
        print(f"- {k}: {v} présents, {total_races - v} manquants/Null")
    print()

    print("=== Exemple brut d'une course ===")
    print(json.dumps(example_race, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
import requests
import json

URL = "https://online.turfinfo.api.pmu.fr/rest/client/1/programme/05112025"

def safe_get(obj, path, default=None):
    """Utility to safely get nested JSON keys using a.b.c notation."""
    keys = path.split(".")
    for k in keys:
        if not isinstance(obj, dict) or k not in obj:
            return default
        obj = obj[k]
    return obj

def main():
    print(f"Téléchargement du programme : {URL}")
    resp = requests.get(URL)
    data = resp.json()

    print(data.keys())  # pour vérifier la structure racine

    programme = data.get("programme", {})
    print(programme.keys())

    # -------------------------
    # PROGRAMME.DATE
    # -------------------------
    program_date = programme.get("date")
    print(f"Date du programme trouvée : {program_date}")
    print()

    # -------------------------
    # RÉUNIONS
    # -------------------------
    reunions = programme.get("reunions", [])
    print(f"Nombre de réunions : {len(reunions)}")
    print()

    meeting_stats = {
        "numOfficiel": 0,
        "nature": 0,
        "hippodrome.code": 0,
        "meteo.temperature": 0,
        "meteo.directionVent": 0
    }

    race_stats = {
        "typePiste": 0,
        "categorieParticularite": 0,
        "conditionAge": 0,
        "nombreDeclaresPartants": 0,
        "conditions": 0,
        "penetrometre.valeurMesure": 0,
        "penetrometre.intitule": 0,
        "ordreArrivee": 0,
        "dureeCourse": 0,
        "statut": 0,
        "categorieStatut": 0,
        "paris[].codePari": 0
    }

    total_races = 0

    example_race = None

    # -------------------------
    # LOOP MEETINGS + RACES
    # -------------------------
    for reunion in reunions:

        if reunion.get("numOfficiel") is not None:
            meeting_stats["numOfficiel"] += 1

        if reunion.get("nature") is not None:
            meeting_stats["nature"] += 1

        if safe_get(reunion, "hippodrome.code") is not None:
            meeting_stats["hippodrome.code"] += 1

        if safe_get(reunion, "meteo.temperature") is not None:
            meeting_stats["meteo.temperature"] += 1

        if safe_get(reunion, "meteo.directionVent") is not None:
            meeting_stats["meteo.directionVent"] += 1

        # Courses
        courses = reunion.get("courses", [])
        total_races += len(courses)

        for course in courses:

            # Save an example
            if example_race is None:
                example_race = course

            # Count all fields presence
            for key in race_stats.keys():

                if key == "paris[].codePari":
                    paris = course.get("paris", [])
                    if any(p.get("codePari") is not None for p in paris):
                        race_stats[key] += 1
                else:
                    if safe_get(course, key) is not None:
                        race_stats[key] += 1

    # -------------------------
    # SUMMARY OUTPUT
    # -------------------------
    print("=== RÉSUMÉ RÉUNIONS ===")
    print(f"Total réunions : {len(reunions)}")
    for k, v in meeting_stats.items():
        print(f"- {k}: {v} présents, {len(reunions) - v} manquants/Null")
    print()

    print("=== RÉSUMÉ COURSES ===")
    print(f"Total courses : {total_races}")
    for k, v in race_stats.items():
        print(f"- {k}: {v} présents, {total_races - v} manquants/Null")
    print()

    print("=== Exemple brut d'une course ===")
    print(json.dumps(example_race, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

# Téléchargement du programme : https://online.turfinfo.api.pmu.fr/rest/client/1/programme/05112025
# dict_keys(['programme', 'timestampPMU'])
# dict_keys(['cached', 'date', 'timezoneOffset', 'reunions', 'prochainesCoursesAPartir', 'datesProgrammesDisponibles'])
# Date du programme trouvée : 1762297200000

# Nombre de réunions : 9

# === RÉSUMÉ RÉUNIONS ===
# Total réunions : 9
# - numOfficiel: 9 présents, 0 manquants/Null
# - nature: 9 présents, 0 manquants/Null
# - hippodrome.code: 9 présents, 0 manquants/Null
# - meteo.temperature: 9 présents, 0 manquants/Null
# - meteo.directionVent: 9 présents, 0 manquants/Null

# === RÉSUMÉ COURSES ===
# Total courses : 63
# - typePiste: 33 présents, 30 manquants/Null
# - categorieParticularite: 63 présents, 0 manquants/Null
# - conditionAge: 45 présents, 18 manquants/Null
# - nombreDeclaresPartants: 63 présents, 0 manquants/Null
# - conditions: 63 présents, 0 manquants/Null
# - penetrometre.valeurMesure: 16 présents, 47 manquants/Null
# - penetrometre.intitule: 45 présents, 18 manquants/Null
# - ordreArrivee: 63 présents, 0 manquants/Null
# - dureeCourse: 63 présents, 0 manquants/Null
# - statut: 63 présents, 0 manquants/Null
# - categorieStatut: 63 présents, 0 manquants/Null
# - paris[].codePari: 63 présents, 0 manquants/Null

# === Exemple brut d'une course ===
# {
#   "cached": false,
#   "departImminent": false,
#   "arriveeDefinitive": true,
#   "timezoneOffset": 3600000,
#   "numReunion": 1,
#   "numExterneReunion": 1,
#   "numOrdre": 1,
#   "numExterne": 1,
#   "heureDepart": 1762344720000,
#   "libelle": "PRIX ONIRIS",
#   "libelleCourt": "ONIRIS",
#   "montantPrix": 19000,
#   "parcours": "",
#   "distance": 3000,
#   "distanceUnit": "METRE",
#   "corde": "CORDE_GAUCHE",
#   "discipline": "MONTE",
#   "specialite": "TROT_MONTE",
#   "categorieParticularite": "APPRENTIS_LADS_JOCKEYS",
#   "conditionSexe": "TOUS_CHEVAUX",
#   "nombreDeclaresPartants": 14,
#   "grandPrixNationalTrot": false,
#   "numSocieteMere": 441301,
#   "pariMultiCourses": false,
#   "pariSpecial": false,
#   "montantTotalOffert": 19000,
#   "montantOffert1er": 8550,
#   "montantOffert2eme": 4750,
#   "montantOffert3eme": 2660,
#   "montantOffert4eme": 1520,
#   "montantOffert5eme": 950,
#   "conditions": "PRIX ONIRIS Course  1 Course F APPRENTIS - LADS-JOCKEYS 19.000. - Monté. - 3.000 mètres. 8.550, 4.750, 2.660, 1.520, 950, 380, 190.- alloués par la S.E.T.F. Pour 5 ans, n'ayant pas gagné 57.000. - Recul de 25 m. à 28.000. Poids minimum (voir Conditions Générales).",
#   "numCourseDedoublee": 0,
#   "paris": [
#     {
#       "typePari": "SIMPLE_GAGNANT",
#       "miseBase": 200,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "reportable": true,
#       "misEnPaiement": true,
#       "codePari": "SIMPLE_GAGNANT",
#       "spotAutorise": true,
#       "ordre": false,
#       "combine": true,
#       "nbChevauxReglementaire": 1,
#       "complement": false,
#       "infosJackpot": {
#         "miseBase": 300,
#         "tauxContribution": {
#           "numerateur": 1,
#           "denominateur": 3
#         }
#       }
#     },
#     {
#       "poolId": "652ef740-9d3b-4940-b220-380c8f62a718",
#       "typePari": "E_SIMPLE_GAGNANT",
#       "miseBase": 100,
#       "miseMax": 3000000,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "cagnotte": 0,
#       "reportable": true,
#       "codePari": "E_SIMPLE_GAGNANT",
#       "spotAutorise": true,
#       "ordre": false,
#       "combine": true,
#       "nbChevauxReglementaire": 1,
#       "complement": false,
#       "infosJackpot": {
#         "miseBase": 150,
#         "tauxContribution": {
#           "numerateur": 1,
#           "denominateur": 3
#         }
#       }
#     },
#     {
#       "typePari": "SIMPLE_PLACE",
#       "miseBase": 200,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "reportable": true,
#       "misEnPaiement": true,
#       "codePari": "SIMPLE_PLACE",
#       "spotAutorise": true,
#       "ordre": false,
#       "combine": true,
#       "nbChevauxReglementaire": 1,
#       "complement": false,
#       "infosJackpot": {
#         "miseBase": 300,
#         "tauxContribution": {
#           "numerateur": 1,
#           "denominateur": 3
#         }
#       }
#     },
#     {
#       "poolId": "ed63732a-5020-480d-8418-05fd90386a41",
#       "typePari": "E_SIMPLE_PLACE",
#       "miseBase": 100,
#       "miseMax": 3000000,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "cagnotte": 0,
#       "reportable": true,
#       "codePari": "E_SIMPLE_PLACE",
#       "spotAutorise": true,
#       "ordre": false,
#       "combine": true,
#       "nbChevauxReglementaire": 1,
#       "complement": false,
#       "infosJackpot": {
#         "miseBase": 150,
#         "tauxContribution": {
#           "numerateur": 1,
#           "denominateur": 3
#         }
#       }
#     },
#     {
#       "typePari": "COUPLE_GAGNANT",
#       "miseBase": 200,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "reportable": true,
#       "misEnPaiement": true,
#       "codePari": "COUPLE_GAGNANT",
#       "spotAutorise": true,
#       "valeursFlexiAutorisees": [
#         50
#       ],
#       "ordre": false,
#       "combine": true,
#       "nbChevauxReglementaire": 2,
#       "complement": true
#     },
#     {
#       "poolId": "42872eff-f8b5-43f7-8308-a19f599566f2",
#       "typePari": "E_COUPLE_GAGNANT",
#       "miseBase": 100,
#       "miseMax": 3000000,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "cagnotte": 0,
#       "reportable": true,
#       "codePari": "E_COUPLE_GAGNANT",
#       "spotAutorise": true,
#       "ordre": false,
#       "combine": true,
#       "nbChevauxReglementaire": 2,
#       "complement": true
#     },
#     {
#       "typePari": "COUPLE_PLACE",
#       "miseBase": 200,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "reportable": true,
#       "misEnPaiement": true,
#       "codePari": "COUPLE_PLACE",
#       "spotAutorise": true,
#       "valeursFlexiAutorisees": [
#         50
#       ],
#       "ordre": false,
#       "combine": true,
#       "nbChevauxReglementaire": 2,
#       "complement": true
#     },
#     {
#       "poolId": "4cfffb91-0b2b-4f39-8e63-33c853565afc",
#       "typePari": "E_COUPLE_PLACE",
#       "miseBase": 100,
#       "miseMax": 3000000,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "cagnotte": 0,
#       "reportable": true,
#       "codePari": "E_COUPLE_PLACE",
#       "spotAutorise": true,
#       "ordre": false,
#       "combine": true,
#       "nbChevauxReglementaire": 2,
#       "complement": true
#     },
#     {
#       "typePari": "DEUX_SUR_QUATRE",
#       "miseBase": 300,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "reportable": true,
#       "misEnPaiement": true,
#       "codePari": "DEUX_SUR_QUATRE",
#       "spotAutorise": true,
#       "valeursFlexiAutorisees": [
#         25,
#         50
#       ],
#       "ordre": false,
#       "combine": true,
#       "nbChevauxReglementaire": 2,
#       "complement": true,
#       "infosJackpot": {
#         "miseBase": 400,
#         "tauxContribution": {
#           "numerateur": 1,
#           "denominateur": 4
#         }
#       }
#     },
#     {
#       "poolId": "1bce2165-2cb1-4ad4-b846-979eaa84430d",
#       "typePari": "E_DEUX_SUR_QUATRE",
#       "miseBase": 300,
#       "miseMax": 3000000,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "cagnotte": 0,
#       "reportable": true,
#       "codePari": "E_DEUX_SUR_QUATRE",
#       "spotAutorise": true,
#       "valeursFlexiAutorisees": [
#         50
#       ],
#       "ordre": false,
#       "combine": true,
#       "nbChevauxReglementaire": 2,
#       "complement": true,
#       "infosJackpot": {
#         "miseBase": 400,
#         "tauxContribution": {
#           "numerateur": 1,
#           "denominateur": 4
#         }
#       }
#     },
#     {
#       "typePari": "TRIO",
#       "miseBase": 200,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "reportable": false,
#       "misEnPaiement": true,
#       "codePari": "TRIO",
#       "spotAutorise": true,
#       "valeursFlexiAutorisees": [
#         50
#       ],
#       "ordre": false,
#       "combine": true,
#       "nbChevauxReglementaire": 3,
#       "complement": true
#     },
#     {
#       "poolId": "6dc09a43-3ad2-42c3-827d-50fd5f07f3e7",
#       "typePari": "E_TRIO",
#       "miseBase": 100,
#       "miseMax": 3000000,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "cagnotte": 0,
#       "reportable": false,
#       "codePari": "E_TRIO",
#       "spotAutorise": true,
#       "ordre": false,
#       "combine": true,
#       "nbChevauxReglementaire": 3,
#       "complement": true
#     },
#     {
#       "typePari": "MULTI",
#       "miseBase": 300,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "reportable": false,
#       "misEnPaiement": true,
#       "codePari": "MULTI",
#       "spotAutorise": true,
#       "valeursFlexiAutorisees": [
#         25,
#         50
#       ],
#       "valeursRisqueAutorisees": [
#         4,
#         5,
#         6,
#         7
#       ],
#       "ordre": false,
#       "combine": true,
#       "nbChevauxReglementaire": 4,
#       "complement": false
#     },
#     {
#       "poolId": "f77a1706-afd8-445a-b869-a9d2785f0116",
#       "typePari": "E_MULTI",
#       "miseBase": 300,
#       "miseMax": 3000000,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "cagnotte": 0,
#       "reportable": false,
#       "codePari": "E_MULTI",
#       "spotAutorise": true,
#       "valeursFlexiAutorisees": [
#         50
#       ],
#       "valeursRisqueAutorisees": [
#         4,
#         5,
#         6,
#         7
#       ],
#       "ordre": false,
#       "combine": true,
#       "nbChevauxReglementaire": 4,
#       "complement": false
#     },
#     {
#       "typePari": "REPORT_PLUS",
#       "enVente": false,
#       "reportable": false,
#       "codePari": "REPORT_PLUS",
#       "spotAutorise": false,
#       "ordre": false,
#       "combine": false,
#       "nbChevauxReglementaire": 1,
#       "complement": false
#     },
#     {
#       "poolId": "e8e69ed9-acde-4a63-8e28-2f4c8761760a",
#       "typePari": "E_REPORT_PLUS",
#       "miseBase": 100,
#       "miseMax": 3000000,
#       "enVente": false,
#       "audience": "NATIONAL",
#       "reportable": false,
#       "codePari": "E_REPORT_PLUS",
#       "spotAutorise": false,
#       "ordre": false,
#       "combine": false,
#       "nbChevauxReglementaire": 1,
#       "complement": false
#     }
#   ],
#   "statut": "FIN_COURSE",
#   "categorieStatut": "ARRIVEE",
#   "dureeCourse": 228770,
#   "participants": [],
#   "ecuries": [],
#   "incidents": [
#     {
#       "type": "DISQUALIFIE_POUR_ALLURE_IRREGULIERE",
#       "numeroParticipants": [
#         1,
#         2,
#         12
#       ]
#     }
#   ],
#   "rapportsDefinitifsDisponibles": true,
#   "isArriveeDefinitive": true,
#   "isDepartImminent": false,
#   "isDepartAJPlusUn": false,
#   "cagnottes": [],
#   "pronosticsExpires": false,
#   "replayDisponible": true,
#   "hippodrome": {
#     "codeHippodrome": "PET",
#     "libelleCourt": "NANTES",
#     "libelleLong": "HIPPODROME DE NANTES"
#   },
#   "epcPourTousParis": true,
#   "courseTrackee": false,
#   "courseExclusiveInternet": false,
#   "formuleChampLibreIndisponible": false,
#   "ordreArrivee": [
#     [
#       7
#     ],
#     [
#       3
#     ],
#     [
#       9
#     ],
#     [
#       13
#     ],
#     [
#       5
#     ],
#     [
#       14
#     ],
#     [
#       6
#     ],
#     [
#       8
#     ],
#     [
#       4
#     ],
#     [
#       11
#     ],
#     [
#       10
#     ]
#   ],
#   "hasEParis": true
# }