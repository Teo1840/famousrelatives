import { buildGraph } from '/static/js/graph.js';
import { getActiveList } from './main.js';
import { generarUUID } from './utils.js';

export function showPopup(currentIndex) {
  const list = getActiveList();
  const a = list[currentIndex];
  console.log(currentIndex);
  if (!a) return;

  const toggle = document.getElementById("switch-coParentIsTargetPerson");

  renderPopupInfo(a);
  requestAnimationFrame(() => {
    renderGraph(a, toggle.checked);
  });

  document.getElementById('popup').style.display = 'flex';
}

function renderGraph(a, useDirectPath) {
  const container = document.getElementById('mynetwork');

  const { nodes, edges } = buildGraph(
    a,
    generarUUID,
    useDirectPath
  );

  // limpiar grafo anterior
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

  container.innerHTML = `
    <h3>${a.nombre}</h3>
    <img src="${a.portraitUrl || 'https://via.placeholder.com/200'}" width="200">
    <p><i>${a.relacion || ''}</i></p>
    <p><b>Cercanía:</b> ${a.cercania || ''}</p>
    <pre>${a.detalle || ''}</pre>
  `;
}

export function closePopup() {
  document.getElementById('popup').style.display = 'none';
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