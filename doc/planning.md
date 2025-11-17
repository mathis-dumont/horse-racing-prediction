# 🗂️ **PMU Prediction Project — Planning & Status**

## 📌 **Project Goal**

Build a full horse-race prediction system using PMU API data:

* Automatic data ingestion from PMU JSON endpoints
* Normalized PostgreSQL database (Supabase)
* Daily automated ingestion
* ML training pipeline
* Prediction API + deployment
* Optional front-end / dashboard

---

# ✅ **1. Architecture & Setup**

### ✔️ Status: **COMPLETED**

* Defined global architecture (ingestion → database → ML → API)
* Created project structure (`src/`, `scripts/`, `tests/`, etc.)
* Defined full SQL schema (10 tables)
* Connected DBeaver to Supabase
* Solved IPv6 / Supabase connection issue using **pooler IPv4**
* Added `.env`, `.env.example`, `.gitignore`, requirements.txt
* Implemented repo-dump script (`dump_repo.py`)

### 🔜 Nothing left here.

---

# 📁 **2. Database Schema Creation**

### ✔️ Status: **COMPLETED**

* Implemented all SQL tables:

  * `daily_program`
  * `race_meeting`
  * `race`
  * `horse`
  * `race_participant`
  * `horse_race_history`
  * `race_bet`
  * `bet_report`
  * `prediction`
  * raw tables (JSON backups)
* Added missing column `race_status_category`
* Verified schema integrity via DBeaver

### 🔜 Nothing left here.

---

# 📡 **3. JSON Inspection (Quality & Feature Coverage)**

### ✔️ Status: **COMPLETED**

* Created 4 inspection scripts:

  * `inspect_programme.py`
  * `inspect_participants.py`
  * `inspect_performances.py`
  * `inspect_rapports.py`
* Verified expected fields vs API actual fields (JSON 1→4)
* Created Markdown **feature reliability** file in canvas

### 🔜 Nothing left here.

---

# 📥 **4. JSON 1 Ingestion (Programme du Jour)**

### ✔️ Status: **COMPLETED**

Scripts:

* `ingest_programme_day.py`

Tasks done:

* Ingests into:

  * `daily_program`
  * `race_meeting`
  * `race`
* Handling:

  * timestamps → dates
  * duration (ms → seconds)
  * penetrometer with French decimal `"4,2"` fixed
  * upsert logic
  * logging

### 🔵 Where you stopped

JSON 1 ingestion now **works end-to-end**.

### 🔜 Next:

➡️ Move to ingestion of **JSON 2** (Participants)

---

# 🐎 **5. JSON 2 Ingestion — Participants & Horses**

### ⏳ Status: **NEXT STEP**

This will fill:

* `horse`
* `race_participant`

Tasks to do:

* Fetch JSON 2 per course:

  ```
  /rest/client/61/programme/{date}/R{numReunion}/C{numCourse}/participants
  ```
* Upsert horses (avoid duplicates with same name)
* Insert/update race participants:

  * age, sexe, trainer, driver
  * gains, musique, reports (ref odds, live odds)
  * post-race leakage fields stored too
* Link to the right `race_id` using programme table

### 🔜 To be implemented next (we can do it together)

---

# 📚 **6. JSON 3 Ingestion — Performances détaillées**

### ⏳ Status: **PENDING**

Will populate:

* `horse_race_history`

Tasks:

* Convert dates, allocations, distances
* Handle conditional fields (many nulls)
* Ensure correct identification of “itsHim”

---

# 💸 **7. JSON 4 Ingestion — Rapports définitifs**

### ⏳ Status: **PENDING**

Will fill:

* `race_bet`
* `bet_report`

Tasks:

* Insert one row per pari
* Insert many rows per rapport (dividendes)
* Handle `rembourse` (bool)

---

# 🤖 **8. Feature Engineering & ML Pipeline**

### ⏳ Status: **PENDING**

Tasks:

* Build feature table or on-the-fly features:

  * horse speed metrics
  * form indicators
  * trainer stats
  * race difficulty
  * bet odds transformations
* Split train / val sets
* Select model:

  * XGBoost
  * LightGBM
  * Logistic regression baseline
* Train, evaluate, log metrics
* Save model weights & version

---

# 🌐 **9. Prediction API (FastAPI)**

### ⏳ Status: **PENDING**

Tasks:

* Create FastAPI app
* Endpoints:

  * `/predict/today`
  * `/predict/race/{race_id}`
  * `/health`
* Load latest model
* Generate predictions per horse
* Store predictions in DB

Deployment options:

* Railway
* Render
* Supabase Function (experimental)
* VPS cheap option

---

# 🔁 **10. Automation & Scheduling**

### ⏳ Status: **PENDING**

* GitHub Actions or cron job:

  * Every morning: ingest JSON 1→4
  * After ingestion: run prediction script
  * Insert predictions into DB
* Monitor failures via logging

---

# 📊 **11. Optional: Front-End**

### ⏳ Status: **OPTIONAL**

* Streamlit dashboard
* Simple web UI (React or plain HTML)
* Display predictions & past accuracy

---

# 🧩 **Current Position in the Project**

### ✔️ You have completed:

* Architecture
* Database schema
* JSON analysis
* JSON 1 ingestion working end-to-end

### 🔥 **Next concrete step:**

👉 Implement **JSON 2 ingestion** (participants & horses)

---

