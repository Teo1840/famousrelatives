// Búsqueda y armado de los caminos de parentesco.
// Port de services/tree_functions.py: misma lógica, mismos datos guardados.
import {
  NO_RELATIONSHIP, SessionExpired,
  fetchRelationship, fetchFamilyMembers, fetchPortrait,
} from "./fs-api.js";
import { obtenerArbol, guardarArbol, guardarRetrato } from "./store.js";

// Consultas en paralelo a FamilySearch. Más = más rápido pero más 429.
const MAX_WORKERS = 2;
// Segundos entre consultas durante "Actualizar mis árboles".
const FORCE_REFRESH_RATE_INTERVAL = 0.5;

export const DEFAULT_PORTRAIT_URL = "https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png";

// --Simplificar JSON--
export function buildPerson(person) {
  if (!person) return { nombre: "", id: "", lifespan: "", portraitUrl: null, gender: "" };

  const details = person.nameConclusion?.details || {};
  const isMe = person.relationshipToPrevious === "ME";

  return {
    nombre: details.fullText || "",
    id: person.id || "",
    lifespan: person.lifespan || "",
    // La foto del usuario que da la API necesita autenticación y no carga en <img>;
    // se reemplaza después con la del endpoint de retrato.
    portraitUrl: isMe ? null : (person.portraitUrl ?? null),
    gender: person.gender || "",
  };
}

// --Pasar de JSON a listas--
function processJson(generations) {
  const asc = [];
  const desc = [];
  let ancestor = buildPerson(null);
  let viewerId = null;
  let coParentIsPathPerson = false;

  for (const gen of generations) {
    // Antepasado común
    if (gen.apex) {
      const person = gen.apex.person || {};
      if (person.commonAncestor) ancestor = buildPerson(person);
      else asc.push(buildPerson(person));
      continue;
    }
    // Ascendentes
    const ascSide = gen.ascendingSide;
    if (ascSide) {
      const person = buildPerson(ascSide.person);
      if (ascSide.coParentIsPathPerson) { // la persona es pariente de mi cónyuge
        coParentIsPathPerson = true;
        const coParent = buildPerson(ascSide.coParent);
        // La unión de este nodo con el anterior es un matrimonio, no sangre.
        person.conyuge = true;
        asc.push(coParent);
        asc.push(person);
      } else {
        asc.push(person);
      }
      if (ascSide.indexInPath === 0) viewerId = person.id;
    }
    // Descendentes
    const descSide = gen.descendingSide;
    if (descSide) {
      const person = buildPerson(descSide.person);
      if (descSide.coParentIsTargetPerson) { // la persona es cónyuge de mi pariente
        const coParent = buildPerson(descSide.coParent);
        coParent.conyuge = true;
        desc.push(person);
        desc.push(coParent);
      } else {
        desc.push(person);
      }
    }
  }

  return { asc, desc, ancestor, viewerId, coParentIsPathPerson };
}

function parseTreeData(data) {
  const generations = data?.generations || [];
  if (!generations.length) return null;

  const { asc, desc, ancestor, viewerId, coParentIsPathPerson } = processJson(generations);
  return {
    asc, desc, ancestor, viewerId, coParentIsPathPerson,
    target: data.targetPerson || {},
    relationship: data.relationshipDescription,
  };
}

const pathLength = path => (path.asc?.length || 0) + (path.desc?.length || 0);

const isSpouse = target => ["HUSBAND", "WIFE", "SPOUSE"].includes(target?.relationshipToPrevious);

function buildTreeData(parsed, famoso, extraParsed) {
  const mainPath = {
    asc: parsed.asc,
    desc: parsed.desc,
    antepasado_comun: parsed.ancestor || {},
    coParentIsPathPerson: parsed.coParentIsPathPerson,
  };
  const mainLength = pathLength(mainPath);

  let directPath = null;
  let directLength = mainLength;

  const target = parsed.target;
  const coParentIsTargetPerson = isSpouse(target);

  if ((coParentIsTargetPerson || parsed.coParentIsPathPerson) && extraParsed) {
    const extraDesc = extraParsed.desc.slice();
    if (extraDesc.length) extraDesc.pop();
    extraDesc.push(buildPerson(target));

    directPath = {
      asc: extraParsed.asc,
      desc: extraDesc,
      antepasado_comun: extraParsed.ancestor,
      coParentIsPathPerson: extraParsed.coParentIsPathPerson,
    };
    directLength = pathLength(directPath);
  }

  return {
    person_code: famoso.person_code,
    name: famoso.name,
    info: famoso.info,
    topics: famoso.topics || [],
    cercania: mainLength,
    relationshipDescription: parsed.relationship,
    portraitUrl: target.portraitUrl ?? DEFAULT_PORTRAIT_URL,
    coParentIsTargetPerson,
    mainPath,
    directPath,
    direct_length: directLength,
  };
}

