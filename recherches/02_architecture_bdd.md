## Architecture complète des tables

### 1. Table `programme_jour`

Niveau : **un jour de courses**

* `id_programme` : identifiant interne (clé primaire)
* `date_programme` : date du programme (JSON1 : `programme.date`), unique

---

### 2. Table `reunion`

Niveau : **réunion (R1, R2, …)**

* `id_reunion` : identifiant interne
* `id_programme` : lien vers `programme_jour`
* `num_reunion` : numéro officiel de la réunion (JSON1 : `reunions[].numOfficiel`)
* `nature` : DIURNE, NOCTURNE… (JSON1 : `reunions[].nature`)
* `hippodrome_code` : code hippodrome (JSON1 : `reunions[].hippodrome.code`)
* `meteo_temperature` : température (JSON1 : `reunions[].meteo.temperature`)
* `meteo_vent` : direction du vent (JSON1 : `reunions[].meteo.directionVent`)

Contrainte logique : `(id_programme, num_reunion)` doit être unique.

---

### 3. Table `course`

Niveau : **course dans une réunion**

* `id_course` : identifiant interne
* `id_reunion` : lien vers `reunion`
* `num_course` : numéro de la course dans la réunion (JSON1 : champ de type `numOrdre` ou équivalent)
* `discipline` : plat, trot, obstacle… (JSON1 : `reunions[].courses[].discipline`)
* `categorie_course` : handicap, course à conditions, réclamer… (JSON1 : `categorieParticularite`)
* `condition_age` : condition d’âge (JSON1 : `conditionAge`)
* `distance_m` : distance (JSON1 : `distance`)
* `type_piste` : GAZON, PSF, SABLE… (JSON1 : `typePiste`)
* `terrain_libelle` : Bon, Souple, etc. (JSON1 : `penetrometre.intitule`)
* `penetrometre` : valeur numérique (JSON1 : `penetrometre.valeurMesure`)
* `nb_declares` : nombre de partants (JSON1 : `nombreDeclaresPartants`)
* `conditions_texte` : texte libre de conditions (JSON1 : `conditions`)
* `statut_course` : TERMINEE, ANNULEE… (JSON1 : `statut` / `categorieStatut`)
* `ordre_arrivee_brut` : stockage brut de l’ordre d’arrivée (liste JSON) – leakage
* `duree_course` : durée de la course – leakage

Contrainte : `(id_reunion, num_course)` unique.

---

### 4. Table `cheval`

Niveau : **cheval unique**

* `id_cheval` : identifiant interne
* `nom` : nom du cheval
* `sexe` : M, F, H, etc.
* `annee_naissance` : optionnel si dispo
* éventuellement : `id_cheval_pmu` si l’API expose un ID stable

Contrainte possible : `(nom, annee_naissance)` unique si pas d’ID PMU.

---

### 5. Table centrale `participant_course`

Niveau : **cheval dans une course donnée**
C’est la table cœur du dataset.

* `id_participant` : identifiant interne
* `id_course` : lien vers `course`
* `id_cheval` : lien vers `cheval`
* `num_pmu` : dossard (JSON2 : `participants[].numPmu`)
* `age` : âge (JSON2 : `age`)
* `sexe` : rappel au cas où (JSON2 : `sexe`)
* `entraineur` : nom (JSON2 : `entraineur`)
* `driver_jockey` : nom (JSON2 : `driver`)
* `deferrage` : état de déferrage (JSON2 : `deferre`)
* `nb_courses_carriere` : nb de courses (JSON2 : `nombreCourses`)
* `gains_carriere` : gains cumulés (JSON2 : `gainsParticipant.gainsCarriere`)
* `cote_reference` : cote du matin (JSON2 : `dernierRapportReference.rapport`)
* `cote_directe` : cote live (JSON2 : `dernierRapportDirect.rapport`, attention leakage)
* `musique_brute` : la musique telle quelle (JSON2 : `musique`)

Cibles / infos post-course (leakage) :

* `rang_arrivee` : rang final (JSON2 : `ordreArrivee`)
* `incident` : DQ, TOMBE, ARRÊTE… (JSON2 : `incident`)
* `temps_obtenu` : temps du cheval (JSON2 : `tempsObtenu`)
* `reduction_km` : réduction kilométrique (JSON2 : `reductionKilometrique`)
* `commentaire_post_course` : commentaire (JSON2 : `commentaireApresCourse`)
* `avis_entraineur` : avis pré-course (JSON2 : `avisEntraineur`)

Contrainte : `(id_course, num_pmu)` unique.

---

### 6. Table `historique_course_cheval`

Niveau : **perf passée d’un cheval dans une course**

* `id_hist` : identifiant interne
* `id_cheval` : lien vers `cheval`
* `date_course` : date de la course passée (JSON3 : `coursesCourues[].date`)
* `discipline` : (JSON3 : `discipline`)
* `allocation` : allocation totale (JSON3 : `allocation`)
* `distance_m` : distance (JSON3 : `distance`)
* `temps_premier` : temps du vainqueur (JSON3 : `tempsDuPremier`)
* `place` : place du cheval (JSON3 : `participants[].place.place`)
* `statut_arrivee` : PLACE, NON_CLASSE, DISQUALIFIE… (JSON3 : `statusArrivee`)
* `poids_jockey` : poids porté (JSON3 : `poidsJockey`)
* `corde` : numéro de corde / stalle (JSON3 : `corde`)
* `reduction_km` : réduction kilométrique (JSON3 : `reductionKilometrique`)
* `distance_parcourue` : distance réellement parcourue (JSON3 : `distanceParcourue`)

---

### 7. Table `pari_course`

Niveau : **type de pari sur une course**

* `id_pari` : identifiant interne
* `id_course` : lien vers `course`
* `type_pari` : SIMPLE_GAGNANT, TRIO, MULTI… (JSON4 : `typePari`)
* `famille_pari` : Simple, Couple, etc. (JSON4 : `famillePari`)
* `mise_base` : mise de base (JSON4 : `miseBase`)
* `rembourse` : pari remboursé / annulé (JSON4 : `rembourse`)

---

### 8. Table `rapport_pari`

Niveau : **rapport pour une combinaison**

* `id_rapport` : identifiant interne
* `id_pari` : lien vers `pari_course`
* `combinaison` : ex "7", "7-3" (JSON4 : `rapports[].combinaison`)
* `dividende` : dividende (JSON4 : `dividende`)
* `dividende_pour_1e` : dividende pour 1€ (JSON4 : `dividendePourUnEuro`)
* `nb_gagnants` : nombre de tickets gagnants (JSON4 : `nombreGagnants`)

---

### 9. Table `prediction`

Niveau : **prédiction du modèle pour un cheval dans une course**

* `id_prediction` : identifiant interne
* `id_participant` : lien vers `participant_course`
* `modele_version` : identifiant du modèle utilisé (string)
* `proba_gagnant` : probabilité prédite de gagner
* `proba_place_top3` : probabilité d’être dans le top 3
* `created_at` : date/heure de la prédiction

---

### 10. (Optionnel mais très utile) Tables `raw_*`

Pour ne jamais perdre d’info, tu peux avoir 4 tables brutes :

* `raw_programme`
* `raw_participants`
* `raw_performances`
* `raw_rapports`

Dans chacune :

* un identifiant
* `date_programme`
* éventuellement `id_course` ou clés utiles
* une colonne `payload_json` avec **le JSON brut complet**.