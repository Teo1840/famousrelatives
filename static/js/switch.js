import { renderCards } from './card.js';
import { getActiveList, updateListCount, getSortLength, getSortMinSideLength } from './main.js';

export function initSwitches() {

  const directToggle = document.getElementById("switch-coParentIsTargetPerson");
  const coParentToggle = document.getElementById("switch-coParentIsPathPerson");

  function update() {
    if (!window.fullList) return;

    let list = getActiveList();

    if (window.activeTopicFilter) {
      list = list.filter(a => (a.topics ?? []).includes(window.activeTopicFilter));
    }

    const sortByAscToggle = document.getElementById("switch-sortByAsc");
    list = [...list].sort(sortByAscToggle?.checked
      ? (a, b) => getSortMinSideLength(a) - getSortMinSideLength(b)
      : (a, b) => getSortLength(a) - getSortLength(b)
    );

    renderCards(list);
    updateListCount(list);
    window.currentIndex = 0;
  }

  const TOPIC_DESCRIPTIONS = {
    "presidentes uruguayos": `
      Lista basada en <a href="https://es.wikipedia.org/wiki/Anexo:Gobernantes_de_Uruguay" target="_blank">Wikipedia: Gobernantes de Uruguay</a>.<br>
      <strong>Presidentes no encontrados en FamilySearch</strong> (si los encontrás, ¡agregálos!):
      Claudio Williman, José Serrato, Juan José de Amézaga, José Mujica.
    `,
    "treinta y tres orientales": `
      Lista basada en <a href="https://www.geni.com/projects/33-Orientales/8298" target="_blank">Geni: Los 33 Orientales</a>.
      Existen al menos 16 versiones distintas de la lista — los integrantes varían según la fuente histórica.<br>
      <strong>Orientales no encontrados en FamilySearch</strong> (si los encontrás, ¡agregálos!):
      Francisco Lavalleja, Manuel Lavalleja, Juan Acosta, Basilio Araújo, Juan Arteaga, Felipe Carapé, Andrés Cheveste,
      Carmelo Colman, Manuel Freire, Javier Chávez Zibil, Tiburcio Gómez, Ignacio Medina, Manuel Meléndez, Avelino Miranda,
      Santiago Nievas, Ignacio Núñez, Dionisio Oribe, Juan Ortiz, Ramón Ortiz, Celedonio Rojas, Juan Rosas, Gregorio Sanabria,
      Juan Spikerman, Jacinto Trápani, Agustín Velázquez, Pablo Zufriategui, Andrés Areguatí.
    `
  };

  function showTopicDescription(topic) {
    const el = document.getElementById("topic-description");
    if (!el) return;
    const html = topic && TOPIC_DESCRIPTIONS[topic];
    el.innerHTML = html || "";
    el.style.display = html ? "block" : "none";
  }

  function selectTopic(topic) {
    window.activeTopicFilter = topic || null;
    document.querySelectorAll(".topic-chip").forEach(chip => {
      chip.classList.toggle("active", chip.dataset.topic === (topic || ""));
    });
    showTopicDescription(topic);
    update();
  }

  function buildTopicChips() {
    const container = document.getElementById("topic-filters");
    if (!container) return;

    container.innerHTML = "";

    const topicSet = new Set();
    (window.arboles || []).forEach(a => (a.topics || []).forEach(t => topicSet.add(t)));

    if (topicSet.size === 0) return;

    const allChip = document.createElement("button");
    allChip.className = "topic-chip active";
    allChip.textContent = "Todos";
    allChip.dataset.topic = "";
    allChip.addEventListener("click", () => selectTopic(null));
    container.appendChild(allChip);

    topicSet.forEach(topic => {
      const chip = document.createElement("button");
      chip.className = "topic-chip";
      chip.textContent = topic;
      chip.dataset.topic = topic;
      chip.addEventListener("click", () => selectTopic(topic));
      container.appendChild(chip);
    });
  }

  if (directToggle) {
    directToggle.addEventListener("change", update);
  }

  if (coParentToggle) {
    coParentToggle.addEventListener("change", update);
  }

  const sortByAscToggle = document.getElementById("switch-sortByAsc");
  if (sortByAscToggle) {
    sortByAscToggle.addEventListener("change", update);
  }

  buildTopicChips();

  // 🌙 MODO OSCURO
  const darkToggle = document.getElementById("switchDarkMode");
  const darkText = document.getElementById("darkModeText");

  if (darkToggle) {
    const isDark = localStorage.getItem("darkMode") === "true";
    if (isDark) {
      document.body.classList.add("dark-mode");
      darkToggle.checked = true;
      if (darkText) darkText.textContent = "Modo oscuro";
    }

    darkToggle.addEventListener("change", () => {
      document.body.classList.toggle("dark-mode");
      const nowDark = document.body.classList.contains("dark-mode");
      localStorage.setItem("darkMode", nowDark);

      if (darkText) {
        darkText.textContent = nowDark ? "Modo oscuro" : "Modo claro";
      }

      const popup = document.getElementById('popup');
      if (popup?.style.display === 'flex' && window.showPopup) {
        window.showPopup(window.currentIndex);
      }
    });
  }
}