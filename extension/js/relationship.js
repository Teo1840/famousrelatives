export function ancestorTerm(n, female) {
  const s = female ? "a" : "o";
  if (n === 1) return female ? "madre" : "padre";
  if (n === 2) return `abuel${s}`;
  if (n === 3) return `bisabuel${s}`;
  if (n === 4) return `tatarabuel${s}`;
  const degree = n - 3;
  return `${degree}° tatarabuel${s}`;
}

function descendantTerm(n, female) {
  const s = female ? "a" : "o";
  if (n === 1) return female ? "hija" : "hijo";
  if (n === 2) return `niet${s}`;
  if (n === 3) return `bisniet${s}`;
  if (n === 4) return `tataranieto${female ? "a" : ""}`;
  const degree = n - 3;
  return `${degree}° tataranieto${female ? "a" : ""}`;
}

const ORDINALS_MALE   = ["", "", "segundo", "tercero", "cuarto", "quinto", "sexto", "séptimo", "octavo", "noveno", "décimo"];
const ORDINALS_FEMALE = ["", "", "segunda", "tercera", "cuarta", "quinta", "sexta", "séptima", "octava", "novena", "décima"];

function ordinal(n, female) {
  const list = female ? ORDINALS_FEMALE : ORDINALS_MALE;
  return n < list.length ? list[n] : `${n}°`;
}

// Parentesco de sangre sin sujeto ("bisabuela", "primo segundo"), o "" si
// los dos lados están vacíos (es la misma persona).
function relationshipTerm(ascLen, descLen, female) {
  let rel;

  if (ascLen === 0 && descLen === 0) return "";

  if (descLen === 0) {
    rel = ancestorTerm(ascLen, female);
  } else if (ascLen === 0) {
    rel = descendantTerm(descLen, female);
  } else {
    const minSide = Math.min(ascLen, descLen);
    const removed = Math.abs(ascLen - descLen);

    if (minSide === 1) {
      if (removed === 0) {
        rel = female ? "hermana" : "hermano";
      } else if (ascLen < descLen) {
        const base = female ? "sobrina" : "sobrino";
        if (descLen === 2) {
          rel = base;
        } else {
          rel = `${base} ${descendantTerm(descLen - 1, female)}`;
        }
      } else {
        const base = female ? "tía" : "tío";
        if (ascLen === 2) {
          rel = base;
        } else {
          rel = `${base} ${ancestorTerm(ascLen - 1, female)}`;
        }
      }
    } else {
      const degree = minSide - 1;
      const base = female ? "prima" : "primo";
      const degStr = degree >= 2 ? ` ${ordinal(degree, female)}` : "";
      const remStr = removed > 0
        ? ` ${removed} ${removed === 1 ? "vez" : "veces"} removid${female ? "a" : "o"}`
        : "";
      rel = `${base}${degStr}${remStr}`;
    }
  }

  return rel;
}

export function computeRelationshipDescription(ascLen, descLen, personName, gender) {
  const rel = relationshipTerm(ascLen, descLen, gender?.toUpperCase() === "FEMALE");
  return rel ? `${personName} es tu ${rel}` : personName;
}

const isFemale = p => p?.gender?.toUpperCase() === "FEMALE";
const isMale = p => p?.gender?.toUpperCase() === "MALE";
const spouseWord = p => isFemale(p) ? "esposa" : isMale(p) ? "esposo" : "cónyuge";
const article = p => isFemale(p) ? "la" : "el";

// Descripción en español del camino que muestra la tarjeta, incluidos los
// parentescos políticos. Reemplaza al texto en inglés de FamilySearch.
// Los nodos que entran por un casamiento (ver processJson en trees.js) no
// cuentan como generaciones: con coParentIsPathPerson, "asc" tiene a mi cónyuge
// de más; si la persona famosa es cónyuge de mi pariente, es el último de "desc".
export function describePath(a, useDirect) {
  const path = useDirect ? a?.directPath : a?.mainPath;
  if (!path?.asc || !path?.desc) return a?.relationshipDescription || "";

  const asc = path.asc;
  const desc = path.desc;
  const viaMySpouse = !!path.coParentIsPathPerson;
  const viaTargetSpouse = !useDirect && !!a.coParentIsTargetPerson && desc.length > 0;

  const ascLen = asc.length - (viaMySpouse ? 1 : 0);
  const descLen = desc.length - (viaTargetSpouse ? 1 : 0);
  const target = desc.at(-1);
  // Mi pariente: la persona famosa, o la persona con la que está casada.
  const relative = (viaTargetSpouse ? desc.at(-2) : target) ?? path.antepasado_comun;

  const rel = relationshipTerm(Math.max(ascLen, 0), Math.max(descLen, 0), isFemale(relative));
  if (!rel) return a.relationshipDescription || "";

  let phrase = `tu ${rel}`;
  if (viaMySpouse) {
    // Lo normal: el último de "asc" soy yo (marcado "conyuge") y antes está mi cónyuge.
    const i = asc.findIndex(p => p.conyuge);
    const mySpouse = i === asc.length - 1 ? asc[i - 1] : null;
    phrase = `${article(relative)} ${rel} de tu ${spouseWord(mySpouse)}`;
  }
  if (viaTargetSpouse) {
    phrase = `${article(target)} ${spouseWord(target)} de ${phrase}`.replace(/ de el /g, " del ");
  }
  return `${a.name} es ${phrase}`;
}
