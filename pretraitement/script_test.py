import json
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

# --- CONFIGURATION (Identique) ---
# ... (PRE_RACE_FEATURES inchangé) ...

# NOTE: Pour garder le script complet et exécutable, je réinsère la configuration ici:
PRE_RACE_FEATURES = {
    'course': [
        'discipline', 'specialite', 'distance', 'typePiste', 'corde',
        'categorieParticularite', 'conditionSexe', 'conditionAge', 'libelle', 'parcours',
        'nombreDeclaresPartants', 'montantPrix', 
        'montantOffert1er', 'montantOffert2eme', 'montantOffert3eme', 'montantOffert4eme', 'montantOffert5eme',
        'hippodrome.code', 'pays.code', 'pays.libelle', 'nature', 'meteo.temperature', 
        'meteo.forceVent', 'meteo.nebulositeLibelleCourt',
        'penetrometre.intitule', 'penetrometre.valeurMesure',
    ],
    'participant': [
        'idCheval', 'nom', 'numPmu', 'age', 'sexe', 'race', 'robe.code', 
        'proprietaire', 'entraineur', 'driver', 'driverChange', 'indicateurInedit',
        'oeilleres', 'deferre', 
        'handicapDistance', 
        'handicapPoids', 
        'musique',
        'nombreCourses', 'nombreVictoires', 'nombrePlaces', 'nombrePlacesSecond', 
        'nombrePlacesTroisieme',
        'gainsParticipant.gainsCarriere', 'gainsParticipant.gainsVictoires', 
        'gainsParticipant.gainsPlace', 'gainsParticipant.gainsAnneeEnCours',
        'gainsParticipant.gainsAnneePrecedente',
        'nomPere', 'nomMere', 
        'dernierRapportReference.rapport',
        'avisEntraineur'
    ]
}


# --- ÉTAPE 1: FONCTIONS D'INGESTION ET D'APLATISSEMENT (MOCK DATA CORRIGÉ) ---

def generate_mock_data(num_observations=1000):
    """
    Simule la sortie de la fonction load_and_join_data.
    CORRECTION : Assure que 'target_rang_arrivee' est inclus dans la liste de données.
    """
    data = []
    
    for i in range(num_observations):
        discipline = np.random.choice(['ATTELE', 'PLAT', 'HAIE'])
        is_trot = (discipline == 'ATTELE')
        distance = np.random.randint(1800, 3000)
        type_piste = 'PSF' if discipline == 'PLAT' else ('GAZON' if discipline == 'HAIE' else None)
        
        if type_piste == 'GAZON':
            terrain_intitule = np.random.choice(['Souple', 'Bon', 'Lourd'])
            penetrometre_valeur = np.random.uniform(2.5, 4.5)
        else:
            terrain_intitule = None
            penetrometre_valeur = None
            
        if discipline != 'ATTELE':
             condition_age = np.random.choice(['3 ans', '4 ans et plus', 'Tous ages'])
        else:
             condition_age = None 
        
        # Cible (Simulation post-course)
        rank = np.random.randint(1, 17) 
        target_rang_arrivee = rank if rank <= 16 else None # L'info brute de rang
        gains_carriere = np.random.randint(100000, 5000000) 
        
        record = {
            # A. Identification
            'id_course_global': f"2024-06-01-R1-C{i%8+1}",
            'numPmu': i % 16 + 1,
            'idCheval': f"CH{np.random.randint(1000, 9999)}",
            
            # B. Contexte de la Course (JSON 1)
            'discipline': discipline,
            'distance': distance,
            'typePiste': type_piste,
            'pays.libelle': 'FRANCE', 
            'montantOffert1er': 50000,
            'montantOffert2eme': 20000,
            'montantOffert3eme': 10000,
            'montantOffert4eme': 5000,
            'montantOffert5eme': 2500,
            'meteo.temperature': np.random.uniform(10, 30),
            'meteo.forceVent': np.random.uniform(0, 15),
            'conditionAge': condition_age, 
            
            'penetrometre.intitule': terrain_intitule,
            'penetrometre.valeurMesure': penetrometre_valeur,
            
            # C/D. Profil & Setup (JSON 2)
            'age': np.random.randint(3, 10),
            'entraineur': f"E{np.random.randint(1, 20)}",
            'driver': f"D{np.random.randint(1, 30)}",
            'deferre': np.random.choice(['P', 'F', 'D4', None]) if is_trot else None,
            'handicapDistance': np.random.choice([0, 25, 50]) if is_trot else 0,
            'driverChange': np.random.choice([True, False]),
            'musique': "1D2P3A", 
            'nombreCourses': np.random.randint(0, 50),
            'nombreVictoires': np.random.randint(0, 10),
            'gainsParticipant.gainsCarriere': gains_carriere,
            'gainsParticipant.gainsVictoires': int(gains_carriere * 0.5),
            'gainsParticipant.gainsPlace': int(gains_carriere * 0.3),
            'dernierRapportReference.rapport': np.random.randint(200, 5000),
            
            # Z. CIBLE BRUTE : C'est ce champ qui manquait d'être explicitement inséré
            'target_rang_arrivee': target_rang_arrivee 
        }
        data.append(record)
            
    df = pd.DataFrame(data)
    
    # Création de la cible binaire à partir de l'info brute
    df['target_est_gagnant'] = (df['target_rang_arrivee'] == 1).astype(int)
    
    # Sécurité anti-leakage : Suppression immédiate de la colonne brute (post-course)
    return df.drop(columns=['target_rang_arrivee'], errors='ignore')


