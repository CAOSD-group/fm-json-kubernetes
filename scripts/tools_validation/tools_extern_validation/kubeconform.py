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

Tool: kubeconform
URL: https://github.com/yannh/kubeconform
Purpose: Schema validation of Kubernetes manifests using JSON schemas.
Notes: Fast, strict, supports local schemas.
"""

import json
import csv
from pathlib import Path
from collections import defaultdict

json_dir = Path('../../resources/results_data_tools/results_kubeconform02')
csv_output = '../../evaluation/validation_results_kubeconform_final.csv'
timing_file = json_dir / "batch_times.txt"

results = defaultdict(lambda: {
    "valid": True,
    "avg_time": 0.0,
    "status": "valid",
    "msg": ""
})

# Leer duración por batch
batch_times = {}
if timing_file.exists():
    with open(timing_file, encoding="utf-8") as tf:
        for line in tf:
            parts = line.strip().split(",")
            if len(parts) == 2:
                batch_name, duration_str = parts
                try:
                    batch_times[batch_name] = float(duration_str)
                except ValueError:
                    continue

# Procesar archivos JSON por batch
for json_file in json_dir.glob("*.json"):
    with open(json_file, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f" Archivo JSON inválido: {json_file}")
            continue

    entries = data.get("resources", [])
    for entry in entries:
        fname = Path(entry.get("filename", "")).name
        status = entry.get("status", "valid")
        msg = entry.get("msg", "")
        valid = status == "valid"
        results[fname] = {
            "valid": valid,
            "avg_time": 0.0,  # Se sobrescribirá luego con el valor correcto
            "status": status,
            "msg": msg
        }

# Incluir válidos que no están explícitos en los JSON
input_dir = Path('../scriptJsonToUvl/yamls_agrupation/yamls-tools-files')
#input_dir=Path('./small')

for file in input_dir.rglob("*.yaml"):
    fname = file.name
    if fname not in results:
        results[fname] = {
            "valid": True,
            "avg_time": 0.0,            
            "status": "valid",
            "msg": ""
        }

# Estadísticas
total = len(results)
valid_count = sum(1 for r in results.values() if r["valid"])
invalid_count = total - valid_count

# Aplicar tiempos promedio por lotes reales
BATCH_SIZE = 300  # Igual que el definido en el script de bash
sorted_items = sorted(results.items())
batch_durations = list(batch_times.values())

for batch_index in range(len(batch_durations)):
    start = batch_index * BATCH_SIZE
    end = min(start + BATCH_SIZE, len(sorted_items))
    current_batch_items = sorted_items[start:end]

    if not current_batch_items:
        continue

    duration = batch_durations[batch_index]
    avg_time = round(duration / len(current_batch_items), 4)

    for fname, info in current_batch_items:
        info["avg_time"] = avg_time
        results[fname] = info


# Escribir CSV
Path(csv_output).parent.mkdir(parents=True, exist_ok=True)
with open(csv_output, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["file", "valid", "avg_validation_time_ms", "status", "msg"])

    for i, (file_name, info) in enumerate(sorted(results.items()), 1):
        #if i % 800 == 0:
        #    print(f"Soy múltiplo de 800, número de: {i}")

        writer.writerow([
            file_name,
            info["valid"],
            info["status"],
            round(info["avg_time"], 4),
            info["msg"]
        ])

    writer.writerow([])
    writer.writerow(["VÁLIDOS", "INVÁLIDOS", "TOTAL", "", ""])
    writer.writerow([valid_count, invalid_count, total, "", ""])

print("\n RESUMEN VALIDATION - kubeconform")
print(f"Total archivos analizados: {total}")
print(f" Valids (True): {valid_count}")
print(f" Invalids (False): {invalid_count}")