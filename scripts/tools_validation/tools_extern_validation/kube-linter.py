import json
import csv
import os
from pathlib import Path
from collections import defaultdict

json_dir = "../../resources/results_data_tools/results_kubeLinter01"
csv_output = '../../evaluation/validation_results_kubeLinter_final.csv'
timing_file = os.path.join(json_dir, "batch_times.txt")
#input_dir = "./small"
input_dir = "../../resources/yamls_agrupation/yamls-tools-files"

Path(csv_output).parent.mkdir(parents=True, exist_ok=True)

results = defaultdict(lambda: {
    "valid": True,
    "failed_checks": set(),
    "remediations": set(),
    "avg_time": 0.0
})

batch_times = {}
if os.path.exists(timing_file):
    with open(timing_file, encoding="utf-8") as tf:
        for line in tf:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                batch_times[parts[0]] = float(parts[1])

for fname in os.listdir(json_dir):
    if not fname.endswith(".json"):
        continue

    json_path = os.path.join(json_dir, fname)
    batch_name = fname.replace(".json", "")
    batch_duration = batch_times.get(batch_name, 0.0)

    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"Archivo JSON inválido: {fname}")
        continue

    if not isinstance(data, dict) or "Reports" not in data or not isinstance(data["Reports"], list):
        print(f"Advertencia: {fname} no contiene 'Reports' válidos.")
        continue

    total_files = 0
    batch_file_path = f"batch_{batch_name}"
    if os.path.exists(batch_file_path):
        with open(batch_file_path, encoding="utf-8") as bf:
            total_files = sum(1 for _ in bf)

    avg_time = round(batch_duration / total_files, 2) if total_files else 0.0

    for issue in data["Reports"]:
        fpath = issue.get("Object", {}).get("Metadata", {}).get("FilePath", "")
        if fpath:
            fname_only = os.path.basename(fpath)
            results[fname_only]["avg_time"] = avg_time
            results[fname_only]["valid"] = False
            results[fname_only]["failed_checks"].add(issue.get("Check", "").strip())
            results[fname_only]["remediations"].add(issue.get("Remediation", "").strip())

# Agregar archivos no analizados (válidos por defecto)
for root, _, files in os.walk(input_dir):
    for file in files:
        if file.endswith(".yaml") and file not in results:
            results[file] = {
                "valid": True,
                "failed_checks": set(),
                "remediations": set(),
                "avg_time": 0.0
            }

total = len(results)
valid_count = sum(1 for r in results.values() if r["valid"])
invalid_count = total - valid_count

with open(csv_output, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["file", "valid", "avg_validation_time_ms", "failed_checks", "remediations"])
    for file_name, info in sorted(results.items()):
        writer.writerow([
            file_name,
            str(info["valid"]).lower(),
            round(info["avg_time"], 2),
            "; ".join(sorted(info["failed_checks"])),
            "; ".join(sorted(info["remediations"]))
        ])
    writer.writerow([])
    writer.writerow(["VÁLIDOS", "INVÁLIDOS", "TOTAL", "", ""])
    writer.writerow([valid_count, invalid_count, total, "", ""])

print("\n RESUMEN VALIDATION KubeLinter")
print(f"Total files analizados: {total}")
print(f" Valids (True): {valid_count}")
print(f" Invalids (False): {invalid_count}")
print(f" CSV generado en: {csv_output}")