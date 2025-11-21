// ---- Données simulées (mock) ----
// Tu remplaceras ça par des appels API plus tard

const mockCourses = [
  {
    id: "R1C3",
    label: "R1C3 — Prix d'Enghien",
    time: "15:15",
    track: "Enghien",
    type: "Plat",
    bets: ["Simple gagnant", "Simple placé", "Couplé"]
  },
  {
    id: "R2C5",
    label: "R2C5 — Grand Handicap",
    time: "16:40",
    track: "Longchamp",
    type: "Obstacle",
    bets: ["Simple gagnant", "Simple placé", "Tiercé"]
  },
  {
    id: "R3C2",
    label: "R3C2 — Prix du Haras",
    time: "18:05",
    track: "Vincennes",
    type: "Trot",
    bets: ["Simple gagnant", "Simple placé", "Quinté+"]
  }
];

const mockPredictions = {
  // Clé = course_id + bet_type simplifié
  "R1C3|Simple gagnant": [
    {
      horse: "Cheval 5",
      p_win: 0.32,
      p_place: 0.58,
      odds: 7.5,
      comment: "Bon outsider, intéressant en placé."
    },
    {
      horse: "Cheval 3",
      p_win: 0.25,
      p_place: 0.50,
      odds: 5.2,
      comment: "Cheval régulier, pari raisonnable."
    },
    {
      horse: "Cheval 1",
      p_win: 0.18,
      p_place: 0.42,
      odds: 3.8,
      comment: "Favori logique, mais moins de value."
    }
  ],
  "R2C5|Simple placé": [
    {
      horse: "Cheval 8",
      p_win: 0.15,
      p_place: 0.52,
      odds: 11.0,
      comment: "Profil spéculatif mais value en placé."
    },
    {
      horse: "Cheval 2",
      p_win: 0.22,
      p_place: 0.55,
      odds: 4.3,
      comment: "Bon compromis risque / gain."
    }
  ]
};

const mockResults = [
  {
    course: "R1C1 — Prix de la Forêt",
    bet_type: "Simple gagnant",
    model_pred: "Cheval 4 (28%)",
    real_result: "Cheval 4 — 1er",
    correct: true
  },
  {
    course: "R1C2 — Prix des Alpes",
    bet_type: "Simple placé",
    model_pred: "Cheval 2 (49%)",
    real_result: "Cheval 2 — 5e",
    correct: false
  },
  {
    course: "R2C1 — Prix du Midi",
    bet_type: "Simple gagnant",
    model_pred: "Cheval 7 (22%)",
    real_result: "Cheval 7 — 2e",
    correct: false
  }
];

const mockStats = {
  from_date: "01/02/2025",
  global: 0.62,
  simple_gagnant: 0.29,
  simple_place: 0.54
};

// ---- Helpers ----

function formatPercent(p) {
  return `${Math.round(p * 100)}%`;
}

// ---- Rendering ----

function renderCourses() {
  const container = document.getElementById("courses-list");
  container.innerHTML = "";

  mockCourses.forEach((course) => {
    const el = document.createElement("div");
    el.className = "course-item";
    el.dataset.courseId = course.id;

    el.innerHTML = `
      <div class="course-main">
        <span class="course-title">${course.label}</span>
        <span class="course-sub">${course.track} • ${course.type}</span>
      </div>
      <div class="course-meta">
        <span class="tag">${course.time}</span>
        <span class="course-sub">Cliquer pour les paris</span>
      </div>
    `;

    el.addEventListener("click", () => openBetsForCourse(course));
    container.appendChild(el);
  });
}

function openBetsForCourse(course) {
  const panel = document.getElementById("bets-panel");
  const title = document.getElementById("bets-course-title");
  const list = document.getElementById("bets-list");

  title.textContent = `Types de paris — ${course.label}`;
  list.innerHTML = "";

  course.bets.forEach((bet) => {
    const betEl = document.createElement("div");
    betEl.className = "bet-chip";

    betEl.innerHTML = `
      <span class="bet-label">${bet}</span>
      <button class="bet-btn">Lancer la prédiction</button>
    `;

    betEl.querySelector("button").addEventListener("click", (e) => {
      e.stopPropagation();
      handlePredictionRequest(course, bet);
    });

    list.appendChild(betEl);
  });

  panel.classList.remove("hidden");
}

function handlePredictionRequest(course, betType) {
  // TODO : remplacer la logique mock par un appel API vers Flask
  // fetch("/api/predict", { method: "POST", body: JSON.stringify({ ... }) })

  const key = `${course.id}|${betType}`;
  const preds = mockPredictions[key];

  const title = document.getElementById("predictions-title");
  const body = document.getElementById("predictions-body");
  const panel = document.getElementById("predictions-panel");

  title.textContent = `Prédictions — ${course.label} — ${betType}`;
  body.innerHTML = "";

  if (!preds) {
    const row = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 5;
    td.textContent = "Pas encore de prédictions disponibles pour cette combinaison.";
    row.appendChild(td);
    body.appendChild(row);
  } else {
    preds.forEach((p) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${p.horse}</td>
        <td>${formatPercent(p.p_win)}</td>
        <td>${formatPercent(p.p_place)}</td>
        <td>${p.odds.toFixed(1)}</td>
        <td>${p.comment}</td>
      `;
      body.appendChild(tr);
    });
  }

  panel.classList.remove("hidden");
}

function renderResults() {
  const body = document.getElementById("results-body");
  body.innerHTML = "";

  mockResults.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${r.course}</td>
      <td>${r.bet_type}</td>
      <td>${r.model_pred}</td>
      <td>${r.real_result}</td>
      <td class="${r.correct ? "text-success" : "text-danger"}">
        ${r.correct ? "✔" : "✘"}
      </td>
    `;
    body.appendChild(tr);
  });
}

function renderStats() {
  document.getElementById("stat-global").textContent = formatPercent(
    mockStats.global
  );
  document.getElementById("stat-sg").textContent = formatPercent(
    mockStats.simple_gagnant
  );
  document.getElementById("stat-sp").textContent = formatPercent(
    mockStats.simple_place
  );
  document.getElementById(
    "stat-period"
  ).textContent = `Depuis le ${mockStats.from_date}`;
}

// ---- Initialisation ----

document.addEventListener("DOMContentLoaded", () => {
  // Date du jour dans l'en-tête des courses
  const dateEl = document.getElementById("courses-date");
  const today = new Date();
  const formatter = new Intl.DateTimeFormat("fr-FR", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit"
  });
  dateEl.textContent = formatter.format(today);

  renderCourses();
  renderResults();
  renderStats();

  const closeBetsBtn = document.getElementById("close-bets");
  closeBetsBtn.addEventListener("click", () => {
    document.getElementById("bets-panel").classList.add("hidden");
  });
});
