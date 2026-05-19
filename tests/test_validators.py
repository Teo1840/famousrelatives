import pytest

#python -m pytest -v

from services.validators import (
    validate_person_code,
    validate_name,
    validate_info,
    validate_row
)

from services.csv_validation import (
    validate_csv_file
)

# -------------------
# person_code
# -------------------

def test_valid_person_code():
    assert validate_person_code("AB12-3CD") == "AB12-3CD"

def test_invalid_person_code_format():
    with pytest.raises(ValueError):
        validate_person_code("abc-123")

def test_person_code_not_string():
    with pytest.raises(ValueError):
        validate_person_code(123)

# -------------------
# name
# -------------------

def test_valid_name():
    assert validate_name("  Juan Perez  ") == "Juan Perez"

def test_empty_name():
    with pytest.raises(ValueError):
        validate_name("")

# -------------------
# info
# -------------------

def test_valid_info():
    assert validate_info("Algo") == "Algo"

def test_info_too_long():
    with pytest.raises(ValueError):
        validate_info("a" * 201)

# -------------------
# row
# -------------------

def test_valid_row():
    row = {
        "person_code": "AB12-3CD",
        "name": "Juan",
        "info": "Test"
    }

    result = validate_row(row)

    assert result["person_code"] == "AB12-3CD"
    assert result["name"] == "Juan"
    assert result["info"] == "Test"

def test_invalid_row():
    row = {
        "person_code": "bad",
        "name": "",
        "info": "ok"
    }

    with pytest.raises(ValueError):
        validate_row(row)

def test_csv_ok(tmp_path):
    file = tmp_path / "test.csv"
    file.write_text(
        "person_code;name;info\n"
        "AB12-3CD;Juan;Hola\n"
    )

    rows = validate_csv_file(file)
    assert len(rows) == 1


def test_csv_missing_column(tmp_path):
    file = tmp_path / "test.csv"
    file.write_text(
        "person_code;name\n"
        "AB12-3CD;Juan\n"
    )

    with pytest.raises(ValueError):
        validate_csv_file(file)


def test_csv_duplicate(tmp_path):
    file = tmp_path / "test.csv"
    file.write_text(
        "person_code;name;info\n"
        "AB12-3CD;Juan;Hola\n"
        "AB12-3CD;Maria;Test\n"
    )

    rows = validate_csv_file(file)
    assert len(rows) == 1  # duplicate is skipped silently

def test_name_trimming():
    assert validate_name("  Juan  ") == "Juan"


def test_info_trimming():
    assert validate_info("  Hola  ") == "Hola"

def test_person_code_lowercase():
    with pytest.raises(ValueError):
        validate_person_code("ab12-3cd")