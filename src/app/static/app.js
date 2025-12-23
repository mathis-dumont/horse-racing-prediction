// ======================================================
// Helpers
// ======================================================

function formatPercent(p) {
  return `${Math.round(p * 100)}%`;
}

// ======================================================
// RACES DU JOUR (API réelle)
// ======================================================

async function loadRaces() {
  const container = document.getElementById("courses-list");
  container.innerHTML = "<p>Chargement des courses…</p>";

  try {
    const response = await fetch("/api/races");
    const races = await response.json(); // ⬅️ C’EST UNE LISTE DIRECTE

    if (!Array.isArray(races) || races.length === 0) {
      container.innerHTML = "<p>Aucune course disponible.</p>";
      return;
    }

    container.innerHTML = "";

    races.forEach((race) => {
      const el = document.createElement("div");
      el.className = "course-item";
      el.dataset.courseId = race.id;

      el.innerHTML = `
        <div class="course-main">
          <span class="course-title">${race.label}</span>
          <span class="course-sub">${race.type} • ${race.distance} m • ${race.runners} partants</span>
        </div>
        <div class="course-meta">
          <span class="tag">${race.time || "—"}</span>
          <span class="course-sub">Cliquer pour les paris</span>
        </div>
      `;

      // On garde ton comportement existant
      el.addEventListener("click", () => openBetsForCourse(race));

      container.appendChild(el);
    });

  } catch (err) {
    console.error(err);
    container.innerHTML = "<p>Erreur lors du chargement des courses.</p>";
  }
}


// ======================================================
// BETS & PRÉDICTIONS (ENCORE MOCK)
// ======================================================

// Pour l’instant, on garde une version simple
function openBetsForRace(raceLabel) {
  const panel = document.getElementById("bets-panel");
  const title = document.getElementById("bets-course-title");
  const list = document.getElementById("bets-list");

  title.textContent = `Types de paris — ${raceLabel}`;
  list.innerHTML = "";

  const bets = ["Simple gagnant", "Simple placé"];

  bets.forEach((bet) => {
    const betEl = document.createElement("div");
    betEl.className = "bet-chip";

    betEl.innerHTML = `
      <span class="bet-label">${bet}</span>
      <button class="bet-btn">Lancer la prédiction</button>
    `;

    betEl.querySelector("button").addEventListener("click", (e) => {
      e.stopPropagation();
      alert("Prédictions non branchées pour l’instant 🙂");
    });

    list.appendChild(betEl);
  });

  panel.classList.remove("hidden");
}

// ======================================================
// RÉSULTATS & STATS (TOUJOURS MOCK)
// ======================================================

function renderResults() {
  const body = document.getElementById("results-body");
  if (!body) return;

  body.innerHTML = `
    <tr>
      <td colspan="5">Résultats non branchés pour l’instant</td>
    </tr>
  `;
}

function renderStats() {
  const global = document.getElementById("stat-global");
  if (!global) return;

  global.textContent = "–";
  document.getElementById("stat-sg").textContent = "–";
  document.getElementById("stat-sp").textContent = "–";
  document.getElementById("stat-period").textContent = "";
}

// ======================================================
// INITIALISATION
// ======================================================

document.addEventListener("DOMContentLoaded", () => {
  // Date du jour dans l'en-tête
  const dateEl = document.getElementById("courses-date");
  const today = new Date();
  const formatter = new Intl.DateTimeFormat("fr-FR", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit"
  });
  dateEl.textContent = formatter.format(today);

  // Charger réunions + courses depuis l'API
  loadMeetings();
});


function loadMeetings() {
  fetch("/api/races")
    .then(res => res.json())
    .then(data => {
      renderMeetings(data);
    })
    .catch(err => {
      console.error("Erreur chargement races :", err);
    });
}

function renderMeetings(meetings) {
  const container = document.getElementById("courses-list");
  container.innerHTML = "";

  meetings.forEach(meeting => {
    // ---- Réunion ----
    const meetingEl = document.createElement("div");
    meetingEl.className = "meeting";

    meetingEl.innerHTML = `
      <h3 class="meeting-title">
        Réunion R${meeting.meeting_number} — ${meeting.track}
      </h3>
    `;

    // ---- Courses ----
    meeting.races.forEach(race => {
      const raceEl = document.createElement("div");
      raceEl.className = "course-item";
      raceEl.dataset.raceId = race.id;

      raceEl.innerHTML = `
        <div class="course-main">
          <span class="course-title">${race.id}</span>
          <span class="course-sub">
            ${race.type} • ${race.distance ?? "—"} m • ${race.runners ?? "—"} partants
          </span>
        </div>
      `;

      // clic → afficher participants
      raceEl.addEventListener("click", () => {
        toggleParticipants(raceEl, race.id);
      });

      meetingEl.appendChild(raceEl);
    });

    container.appendChild(meetingEl);
  });
}

function toggleParticipants(raceEl, raceId) {
  console.log("toggleParticipants called with:", raceId);

  const existing = raceEl.querySelector(".participants");
  if (existing) {
    existing.remove();
    return;
  }

  fetch(`/api/races/${raceId}/participants`)
    .then(res => {
      console.log("API response status:", res.status);
      return res.json();
    })
    .then(data => {
      console.log("Participants data:", data);

      const list = document.createElement("div");
      list.className = "participants";

      data.forEach(p => {
        const row = document.createElement("div");
        row.textContent = `${p.pmu_number} - ${p.horse} (${p.odds ?? "—"})`;
        list.appendChild(row);
      });

      raceEl.appendChild(list);
    })
    .catch(err => {
      console.error("Erreur fetch participants:", err);
    });
}
