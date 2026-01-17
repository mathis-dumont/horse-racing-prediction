# Horse Racing Prediction using Machine Learning

This project aims to design a comprehensive platform for data processing and horse racing prediction (Trotting), based on Machine Learning techniques (XGBoost).

It covers the entire pipeline:
- automated data ingestion (ETL),
- storage and historization (PostgreSQL),
- training and deployment of a predictive model,
- exposure of results via a REST API and user interface.

> **Note:** This project serves as a technical demonstration of a complete ML pipeline architecture. The implemented models and strategies are intentionally simplified for educational purposes and are not profitable.

---

## Project Objectives

* Centralize and historize PMU data (programs, participants, performances, reports)
* Generate **calibrated win probabilities**
* Detect **exploitable mathematical edges**
* Provide a **clear and fast UI** for daily analysis
* Ensure **automated and reproducible execution** (CI/CD & CRON)

---
## Documentation

This project required the implementation of numerous steps. The documentation for the main steps is located in the `doc` folder.

---

## Prerequisites

Before starting, make sure you have the following tools installed on your machine:

### Docker

* **Docker** & **Docker Compose**
  Essential for the recommended method (execution via containers).

---

### Make

The project uses a **Makefile** as a single entry point to:

* launch Docker services,
* run tests,
* trigger ETL and Machine Learning pipelines.

The `make` tool must therefore be installed on your machine.

#### Linux (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install make
```

#### macOS

Install Apple developer tools (includes `make`):

```bash
xcode-select --install
```

#### Windows

Two options are available:

**Option 1 – WSL (recommended)**
Install Ubuntu via the Microsoft Store, then:

```bash
sudo apt update
sudo apt install make
```

**Option 2 – Git Bash**
Install *Git for Windows*, then verify that `make` is available:

```bash
make --version
```

---

### Python and Database (local installation only)

These prerequisites are necessary **only if you are not using Docker**:

* **Python 3.12+**
* **PostgreSQL**

---

## Installation & Startup

This project is designed to be launched quickly via **Docker** (recommended). Manual local installation is also possible for specific development.


### Configuration

1.  **Cloning the project:**
    ```bash
    git clone <repo-url>
    cd <project-name>
    ```

2.  **Environment variables:**
    The project requires a `.env` file at the root to function (database connection)
    
    Create a `.env` file at the root and fill in the following variables:
    ```ini
    # Example .env configuration
    DB_URL=postgresql://user:password@host.docker.internal:5432/database_name
    ```
    > **Note:** If the Supabase database password was not provided to you, you must run your PostgreSQL database on your host machine. Use `host.docker.internal` as the host in `DB_URL` so the Docker container can reach it.

---

### Method 1: Quick Start with Docker (Recommended)

Using the `Makefile` greatly simplifies interaction with Docker Compose.

**1. Building the images**
Compile the Docker images for the backend and frontend.
```bash
make build
# Or to force a rebuild without cache: make build-nc
```

**2. Launching the services**
Starts the containers in the background (detached mode).
```bash
make up
```

**3. Data initialization (ETL & ML)**
Once the containers are launched, you must populate the database and train the model.

*   **Model training:**
    Trains the XGBoost model on the data present in the database.
    ```bash
    make train
    ```

*   **Optional:** Data ingestion (ETL):
    Downloads and inserts programs, participants, and reports for the current date.
    ```bash
    make ingest
    ```
    *This is optional, as the database is hosted on Supabase and is populated daily by a CRON job.*

**4. Application access**
*   **Frontend (User Interface):** [http://localhost:8501](http://localhost:8501)
*   **Backend (API Documentation):** [http://localhost:8000/docs](http://localhost:8000/docs)

**Useful commands:**
*   `make logs`: Display logs in real time.
*   `make down`: Stop the containers.
*   `make clean`: Complete shutdown, volume deletion, and Python cache cleanup (`__pycache__`).

---

### Method 2: Local Installation and Startup (Without Docker)

If you need to develop without Docker, follow these steps. You will need two terminals.

#### Specific prerequisites
*   Make sure your PostgreSQL database is accessible in the .env file. (see Docker configuration section).

#### 1. Backend (API)

In a **first terminal**:

```bash
cd backend

# Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure PYTHONPATH (Important for absolute imports 'src.*')
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Launch API server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Frontend (Streamlit)

In a **second terminal**:

```bash
cd frontend

# Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Launch application
streamlit run app.py --server.port 8501
```

---

## Automation (GitHub Actions)

The project integrates **complete automation** via **GitHub Actions**, ensuring database updates.

### Daily ingestion (CRON)

A GitHub Actions workflow is executed **daily** to:

* Automatically retrieve PMU data for the day
* Update the **Supabase (PostgreSQL)** database
* Ensure the database is always synchronized without manual intervention

This automation explains why the `make ingest` step is optional.

---

## Architecture & Operation

This project is based on a **Microservices-lite**, clearly separating responsibilities and data flows.

### Overview

1. **Frontend (Streamlit)**

   * Interactive dashboard
   * No direct database connection
   * Exclusive communication via REST API

2. **Backend (FastAPI)**

   * Exposure of business endpoints
   * ML model loaded in memory at startup

3. **Data & ML Pipeline**

   * **ETL**: multithreaded PMU data ingestion
   * **Training**: XGBoost model generation
   * **Inference**: real-time predictions via API

---

## Tests & Code Quality

The project includes commands to run unit and integration tests via Docker, ensuring an isolated environment.

```bash
# Run Backend tests (Pytest)
make test-backend

# Run Frontend tests (Pytest + Mocking)
make test-frontend

# Run all tests
make test-all
```

---

## Project Structure

The file organization follows industry standards to ensure maintainability and scalability.

```bash
.
├── Makefile                # Command orchestrator (Entry point)
├── docker-compose.yml      # Docker services configuration
├── .env                    # Environment variables (Not versioned)
│
├── backend/                # API & ML Logic
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── src/
│   │   ├── api/            # FastAPI Routes, Schemas (Pydantic), Repositories
│   │   ├── core/           # Global Config, Database Manager
│   │   ├── ingestion/      # ETL (Programs, Participants, Reports)
│   │   ├── ml/             # Feature Engineering, Training, Prediction
│   │   └── cli/            # Command-line scripts (e.g., etl.py)
│   └── tests/              # Unit and integration tests (Pytest)
│
├── frontend/               # Streamlit Interface
│   ├── Dockerfile
│   ├── app.py              # Application entry point
│   ├── ui/                 # Visual components (Sidebar, Grids, Analysis)
│   ├── state/              # Session state management
│   ├── api/                # Internal HTTP client to Backend
│   └── tests/              # End-to-End and UI tests
│
└── data/                   # ML model (.pkl) and local dumps
```

---

## Main Features

### 1. Programs & Odds

* Meetings and races by date
* Participants, drivers, trainers
* Live odds

### 2. AI Predictions

* Calibrated probabilities (0–100%)
* Predictive ranking
* Feature engineering (form, music, shoeing...)

### 3. "Sniper" Module

Automated **Value Betting** strategy:

* AI vs market comparison
* Positive edge detection
* Strict filters (odds, minimum edge, liquidity)

---

## Best Practices & Ops

### Docker error handling
If you encounter permission errors (e.g., `Permission denied: '__pycache__'`) due to Docker creating files as root on your host system, use the command:

```bash
make clean
# This command stops containers and forces cache deletion with sudo
```

### Adding a new dependency
If you add a library to `backend/requirements.txt` or `frontend/requirements.txt`, you must rebuild the images:

```bash
make build
```

---

## API Documentation

Once the backend is launched, interactive documentation (Swagger UI) is automatically available. It allows you to test endpoints and view expected data schemas.

*   **Local URL:** `http://localhost:8000/docs`
*   **JSON Schema:** `http://localhost:8000/openapi.json`

---

## Contribution

1. Create a branch (`feature/my-feature`)
2. Implement + test (`make test-all`)
3. Commit
4. Open a Pull Request

---