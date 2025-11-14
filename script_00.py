import requests
import pandas as pd
from datetime import datetime

def fetch_and_merge_race_data(url_programme, url_participants, url_performances, reunion_num, course_num):
    """
    Récupère les données d'une course depuis 3 endpoints PMU, les fusionne
    et les retourne sous forme de DataFrame pandas.

    Args:
        url_programme (str): URL de l'API pour le programme complet de la journée.
        url_participants (str): URL de l'API pour la liste des participants de la course.
        url_performances (str): URL de l'API pour l'historique des performances.
        reunion_num (int): Le numéro de la réunion à cibler (ex: 1 pour R1).
        course_num (int): Le numéro de la course à cibler (ex: 1 pour C1).

    Returns:
        pandas.DataFrame: Un DataFrame où chaque ligne est un cheval de la course,
                          avec toutes les informations fusionnées. Retourne None en cas d'erreur.
    """
    try:
        # --- ÉTAPE 1 : TÉLÉCHARGEMENT DES DONNÉES DEPUIS LES URLS ---
        print("1. Téléchargement des données depuis les 3 URL...")
        headers = {'User-Agent': 'Mozilla/5.0'} # Certains APIs requièrent un User-Agent
        
        response_prog = requests.get(url_programme, headers=headers)
        response_prog.raise_for_status()
        programme_journee = response_prog.json()

        response_parts = requests.get(url_participants, headers=headers)
        response_parts.raise_for_status()
        participants_data = response_parts.json()

        response_perfs = requests.get(url_performances, headers=headers)
        response_perfs.raise_for_status()
        performances_data = response_perfs.json()
        print("   => Données téléchargées avec succès.")

    except requests.exceptions.RequestException as e:
        print(f"   => ERREUR : Impossible de récupérer les données. Vérifiez les liens. Détails : {e}")
        return None
    except requests.exceptions.JSONDecodeError:
        print("   => ERREUR : La réponse reçue n'est pas un JSON valide. L'API a peut-être changé.")
        return None

    # --- ÉTAPE 2 : TRAITEMENT ET FUSION DES DONNÉES ---
    print("2. Traitement et fusion des données...")
    
    # Créer un dictionnaire pour un accès rapide à l'historique de chaque cheval
    performances_map = {p['numPmu']: p.get('coursesCourues', []) for p in performances_data.get('participants', [])}

    # Trouver la course cible dans le JSON du programme de la journée
    target_course_data = None
    target_reunion_data = None
    for reunion in programme_journee.get('programme', {}).get('reunions', []):
        if reunion.get('numOfficiel') == reunion_num:
            target_reunion_data = reunion
            for course in reunion.get('courses', []):
                if course.get('numOrdre') == course_num:
                    target_course_data = course
                    break
            break
            
    if not target_course_data:
        print(f"   => ERREUR : Impossible de trouver la course R{reunion_num}C{course_num} dans le programme.")
        return None

    # Extraire les caractéristiques générales de la course
    date_course = datetime.fromtimestamp(programme_journee.get('programme', {}).get('date', 0) / 1000)
    course_features = {
        'race_hippodrome': target_reunion_data.get('hippodrome', {}).get('libelleCourt'),
        'race_distance': target_course_data.get('distance'),
        'race_discipline': target_course_data.get('discipline'),
        'race_allocation': target_course_data.get('montantPrix'),
        'race_nb_partants': target_course_data.get('nombreDeclaresPartants')
    }

    flat_data_list = []
    
    # Boucle sur chaque participant pour créer une ligne de données
    for participant in participants_data.get('participants', []):
        row = {}
        
        # 1. Ajouter les infos de la course (identiques pour tous)
        row.update(course_features)
        
        # 2. Ajouter les infos spécifiques du participant
        row['horse_num'] = participant.get('numPmu')
        row['horse_nom'] = participant.get('nom')
        row['horse_age'] = participant.get('age')
        row['horse_sexe'] = participant.get('sexe')
        row['horse_driver'] = participant.get('driver')
        row['horse_entraineur'] = participant.get('entraineur')
        row['horse_deferrage'] = participant.get('deferre', 'FERRE')
        row['horse_cote'] = participant.get('dernierRapportDirect', {}).get('rapport')
        
        # 3. Ajouter la CIBLE (le résultat)
        place = participant.get('ordreArrivee')
        row['result_place'] = place if place is not None else 0 # 0 pour les non-placés/disqualifiés
        row['result_a_gagne'] = 1 if place == 1 else 0
        row['result_incident'] = participant.get('incident', 'RAS')

        # 4. Feature Engineering simple à partir de l'historique
        cheval_historique = performances_map.get(participant['numPmu'], [])
        
        if cheval_historique:
            last_race = cheval_historique[0]
            date_derniere_course = datetime.fromtimestamp(last_race['date'] / 1000)
            row['hist_jours_depuis_derniere_course'] = (date_course - date_derniere_course).days
            
            perf_cheval = next((p for p in last_race.get('participants', []) if p.get('itsHim')), None)
            
            if perf_cheval:
                row['hist_place_derniere_course'] = perf_cheval.get('place', {}).get('place')
                row['hist_rk_derniere_course'] = perf_cheval.get('reductionKilometrique')
            else:
                 row['hist_place_derniere_course'] = None
                 row['hist_rk_derniere_course'] = None
        else:
            row['hist_jours_depuis_derniere_course'] = None
            row['hist_place_derniere_course'] = None
            row['hist_rk_derniere_course'] = None
        
        flat_data_list.append(row)
        
    print("   => Fusion des données terminée.")
    return pd.DataFrame(flat_data_list)

