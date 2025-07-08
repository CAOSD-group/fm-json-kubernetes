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

Tool: kube-score
URL: https://kube-score.com/
Purpose: Static analysis of YAML manifests based on best practices.
Notes: Produces structured output; supports JSON.
"""

import os
import csv
from pathlib import Path
from collections import defaultdict

RESULTS_DIR = "../../resources/results_data_tools/results_kube-score"
YAML_DIR="../../resources/yamls_agrupation/yamls-tools-files"
CSV_OUTPUT = "../../evaluation/validation_results_kube-score_final.csv"
TIMING_FILE = os.path.join(RESULTS_DIR, "batch_times.txt")

Path(CSV_OUTPUT).parent.mkdir(parents=True, exist_ok=True)

# Leer tiempos por lote
batch_times = {}
if os.path.exists(TIMING_FILE):
    with open(TIMING_FILE, encoding="utf-8") as f:
        for line in f:
            batch_id, time_str = line.strip().split(",")
            batch_times[batch_id] = int(time_str)

# Mapear archivos a sus lotes
batch_file_map = defaultdict(list)
for batch_file in os.listdir(RESULTS_DIR):
    if batch_file.endswith(".txt"):
        batch_id = batch_file.replace(".txt", "")
        with open(os.path.join(RESULTS_DIR, batch_file), encoding="utf-8") as f:
            for line in f:
                if line.startswith("### path="):
                    fname = os.path.basename(line.strip().split("=", 1)[1])
                    batch_file_map[batch_id].append(fname)

# Resultados por archivo
results = defaultdict(lambda: {
    "valid": True,
    "issues": [],
    "avg_time": 0.0
})

# Analizar archivos de texto por lote
for txt_file in Path(RESULTS_DIR).glob("*.txt"):
    batch_id = txt_file.stem
    files_in_batch = batch_file_map.get(batch_id, [])
    avg_time = round(batch_times.get(batch_id, 0) / len(files_in_batch), 2) if files_in_batch else 0.0

    current_file = None
    with open(txt_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("### path="):
                current_file = os.path.basename(line.split("=", 1)[1])
                results[current_file]["avg_time"] = avg_time
                continue
            if current_file and (
                "Failed to parse" in line or
                line.startswith("[CRITICAL]") or
                line.startswith("[WARNING]")
            ):
                results[current_file]["valid"] = False
                results[current_file]["issues"].append(line)

# Asegurar todos los YAML estén representados
yaml_files = {f.name for f in Path(YAML_DIR).rglob("*.yaml")}
for fname in yaml_files:
    if fname not in results:
        results[fname] = {"valid": True, "issues": [], "avg_time": 0.0}

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

# Mostrar resumen
print("\n RESUMEN VALIDATION kube-score")
print(f"Total files analizados: {len(results)}")
print(f"  Valids (True): {sum(1 for r in results.values() if r['valid'])}")
print(f" Invalids (False): {sum(1 for r in results.values() if not r['valid'])}")