# Analyse de Features Brutes

## 1. Inventaire des features brutes par JSON

### 1.1 Programme du jour (JSON 1) 
https://online.turfinfo.api.pmu.fr/rest/client/1/programme/05112025

> Notation générique : `reunions[]` = une réunion, `courses[]` = une course dans une réunion.

| Chemin JSON | Description | Type | Niveau | Rôle | Correction / Note de Conditionnalité |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `programme.date` | Date du programme (jour de courses). | Date/Heure | Programme | Explicatif / ID de journée | **OK** |
| `reunions[].numOfficiel` | Numéro officiel de la réunion (R1, R2…). | Int | Réunion | ID / Explicatif | **OK** |
| `reunions[].nature` | Nature de la réunion (DIURNE, NOCTURNE…). | Catégoriel | Réunion | Explicatif | **OK** |
| `reunions[].hippodrome.code` | Code court de l’hippodrome. | Catégoriel | Réunion | Explicatif | **OK** |
| `reunions[].meteo.temperature` | Température prévue/mesurée. | Float | Réunion | Explicatif | **OK** |
| `reunions[].meteo.directionVent` | Direction du vent. | Catégoriel | Réunion | Explicatif | **OK** |
| `reunions[].courses[].typePiste` | Type de piste (GAZON, PSF, SABLE…). | Catégoriel | Course | Explicatif | **Conditionnel.** Absent pour certaines courses. |
| `reunions[].courses[].categorieParticularite` | Catégorie de course (HANDICAP, COURSE\_A\_CONDITIONS, RECLAMER, AUTOSTART…). | Catégoriel | Course | Explicatif | **OK** |
| `reunions[].courses[].conditionAge` | Condition d’âge. | Texte libre | Course | Explicatif | **Conditionnel.** Absent pour certaines courses. |
| `reunions[].courses[].nombreDeclaresPartants` | Nombre de chevaux déclarés partants. | Int | Course | Explicatif | **OK** |
| `reunions[].courses[].conditions` | Texte libre détaillant les conditions (gains maximaux, reculs, engagements). | Texte libre | Course | Explicatif | **OK** |
| `reunions[].courses[].penetrometre.valeurMesure` | Valeur numérique du pénétromètre. | Float | Course | Explicatif | **Très Conditionnel.** Souvent uniquement sur Herbe. |
| `reunions[].courses[].penetrometre.intitule` | Libellé du terrain (Bon, Souple, Très lourd…). | Catégoriel | Course | Explicatif | **Conditionnel.** Présent pour de nombreuses surfaces (PSF, Herbe), mais pas garanti. |
| `reunions[].courses[].paris[].codePari` | Code du type de pari (SIMPLE\_GAGNANT, TRIO, MULTI, QUINTE\_PLUS…). | Catégoriel | Pari (au niveau course) | Explicatif | **OK** |
| `reunions[].courses[].ordreArrivee` | Ordre d’arrivée de la course (liste de numéros de chevaux). | Liste d’int | Course | **Cible / Leakage** | **OK** |
| `reunions[].courses[].dureeCourse` | Durée totale de la course. | Int | Course | **Cible / Leakage** | **OK** |
| `reunions[].courses[].statut` / `categorieStatut` | Statut final de la course (TERMINEE, ANNULEE…). | Catégoriel | Course | **Post-course / leakage** | **OK** |

---

### 1.2 Participants de la course (JSON 2)
https://online.turfinfo.api.pmu.fr/rest/client/61/programme/05112025/R1/C1/participants

Niveau **cheval-dans-course**.

