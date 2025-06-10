import os
import json
import csv
from pathlib import Path
from collections import defaultdict

# Configuraciones
RESULTS_DIR = "./results_terrascan"
CSV_OUTPUT = "./results/terrascan/validation_results.csv"
TIMING_FILE = os.path.join(RESULTS_DIR, "batch_times.txt")

# Crear directorio para CSV si no existe
Path(CSV_OUTPUT).parent.mkdir(parents=True, exist_ok=True)

# 1. Cargar tiempos por batch
batch_times = {}
with open(TIMING_FILE, "r") as f:
    for line in f:
        batch_id, time_ms = line.strip().split(",")
        batch_times[batch_id] = int(time_ms)

rows = []

# 2. Procesar cada JSON de resultados en el directorio
for filename in os.listdir(RESULTS_DIR):
    if not filename.endswith(".json"):
        continue

    batch_id = filename.replace(".json", "")
    json_path = os.path.join(RESULTS_DIR, filename)

    with open(json_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error de JSON en {filename}")
            continue

    # Extraer violaciones y errores de escaneo
    violations = data.get("results", {}).get("violations", [])
    scan_errors = data.get("results", {}).get("scan_errors", [])

    # Agrupar violaciones por archivo
    violated_by_file = defaultdict(list)
    for v in violations:
        file_name = v.get("file", "unknown")
        rule_name = v.get("rule_name", "unknown")
        violated_by_file[file_name].append(rule_name)

    # Archivos con errores de escaneo
    errored_files = set()
    for err in scan_errors:
        msg = err.get("errMsg", "")
        # Si el mensaje contiene nombre de archivo, extraerlo
        if "file '" in msg:
            path = msg.split("file '")[-1].split("'")[0]
            errored_files.add(os.path.basename(path))
        else:
            # Si no, puede que tengamos solo directorio u otro texto, opcionalmente se puede agregar un identificador genérico
            errored_files.add("scan_error_generic")

    # Conjunto de todos los archivos afectados
    all_files = set(violated_by_file.keys()) | errored_files

    # Calcular tiempo promedio por archivo en este batch (dividir tiempo total batch por cantidad de archivos)
    avg_time_per_file = 0
    total_files_in_batch = max(len(all_files), 1)  # para evitar división por cero
    avg_time_per_file = round(batch_times.get(batch_id, 0) / total_files_in_batch, 2)

    # Construir filas para CSV
    for fname in all_files:
        is_valid = "false"
        failed_rules = violated_by_file.get(fname, [])
        if fname in errored_files:
            failed_rules.append("scan_error")
        rows.append([fname, is_valid, avg_time_per_file, ";".join(failed_rules)])

# Guardar CSV
with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["file", "valid", "avg_validation_time_ms", "failed_checks"])
    writer.writerows(rows)

print(f"CSV generado en: {CSV_OUTPUT}")