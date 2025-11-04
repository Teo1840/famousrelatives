# MAIN
import csv
from arboles_funciones import procesar_codigos, generar_arbol_html
import webbrowser
import os
import datetime

# Configuración REQUEST
CSV_PATH = "C:/Users/Usuario/Desktop/famousrelatives/famosos.csv"
TOKEN = "p0-uYeW2gDA2w0.h5A5GcBXfs1"
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140.0.0.0 Safari/537.36",
    "Accept": "application/json",
}
cookies = {"fssessionid": TOKEN,    }

# Leer códigos desde CSV
codigos = []
with open(CSV_PATH, encoding="cp1252") as f:
    reader = csv.reader(f)
    for row in reader:
        if row and row[0] != "codigo_persona;nombre;info":
            codigos.append(row[0])

# Procesar CSV y generar arboles
mini_arboles = procesar_codigos(codigos, headers, cookies)
mini_arboles_ordenados = sorted(mini_arboles, key=lambda a: a["cercania"]) # Ordenar los árboles por cercania
print(f"Se generaron {len(mini_arboles)} mini árboles.")

# Generar HTML con los arboles y crear archivo
html_content = generar_arbol_html(mini_arboles_ordenados)
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
file_name = f"mini_arboles_{timestamp}.html"
file_path = os.path.join(r"C:\Users\Usuario\Desktop\famousrelatives\mini_arboles",file_name)
with open(file_path, "w", encoding="utf-8") as file:
    file.write(html_content)

# Abrir en navegador
webbrowser.open(f"file://{file_path}")