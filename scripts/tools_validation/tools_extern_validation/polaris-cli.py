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

Tool: Polaris CLI
URL: https://github.com/FairwindsOps/polaris
Purpose: Audit Kubernetes manifests for best practices and configuration issues.
Notes: Requires specific flags for CLI summary output.
"""

import os
import json
import csv
from pathlib import Path

results_dir = "../../resources/results_data_tools/results_polaris-cli"
csv_output = '../../evaluation/validation_results_polaris-cli_final.csv'
timing_file = os.path.join(results_dir, "batch_times.txt")


Path(csv_output).parent.mkdir(parents=True, exist_ok=True)

# Cargar tiempos de validación por batch
batch_times = {}
with open(timing_file, "r") as f:
    for line in f:
        batch_id, time_ms = line.strip().split(",")
        batch_times[batch_id] = int(time_ms)

rows = []

# Procesar cada batch
for filename in os.listdir(results_dir):
    if filename.endswith(".json"):
        batch_id = filename.replace(".json", "")
        json_path = os.path.join(results_dir, filename)

        with open(json_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f" Error de JSON en {filename}")
                continue

        # Tiempo medio por archivo
        avg_time = round(batch_times.get(batch_id, 0) / len(data), 2) if data else 0.0
        #round(batch_durations[batch_index] / actual_count, 4)
        for obj in data:
            source = obj.get("SourceName", "unknown").split("/")[-1]
            failed_ids = []

            for result in obj.get("Results", []):
                checks = result.get("Results", {})
                failed_ids += [cid for cid, c in checks.items() if not c.get("Success", False)]

                pod_result = result.get("PodResult")
                if pod_result and isinstance(pod_result, dict):
                    pod_checks = pod_result.get("Results", {}) or {}
                    failed_ids += [cid for cid, c in pod_checks.items() if not c.get("Success", False)]

                    # ContainerResults
                    container_results = pod_result.get("ContainerResults", [])
                    #print(f"ESTA VACIO? {container_results}")
                    if isinstance(container_results, list):
                        for container in container_results:
                            container_checks = container.get("Results", {})
                            failed_ids += [cid for cid, c in container_checks.items() if not c.get("Success", False)]


            valid = "true" if not failed_ids else "false"
            rows.append([source, valid, avg_time, ";".join(failed_ids)])

# Guardar CSV
with open(csv_output, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["file", "valid", "avg_validation_time_ms", "failed_checks"])
    writer.writerows(rows)

print(f" CSV generado: {csv_output}")