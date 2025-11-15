import json
import sys
from pathlib import Path


def truncate_root_participants(data, max_participants_to_keep=3):
    """
    Cas spécial pour le JSON des PERFORMANCES :
    - On tronque UNIQUEMENT la liste data["participants"] au niveau racine.
    - On laisse toutes les autres listes INTACTES
      (coursesCourues, participants des courses passées, etc.).
    """
    if isinstance(data, dict) and "participants" in data and isinstance(data["participants"], list):
        # Copie superficielle pour éviter de modifier l'objet original (optionnel)
        data = dict(data)
        data["participants"] = data["participants"][:max_participants_to_keep]
    return data


def truncate_lists_selective(obj, max_items=3, parent_key=None, allow_root_truncation=True):
    """
    Troncature SÉLECTIVE et RÉCURSIVE pour les JSON de type 'programme',
    'participants', 'rapports', etc.

    - On parcourt récursivement tout l'objet JSON.
    - Pour chaque LISTE :
        * Si sa clé parente est 'critique' (structurelle), on NE TRONQUE PAS.
        * Si c'est une liste RACINE (parent_key=None) et que allow_root_truncation=False,
          on NE TRONQUE PAS.
        * Sinon, on tronque la liste à max_items éléments.
    - Pour les dicts, on propage la clé courante comme parent_key aux valeurs.
    - Les valeurs simples sont laissées telles quelles.
    """

    # Listes structurelles (qu'on ne veut pas tronquer)
    CRITICAL_LIST_KEYS = {
        "reunions",
        "courses",
        "paris",
        "ordreArrivee",
        "rapports",        # important pour garder tous les rapports d'un pari
        "cagnottes",
        "parisEvenement",
    }

    # Cas des listes
    if isinstance(obj, list):
        # Liste sous une clé structurelle -> on la garde complètement
        if parent_key in CRITICAL_LIST_KEYS:
            return [truncate_lists_selective(item, max_items, parent_key, allow_root_truncation)
                    for item in obj]

        # Liste racine (parent_key == None)
        if parent_key is None and not allow_root_truncation:
            # Exemple typique : JSON de rapports, où la racine est la liste des types de paris
            return [truncate_lists_selective(item, max_items, parent_key, allow_root_truncation)
                    for item in obj]

        # Liste non critique -> on tronque à max_items
        return [truncate_lists_selective(item, max_items, parent_key, allow_root_truncation)
                for item in obj[:max_items]]

    # Cas des dictionnaires
    elif isinstance(obj, dict):
        new_dict = {}
        for key, value in obj.items():
            # On passe la clé courante comme parent_key à la valeur
            new_dict[key] = truncate_lists_selective(value, max_items, parent_key=key,
                                                     allow_root_truncation=allow_root_truncation)
        return new_dict

    # Valeur simple (str, int, float, bool, None)
    else:
        return obj


def process_file(input_path: Path, max_items=3):
    print(f"\nTraitement de {input_path}...")

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    stem_lower = input_path.stem.lower()

    # 1) Cas spécial : JSON de PERFORMANCES
    if "performances" in stem_lower:
        print("  → Détection : JSON de performances.")
        print("    Troncature UNIQUEMENT de la liste racine 'participants'.")
        truncated = truncate_root_participants(data, max_participants_to_keep=max_items)

    else:
        # 2) JSON génériques (programme / participants / rapports / autres)
        #    On utilise la troncature sélective.
        allow_root_truncation = True

        # Cas particulier des JSON de RAPPORTS :
        # racine = liste de types de paris → on NE veut PAS tronquer cette liste.
        if "rapport" in stem_lower or "rapports" in stem_lower:
            print("  → Détection : JSON de rapports.")
            print("    Aucune troncature sur la liste racine ni sur les listes 'rapports'.")
            allow_root_truncation = False
        else:
            print("  → Détection : JSON générique (programme/participants/autres).")
            print("    Troncature sélective (hors listes structurelles).")

        truncated = truncate_lists_selective(data, max_items=max_items,
                                             parent_key=None,
                                             allow_root_truncation=allow_root_truncation)

    output_path = input_path.with_name(input_path.stem + f"_sample{input_path.suffix}")
    with output_path.open("w", encoding="utf-8") as f:
        # ✨ JSON compact : aucune indentation, aucun espace inutile
        json.dump(truncated, f, ensure_ascii=False, separators=(',', ':'))

    print(f"  → Fichier échantillonné écrit dans : {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage : python sample_pmu_jsons.py fichier1.json fichier2.json ...")
        print("Exemple :")
        print("  python sample_pmu_jsons.py programme_05112025.json participants_R1_C1.json "
              "performances_R1_C1.json rapports_R1_C1.json")
        sys.exit(1)

    # Nombre max d'éléments pour les listes NON critiques
    max_items = 3

    for path_str in sys.argv[1:]:
        path = Path(path_str)
        if not path.exists():
            print(f"⚠️  Fichier introuvable : {path}")
            continue
        process_file(path, max_items=max_items)


if __name__ == "__main__":
    main()
