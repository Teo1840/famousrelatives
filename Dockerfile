# Imagen base de Python
FROM python:3.12

# Instalar el conector de MySQL
RUN pip install mysql-connector-python

# Copiar archivos de tu proyecto
COPY app.py /app/app.py
COPY tablas.sql /app/tablas.sql

WORKDIR /app

# Comando por defecto al iniciar el contenedor
CMD ["python", "app.py"]