# --- ÉTAPE 2: NETTOYAGE ET FEATURE ENGINEERING DES DONNÉES BRUTES Saines (Inchangé) ---
# ... [process_features_for_ml fonction inchangée] ...

def process_features_for_ml(df):
    
    RENAME_MAP = {
        'dernierRapportReference.rapport': 'cote_reference',
        'penetrometre.intitule': 'terrain_libelle',
        'penetrometre.valeurMesure': 'penetrometre_valeur',
        'gainsParticipant.gainsCarriere': 'gains_carriere',
        'gainsParticipant.gainsVictoires': 'gains_victoires',
        'gainsParticipant.gainsPlace': 'gains_place',
        'gainsParticipant.gainsAnneeEnCours': 'gains_annee_courante',
        'gainsParticipant.gainsAnneePrecedente': 'gains_annee_precedente',
        'meteo.temperature': 'temperature',
        'pays.libelle': 'pays_libelle',
        'meteo.forceVent': 'forceVent',
        'meteo.nebulositeLibelleCourt': 'nebulosite',
    }

    cols_to_rename = {k: v for k, v in RENAME_MAP.items() if k in df.columns}
    df = df.rename(columns=cols_to_rename)
    
    df['cote_reference'] = df['cote_reference'].fillna(0) / 100.0
    
    df['deferre'] = df['deferre'].fillna('NON_DEFERRE').astype(str)
    df['typePiste'] = df['typePiste'].fillna('NON_APPLICABLE').astype(str)
    
    # Assurer que les colonnes renommées existent avant d'appeler fillna
    if 'terrain_libelle' in df.columns:
        df['terrain_libelle'] = df['terrain_libelle'].fillna('NON_MESURE').astype(str)
    
    df['conditionAge'] = df['conditionAge'].fillna('TOUS_AGES_STD').astype(str)
    df['musique'] = df['musique'].astype(str)
    
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) 
        
    df['ratio_victoires_carriere'] = df['nombreVictoires'] / df['nombreCourses'].replace(0, 1)
    df['gains_par_course'] = df['gains_carriere'] / df['nombreCourses'].replace(0, 1)
    df['musique_length'] = df['musique'].apply(len)
    
    cols_to_exclude = [
        'id_course_global', 'idCheval', 'nom', 'target_est_gagnant', 
        'musique', 'nombreCourses', 'nombreVictoires', 'gains_carriere', 'gains_victoires', 'gains_place',
        'libelle', 'parcours', 'avisEntraineur', 'nomPere', 'nomMere', 
        'gains_annee_courante', 'gains_annee_precedente', 
        'montantOffert1er', 'montantOffert2eme', 'montantOffert3eme', 'montantOffert4eme', 'montantOffert5eme'
    ]
    
    final_features = [col for col in df.columns if col not in cols_to_exclude]
    
    return df, final_features

# --- ÉTAPE 3: MODÉLISATION (Inchangé) ---
def run_model(df_features_cible, final_features):
    
    X = df_features_cible[final_features]
    Y = df_features_cible['target_est_gagnant']
    
    X_train, X_test, Y_train, Y_test = train_test_split(
        X, Y, test_size=0.2, random_state=42, stratify=Y
    )
    
    numerical_features = X.select_dtypes(include=np.number).columns.tolist()
    
    if 'numPmu' in numerical_features:
        numerical_features.remove('numPmu') 
        
    categorical_features = X.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
    categorical_features.append('numPmu') 

    print(f"\n--- Statistiques du Dataset ---")
    print(f"Features numériques ML: {numerical_features}")
    print(f"Features catégorielles ML: {categorical_features}")

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numerical_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
        ],
        remainder='drop'
    )
    
    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', LogisticRegression(solver='liblinear', class_weight='balanced', random_state=42, max_iter=200))
    ])

    print("\nDébut de l'entraînement...")
    model_pipeline.fit(X_train, Y_train)
    
    Y_pred_proba = model_pipeline.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(Y_test, Y_pred_proba)
    
    print("--- Résultats de la Prédiction ---")
    print(f"AUC (Probabilité de finir 1er): {auc:.4f}")
    
    results = X_test.copy()
    results['Proba_Gagner'] = Y_pred_proba
    results['True_Gagnant'] = Y_test
    
    print("\nExemple de prédictions (Proba de finir 1er) :")
    print(results[['numPmu', 'discipline', 'cote_reference', 'Proba_Gagner', 'True_Gagnant']].sort_values(by='Proba_Gagner', ascending=False).head(5))
    
    return model_pipeline


# --- EXÉCUTION PRINCIPALE ---

if __name__ == "__main__":
    
    print("Démarrage de la pipeline d'ingestion et de modélisation avec les features complètes...")
    
    df_brut = generate_mock_data(num_observations=5000)
    
    df_clean, features_ml = process_features_for_ml(df_brut)
    
    final_model = run_model(df_clean, features_ml)