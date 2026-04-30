import { showPopup } from './popup.js';
import { getActiveList } from './main.js';

function getCardColor(a) {
  const isPath = a?.mainPath?.coParentIsPathPerson;
  const isTarget = a?.coParentIsTargetPerson;

  if (isPath && isTarget) return 'var(--card-both)';
  if (isPath) return 'var(--card-path)';
  if (isTarget) return 'var(--card-target)';
  return 'var(--card-bg)';
}

function getEffectiveLength(a) {
  const main = a?.mainPath?.coParentIsPathPerson;
  const direct = a?.directPath?.coParentIsPathPerson;

  const useDirect = a?.directPath && !(main && (direct ?? true));

  return useDirect
    ? (a.direct_length ?? 0)
    : (a.cercania ?? 0);
}

export function createCard(a) {
  const defaultPortraitUrl =
    'https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png';

  const card = document.createElement("div");
  card.className = "card";

  card.style.setProperty('--card-color', getCardColor(a));

  const effective = getEffectiveLength(a);
  card.dataset.effectiveLength = effective;

  card.dataset.personCode = a.person_code; // 🔥 clave para popup

  card.innerHTML = `
    <img src="${a.portraitUrl || defaultPortraitUrl}" width="150">
    <h3>${a.name}</h3>
    <small><i>${a.relationshipDescription || ""}</i></small><br>
    <small class="metric"></small><br>
    <small>${a.info || ""}</small>
  `;

  // 🔥 CLICK → abre popup (sin romper arquitectura)
  card.addEventListener("click", () => {
    const list = getActiveList();

    const index = list.findIndex(
      x => x.person_code === card.dataset.personCode
    );

    if (index === -1) return;

    window.currentIndex = index;
    showPopup(index);

    const popup = document.getElementById("popup");
    if (popup) popup.style.display = "flex";
  });

  return card;
}

export function renderCards(list) {
  const container = document.getElementById("cards-container");
  if (!container) return;

  container.innerHTML = "";

  list.forEach(a => {
    const card = createCard(a);
    container.appendChild(card);
  });

  updateCardMetrics();
}

export function updateCardMetrics() {
  const cards = document.querySelectorAll(".card");

  cards.forEach(card => {
    const metricEl = card.querySelector(".metric");
    if (!metricEl) return;

    metricEl.textContent = `Cercanía: ${card.dataset.effectiveLength}`;
  });
}