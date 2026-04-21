def validate_person_code(person_code):
    """Valida que el código tenga el formato correcto, por ejemplo ABC1-23D"""
    import re
    if not isinstance(person_code, str):
        raise ValueError("El código debe ser un string")
    pattern = r"^[A-Z0-9]{4}-[A-Z0-9]{3}$"
    if not re.match(pattern, person_code):
        raise ValueError(f"Código inválido: {person_code}")
    return person_code

def validate_parent_code(parent_code):
    """Valida parent_code según las mismas reglas que person_code"""
    if parent_code == "":
        return parent_code  # permitido vacío
    return validate_person_code(parent_code)

def validate_name(name):
    """Valida que el nombre no esté vacío y sea un string"""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Nombre inválido")
    return name.strip()

def validate_info(info):
    """Opcional: valida que info sea un string, máximo 200 caracteres"""
    if not isinstance(info, str):
        raise ValueError("Info debe ser una cadena")
    if len(info) > 200:
        raise ValueError("Info demasiado larga (máx. 200 caracteres)")
    return info.strip()

def validate_row(row):
    """
    Valida una fila completa del CSV.
    row: dict con keys: person_code, parent_code, name, info
    Retorna fila validada o lanza ValueError si algo no es válido.
    """
    return {
        "person_code": validate_person_code(row["person_code"]),
        "parent_code": validate_parent_code(row.get("parent_code", "")),
        "name": validate_name(row["name"]),
        "info": validate_info(row["info"])
    }