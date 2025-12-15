import requests
import json

URL = "https://online.turfinfo.api.pmu.fr/rest/client/61/programme/05112025/R1/C1/participants"

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
    print(f"Téléchargement des participants : {URL}")
    resp = requests.get(URL)
    resp.raise_for_status()
    data = resp.json()

    # Certains endpoints PMU renvoient directement une liste de participants,
    # d'autres un objet avec une clé 'participants' : on gère les deux cas.
    if isinstance(data, dict):
        participants = data.get("participants", [])
    elif isinstance(data, list):
        participants = data
    else:
        participants = []

    print(f"Nombre de participants : {len(participants)}\n")

    # Champs à analyser
    fields = {
        "numPmu": "numPmu",
        "age": "age",
        "sexe": "sexe",
        "entraineur": "entraineur",
        "driver": "driver",
        "deferre": "deferre",
        "musique": "musique",
        "nombreCourses": "nombreCourses",
        "gainsParticipant.gainsCarriere": "gainsParticipant.gainsCarriere",
        "dernierRapportReference.rapport": "dernierRapportReference.rapport",
        "dernierRapportDirect.rapport": "dernierRapportDirect.rapport",
        "ordreArrivee": "ordreArrivee",
        "incident": "incident",
        "tempsObtenu": "tempsObtenu",
        "reductionKilometrique": "reductionKilometrique",
        "commentaireApresCourse": "commentaireApresCourse",
        "avisEntraineur": "avisEntraineur",
    }

    stats = {name: {"present": 0, "missing_or_null": 0} for name in fields.keys()}

    example_participant = None

    for p in participants:
        if example_participant is None:
            example_participant = p

        for label, path in fields.items():
            value = safe_get(p, path)
            if value is None:
                stats[label]["missing_or_null"] += 1
            else:
                stats[label]["present"] += 1

    # Résumé
    print("=== RÉSUMÉ PARTICIPANTS ===")
    for label, s in stats.items():
        print(
            f"- {label}: "
            f"{s['present']} présents, "
            f"{s['missing_or_null']} manquants/Null"
        )

    # Exemple brut pour inspection manuelle
    print("\n=== Exemple brut d'un participant ===")
    if example_participant is not None:
        print(json.dumps(example_participant, indent=2, ensure_ascii=False))
    else:
        print("Aucun participant dans la réponse.")

if __name__ == "__main__":
    main()

# RESULTATS :
# Téléchargement des participants : https://online.turfinfo.api.pmu.fr/rest/client/61/programme/05112025/R1/C1/participants
# Nombre de participants : 14

# === RÉSUMÉ PARTICIPANTS ===
# - numPmu: 14 présents, 0 manquants/Null
# - age: 14 présents, 0 manquants/Null
# - sexe: 14 présents, 0 manquants/Null
# - entraineur: 14 présents, 0 manquants/Null
# - driver: 14 présents, 0 manquants/Null
# - deferre: 9 présents, 5 manquants/Null
# - musique: 14 présents, 0 manquants/Null
# - nombreCourses: 14 présents, 0 manquants/Null
# - gainsParticipant.gainsCarriere: 14 présents, 0 manquants/Null
# - dernierRapportReference.rapport: 14 présents, 0 manquants/Null
# - dernierRapportDirect.rapport: 14 présents, 0 manquants/Null
# - ordreArrivee: 11 présents, 3 manquants/Null
# - incident: 3 présents, 11 manquants/Null
# - tempsObtenu: 11 présents, 3 manquants/Null
# - reductionKilometrique: 11 présents, 3 manquants/Null
# - commentaireApresCourse: 14 présents, 0 manquants/Null
# - avisEntraineur: 14 présents, 0 manquants/Null

# === Exemple brut d'un participant ===
# {
#   "idCheval": "KING DU PLESSIS-DANA VICTIS-DIJON",
#   "nom": "KING DU PLESSIS",
#   "numPmu": 1,
#   "age": 5,
#   "sexe": "HONGRES",
#   "race": "TROTTEUR FRANCAIS",
#   "statut": "PARTANT",
#   "oeilleres": "SANS_OEILLERES",
#   "proprietaire": "Ecurie Christian BOISNARD",
#   "entraineur": "CH. BOISNARD",
#   "driver": "Mme R. HAGHIGHAT",
#   "driverChange": false,
#   "robe": {
#     "code": "020",
#     "libelleCourt": "BAI",
#     "libelleLong": "BAI"
#   },
#   "indicateurInedit": false,
#   "musique": "6a3a7a6a8a7a5a4aDa6a",
#   "nombreCourses": 22,
#   "nombreVictoires": 0,
#   "nombrePlaces": 15,
#   "nombrePlacesSecond": 1,
#   "nombrePlacesTroisieme": 3,
#   "gainsParticipant": {
#     "gainsCarriere": 1403500,
#     "gainsVictoires": 0,
#     "gainsPlace": 1403500,
#     "gainsAnneeEnCours": 496000,
#     "gainsAnneePrecedente": 907500
#   },
#   "nomPere": "DIJON",
#   "nomMere": "DANA VICTIS",
#   "incident": "DISQUALIFIE_POUR_ALLURE_IRREGULIERE",
#   "jumentPleine": false,
#   "engagement": false,
#   "supplement": 0,
#   "handicapDistance": 3000,
#   "handicapPoids": 570,
#   "poidsConditionMonteChange": false,
#   "dernierRapportDirect": {
#     "typePari": "SIMPLE_GAGNANT",
#     "rapport": 83.0,
#     "typeRapport": "DIRECT",
#     "indicateurTendance": " ",
#     "nombreIndicateurTendance": 0.0,
#     "dateRapport": 1762344881000,
#     "permutation": 1,
#     "favoris": false,
#     "numPmu1": 1,
#     "grossePrise": false
#   },
#   "dernierRapportReference": {
#     "typePari": "SIMPLE_GAGNANT",
#     "rapport": 34.0,
#     "typeRapport": "REFERENCE",
#     "indicateurTendance": "+",
#     "nombreIndicateurTendance": 7.16,
#     "dateRapport": 1762342805000,
#     "permutation": 1,
#     "favoris": false,
#     "numPmu1": 1,
#     "grossePrise": false
#   },
#   "urlCasaque": "https://www.pmu.fr/back-assets/hippique/casaques/05112025/R1/C1/P1.png",
#   "commentaireApresCourse": {
#     "texte": "A été sanctionné dans la phase finale alors qu'il n'était pas menaçant.",
#     "source": "GENY"
#   },
#   "eleveur": "M. Jean Louis QUINTON",
#   "allure": "TROT",
#   "avisEntraineur": "NEUTRE"
# }