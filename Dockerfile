# Imagen base de Python
FROM python:3.14

# Copiar el requirements y luego instalar dependencias
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiar archivos del proyecto
COPY app.py /app/app.py
COPY tree_functions.py /app/tree_functions.py
COPY db.py /app/db.py
COPY famosos.csv /app/famosos.csv
COPY templates /app/templates

WORKDIR /app

CMD ["python", "app.py"]