import os
import json
import csv
from pathlib import Path

results_dir = "./results_conftest"
csv_output = "./results/conftest/validation_results01.csv"
timing_file = os.path.join(results_dir, "batch_times.txt")

Path(csv_output).parent.mkdir(parents=True, exist_ok=True)

# Cargar tiempos por batch
batch_times = {}
with open(timing_file, "r") as f:
    for line in f:
        batch_id, time_ms = line.strip().split(",")
        batch_times[batch_id] = int(time_ms)

rows = []

# Leer resultados JSON
for filename in os.listdir(results_dir):
    if not filename.endswith(".json"):
        continue

    batch_id = filename.replace(".json", "")
    json_path = os.path.join(results_dir, filename)

    with open(json_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error de JSON en {filename}")
            continue

    avg_time = round(batch_times.get(batch_id, 0) / len(data), 4) if data else 0.0

    for entry in data:
        source = os.path.basename(entry.get("filename", "unknown"))
        failures = entry.get("failures", [])
        failed_msgs = [f.get("msg", "") for f in failures]
        valid = "false" if failures else "true"
        rows.append([source, valid, avg_time, ";".join(failed_msgs)])

# Guardar CSV
with open(csv_output, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["file", "valid", "avg_validation_time_ms", "failed_messages"])
    writer.writerows(rows)

print(f"CSV generado: {csv_output}")
