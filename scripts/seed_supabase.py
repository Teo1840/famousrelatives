"""Genera supabase/seed.sql con los famosos de famosos.csv y las descripciones
de las categorías, para pegar una vez en el editor SQL de Supabase.

Uso (desde la raíz del proyecto):  python scripts/seed_supabase.py
Se puede volver a correr: actualiza las filas existentes en vez de duplicarlas.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services.csv_validation import validate_csv_file  # noqa: E402

CSV_PATH = os.path.join(ROOT, "famosos.csv")
OUT_PATH = os.path.join(ROOT, "supabase", "seed.sql")

# Copiadas de TOPIC_DESCRIPTIONS en static/js/switch.js.
CATEGORIAS = {
    "Deportistas": "Grupo de deportistas destacados de la región incluyendo futbolistas y pilotos de automovilismo.",
    "Presidentes uruguayos": 'Lista basada en <a href="https://es.wikipedia.org/wiki/Anexo:Gobernantes_de_Uruguay" target="_blank">Wikipedia: Gobernantes de Uruguay</a>.',
    "Treinta y Tres Orientales": (
        'Lista basada en <a href="https://www.geni.com/projects/33-Orientales/8298" target="_blank">Geni: Los 33 Orientales</a>. '
        "Existen al menos 16 versiones distintas de la lista — los integrantes varían según la fuente histórica.<br>"
        "<strong>Orientales no encontrados en FamilySearch</strong> (si los encontrás, ¡agregálos!): "
        "Juan Acosta, Juan Arteaga, Felipe Carapé, Carmelo Colman, Javier Chávez Zibil, Ignacio Medina, Manuel Meléndez, "
        "Avelino Miranda, Santiago Nievas, Ignacio Núñez, Dionisio Oribe, Juan Ortiz, Juan Rosas, Agustín Velázquez, "
        "Andrés Areguatí."
    ),
}


def lit(value):
    """Texto SQL entre comillas simples, o NULL."""
    if value is None:
        return "null"
    return "'" + str(value).replace("'", "''") + "'"


def arr(values):
    """Array SQL de texto, ej. array['a','b']::text[]."""
    return "array[" + ",".join(lit(v) for v in values) + "]::text[]"


def main():
    rows = validate_csv_file(CSV_PATH)
    out = ["-- Generado por scripts/seed_supabase.py — no editar a mano.", ""]

    out.append("insert into famosos (person_code, name, info, topics, paises, wiki) values")
    values = [
        f"  ({lit(r['person_code'])}, {lit(r['name'])}, {lit(r['info'])}, "
        f"{arr(r['topics'])}, {arr(r['paises'])}, {lit(r['wiki'])})"
        for r in rows
    ]
    out.append(",\n".join(values))
    out.append("on conflict (person_code) do update set name = excluded.name, info = excluded.info, "
               "topics = excluded.topics, paises = excluded.paises, wiki = excluded.wiki;")
    out.append("")

    # Todas las categorías usadas, con descripción si la hay.
    usadas = sorted({t for r in rows for t in r["topics"]} | set(CATEGORIAS))
    out.append("insert into categorias (nombre, descripcion) values")
    out.append(",\n".join(f"  ({lit(c)}, {lit(CATEGORIAS.get(c))})" for c in usadas))
    out.append("on conflict (nombre) do update set descripcion = coalesce(excluded.descripcion, categorias.descripcion);")
    out.append("")

    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"{len(rows)} famosos y {len(usadas)} categorías -> {OUT_PATH}")


if __name__ == "__main__":
    main()
