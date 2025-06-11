import os
import csv
from pathlib import Path

# Configuraciones
RESULTS_DIR = "./results_trivy"
CSV_OUTPUT = "./results/trivy/validation_results.csv"
TIMING_FILE = os.path.join(RESULTS_DIR, "batch_times.txt")

Path(CSV_OUTPUT).parent.mkdir(parents=True, exist_ok=True)

# Cargar tiempos por batch
batch_times = {}
with open(TIMING_FILE, "r") as f:
    for line in f:
        batch_id, time_ms = line.strip().split(",")
        batch_times[batch_id] = int(time_ms)

rows = []

def parse_trivy_table_lines(content):
    result = []
    for line in content.splitlines():
        line = line.strip()

        # Detecta filas de contenido con al menos 3 columnas delimitadas por │
        if line.startswith("│") and line.endswith("│"):
            parts = line.split("│")
            if 'Target' == parts[1].strip():
                continue
            if len(parts) >= 4:
                target = parts[1].strip()
                misconf_count = parts[3].strip()
                result.append((target, misconf_count))
        if line.startswith("Legend"): ## Se usa para detectar el final de la tabla, ya no hay mas datos de la tabla
            print(f"Se detecta el final de la tabla, muestra de leyenda")
            break
    return result

# Procesar cada archivo de resultados
for filename in os.listdir(RESULTS_DIR):
    if not filename.endswith(".txt"):
        continue

    batch_id = filename.replace(".txt", "")
    filepath = os.path.join(RESULTS_DIR, filename)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    table_data = parse_trivy_table_lines(content)

    """if not table_data: ## 
        print(table_data)
        print(f"No se encontró tabla en: {filename}")
        continue"""

    total_files = len(table_data)
    avg_time = round(batch_times.get(batch_id, 0) / total_files, 2) if total_files else 0

    for fname, misconf_count in table_data:
        is_valid = "true" if misconf_count == "0" else "false"
        rows.append([fname, is_valid, avg_time, misconf_count])

# Guardar resultados en CSV
with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["file", "valid", "avg_validation_time_ms", "misconfiguration_count"])
    writer.writerows(rows)

print(f"CSV generado en: {CSV_OUTPUT}")