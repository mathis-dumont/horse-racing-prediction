import requests
import pandas as pd
import numpy as np
import xgboost as xgb
import sklearn
import pickle
import sys
import os
import time
import urllib3
from datetime import datetime

# ==========================================
# 0. PRODUCTION CONFIGURATION
# ==========================================
# API Settings
BASE_URL = "https://online.turfinfo.api.pmu.fr/rest/client/1/programme"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Origin": "https://www.pmu.fr",
    "Referer": "https://www.pmu.fr/"
}
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Model Settings
CALIBRATOR_FILE = 'probability_calibrator.pkl' 
ARTIFACTS_FILE = 'model_artifacts.pkl'

# Strategy Settings (The "Sniper")
MIN_ODDS = 5.0
MAX_ODDS = 20.0
MIN_EDGE = 0.05

# ==========================================
# 1. LIVE DATA FETCHER (IN-MEMORY)
# ==========================================
def safe_get(data, key, default=None):
    if isinstance(data, dict): return data.get(key, default)
    return default

def get_shoeing_code(shoeing_raw):
    code = safe_get(shoeing_raw, 'code') if isinstance(shoeing_raw, dict) else shoeing_raw
    if not code: return "FERRE"
    mapping = {
        'DEFERRE_ANTERIEURS': 'DA', 'DEFERRE_POSTERIEURS': 'DP', 'DEFERRE_DES_4': 'D4',
        'PLAQUE_ANTERIEURS': 'PA', 'PLAQUE_POSTERIEURS': 'PP', 'PLAQUE_DES_4': 'P4',
        'PLAQUE_ANTERIEURS_DEFERRE_POSTERIEURS': 'PADP', 'DEFERRE_ANTERIEURS_PLAQUE_POSTERIEURS': 'DAPP'
    }
    return mapping.get(code, "FERRE")

def extract_name(person_data):
    if not person_data: return "Unknown"
    if isinstance(person_data, dict):
        return f"{person_data.get('nom', '')} {person_data.get('prenom', '')}".strip()
    return str(person_data).strip()

def fetch_data(url):
    for _ in range(3): # 3 Retries
        try:
            r = requests.get(url, headers=HEADERS, timeout=5, verify=False)
            if r.status_code == 200: return r.json()
        except: time.sleep(0.5)
    return None

def get_live_runners():
    """Fetches today's race data and returns a DataFrame directly."""
    today = datetime.now()
    date_str = today.strftime('%d%m%Y')
    iso_date = today.strftime('%Y-%m-%d')
    
    print(f" Connecting to PMU API for {date_str}...")
    program = fetch_data(f"{BASE_URL}/{date_str}?specialisation=INTERNET")
    
    if not program or 'programme' not in program:
        print(" API Error: Could not fetch program.")
        return None

    runners_list = []
    
    for reunion in program['programme']['reunions']:
        r_num = reunion['numOfficiel']
        for race in reunion['courses']:
            c_num = race['numOrdre']
            discipline = race.get('discipline', '').upper()
            
            if discipline not in ['ATTELE', 'MONTE']: continue
            
            # Fetch Race Detail
            details = fetch_data(f"{BASE_URL}/{date_str}/R{r_num}/C{c_num}/participants?specialisation=INTERNET")
            if not details or 'participants' not in details: continue
            
            race_runners = []
            for p in details['participants']:
                try:
                    # Odds Logic
                    odds = 1.0
                    if p.get('dernierRapportDirect'): odds = p['dernierRapportDirect'].get('rapport', 1.0)
                    elif p.get('dernierRapportReference'): odds = p['dernierRapportReference'].get('rapport', 1.0)

                    runner = {
                        'program_date': iso_date,
                        'race_id': f"{iso_date}_R{r_num}_C{c_num}",
                        'horse_name': p.get('nom', 'Unknown'),
                        'horse_age': today.year - p.get('anneeNaissance') if p.get('anneeNaissance') else 0,
                        'distance_m': race.get('distance', 0),
                        'declared_runners_count': race.get('nombreDeclaresPartants', 0),
                        'shoeing_status': get_shoeing_code(p.get('deferre')),
                        'driver': extract_name(p.get('driver') or p.get('jockey')),
                        'jockey_name': extract_name(p.get('driver') or p.get('jockey')), # Mapped for model
                        'trainer_name': extract_name(p.get('entraineur')),
                        'career_winnings': safe_get(p.get('gainsParticipant'), 'gainsCarriere', 0),
                        'sex': p.get('sexe', 'M'),
                        'reference_odds': float(odds),
                        'is_debutant': 1 if p.get('musique') == 'Inédit' else 0,
                        'breed': p.get('race', 'TROT'),
                        'discipline': discipline,
                        'race_month': today.month,
                        'race_day_of_week': today.weekday(),
                        'is_clinker': 1 if safe_get(p.get('oeilleres'), 'code') else 0
                    }
                    race_runners.append(runner)
                except: continue
            
            # Feature Engineering (In-Memory)
            if race_runners:
                df_r = pd.DataFrame(race_runners)
                df_r['winnings_rank_in_race'] = df_r['career_winnings'].rank(ascending=False, method='min')
                df_r['odds_rank_in_race'] = df_r['reference_odds'].rank(ascending=True, method='min')
                avg_win = df_r['career_winnings'].mean()
                df_r['relative_winnings'] = df_r['career_winnings'] / avg_win if avg_win > 0 else 0
                df_r['winnings_per_race'] = df_r['career_winnings'] / 10 # Approx
                runners_list.append(df_r)

    if runners_list:
        return pd.concat(runners_list, ignore_index=True)
    return pd.DataFrame()

