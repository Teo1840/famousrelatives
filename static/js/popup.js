import { buildGraph } from '/static/js/graph.js';
import { getActiveList } from './main.js';
import { generarUUID } from './utils.js';

export function showPopup(currentIndex) {
  const list = getActiveList();
  const a = list[currentIndex];
  if (!a) return;

  const toggle = document.getElementById("switch-coParentIsTargetPerson");

  renderPopupInfo(a);

  requestAnimationFrame(() => {
    renderGraph(a, toggle?.checked);
  });

  document.getElementById('popup').style.display = 'flex';
}

function renderGraph(a, useDirectPath) {
  const container = document.getElementById('mynetwork');
  if (!container) return;

  // 🔥 limpiar contenido previo
  container.innerHTML = "";

  const { nodes, edges } = buildGraph(
    a,
    generarUUID,
    useDirectPath
  );

  // 🔥 destruir grafo anterior
  if (window.network) {
    window.network.destroy();
    window.network = null;
  }

  if (!nodes.length) {
    container.innerHTML = "<p>No hay datos para mostrar</p>";
    return;
  }

  const data = {
    nodes: new vis.DataSet(nodes),
    edges: new vis.DataSet(edges)
  };

  const options = {
    physics: false,
    edges: {
      smooth: {
        type: "cubicBezier",
        roundness: 0.5
      }
    }
  };

  window.network = new vis.Network(container, data, options);
  window.network.fit();
}

function renderPopupInfo(a) {
  const container = document.getElementById('popup-body');
  if (!container) return;

  const showDirect = document.getElementById("switch-coParentIsTargetPerson")?.checked;

  const valor = showDirect
    ? (a.direct_length ?? '')
    : (a.cercania ?? '');

  container.innerHTML = `
    <h3>${a.name}</h3>
    <img src="${a.portraitUrl || 'https://via.placeholder.com/200'}" width="200">
    <p><i>${a.relationshipDescription || ''}</i></p>
    <p><b>${'Cercanía'}:</b> ${valor}</p>
    <pre>${a.detalle || ''}</pre>
  `;
}

export function closePopup() {
  const popup = document.getElementById('popup');
  if (popup) {
    popup.style.display = 'none';
  }

  // 🔥 limpiar grafo al cerrar
  if (window.network) {
    window.network.destroy();
    window.network = null;
  }
}

export function nextPopup(e) {
  e.stopPropagation();

  const list = getActiveList();
  if (!list?.length) return;

  window.currentIndex = (window.currentIndex + 1) % list.length;

  showPopup(window.currentIndex);
}

export function prevPopup(e) {
  e.stopPropagation();

  const list = getActiveList();
  if (!list?.length) return;

  window.currentIndex =
    (window.currentIndex - 1 + list.length) % list.length;

  showPopup(window.currentIndex);
}