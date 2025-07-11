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

Tool: Trivy
URL: https://github.com/aquasecurity/trivy
Purpose: Kubernetes and container security scanner.
Notes: YAML validation must be configured; results filtered from Trivy’s full output.
"""

import os
import csv
from pathlib import Path

# Configuraciones
RESULTS_DIR = "../../../resources/results_data_tools/results_trivy01"
YAML_DIR ="../../../resources/yamls_agrupation/yamls-tools-files"
CSV_OUTPUT = "../../../evaluation/validation_results_trivy_final.csv"
TIMING_FILE = os.path.join(RESULTS_DIR, "batch_times.txt")

Path(CSV_OUTPUT).parent.mkdir(parents=True, exist_ok=True)

# Cargar tiempos por batch
batch_times = {}
with open(TIMING_FILE, "r") as f:
    for line in f:
        batch_id, time_ms = line.strip().split(",")
        batch_times[batch_id] = int(time_ms)

# Diccionario de resultados por archivo
results = {}  # fname -> (is_valid, avg_time, misconf_count)

def parse_trivy_table_lines(content):
    result = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("│") and line.endswith("│"):
            parts = line.split("│")
            if 'Target' == parts[1].strip():
                continue
            if len(parts) >= 4:
                target = parts[1].strip()
                misconf_count = parts[3].strip()
                result.append((target, misconf_count))
        if line.startswith("Legend"):
            print("Se detecta el final de la tabla, muestra de leyenda")
            break
    return result

# Procesar resultados
for filename in os.listdir(RESULTS_DIR):
    if not filename.endswith(".txt"):
        continue

    batch_id = filename.replace(".txt", "")
    filepath = os.path.join(RESULTS_DIR, filename)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    table_data = parse_trivy_table_lines(content)
    total_files = len(table_data)
    avg_time = round(batch_times.get(batch_id, 0) / total_files, 2) if total_files else 0

    for fname, misconf_count in table_data:
        try:
            misconf_count = int(misconf_count)
        except ValueError:
            misconf_count = 0
        is_valid = misconf_count == 0
        results[fname] = (is_valid, avg_time, misconf_count)

# Revisión contra el directorio de YAMLs (no usamos _expected.txt)
yaml_files = {f.name for f in Path(YAML_DIR).rglob("*.yaml")}

# Detectar YAMLs que no fueron mencionados en ningún resultado
missing_yamls = yaml_files - set(results.keys())
if missing_yamls:
    #print(" Archivos YAML no reportados por Trivy:")
    for mf in sorted(missing_yamls):
        #print(f"  - {mf}")
        results[mf] = (True, 0, 0)

# Guardar CSV y resumen
true_count = 0
false_count = 0

with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["file", "valid", "avg_validation_time_ms", "misconfiguration_count"])

    for fname in sorted(results.keys()):
        is_valid, avg_time, misconf_count = results[fname]
        writer.writerow([fname, str(is_valid).lower(), avg_time, misconf_count])
        if is_valid:
            true_count += 1
        else:
            false_count += 1

    writer.writerow([])
    writer.writerow(["TOTAL_VALID", true_count])
    writer.writerow(["TOTAL_INVALID", false_count])

print(f"\n Archivos válidos (true): {true_count}")
print(f" Archivos inválidos (false): {false_count}")
print(f" CSV generado en: {CSV_OUTPUT}")