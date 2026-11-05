import { renderCards } from './card.js';
import { getActiveList, updateListCount, getSortLength, getSortMinSideLength, getDisplayedPath, getViewerAncestors, getViewerId } from './main.js';
import { ancestorTerm } from './relationship.js';

// Redibuja las tarjetas respetando filtros, slider y orden actuales.
// La asigna initSwitches(); main.js la usa al llegar árboles nuevos.
export let refrescarLista = () => {};
// Vuelve a armar los chips de temas (puede haber temas nuevos).
export let refrescarTemas = () => {};

// El slider al máximo no limita (si no, quedarían ocultos los árboles más lejanos).
function sliderSinLimite(slider) {
  return Number(slider.value) >= Number(slider.max);
}

export function initSwitches() {

  const directToggle = document.getElementById("switch-coParentIsTargetPerson");
  const coParentToggle = document.getElementById("switch-coParentIsPathPerson");

  function update() {
    if (!window.fullList) return;

    let list = getActiveList();

    if (window.activeTopicFilter) {
      list = list.filter(a => (a.topics ?? []).includes(window.activeTopicFilter));
    }

    const cercaniaSlider = document.getElementById("slider-maxCercania");
    if (cercaniaSlider && !sliderSinLimite(cercaniaSlider)) {
      const maxCercania = Number(cercaniaSlider.value);
      list = list.filter(a => getSortLength(a) <= maxCercania);
    }

    // Conteos del desplegable de ancestros con los demás filtros ya aplicados.
    buildAncestorOptions(list);

    if (window.activeAncestorFilter) {
      const viewerId = getViewerId(window.arboles);
      list = list.filter(a =>
        getViewerAncestors(getDisplayedPath(a), viewerId)
          .some(x => x.person.id === window.activeAncestorFilter)
      );
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
    "deportistas": `
      Grupo de deportistas destacados de la región incluyendo futbolistas y pilotos de automovilismo.
    `,
    "presidentes uruguayos": `
      Lista basada en <a href="https://es.wikipedia.org/wiki/Anexo:Gobernantes_de_Uruguay" target="_blank">Wikipedia: Gobernantes de Uruguay</a>.
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
    allChip.className = "topic-chip" + (window.activeTopicFilter ? "" : " active");
    allChip.textContent = "Todos";
    allChip.dataset.topic = "";
    allChip.addEventListener("click", () => selectTopic(null));
    container.appendChild(allChip);

    topicSet.forEach(topic => {
      const chip = document.createElement("button");
      chip.className = "topic-chip" + (topic === window.activeTopicFilter ? " active" : "");
      chip.textContent = topic;
      chip.dataset.topic = topic;
      chip.addEventListener("click", () => selectTopic(topic));
      container.appendChild(chip);
    });
  }

  // 🌳 FILTRO POR ANCESTRO: padres y abuelos que aparecen en los caminos.
  const GEN_LABELS = { 1: "Padres", 2: "Abuelos", 3: "Bisabuelos" };

  // Opciones: todos los ancestros de la lista activa (switches de cónyuge).
  // Conteos: sobre countList (la lista con tema y cercanía aplicados).
  function buildAncestorOptions(countList) {
    const select = document.getElementById("filtro-ancestro");
    if (!select) return;

    const viewerId = getViewerId(window.arboles);
    const found = new Map(); // id -> { person, gen, count }
    (getActiveList() || []).forEach(a => {
      getViewerAncestors(getDisplayedPath(a), viewerId).forEach(({ person, gen }) => {
        if (!found.has(person.id)) found.set(person.id, { person, gen, count: 0 });
      });
    });
    (countList || getActiveList() || []).forEach(a => {
      getViewerAncestors(getDisplayedPath(a), viewerId).forEach(({ person }) => {
        const entry = found.get(person.id);
        if (entry) entry.count++;
      });
    });

    // Si el ancestro elegido ya no aparece, se quita el filtro.
    if (window.activeAncestorFilter && !found.has(window.activeAncestorFilter)) {
      window.activeAncestorFilter = null;
    }

    select.innerHTML = "";
    const all = document.createElement("option");
    all.value = "";
    all.textContent = "Todas las ramas";
    select.appendChild(all);

    const byGen = new Map();
    [...found.values()]
      .sort((x, y) => x.gen - y.gen || (x.person.nombre || "").localeCompare(y.person.nombre || ""))
      .forEach(e => {
        if (!byGen.has(e.gen)) byGen.set(e.gen, []);
        byGen.get(e.gen).push(e);
      });

    byGen.forEach((entries, gen) => {
      const group = document.createElement("optgroup");
      group.label = GEN_LABELS[gen] || `Generación ${gen}`;
      entries.forEach(({ person, count }) => {
        const term = ancestorTerm(gen, person.gender === "FEMALE");
        const opt = document.createElement("option");
        opt.value = person.id;
        opt.textContent = `${term.charAt(0).toUpperCase()}${term.slice(1)} — ${person.nombre || person.id}`
          + (person.lifespan ? ` (${person.lifespan})` : "")
          + ` · ${count} ${count === 1 ? "árbol" : "árboles"}`;
        group.appendChild(opt);
      });
      select.appendChild(group);
    });

    select.value = window.activeAncestorFilter || "";
    select.disabled = found.size === 0;
  }

  const ancestorSelect = document.getElementById("filtro-ancestro");
  if (ancestorSelect) {
    ancestorSelect.addEventListener("change", () => {
      window.activeAncestorFilter = ancestorSelect.value || null;
      update();
    });
  }

  // update() también rearma el desplegable: los switches cambian qué camino se muestra.
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

  // ⚙️ BOTON DE SETTINGS: abrir/cerrar el desplegable
  // Vive acá (en vez del <script> inline de dashboard_header.html) para que
  // siga funcionando en el HTML exportado por export.js, que descarta ese
  // <script> junto con el resto de acciones que dependen del servidor.
  const settingsToggle = document.getElementById("btn-settings-toggle");
  const settingsActions = document.getElementById("settings-actions");

  if (settingsToggle && settingsActions) {
    settingsToggle.addEventListener("click", function() {
      settingsActions.classList.toggle("open");
    });

    document.addEventListener("click", function(e) {
      if (!e.target.closest(".settings-menu")) {
        settingsActions.classList.remove("open");
      }
    });
  }

  // 🎚️ SLIDER: cercanía máxima
  const cercaniaSlider = document.getElementById("slider-maxCercania");
  const cercaniaValueEl = document.getElementById("maxCercaniaValue");

  if (cercaniaSlider) {
    const mostrarValor = () => {
      if (cercaniaValueEl) {
        cercaniaValueEl.textContent = sliderSinLimite(cercaniaSlider) ? "sin límite" : cercaniaSlider.value;
      }
    };
    mostrarValor();

    cercaniaSlider.addEventListener("input", () => {
      mostrarValor();
      update();
    });
  }

  buildTopicChips();

  refrescarLista = update;
  refrescarTemas = buildTopicChips;

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