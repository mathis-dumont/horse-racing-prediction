---

## ✅ Maintenant : quoi faire pas à pas (plan pour débutant)

Je te propose un chemin **simple et progressif**. Tu pourras cocher au fur et à mesure.

---

### Étape 0 – Organisation du projet

1. Créer un dossier de projet sur ton PC.
2. Créer un repo Git (et le pousser plus tard sur GitHub).
3. Noter dans un fichier texte les 10 tables ci-dessus (pour les avoir sous les yeux).

---

### Étape 1 – Créer la base & les tables

1. Choisir ton hébergeur Postgres (ex : Supabase / Neon).
2. Créer une nouvelle base de données.
3. Créer les tables **dans l’ordre des dépendances** :

   * `programme_jour`
   * `reunion`
   * `course`
   * `cheval`
   * `participant_course`
   * `historique_course_cheval`
   * `pari_course`
   * `rapport_pari`
   * `prediction`
   * (optionnel) `raw_*`
4. Vérifier que :

   * les clés étrangères sont bien en place (ex : `id_course` pointe vers `course`)
   * tu n’as pas d’erreurs de type / de nom.

*À ce stade, tu n’écris toujours pas de ML, tu construis juste ta “maison de données”.*

---

### Étape 2 – Comprendre et valider les JSON

1. Récupérer **un exemple réel** des 4 JSON du PMU pour un jour de courses (en local).
2. Ouvrir chaque JSON dans un visualiseur (VS Code, etc.) :

   * repérer les chemins que tu as listés (ex : `reunions[].courses[]`).
3. Vérifier que pour un même jour :

   * tu peux identifier clairement `date_programme`
   * `num_reunion` et `num_course` sont bien présents
   * `num_pmu` est bien là pour les participants
4. Noter sur un papier ou un petit schéma :

   * **comment tu vas passer** de JSON1 → `id_course`
   * puis JSON2/4 → reprise de la même course via `num_reunion`, `num_course`, `num_pmu`.

---

### Étape 3 – Ingestion d’un seul jour de données

#### 3A. Remplir `programme_jour`, `reunion`, `course` (JSON 1)

1. Choisir une date de programme.
2. À partir du JSON1 :

   * créer une entrée dans `programme_jour` pour la date.
   * pour chaque `reunion` :

     * créer une entrée dans `reunion` liée au `programme_jour`.
   * pour chaque `course` :

     * créer une entrée dans `course` liée à la bonne `reunion`.

Objectif :
👉 Être capable de dire : “pour telle date, telle réunion, telle course, j’ai un `id_course` en base”.

---

#### 3B. Remplir `cheval` et `participant_course` (JSON 2)

1. Prendre le JSON2 du même jour.
2. Pour chaque `participant` :

   * retrouver la bonne `course` en combinant :

     * `date_programme` + `num_reunion` + `num_course`
   * vérifier si le cheval existe déjà dans `cheval` (via son nom / id pmu) :

     * s’il n’existe pas → le créer
   * créer une entrée dans `participant_course` avec :

     * les infos du jour (age, driver, déferrage, cotes…)
     * les cibles (rang_arrivee, incident, etc.)

Objectif :
👉 Être capable de faire une requête “donne-moi tous les participants de la course X” directement en base.

---

#### 3C. Remplir `historique_course_cheval` (JSON 3)

1. Prendre le JSON3 (performances).
2. Pour chaque cheval/participant dans le JSON3 :

   * identifier le cheval dans ta table `cheval`
   * pour chaque `coursesCourues[]` :

     * créer une ligne `historique_course_cheval` avec les champs que tu as listés.

Objectif :
👉 Être capable plus tard de calculer, pour un cheval donné, ses stats historiques en lisant cette table.

---

#### 3D. Remplir `pari_course` et `rapport_pari` (JSON 4)

1. Prendre le JSON4 (rapports).
2. Pour chaque bloc (type de pari) :

   * retrouver la `course` concernée
   * créer une ligne dans `pari_course`.
3. Pour chaque `rapport` :

   * créer une ligne dans `rapport_pari` :

     * si `type_pari = SIMPLE_GAGNANT`, tu sauras plus tard relier `combinaison` (numéro) à `participant_course.num_pmu`.

Objectif :
👉 Garder les rapports pour faire des analyses de rentabilité plus tard (pas nécessaire pour le premier modèle).

---

### Étape 4 – Vérifier que tout se relie bien

1. Faire mentalement ou dans un outil (ex : interface SQL) des requêtes comme :

   * “Tous les participants de la course C1 de la réunion R1 à la date D.”
   * “Toutes les courses d’un jour donné.”
2. Vérifier :

   * que les `id_course` sont cohérents
   * que chaque `participant_course` pointe bien vers une `course` et un `cheval`.

Si ça marche pour **un jour**, tu pourras ensuite généraliser à plusieurs jours, puis plusieurs années.

---

### Étape 5 – Première extraction “dataset ML”

1. Décider d’une cible simple : par exemple `est_gagnant` (rang_arrivee == 1).
2. Construire (en pseudo) une requête qui donne :

   * les colonnes de `course` (contexte)
   * les colonnes de `participant_course` (cheval-dans-course)
   * la cible dérivée de `rang_arrivee`
3. Exporter ce résultat (en pandas plus tard) pour un premier jeu de données.

Objectif :
👉 Avoir une première “table à plat” 1 ligne = 1 cheval dans 1 course, prête pour jouer avec un petit modèle.

---

### Étape 6 – Documentation minimale

1. Écrire un petit fichier `docs.md` ou `README` où tu expliques :

   * quelles tables existent
   * ce que contient chaque table
   * comment tu relies les JSON PMU à ces tables.

Ça t’évitera de te perdre dans 1 mois 😉

---

Quand tu veux, on peut prendre l’une de ces étapes (par exemple **Étape 3A ingestion de JSON1**) et je te la détaille en version “pseudo-algo débutant” genre :

> 1. ouvrir le fichier JSON
> 2. parcourir les réunions
> 3. insérer dans telle table, etc.

Sans code dans un premier temps, juste la logique.
