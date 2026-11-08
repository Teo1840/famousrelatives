import { renderCards } from './card.js';
import { getActiveList, updateListCount, getSortLength, getSortMinSideLength, getDisplayedPath, getViewerAncestors, getViewerId } from './main.js';
import { ancestorTerm } from './relationship.js';

// Redibuja las tarjetas respetando filtros, slider y orden actuales.
// La asigna initSwitches(); main.js la usa al llegar árboles nuevos.
export let refrescarLista = () => {};
// Vuelve a armar los chips de temas (puede haber temas nuevos).
export let refrescarTemas = () => {};

// El último puesto del slider es "todos": no limita.
function sliderSinLimite(slider) {
  return Number(slider.value) >= Number(slider.max);
}

// El slider tiene dos modos, según el switch "Ordenar por cercanía al antepasado":
// - apagado: cercanía absoluta = nodos intermedios del camino (sin contarme a mí
//   ni a la persona famosa; el antepasado común sí cuenta), de 1 a 49.
// - prendido: cercanía a la familia = el lado más corto del camino, de 1 a 29.
const MAX_ABSOLUTA = 50; // 1–49 + "todos"
const MAX_FAMILIA = 30;  // 1–29 + "todos"

function modoFamilia() {
  return !!document.getElementById("switch-sortByAsc")?.checked;
}

// asc (incluye al que mira) + antepasado + desc (incluye al famoso) - las 2 puntas.
function nodosIntermedios(a) {
  return Math.max(0, getSortLength(a) - 1);
}

function medidaCercania(a) {
  return modoFamilia() ? getSortMinSideLength(a) : nodosIntermedios(a);
}

function mostrarValorCercania(slider) {
  const titulo = document.getElementById("cercaniaTitulo");
  if (titulo) titulo.textContent = modoFamilia() ? "Cercanía a la familia" : "Cercanía absoluta";
  const valor = document.getElementById("maxCercaniaValue");
  if (valor) valor.textContent = sliderSinLimite(slider) ? "todos" : slider.value;
}

