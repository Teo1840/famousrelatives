import { showPopup } from './popup.js';
import { shouldUseDirectPath } from './main.js';
import { computeRelationshipDescription } from './relationship.js';

// Parentesco político: el camino que se muestra pasa por un cónyuge (mío o de
// la persona famosa). El camino directo nunca pasa por el cónyuge de la persona.
function isPolitico(a) {
  const useDirect = shouldUseDirectPath(a);
  const viaTargetSpouse = !useDirect && a?.coParentIsTargetPerson;
  const viaMySpouse = useDirect ? a?.directPath?.coParentIsPathPerson : a?.mainPath?.coParentIsPathPerson;
  return !!(viaTargetSpouse || viaMySpouse);
}

export function createCard(a) {
  const defaultPortraitUrl =
    'https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png';

  const card = document.createElement("div");
  card.className = isPolitico(a) ? "card card--politico" : "card";

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

// Tarjetas ya creadas, por persona. Se reusan al filtrar/ordenar para no
// recrear el DOM ni recargar las fotos (eso causaba parpadeo con el slider).
// Se recrea solo si cambian los datos o qué camino/borde muestra la tarjeta.
const cardCache = new Map(); // person_code -> { data, sig, el }

function cardSignature(a) {
  return `${shouldUseDirectPath(a)}|${isPolitico(a)}`;
}

export function renderCards(list) {
  const container = document.getElementById("cards-container");
  if (!container) return;

  window.visibleList = list;

  const frag = document.createDocumentFragment();
  list.forEach(a => {
    const sig = cardSignature(a);
    let entry = cardCache.get(a.person_code);
    if (!entry || entry.data !== a || entry.sig !== sig) {
      entry = { data: a, sig, el: createCard(a) };
      cardCache.set(a.person_code, entry);
    }
    frag.appendChild(entry.el);
  });
  // Mueve los nodos existentes (las imágenes ya cargadas no se recargan).
  container.replaceChildren(frag);

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