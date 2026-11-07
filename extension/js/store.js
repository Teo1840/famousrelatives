// Resultados guardados en el navegador (reemplaza a MySQL / db/db.py).
// Cada cuenta de FamilySearch (viewer = su personId) tiene sus propios datos,
// así dos personas que usan la misma computadora no se mezclan.

const DB_NAME = "famousrelatives";
const DB_VERSION = 1;

let dbPromise = null;

function openDB() {
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        const arboles = db.createObjectStore("arboles", { keyPath: ["viewer", "person_code"] });
        arboles.createIndex("viewer", "viewer");
        db.createObjectStore("retratos", { keyPath: "viewer" });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  return dbPromise;
}

async function run(storeName, mode, fn) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, mode);
    const req = fn(tx.objectStore(storeName));
    tx.oncomplete = () => resolve(req?.result);
    tx.onerror = () => reject(tx.error);
  });
}

// { viewer, person_code, data, found, created_at } o undefined.
export function obtenerArbol(viewer, personCode) {
  return run("arboles", "readonly", s => s.get([viewer, personCode]));
}

// found=false: FamilySearch confirmó que no hay parentesco (cache negativo).
export function guardarArbol(viewer, personCode, data, found = true) {
  return run("arboles", "readwrite", s => s.put({
    viewer, person_code: personCode, data: found ? data : null, found, created_at: Date.now(),
  }));
}

export function obtenerArbolesUsuario(viewer) {
  return run("arboles", "readonly", s => s.index("viewer").getAll(viewer));
}

export async function obtenerIdsProcesados(viewer) {
  const rows = await obtenerArbolesUsuario(viewer);
  return new Set(rows.map(r => r.person_code));
}

export function guardarRetrato(viewer, url) {
  return run("retratos", "readwrite", s => s.put({ viewer, url }));
}

export async function obtenerRetrato(viewer) {
  const row = await run("retratos", "readonly", s => s.get(viewer));
  return row ? row.url : null;
}

export async function borrarUsuario(viewer) {
  const rows = await obtenerArbolesUsuario(viewer);
  await run("arboles", "readwrite", s => {
    rows.forEach(r => s.delete([viewer, r.person_code]));
    return null;
  });
  await run("retratos", "readwrite", s => s.delete(viewer));
}
