import { showPopup } from './popup.js';
import { shouldUseDirectPath } from './main.js';
import { computeRelationshipDescription } from './relationship.js';

// Color según el camino que se muestra: el directo nunca pasa por el
// cónyuge de la persona, y puede (o no) pasar por mi cónyuge.
function getCardColor(a) {
  const useDirect = shouldUseDirectPath(a);
  const isTarget = !useDirect && a?.coParentIsTargetPerson;
  const isPath = useDirect ? a?.directPath?.coParentIsPathPerson : a?.mainPath?.coParentIsPathPerson;

  if (isPath && isTarget) return 'var(--card-both)';
  if (isPath)   return 'var(--card-path)';
  if (isTarget) return 'var(--card-target)';
  return 'var(--card-bg)';
}

export function createCard(a) {
  const defaultPortraitUrl =
    'https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png';

  const card = document.createElement("div");
  card.className = "card";

  card.style.setProperty('--card-color', getCardColor(a));

  const useDirect = shouldUseDirectPath(a) && a.directPath != null;
  card.dataset.effectiveLength = useDirect ? (a.direct_length ?? 0) : (a.cercania ?? 0);

  card.dataset.personCode = a.person_code;

  const relDesc = (useDirect && a.directPath)
    ? computeRelationshipDescription(
        a.directPath.asc.length,
        a.directPath.desc.length,
        a.name,
        a.directPath.desc.at(-1)?.gender || ""
      )
    : (a.relationshipDescription || "");

  card.innerHTML = `
    <img src="${a.portraitUrl || defaultPortraitUrl}" width="150" onerror="this.onerror=null;this.src='${defaultPortraitUrl}'">
    <h3>${a.name}</h3>
    <small><i>${relDesc}</i></small><br>
    <small class="metric"></small><br>
    <small>${a.info || ""}</small>
  `;

  // 🔥 CLICK → abre popup (sin romper arquitectura)
  card.addEventListener("click", () => {
    // Misma lista y orden que las tarjetas visibles (para las flechas del popup).
    const list = window.visibleList || [];

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
  window.visibleList = list;

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