| Chemin JSON | Description | Type | Niveau | Rôle | Correction / Note de Conditionnalité |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `participants[].numPmu` | Numéro de programme (dossard). | Int | Cheval-dans-course | ID | **OK** |
| `participants[].age` | Âge du cheval. | Int | Cheval | Explicatif | **OK** |
| `participants[].sexe` | Sexe (M, F, H…). | Catégoriel | Cheval | Explicatif | **OK** |
| `participants[].entraineur` | Nom de l’entraîneur. | Catégoriel | Cheval | Explicatif | **OK** |
| `participants[].driver` | Nom du driver/jockey. | Catégoriel | Cheval-dans-course | Explicatif | **OK** |
| `participants[].deferre` | État de déferrage au trot. | Catégoriel | Cheval-dans-course | Explicatif | **Conditionnel.** Présent uniquement si le cheval est déferré. |
| `participants[].musique` | “Musique” brute. | String | Cheval | Explicatif | **OK** |
| `participants[].nombreCourses` | Nb de courses disputées en carrière. | Int | Cheval | Explicatif | **OK** |
| `participants[].gainsParticipant.gainsCarriere` | Gains cumulés en carrière. | Float (Stocké en Int/centimes) | Cheval | Explicatif | **OK** |
| `participants[].dernierRapportReference.rapport` | Cote “référence” (matin). | Float (Stocké en Int/centimes) | Cheval-dans-course | Explicatif fort | **OK** |
| `participants[].dernierRapportDirect.rapport` | Dernière cote directe (live). | Float (Stocké en Int/centimes) | Cheval-dans-course | Potentiel leakage | **OK** |
| `participants[].ordreArrivee` | Rang final dans la course. | Int | Cheval-dans-course | **Cible / Leakage** | **Conditionnel.** Présent uniquement si le cheval est classé. |
| `participants[].incident` | Incident (DQ, TOMBE, ARRÊTE…). | Catégoriel | Cheval-dans-course | **Cible / Leakage** | **Conditionnel.** Présent uniquement si incident. |
| `participants[].tempsObtenu` | Temps effectif du cheval. | Int | Cheval-dans-course | **Cible / Leakage** | **Conditionnel.** Présent uniquement si le cheval est classé. |
| `participants[].reductionKilometrique` | Réduction kilométrique (temps/distance). | Float | Cheval-dans-course | **Cible / Leakage** | **Conditionnel.** Présent uniquement si le cheval est classé et le chrono mesuré. |
| `participants[].commentaireApresCourse` | Commentaire textuel post-course. | Texte libre | Cheval-dans-course | **Post-course / Leakage** | **OK** |
| `participants[].avisEntraineur` | Avis pré-course. | Catégoriel / texte | Cheval | Explicatif | **OK** |

---

### 1.3 Performances détaillées (JSON 3)
https://online.turfinfo.api.pmu.fr/rest/client/61/programme/05112025/R1/C1/performances-detaillees/pretty

Niveau **historique cheval / course passée**.

#### 1.3.1 Champs au niveau course passée

| Chemin JSON | Description | Type | Niveau | Rôle | Correction / Note de Conditionnalité |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `participants[].coursesCourues[].date` | Date de la course passée. | Date/Heure | Historique | Explicatif | **OK** |
| `participants[].coursesCourues[].discipline` | Discipline (PLAT, ATTELE, etc.). | Catégoriel | Historique | Explicatif | **OK** |
| `participants[].coursesCourues[].allocation` | Allocation totale de la course passée. | Float | Historique | Explicatif | **OK** |
| `participants[].coursesCourues[].distance` | Distance de cette course. | Int | Historique | Explicatif | **OK** |
| `participants[].coursesCourues[].tempsDuPremier` | Temps du vainqueur. | Int | Historique | Explicatif | **Conditionnel.** Absent si aucune réduction kilométrique n'est disponible. |

#### 1.3.2 Champs au niveau “participant dans la course passée”

| Chemin JSON | Description | Type | Niveau | Rôle | Correction / Note de Conditionnalité |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `participants[].coursesCourues[].participants[].itsHim` | True si c’est **le cheval étudié**. | Booléen | Historique | ID / repérage | **OK** |
| `participants[].coursesCourues[].participants[].place.place` | Rang dans cette course passée. | Int | Historique | Explicatif | **Conditionnel.** Peut être `null` en cas de disqualification/non-place. |
| `participants[].coursesCourues[].participants[].place.statusArrivee` | Statut (PLACE, NON\_CLASSE, DISQUALIFIE…). | Catégoriel | Historique | Explicatif | **OK** |
| `participants[].coursesCourues[].participants[].poidsJockey` | Poids porté (plat/obstacle). | Float | Historique | Explicatif | **Conditionnel.** Souvent `null` au Trot. |
| `participants[].coursesCourues[].participants[].corde` | N° de corde / stalle. | Int | Historique | Explicatif | **Conditionnel.** Souvent `null` au Trot. |
| `participants[].coursesCourues[].participants[].reductionKilometrique` | Réduction kilométrique du cheval. | Float | Historique | Explicatif | **Conditionnel.** Champ correct. Absent/Null si chrono non mesuré. |
| `participants[].coursesCourues[].participants[].distanceParcourue` | Distance réellement parcourue (avec reculs). | Int | Historique | Explicatif | **OK** |