// Pone el máximo según el modo; al cambiar de modo vuelve a "todos".
function ajustarSlider(slider) {
  const familia = modoFamilia();
  const modo = familia ? "familia" : "absoluta";
  if (slider.dataset.modo !== modo) {
    const max = familia ? MAX_FAMILIA : MAX_ABSOLUTA;
    slider.dataset.modo = modo;
    slider.max = max;
    slider.value = max;
  }
  mostrarValorCercania(slider);
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
    if (cercaniaSlider) ajustarSlider(cercaniaSlider);
    if (cercaniaSlider && !sliderSinLimite(cercaniaSlider)) {
      const maxCercania = Number(cercaniaSlider.value);
      list = list.filter(a => medidaCercania(a) <= maxCercania);
    }

    // Ancestro y país: cada desplegable cuenta con todos los demás filtros
    // aplicados, así el número de cada opción es lo que se va a ver al elegirla.
    const viewerId = getViewerId(window.arboles);
    const pasaAncestro = a => !window.activeAncestorFilter ||
      getViewerAncestors(getDisplayedPath(a), viewerId).some(x => x.person.id === window.activeAncestorFilter);
    const esDelPais = a => !window.activePaisFilter || (a.paises ?? []).includes(window.activePaisFilter);

    buildAncestorOptions(list.filter(esDelPais));
    buildPaisOptions(list.filter(pasaAncestro));

    list = list.filter(a => pasaAncestro(a) && esDelPais(a));

    const sortByAscToggle = document.getElementById("switch-sortByAsc");
    list = [...list].sort(sortByAscToggle?.checked
      // Lado más corto; si empatan, el camino con menos nodos (cercanía total).
      ? (a, b) => (getSortMinSideLength(a) - getSortMinSideLength(b)) || (getSortLength(a) - getSortLength(b))
      : (a, b) => getSortLength(a) - getSortLength(b)
    );

    renderCards(list);
    updateListCount(list);
    window.currentIndex = 0;
  }

  const TOPIC_DESCRIPTIONS = {
    "Deportistas": `
      Grupo de deportistas destacados de la región incluyendo futbolistas y pilotos de automovilismo.
    `,
    "Presidentes uruguayos": `
      Lista basada en <a href="https://es.wikipedia.org/wiki/Anexo:Gobernantes_de_Uruguay" target="_blank">Wikipedia: Gobernantes de Uruguay</a>.
    `,
    "Treinta y Tres Orientales": `
      Lista basada en <a href="https://www.geni.com/projects/33-Orientales/8298" target="_blank">Geni: Los 33 Orientales</a> y <a href="https://es.wikipedia.org/w/index.php?title=Treinta_y_Tres_Orientales&amp;oldid=50076383" target="_blank">Wikipedia: Treinta y Tres Orientales</a>.
      Existen al menos 16 versiones distintas de la lista — los integrantes varían según la fuente histórica.<br>
      <strong>Orientales no encontrados en FamilySearch</strong> (si los encontrás, ¡agregálos!):
      Juan Acosta, Juan Arteaga, Felipe Carapé, Javier Chávez Zibil, Ignacio Medina,
      Avelino Miranda, Santiago Nievas, Ignacio Núñez, Dionisio Oribe, Juan Ortiz, Juan Rosas, Agustín Velázquez,
      Andrés Areguatí.
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

  // 🔽 DESPLEGABLES PROPIOS ("Pasa por" y "País"): mismo diseño para los dos.
  // Abre/cierra la lista, la cierra al hacer clic afuera y permite usar el teclado.
  function conectarDesplegable(dropdown) {
    const btn = dropdown?.querySelector(".pais-dropdown-btn");
    const lista = dropdown?.querySelector(".pais-dropdown-list");
    if (!btn || !lista) return () => {};

    const abrir = abrirla => {
      lista.hidden = !abrirla;
      btn.setAttribute("aria-expanded", String(abrirla));
    };

    btn.addEventListener("click", () => {
      abrir(lista.hidden);
      if (!lista.hidden) lista.querySelector('[aria-selected="true"]')?.focus();
    });
    document.addEventListener("click", e => {
      if (!dropdown.contains(e.target)) abrir(false);
    });
    dropdown.addEventListener("keydown", e => {
      if (e.key === "Escape") { abrir(false); btn.focus(); }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        const items = [...lista.querySelectorAll('li[role="option"]')];
        if (lista.hidden || !items.length) return;
        e.preventDefault();
        const i = items.indexOf(document.activeElement);
        const next = e.key === "ArrowDown" ? Math.min(i + 1, items.length - 1) : Math.max(i - 1, 0);
        items[next].focus();
      }
    });
    return abrir;
  }

  // Una opción de la lista; "llenar" pone el contenido (texto, bandera...).
  function opcionDesplegable(seleccionada, llenar, alElegir) {
    const li = document.createElement("li");
    li.setAttribute("role", "option");
    li.setAttribute("aria-selected", String(seleccionada));
    li.tabIndex = 0;
    llenar(li);
    li.addEventListener("click", alElegir);
    li.addEventListener("keydown", e => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); alElegir(); }
    });
    return li;
  }

  function textoEn(el, texto) {
    const span = document.createElement("span");
    span.textContent = texto;
    el.replaceChildren(span);
  }

  // 🌳 FILTRO POR ANCESTRO: padres y abuelos que aparecen en los caminos.
  const GEN_LABELS = { 1: "Padres", 2: "Abuelos", 3: "Bisabuelos" };
  const ancestroDropdown = document.getElementById("filtro-ancestro");
  const ancestroBtn = ancestroDropdown?.querySelector(".pais-dropdown-btn");
  const ancestroList = ancestroDropdown?.querySelector(".pais-dropdown-list");
  const abrirAncestros = conectarDesplegable(ancestroDropdown);

  function elegirAncestro(id) {
    window.activeAncestorFilter = id || null;
    abrirAncestros(false);
    update();
  }

  // Opciones: todos los ancestros de la lista activa (switches de cónyuge).
  // Conteos: sobre countList (la lista con tema y cercanía aplicados).
  function buildAncestorOptions(countList) {
    if (!ancestroBtn || !ancestroList) return;

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

    // Si nada cambió (mismas opciones, conteos y selección) no se toca el DOM.
    const sig = JSON.stringify([
      window.activeAncestorFilter,
      [...found.entries()].map(([id, e]) => [id, e.gen, e.count])
    ]);
    if (ancestroDropdown.dataset.sig === sig) return;
    ancestroDropdown.dataset.sig = sig;

    const activo = window.activeAncestorFilter;
    const nombreDe = (person, gen) => {
      const term = ancestorTerm(gen, person.gender === "FEMALE");
      return `${term.charAt(0).toUpperCase()}${term.slice(1)} — ${person.nombre || person.id}`;
    };

    const elegido = activo && found.get(activo);
    textoEn(ancestroBtn.querySelector(".pais-dropdown-value"),
      elegido ? nombreDe(elegido.person, elegido.gen) : "Todas las ramas");
    ancestroBtn.disabled = found.size === 0;

    ancestroList.replaceChildren(
      opcionDesplegable(!activo, li => textoEn(li, "Todas las ramas"), () => elegirAncestro(null))
    );

    const byGen = new Map();
    [...found.values()]
      .sort((x, y) => x.gen - y.gen || (x.person.nombre || "").localeCompare(y.person.nombre || ""))
      .forEach(e => {
        if (!byGen.has(e.gen)) byGen.set(e.gen, []);
        byGen.get(e.gen).push(e);
      });

    byGen.forEach((entries, gen) => {
      const titulo = document.createElement("li");
      titulo.className = "pais-dropdown-grupo";
      titulo.setAttribute("role", "presentation");
      titulo.textContent = GEN_LABELS[gen] || `Generación ${gen}`;
      ancestroList.appendChild(titulo);

      entries.forEach(({ person, count }) => {
        const texto = nombreDe(person, gen)
          + (person.lifespan ? ` (${person.lifespan})` : "")
          + ` · ${count} ${count === 1 ? "árbol" : "árboles"}`;
        ancestroList.appendChild(opcionDesplegable(
          person.id === activo, li => textoEn(li, texto), () => elegirAncestro(person.id)
        ));
      });
    });
  }

  // Código ISO de cada país para mostrar su bandera (flagcdn.com).
  // Para un país nuevo del CSV hay que agregarlo acá; si falta, no se muestra bandera.
  const PAIS_ISO = {
    "Uruguay": "uy", "Argentina": "ar", "Brasil": "br", "Chile": "cl", "Paraguay": "py",
    "México": "mx", "España": "es", "Italia": "it", "Portugal": "pt", "Francia": "fr",
    "Alemania": "de", "Reino Unido": "gb", "Estados Unidos": "us", "Perú": "pe",
    "Bolivia": "bo", "Colombia": "co", "Venezuela": "ve", "Cuba": "cu"
  };

  function banderaImg(pais) {
    const iso = pais && PAIS_ISO[pais];
    if (!iso) return null;
    const img = document.createElement("img");
    img.className = "pais-bandera";
    img.src = `https://flagcdn.com/w40/${iso}.png`;
    img.alt = "";
    return img;
  }

  // 🌎 FILTRO POR PAÍS (columna "pais" de famosos.csv)
  // Desplegable propio (no <select>) para poder mostrar la bandera en cada opción.
  // Opciones: todos los países de la lista activa. Conteos: sobre countList.
  const paisDropdown = document.getElementById("filtro-pais");
  const paisBtn = paisDropdown?.querySelector(".pais-dropdown-btn");
  const paisList = paisDropdown?.querySelector(".pais-dropdown-list");

  const abrirPaises = conectarDesplegable(paisDropdown);

  function elegirPais(pais) {
    window.activePaisFilter = pais || null;
    abrirPaises(false);
    update();
  }

  function contenidoPais(el, pais, texto) {
    el.replaceChildren();
    const img = banderaImg(pais);
    if (img) el.appendChild(img);
    const span = document.createElement("span");
    span.textContent = texto;
    el.appendChild(span);
  }

  function buildPaisOptions(countList) {
    if (!paisDropdown || !paisBtn || !paisList) return;

    const counts = new Map();
    (getActiveList() || []).forEach(a => (a.paises || []).forEach(p => counts.has(p) || counts.set(p, 0)));
    (countList || []).forEach(a => (a.paises || []).forEach(p => counts.has(p) && counts.set(p, counts.get(p) + 1)));

    if (window.activePaisFilter && !counts.has(window.activePaisFilter)) {
      window.activePaisFilter = null;
    }

    // Más árboles primero; si empatan, por nombre.
    const paises = [...counts.entries()].sort((x, y) => y[1] - x[1] || x[0].localeCompare(y[0]));

    const sig = JSON.stringify([window.activePaisFilter, paises]);
    if (paisDropdown.dataset.sig === sig) return;
    paisDropdown.dataset.sig = sig;

    const activo = window.activePaisFilter;
    contenidoPais(paisBtn.querySelector(".pais-dropdown-value"), activo, activo || "Todos los países");
    paisBtn.disabled = paises.length === 0;

    paisList.replaceChildren();
    [[null, null], ...paises].forEach(([pais, n]) => {
      paisList.appendChild(opcionDesplegable(
        (pais || null) === (activo || null),
        li => contenidoPais(li, pais, pais ? `${pais} · ${n} ${n === 1 ? "árbol" : "árboles"}` : "Todos los países"),
        () => elegirPais(pais)
      ));
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

  if (cercaniaSlider) {
    const mostrarValor = () => mostrarValorCercania(cercaniaSlider);
    mostrarValor();

    // Como mucho un redibujo por cuadro mientras se arrastra la barra.
    let redibujoPendiente = false;
    cercaniaSlider.addEventListener("input", () => {
      mostrarValor();
      if (redibujoPendiente) return;
      redibujoPendiente = true;
      requestAnimationFrame(() => {
        redibujoPendiente = false;
        update();
      });
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