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

Tool: kubernetes-validate
URL: https://pypi.org/project/kubernetes-validate/
Purpose: Lightweight JSON Schema validation for Kubernetes manifests.
Notes: Python-based; useful for integration with internal tools.
"""

import os
import csv
from pathlib import Path
from collections import defaultdict

RESULTS_DIR = Path("../../../resources/results_data_tools/results_kubernetes-validate01")
YAML_DIR = Path("../../../resources/yamls_agrupation/yamls-tools-files")
#YAML_DIR = Path("./yamls-tools-files")
CSV_OUTPUT = Path("../../../evaluation/validation_results_kubernetes-validate_final.csv")
TIMING_FILE = RESULTS_DIR / "batch_times.txt"

CSV_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

results = defaultdict(lambda: {
    "valid": True,
    "avg_time": 0.0,
    "issues": []
})

batch_times = {}
if TIMING_FILE.exists():
    with open(TIMING_FILE, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 2:
                batch_id, time_str = parts
                try:
                    batch_times[batch_id] = int(time_str)
                except ValueError:
                    continue

batch_file_map = defaultdict(list)
for batch_file in RESULTS_DIR.glob("*.txt"):
    batch_id = batch_file.stem
    with open(batch_file, encoding="utf-8", errors="replace") as f:
        current_file = None
        for line in f:
            line = line.strip()
            if line.startswith("### path="):
                current_file = line.split("=", 1)[1]
                batch_file_map[batch_id].append(current_file)
                continue
            if current_file and ("ERROR" in line or "error" in line.lower() or "failed" in line.lower()):
                results[current_file]["valid"] = False
                results[current_file]["issues"].append(line)

# Añadir archivos válidos no reportados
for yaml_file in YAML_DIR.rglob("*.yaml"):
    fname = yaml_file.name
    if fname not in results:
        results[fname] = {
            "valid": True,
            "avg_time": 0.0,
            "issues": []
        }

# Asignar tiempo promedio por archivo
for batch_id, files in batch_file_map.items():
    if batch_id in batch_times and files:
        avg_time = round(batch_times[batch_id] / len(files), 2)
        for fname in files:
            results[fname]["avg_time"] = avg_time

# Guardar CSV
with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["file", "valid", "avg_validation_time_ms", "issues"])
    for fname, info in sorted(results.items()):
        writer.writerow([
            fname,
            str(info["valid"]).lower(),
            info["avg_time"],
            "; ".join(info["issues"])
        ])
    writer.writerow([])
    writer.writerow(["TOTAL_VALID", sum(1 for r in results.values() if r["valid"])])
    writer.writerow(["TOTAL_INVALID", sum(1 for r in results.values() if not r["valid"])])

print("\n RESUMEN VALIDATION - kubernetes-validate")
print(f" Total archivos analizados: {len(results)}")
print(f" Valids (True): {sum(1 for r in results.values() if r['valid'])}")
print(f" Invalids (False): {sum(1 for r in results.values() if not r['valid'])}")