# ==========================================
# 2. MODEL ENGINE
# ==========================================
def load_engine():
    if not os.path.exists(CALIBRATOR_FILE):
        print(" Error: Model files not found.")
        sys.exit(1)
    
    with open(ARTIFACTS_FILE, "rb") as f: artifacts = pickle.load(f)
    with open(CALIBRATOR_FILE, "rb") as f: calibrator = pickle.load(f)
    return calibrator, artifacts

def prepare_features(df, artifacts):
    features = artifacts['features']
    known_cats = artifacts['categories']
    
    # Handle missing cols
    for col in features:
        if col not in df.columns:
            df[col] = np.nan
            
    X = df[features].copy()
    
    # Strict Category Sync
    for col, categories in known_cats.items():
        if col in X.columns:
            X[col] = X[col].astype('category')
            X[col] = X[col].cat.set_categories(categories)
    return X

# ==========================================
# 3. MAIN RUNTIME
# ==========================================
def main():
    print(f"--- HORSE RACING SNIPER (Production) ---")
    
    # 1. Fetch
    df = get_live_runners()
    if df.empty:
        print(" No races found currently.")
        return

    print(f" Analyzed {len(df)} runners.")

    # 2. Predict
    calibrator, artifacts = load_engine()
    X = prepare_features(df, artifacts)
    
    # Probabilities
    df['proba'] = calibrator.predict_proba(X)[:, 1]
    
    # 3. Rank & Filter
    df['model_rank'] = df.groupby('race_id')['proba'].rank(ascending=False, method='min')
    
    if 'reference_odds' in df.columns:
        df['implied_prob'] = 1 / df['reference_odds']
        df['edge'] = df['proba'] - df['implied_prob']
        
        # --- STRATEGY FILTER ---
        bets = df[
            (df['model_rank'] == 1) &
            (df['edge'] > MIN_EDGE) &
            (df['reference_odds'] >= MIN_ODDS) &
            (df['reference_odds'] < MAX_ODDS)
        ].sort_values(['race_id'], ascending=True)
        
        # 4. Output
        print("\n" + "="*65)
        print(f"RECOMMENDED BETS ({datetime.now().strftime('%H:%M')})")
        print("="*65)
        
        if bets.empty:
            print("No bets satisfy the Sniper criteria right now.")
            print(f"Criteria: Odds {MIN_ODDS}-{MAX_ODDS} | Edge > {MIN_EDGE:.0%}")
        else:
            # Clean Output Table
            cols = ['race_id', 'horse_name', 'reference_odds', 'proba', 'edge', 'shoeing_status']
            display_df = bets[cols].copy()
            display_df['proba'] = (display_df['proba'] * 100).round(1).astype(str) + '%'
            display_df['edge'] = (display_df['edge'] * 100).round(1).astype(str) + '%'
            
            # Print without index for cleaner look
            print(display_df.to_string(index=False))
            print("-" * 65)
            print(f"Total Bets: {len(bets)}")
    else:
        print("Error: Odds data missing.")

if __name__ == "__main__":
    main()