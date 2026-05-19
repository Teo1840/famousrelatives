import csv
import logging
from services.validators import validate_row

REQUIRED_COLUMNS = {"person_code", "name", "info"}

def validate_csv_schema(headers):
    headers_set = set(headers)

    missing = REQUIRED_COLUMNS - headers_set
    extra = headers_set - REQUIRED_COLUMNS

    errors = []

    if missing:
        errors.append(f"Faltan columnas requeridas: {', '.join(missing)}")

    # opcional: decidir si querés permitir extras
    if extra:
        errors.append(f"Columnas desconocidas: {', '.join(extra)}")

    if errors:
        raise ValueError(" | ".join(errors))


def validate_csv_file(file_path):
    valid_rows = []
    seen = set()

    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=";")

        validate_csv_schema(reader.fieldnames)

        for i, row in enumerate(reader, start=2):

            if not any(row.values()):
                continue

            try:
                validated = validate_row(row)

                if validated["person_code"] in seen:
                    logging.warning(f"Fila {i}: person_code duplicado, omitiendo")
                else:
                    seen.add(validated["person_code"])
                    valid_rows.append(validated)

            except Exception as e:
                logging.warning(f"Fila {i}: {e}, omitiendo")

    return valid_rows