from pathlib import Path
from collections import defaultdict
import csv
import re

input_dir = Path("../../../resources/results_data_tools/results_kyverno")
yaml_dir = Path("../../../resources/yamls_agrupation/yamls-tools-files")
csv_output = '../../../evaluation/validation_results_kyverno_final.csv'
timing_file = input_dir / "batch_times.txt"

results = defaultdict(lambda: {"valid": True, "failures": [], "avg_time": 0})

file_marker = re.compile(r"^##### FILE: (.+) #####")
summary_re = re.compile(r"pass:\s*(\d+),\s*fail:\s*(\d+),\s*warn:\s*(\d+),\s*error:\s*(\d+),\s*skip:\s*(\d+)", re.IGNORECASE)

# Cargar tiempos por batch
batch_times = {}
if timing_file.exists():
    with open(timing_file, encoding="utf-8") as f:
        for line in f:
            batch_id, time_str = line.strip().split(",")
            batch_times[batch_id] = int(time_str)

# Asociar archivos con sus respectivos batch
file_to_batch = {}

for result_file in input_dir.rglob("batch_*.txt"):
    batch_id = result_file.stem
    with open(result_file, encoding="utf-8", errors="replace") as f:
        current_file = None
        for line in f:
            line = line.strip()
            match = file_marker.match(line)
            if match:
                current_file = match.group(1)
                file_to_batch[current_file] = batch_id
                continue

            if current_file is None:
                continue

            if "validation error" in line.lower() or "validation failure" in line.lower():
                results[current_file]["valid"] = False
                results[current_file]["failures"].append(line)

            summary = summary_re.search(line)
            if summary and int(summary.group(2)) > 0:
                results[current_file]["valid"] = False

# Agregar archivos válidos no mencionados
all_yaml_files = {file.name for file in yaml_dir.rglob("*.yaml")}
for yaml_file in all_yaml_files:
    if yaml_file not in results:
        results[yaml_file] = {"valid": True, "failures": [], "avg_time": 0}
    if yaml_file not in file_to_batch:
        file_to_batch[yaml_file] = None

# Asignar tiempos promedios correctos
batch_file_counts = defaultdict(int)
for fname, batch in file_to_batch.items():
    if batch:
        batch_file_counts[batch] += 1

for fname, batch in file_to_batch.items():
    if batch and batch in batch_times and batch_file_counts[batch] > 0:
        avg = round(batch_times[batch] / batch_file_counts[batch], 2)
        results[fname]["avg_time"] = avg

# Generar CSV
true_count = false_count = 0
Path(csv_output).parent.mkdir(parents=True, exist_ok=True)

with open(csv_output, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["file", "valid", "avg_validation_time_ms", "issues"])

    for fname in sorted(results.keys()):
        is_valid = results[fname]["valid"]
        issues = "; ".join(results[fname]["failures"])
        avg_time = results[fname]["avg_time"]
        writer.writerow([fname, str(is_valid).lower(), avg_time, issues])
        if is_valid:
            true_count += 1
        else:
            false_count += 1

    writer.writerow([])
    writer.writerow(["TOTAL_VALID", true_count])
    writer.writerow(["TOTAL_INVALID", false_count])

print(f" Archivos válidos (True): {true_count}")
print(f" Archivos inválidos (False): {false_count}")
print(f" Resultados guardados en: {csv_output}")