---

### 1.4 Rapports définitifs (JSON 4)
https://online.turfinfo.api.pmu.fr/rest/client/1/programme/05112025/R1/C1/rapports-definitifs

JSON sous forme de **liste** (chaque élément = un type de pari).

| Chemin JSON | Description | Type | Niveau | Rôle | Correction / Note de Conditionnalité |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[].typePari` | Type de pari (SIMPLE\_GAGNANT, COUPLE\_GAGNANT, MULTI…). | Catégoriel | Pari (course) | Explicatif | **OK** |
| `[].famillePari` | Famille de pari (Simple, Couple, 2sur4, Trio, Multi…). | Catégoriel | Pari | Explicatif | **OK** 
| `[].miseBase` | Mise de base (ex: 200 = 2€). | Float | Pari | Explicatif | **OK** (Souvent stocké en Int/centimes). |
| `[].rembourse` | True si pari remboursé (annulé). | Booléen | Pari | Cible/Leakage | **OK** |
| `[].rapports[].dividende` | Dividende versé pour la mise de base. | Float (Stocké en Int/centimes) | Rapport | **Cible de rentabilité** | **OK** |
| `[].rapports[].dividendePourUnEuro` | Dividende ramené à 1€. | Float (Stocké en Int/centimes) | Rapport | **Cible de rentabilité** | **OK** |
| `[].rapports[].combinaison` | Combinaison gagnante (ex: "7", "7-3"). | String (liste encodée) | Rapport | **Cible (mapping vers chevaux)** | **OK** |
| `[].rapports[].nombreGagnants` | Nombre de tickets gagnants. | Float | Rapport | **Cible (volume de gagnants)** | **OK** |

---

## 2. Variables cibles possibles (labels)

Mise à jour pour inclure la conditionnalité (`Null` si non classé/incident).

### 2.1 Cibles au niveau cheval-dans-course (JSON 2 / JSON 1)

| Nom de la cible | Description | Type de problème | Champ(s) JSON | Remarque |
| :--- | :--- | :--- | :--- | :--- |
| `rang_arrivee` | Rang final du cheval (1, 2, 3, …). | Classification ordinale ou régression | `participants[].ordreArrivee` | **Conditionnel.** Peut être Null si NP, DQ, Arrêté. |
| `est_gagnant` | 1 si rang = 1, 0 sinon. | Classification binaire | Dérivé de `participants[].ordreArrivee` | Idem. |
| `est_place_top3` | 1 si rang ≤ 3, 0 sinon. | Classification binaire | Dérivé de `participants[].ordreArrivee` | Idem. |
| `incident` | Statut (DQ, TOMBE, ARRÊTE, RAS…). | Classification multi-classes | `participants[].incident` | **Conditionnel.** Présent uniquement en cas d'incident (sinon implicitement "RAS"). |
| `temps_obtenu` | Temps du cheval (ms). | Régression | `participants[].tempsObtenu` | **Conditionnel.** Null si non classé/chronométré. |
| `reduction_kilometrique` | Temps ramené au km. | Régression | `participants[].reductionKilometrique` | **Conditionnel.** Null si non classé/chronométré. |

---

## 3. Champs à exclure / à utiliser avec prudence

Les champs de leakage sont confirmés, avec la nuance de leur nature conditionnelle.

### 3.1 Fuite de données (Data Leakage) — à n’utiliser **que** comme cibles

| Chemin JSON | Motif |
| :--- | :--- |
| `reunions[].courses[].ordreArrivee` / `dureeCourse` / `incidents[]` / `statut` | Résultats finaux au niveau course. |
| `participants[].ordreArrivee` / `tempsObtenu` / `reductionKilometrique` / `incident` | Résultats finaux individuels. **Attention, tous sont conditionnels.** |
| `participants[].commentaireApresCourse` | Commentaire post-course : pur leakage. |
| JSON 4 : tous les champs `dividende`, `combinaison`, `rembourse` | Rapports définitifs, 100% post-course. |

### 3.2 Variables délicates (frontière “feature vs leakage”)

| Chemin JSON | Motif |
| :--- | :--- |
| `participants[].dernierRapportDirect.rapport` | Cote “live” (très proche du départ) : à utiliser seulement si le modèle parie à la dernière minute. |
| `participants[].dernierRapportReference.rapport` | Cote de référence/matin : saine si le modèle est pré-course. |

### 3.4 Champs textuels lourds / à traiter avec du NLP

| Chemin JSON | Motif |
| :--- | :--- |
| `reunions[].courses[].conditions` | Texte libre riche : nécessite NLP pour extraction structurée (reculs, limites de gains). |
| `participants[].avisEntraineur` | Fort potentiel, nécessite catégorisation ou NLP. |

---

## 4. Schéma de dataset proposé (table cheval-course)

Niveau d’observation choisi : **1 ligne = 1 cheval dans 1 course.**

### 4.2 Features de la course (contexte commun pour tous les chevaux d’une course)

| Nom de colonne | Type | Source JSON | Remarques mis à jour |
| :--- | :--- | :--- | :--- |
| `hippodrome_code` | string | JSON1: `reunions[].hippodrome.code` | OK. |
| `discipline` | string | JSON1: `reunions[].courses[].discipline` | OK. |
| `categorie_course` | string | JSON1: `reunions[].courses[].categorieParticularite` | OK. |
| `condition_age` | string | JSON1: `reunions[].courses[].conditionAge` | **Conditionnel.** Gérer les Null pour le Trot R1. |
| `distance_m` | int | JSON1: `reunions[].courses[].distance` | OK. |
| `type_piste` | string | JSON1: `reunions[].courses[].typePiste` | **Conditionnel.** Gérer les Null pour le Trot R1. |
| `terrain_libelle` | string | JSON1: `reunions[].courses[].penetrometre.intitule` | **Conditionnel.** |
| `penetrometre_valeur` | float | JSON1: `reunions[].courses[].penetrometre.valeurMesure` | **Très Conditionnel.** Peut être Null si non pertinent (Trot, PSF). |

### 4.4 Features cheval-dans-course (setup du jour)

| Nom de colonne | Type | Source JSON | Remarques mis à jour |
| :--- | :--- | :--- | :--- |
| `driver_jockey` | string | JSON2: `participants[].driver` | OK. |
| `deferrage` | string | JSON2: `participants[].deferre` | **Conditionnel.** Null si non déferré. |
| `cote_reference` | float | JSON2: `participants[].dernierRapportReference.rapport` | Stocké en Int/centimes dans le JSON, doit être Float. |
| `cote_directe` | float | JSON2: `participants[].dernierRapportDirect.rapport` | À manipuler avec prudence (proximité du leakage). |

### 4.5 Variables cibles (Mise à jour de la gestion des Null)

| Nom de colonne | Type | Source JSON | Remarques mis à jour |
| :--- | :--- | :--- | :--- |
| `target_rang_arrivee` | int | JSON2: `participants[].ordreArrivee` | **Conditionnel.** Null si NP/DQ. Doit être traité (ex: rang 99 pour non-classé). |
| `target_incident` | string | JSON2: `participants[].incident` | **Conditionnel.** Remplacer Null par une catégorie "RAS". |
| `target_reduction_km` | float | JSON2: `participants[].reductionKilometrique` | **Conditionnel.** Null si NP/DQ ou non mesuré. |
| `target_rapport_sg` | float | JSON4: `dividendePourUnEuro` | Joindre par `(id_course, num_pmu)` selon la combinaison gagnante. |