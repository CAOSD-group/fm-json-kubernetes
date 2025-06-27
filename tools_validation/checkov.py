import os
import json
import csv
from pathlib import Path
from collections import defaultdict

json_dir = Path("./results_checkov")
csv_output = Path("./results/checkov/validation_results.csv")
timing_file = json_dir / "batch_times.txt"

results = defaultdict(lambda: {
    "valid": True,
    "avg_time": 0.0,
    "failed_checks": [],
    "summary": ""
})

# Leer duración por batch
batch_times = {}
if timing_file.exists():
    with open(timing_file, encoding="utf-8") as tf:
        for line in tf:
            parts = line.strip().split(",")
            if len(parts) == 2:
                batch_id, time_str = parts
                batch_times[batch_id] = int(time_str)

# Procesar resultados de Checkov
for json_file in json_dir.glob("*.json"):
    batch_id = json_file.stem
    with open(json_file, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f" Error en JSON: {json_file}")
            continue

    for entry in data.get("results", {}).get("failed_checks", []):
        file_path = Path(entry.get("file_path", "")).name
        check_id = entry.get("check_id")
        check_name = entry.get("check_name")
        results[file_path]["valid"] = False
        results[file_path]["failed_checks"].append(f"{check_id} - {check_name}")

    for entry in data.get("results", {}).get("passed_checks", []):
        file_path = Path(entry.get("file_path", "")).name
        if file_path not in results:
            results[file_path]  # se marca como válido por defecto

# Estimar tiempos por archivo
BATCH_SIZE = 300
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

# Crear CSV
csv_output.parent.mkdir(parents=True, exist_ok=True)
with open(csv_output, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["file", "valid", "avg_validation_time_ms", "failed_checks"])

    for fname, info in sorted(results.items()):
        writer.writerow([
            fname,
            str(info["valid"]).lower(),
            info["avg_time"],
            "; ".join(info["failed_checks"])
        ])

print(f"\n Resultados guardados en: {csv_output}")
print(f" Archivos procesados: {len(results)}")
print(f" Archivos válidos: {sum(1 for r in results.values() if r['valid'])}")
print(f" Archivos inválidos: {sum(1 for r in results.values() if not r['valid'])}")