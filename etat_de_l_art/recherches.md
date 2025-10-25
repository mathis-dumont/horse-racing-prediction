# Comprendre les courses hippiques en France

## 1) C’est quoi une course hippique ?

Des chevaux s’affrontent sur une piste ; le premier à franchir le poteau gagne. Une **réunion** rassemble plusieurs **courses** sur une même demi-journée dans un **hippodrome**. Selon la discipline, le cheval est **monté** (jockey) ou **trotte** en tirant un **sulky** (petite voiture, driver).

---

## 2) Qui organise les courses en France ?

Deux grandes entités encadrent officiellement la filière :

* **Le Trot** (Société d’encouragement à l’Élevage du Trotteur Français) pour les courses de trot.
* **France Galop** pour les courses de galop (plat et obstacles).

Elles fixent les règles sportives, la programmation et contribuent à l’organisation des réunions.

---

## 3) Les disciplines 

* **Trot** : le cheval doit **rester à l’allure du trot**. Un départ ou une allure au **galop** constitue une **faute** qui peut entraîner une **disqualification** si elle n’est pas corrigée très vite.

  * **Trot attelé** : le cheval tire un **sulky** où est assis le **driver**.
  * **Trot monté** : le cheval est **monté** par un jockey (sans sulky).
* **Galop** :

  * **Plat** : aucune barrière, c’est la course “pure vitesse/endurance”.
  * **Obstacles** : trois familles — **haies** (petits obstacles), **steeple-chase** (obstacles plus hauts) et **cross-country** (parcours longs avec obstacles dits “naturels”). Une **chute** élimine logiquement le cheval.

---

## 4) Ce qu’on lit dans un programme de course

Pour chaque cheval : **numéro de départ**, **nom**, **jockey/driver**, **entraîneur**, **dernières performances**, **distance**, **état de la piste**, **nombre de partants**, et **cote** (estimation du marché). La cote **évolue** jusqu’au départ.

---

## 5) Les types de paris 

### Paris “simples”

* **Simple gagnant** : trouver **le vainqueur**.
* **Simple placé** : votre cheval doit finir **dans les premiers** (souvent top 3 ; si **< 8 partants**, souvent top 2).
* **Simple 2e** : votre cheval doit finir **exactement 2e**.
* **Simple 4e** : votre cheval doit finir **dans les 4 premiers** (quand l’offre existe).

### Paris “combinés” 

* **Couplé gagnant** : les **deux premiers**, dans **n’importe quel ordre**.
* **Couplé placé** : **deux chevaux** sur le **podium**, peu importe l’ordre.
* **Couplé ordre** : **les deux premiers** dans le **bon ordre**.
* **2/4** : **deux chevaux** parmi les **quatre premiers**.
* **Trio/Tiercé/Quarté/Quinté+** : trouver **3/4/5 premiers**, en **désordre** ou **dans l’ordre** selon la formule. Le **Quinté+** (les 5 premiers, souvent avec variantes) est mythique car **difficile** mais potentiellement **très rémunérateur**.

> Les **noms** varient selon les opérateurs : ce que le **PMU** appelle « **Couplé** » peut s’appeler « **Jumelé** » sur **Zeturf** ou « **Duo** » sur **Betclic**. L’**idée** reste la même.

> Règle générale : **plus le pari est complexe**, **plus le gain potentiel** est élevé… et **plus la probabilité de réussite** diminue.

---

## 6) Les **cotes** : comment les lire et **quand** les regarder ?

La **cote** reflète l’**opinion du marché** sur les chances d’un cheval. Plus elle est **basse**, plus le cheval est **favori** ; plus elle est **haute**, plus c’est un **outsider**.
Dans une journée type, on observe plusieurs **moments clés** où les mises arrivent :

1. **Début de journée / pause déjeuner** : ceux qui n’auront pas le temps plus tard placent leurs paris d’avance.
2. **Environ 30 min avant la course** : la course précédente se termine, les parieurs se reportent sur la suivante.
3. **Entre ~12 et 3 min** : on regarde les **heats/canters** et on écoute les **interviews** (chaîne Equidia, réseaux) avant de se décider.
4. **Entre ~3 min et le départ** : derniers regards sur les chevaux en piste ; **grosses mises** possibles, souvent par des parieurs plus expérimentés qui **attendent le maximum d’information**.

> D’un point de vue pratique, **beaucoup de volume** arrive **entre ~12 minutes et le départ**. Les mises les plus **tardives** peuvent parfois **déplacer fortement** les cotes.

---

## 7) Attention

* **Rumeurs** : beaucoup de courses de plat sont truquées

---

## 8) Périmètre

* **Périmètre de départ** : se concentrer sur le **trot**, en particulier le **trot monté**, réputé plus **lisible** pour initier une approche.

---

## 9) Lexique 

* **Réunion** : ensemble des courses d’une demi-journée dans un hippodrome.
* **Partants / Non-partant** : chevaux au départ / cheval retiré avant la course.
* **Favori / Outsider** : cheval attendu / cheval moins attendu.
* **Cote** : estimation du marché sur les chances d’un cheval (évolue jusqu’au départ).
* **Trot attelé / monté** : attelé = sulky + driver ; monté = jockey en selle.
* **Plat / Obstacles** : sans barrière / avec haies, steeple-chase, cross-country.
* **Disqualification (trot)** : faute d’allure (galop) non corrigée rapidement.
* **Quinté+** : trouver les **cinq premiers** (formule emblématique et difficile).

---

## 10) Paroles d'experts
* La **cote** est le reflet de la  "Vox populi", elle te servira à arbitrer si une course vaut le coup d'être jouer

* PMU, ZTurf : prennent un gros %
* Geny : petit % (là où il faut parier)

---

## 11) Notes pour plus tard


https://duckdb.org/ : permet de faire de l'analyse de données relativement facilement. On peut lui donner à manger du csv, json, MySQL

script pour récupérer en "live" les cotes pmu : 
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