// Árbol que necesita camino directo, no lo tiene y no se confirmó que no exista.
function directPathPending(tree) {
  const needsDirect = tree.coParentIsTargetPerson || tree.mainPath?.coParentIsPathPerson;
  return !!needsDirect && tree.directPath == null && !tree.directPathChecked;
}

// El cache no vence solo: se ignora con "Actualizar mis árboles" o cuando
// la persona es nueva en la lista.
async function getCachedTree(viewer, personCode, forceRefresh) {
  if (forceRefresh) return null;
  const row = await obtenerArbol(viewer, personCode);
  if (!row) return null;
  if (!row.found) return NO_RELATIONSHIP;
  const data = row.data;
  if (data?.name && data?.person_code && !directPathPending(data)) return data;
  return null;
}

// (parentId, ok). ok=false si la consulta falló (error pasajero).
async function fetchParentId(personId, rate) {
  const data = await fetchFamilyMembers(personId, rate);
  if (data === null) return [null, false];
  if (data === NO_RELATIONSHIP) return [null, true];
  const first = (data.parents || [])[0];
  if (!first) return [null, true];
  const id = first.parent1?.id || first.parent2?.id || null;
  return [id, true];
}

async function processOne(famoso, viewer, forceRefresh, rate) {
  const code = famoso.person_code;

  const cached = await getCachedTree(viewer, code, forceRefresh);
  if (cached === NO_RELATIONSHIP) return null;
  if (cached) return cached;

  const data = await fetchRelationship(code, rate);
  if (data === null) return null; // error pasajero: no se guarda

  const parsed = data === NO_RELATIONSHIP ? null : parseTreeData(data);
  if (!parsed) {
    await guardarArbol(viewer, code, null, false);
    return null;
  }

  // Si el camino pasa por un cónyuge, se busca además el camino de sangre
  // a través de un padre de la persona.
  let extraParsed = null;
  let directChecked = true;
  if (isSpouse(parsed.target) || parsed.coParentIsPathPerson) {
    const [parentId, ok] = await fetchParentId(code, rate);
    if (parentId) {
      const extra = await fetchRelationship(parentId, rate);
      if (extra === null) directChecked = false;
      else if (extra !== NO_RELATIONSHIP) extraParsed = parseTreeData(extra);
    } else if (!ok) {
      directChecked = false;
    }
  }

  const tree = buildTreeData(parsed, famoso, extraParsed);
  tree.directPathChecked = directChecked;
  await guardarArbol(viewer, code, tree, true);
  return tree;
}

// Busca a todos los famosos (usa lo guardado salvo forceRefresh).
// onProgress(current, total) se llama al terminar cada persona.
// Lanza SessionExpired si la sesión de FamilySearch se cierra a mitad.
export async function generateTrees(famosos, viewer, { forceRefresh = false, onProgress } = {}) {
  const rate = forceRefresh ? FORCE_REFRESH_RATE_INTERVAL : undefined;
  const total = famosos.length;
  let done = 0;
  let next = 0;
  let expired = null;

  async function worker() {
    while (!expired && next < famosos.length) {
      const famoso = famosos[next++];
      try {
        await processOne(famoso, viewer, forceRefresh, rate);
      } catch (e) {
        if (e instanceof SessionExpired) { expired = e; break; }
        console.error(`Error procesando ${famoso.name}:`, e);
      }
      onProgress?.(++done, total);
    }
  }

  await Promise.all(Array.from({ length: MAX_WORKERS }, worker));
  if (expired) throw expired;

  // Foto de perfil del usuario: se guarda aparte y se aplica al mostrar.
  try {
    const portrait = await fetchPortrait(viewer);
    const url = portrait && portrait !== NO_RELATIONSHIP ? portrait._links?.thumbSquare?.href : null;
    if (url) await guardarRetrato(viewer, url);
  } catch (e) {
    if (e instanceof SessionExpired) throw e;
    console.warn("No se pudo obtener la foto de perfil:", e);
  }
}

export function applyViewerPortrait(tree, viewerId, portraitUrl) {
  for (const key of ["mainPath", "directPath"]) {
    const path = tree[key];
    if (!path) continue;
    for (const list of [path.asc || [], path.desc || []]) {
      for (const node of list) {
        if (node.id === viewerId) node.portraitUrl = portraitUrl;
      }
    }
  }
}