# --- POINT D'ENTRÉE DU SCRIPT ---
if __name__ == "__main__":
    
    # Les 3 variables contenant les liens pour la course R1C1 du 05/11/2025
    # Vous pouvez changer ces liens pour n'importe quelle autre course.
    
    DATE_COURSE = "05112025"
    REUNION = "R1"
    COURSE = "C1"

    # 1. URL pour les informations générales de toutes les courses du jour
    URL_PROGRAMME_JOURNEE = f"https://online.turfinfo.api.pmu.fr/rest/client/1/programme/{DATE_COURSE}"
    
    # 2. URL pour les informations détaillées des participants de la course cible
    URL_PARTICIPANTS_COURSE = f"https://online.turfinfo.api.pmu.fr/rest/client/61/programme/{DATE_COURSE}/{REUNION}/{COURSE}/participants"
    
    # 3. URL pour l'historique de performance de tous les participants de cette course
    URL_PERFORMANCES_COURSE = f"https://online.turfinfo.api.pmu.fr/rest/client/61/programme/{DATE_COURSE}/{REUNION}/{COURSE}/performances-detaillees/pretty"

    # Appel de la fonction principale
    race_dataframe = fetch_and_merge_race_data(
        url_programme=URL_PROGRAMME_JOURNEE, 
        url_participants=URL_PARTICIPANTS_COURSE, 
        url_performances=URL_PERFORMANCES_COURSE,
        reunion_num=1, # Numéro de la réunion (1 pour R1)
        course_num=1   # Numéro de la course (1 pour C1)
    )

    # Affichage et sauvegarde du résultat
    if race_dataframe is not None:
        print("\n--- DataFrame Final Généré ---")
        
        # Configure pandas pour un affichage complet dans la console
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        
        print(race_dataframe)

        # Sauvegarder le résultat dans un fichier CSV pour une utilisation ultérieure
        try:
            filename = f"dataset_{DATE_COURSE}_{REUNION}_{COURSE}.csv"
            race_dataframe.to_csv(filename, index=False, sep=';', encoding='utf-8-sig')
            print(f"\nDataFrame sauvegardé avec succès dans '{filename}'")
        except Exception as e:
            print(f"\nErreur lors de la sauvegarde du fichier : {e}")