import { showPopup } from './popup.js';
import { getActiveList, updateListCount } from './main.js';

function getCardColor(a) {
  if (a?.coParentIsPathPerson) return '#fc9999';
  if (a?.coParentIsTargetPerson) return '#fccccc';
  return 'white';
}

export function createCard(a) {
  const defaultPortraitUrl = 'https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png';

  const card = document.createElement("div");
  card.className = "card";

  card.style.backgroundColor = getCardColor(a);

  card.dataset.cercania = a.cercania ?? 0;
  card.dataset.directLength = a.direct_length ?? 0;

  card.innerHTML = `
    <img src="${a.portraitUrl || defaultPortraitUrl}" width="150">
    <h3>${a.name}</h3>
    <small><i>${a.relationshipDescription || ""}</i></small><br>
    <small class="metric"></small><br>
    <small>${a.info || ""}</small>
  `;

  // 🔥 EVENTO CLICK (ANTES TE FALTABA ESTO)
  card.addEventListener('click', (event) => {
    event.stopPropagation();

    const list = getActiveList();

    const index = list.findIndex(item =>
      item.person_code === a.person_code
    );

    window.currentIndex = index !== -1 ? index : 0;

    showPopup(window.currentIndex);
    document.getElementById('popup').style.display = 'flex';
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
  updateListCount(); // 🔥 ahora vive acá
}

export function updateCardMetrics() {
  const switchDirect = document.getElementById("switch-coParentIsTargetPerson");
  const cards = document.querySelectorAll(".card");

  cards.forEach(card => {
    const metricEl = card.querySelector(".metric");
    if (!metricEl) return;

    const cercania = card.dataset.cercania;
    const direct = card.dataset.directLength;

    metricEl.textContent = `Cercanía: ${
      switchDirect?.checked
        ? (direct ?? '-')
        : (cercania ?? '-')
    }`;
  });
}