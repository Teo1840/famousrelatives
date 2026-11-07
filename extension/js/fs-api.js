// Consultas a FamilySearch (reemplaza a fs_proxy.py).
// Usa la sesión que el usuario ya tiene abierta en el navegador: la cookie
// fssessionid va como token en el encabezado Authorization.

const FS = "https://www.familysearch.org";

// https://developers.familysearch.org/main/docs/throttling
const RATE_LIMIT_INTERVAL = 0.2;   // segundos entre consultas
const MAX_RETRIES_429 = 3;         // intentos ante "demasiadas consultas"
const MAX_RETRIES_SERVER = 3;      // reintentos ante errores 5xx o de red
const TIMEOUT_MS = 20000;

// FamilySearch confirmó que no hay parentesco (HTTP 204). Distinto de null
// (error pasajero), que nunca se guarda en el cache.
export const NO_RELATIONSHIP = Symbol("NO_RELATIONSHIP");

export class SessionExpired extends Error {
  constructor() { super("SESSION_EXPIRED"); }
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

export async function getToken() {
  const cookie = await chrome.cookies.get({ url: FS + "/", name: "fssessionid" });
  return cookie ? cookie.value : null;
}

// Un turno por consulta, compartido entre todas las búsquedas en paralelo.
let nextSlot = 0;
async function waitTurn(intervalSec) {
  const now = Date.now();
  const start = Math.max(now, nextSlot);
  nextSlot = start + intervalSec * 1000;
  if (start > now) await sleep(start - now);
}

async function fetchWithTimeout(url, options) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

// GET a FamilySearch. Devuelve el JSON, NO_RELATIONSHIP (204) o null (error
// pasajero). Lanza SessionExpired si la sesión no sirve (401).
async function fsGet(url, { accept = "application/json", rate = RATE_LIMIT_INTERVAL } = {}) {
  const token = await getToken();
  if (!token) throw new SessionExpired();

  const options = {
    credentials: "omit",
    headers: { Accept: accept, Authorization: `Bearer ${token}` },
  };

  let serverRetries = 0;
  let attempts429 = 0;

  while (true) {
    await waitTurn(Math.max(RATE_LIMIT_INTERVAL, rate));

    let resp;
    try {
      resp = await fetchWithTimeout(url, options);
    } catch (e) {
      if (serverRetries < MAX_RETRIES_SERVER) {
        await sleep(1000 * 2 ** serverRetries++);
        continue;
      }
      console.warn("Error de conexión:", url, e);
      return null;
    }

    if (resp.status === 429 && ++attempts429 < MAX_RETRIES_429) {
      const retryAfter = Number(resp.headers.get("Retry-After")) || 10;
      console.warn(`429: esperando ${retryAfter}s`);
      nextSlot = Math.max(nextSlot, Date.now() + retryAfter * 1000);
      continue;
    }

    if (resp.status >= 500 && serverRetries < MAX_RETRIES_SERVER) {
      await sleep(1000 * 2 ** serverRetries++);
      continue;
    }

    if (resp.status === 200) return resp.json();
    if (resp.status === 204) return NO_RELATIONSHIP;
    if (resp.status === 401) throw new SessionExpired();

    console.warn(`Error ${resp.status}:`, url, await resp.text().catch(() => ""));
    return null;
  }
}

export function fetchRelationship(personId, rate) {
  return fsGet(
    `${FS}/service/tree/tree-data/user-relationship/v2/person/${personId}?showPortraits=true&enforceTemplePolicyEx=true`,
    { rate }
  );
}

export function fetchFamilyMembers(personId, rate) {
  return fsGet(
    `${FS}/service/tree/tree-data/r9/family-members/person/${personId}?includePhotos=true&treeId=PRIVATE`,
    { rate }
  );
}

export function fetchPortrait(personId) {
  return fsGet(`${FS}/service/memories/tps/persons/${personId}/portrait`);
}

export function fetchCurrentUser() {
  return fsGet(`${FS}/platform/users/current`, {
    accept: "application/x-fs-v1+json, application/json",
  });
}
