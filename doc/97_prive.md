
## 11) Notes pour plus tard
* lien du discord : https://discord.gg/8JnDw2Dd (valable 7 jours)

* video pour trouver les json de paris turf : https://www.youtube.com/watch?v=AOiVRQg1iVM

* Site à explorer : https://turfmining.fr/constitution-des-datasets/

* Pour récupérer en live les cotes zeturf : https://www.zeturf.fr/fr/course/2025-04-08/R4C7-vincennes-prix-palma/api/cotes

* https://duckdb.org/ : permet de faire de l'analyse de données relativement facilement. On peut lui donner à manger du csv, json, MySQL

* tous les sites ont le mm fournisseur de cote

* pour une date donnée : https://turfinfo.api.pmu.fr/rest/client/1/programme/05112025

* script pour récupérer en "live" les cotes pmu : 
```python
import requests
import json
import pandas as pd
from datetime import datetime, timedelta

def download_course_id(course_id, specialisation):
    if specialisation not in ["INTERNET", "OFFLINE"]:
        raise ValueError("La spécialisation doit être 'INTERNET' ou 'OFFLINE'")
    
    participants_url = f"https://online.turfinfo.api.pmu.fr/rest/client/1/programme/{course_id}/participants?specialisation={specialisation}"
    
    # Fetch participants data
    response = requests.get(participants_url)
    participants_data = response.json()
    participants = participants_data.get("participants", [])
    
    df_ap = pd.DataFrame({
        "heure_direct": [p["dernierRapportDirect"]["dateRapport"] for p in participants],
        "num_pmu": [p["numPmu"] for p in participants],
        "cote": [str(p["dernierRapportDirect"]["rapport"]).replace('.', ',') for p in participants]
    })
    
    df_ap["course_id"] = course_id
    df_ap["heure_direct"] = pd.to_datetime(df_ap["heure_direct"].dropna().unique()[0] / 1000 - 3600, unit='s').strftime("%H:%M:%S")
    
    df_ap.fillna(0, inplace=True)
    
    return df_ap

# Formulaire pour choisir la réunion et la course
reunion = input("Entrez la réunion (ex: 1 pour R1) : ")
course = input("Entrez le numéro de la course (ex: 1 pour C1) : ")

date_course = datetime.now().strftime("%d%m%Y")  # Prend automatiquement la date du jour

# Formatage des inputs
reunion = f"R{reunion.strip()}"
course = f"C{course.strip()}"

course_id = f"{date_course}/{reunion}/{course}"

# Choix des cotes
specialisation_choice = input("Cotes Offline ou Online ? (Entrez '1' pour OFFLINE ou '2' pour ONLINE) : ")
while specialisation_choice not in ["1", "2"]:
    print("Choix invalide. Veuillez entrer '1' pour OFFLINE ou '2' pour ONLINE.")
    specialisation_choice = input("Choisissez la spécialisation (1 pour OFFLINE, 2 pour ONLINE) : ")

specialisation = "OFFLINE" if specialisation_choice == "1" else "INTERNET"

# Exécution du script
df_cotes = download_course_id(course_id, specialisation)
#print(df_cotes)
print(df_cotes.to_string(index=False))
df_cotes.to_csv("resultats.csv", index=False)
df_cotes.to_excel("resultats.xlsx", index=False)
print("Vous pouvez retrouver les cotes de la course sélectionné dans les fichiers csv et xlsx généré dans le dossier racine.")
```