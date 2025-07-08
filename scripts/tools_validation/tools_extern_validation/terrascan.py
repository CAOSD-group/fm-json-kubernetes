"""
External Tool Validation Wrapper

This script is part of the External Tool Validation Framework, which automates the
execution of third-party tools to validate Kubernetes YAML configuration files.

General behavior:
- Iterate over YAML files in a directory
- Run a specific CLI tool for validation
- Capture and log results
- Optionally format the output as JSON or CSV

Each tool wrapper handles CLI flags, output parsing, and error management for the
corresponding validator. All results are later aggregated using a summary script.

For full documentation and benchmarking results, see the README.md file
included in this module.

Tool handled:

Tool: Terrascan
URL: https://github.com/tenable/terrascan
Purpose: Detect security and compliance issues in IaC (including Kubernetes).
Notes: Use flag `-i k8s` for Kubernetes input. JSON output supported.
"""

import os
import json
import csv
from pathlib import Path
from collections import defaultdict

# Configuraciones
RESULTS_DIR = "../../resources/results_data_tools/results_terrascan"
CSV_OUTPUT = "../../evaluation/validation_results_terrascan_final.csv"
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

    # Extraer violaciones
    violations = data.get("results", {}).get("violations", [])

    # Agrupar violaciones por archivo
    violated_by_file = defaultdict(list)
    for v in violations:
        file_name = os.path.basename(v.get("file", "unknown"))
        rule_name = v.get("rule_name", "unknown")
        violated_by_file[file_name].append(rule_name)

    # Leer la lista de archivos procesados en el batch
    batch_file_list = f"batch_{batch_id[-2:]}"  # Asume que batch_id es como "batch_aa", "batch_ab", etc.
    if not os.path.exists(batch_file_list):
        print(f"Archivo de batch no encontrado: {batch_file_list}")
        continue

    with open(batch_file_list, "r", encoding="utf-8") as bf:
        all_files_in_batch = [os.path.basename(line.strip()) for line in bf if line.strip()]

    # Calcular tiempo promedio
    avg_time_per_file = 0
    total_files = len(all_files_in_batch)
    avg_time_per_file = round(batch_times.get(batch_id, 0) / total_files, 2) if total_files else 0

    for fname in all_files_in_batch:
        if fname in violated_by_file:
            rows.append([fname, "false", avg_time_per_file, ";".join(violated_by_file[fname])])
        else:
            rows.append([fname, "true", avg_time_per_file, ""])

# Guardar CSV
with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["file", "valid", "avg_validation_time_ms", "failed_checks"])
    writer.writerows(rows)

print(f"CSV generado en: {CSV_OUTPUT}")