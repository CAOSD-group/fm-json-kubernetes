import json
import csv
import os
from pathlib import Path
from collections import defaultdict

# Configuraciones
json_dir = "./results_kubeLinter_json"
csv_output = './results/kube-linter/validation_results.csv'
timing_file = os.path.join(json_dir, "batch_times.txt")
input_dir = "./small"

# Crear directorio para CSV si no existe
Path(csv_output).parent.mkdir(parents=True, exist_ok=True)

# Estructura: file -> {valid, failed_checks[], remediations[], avg_time}
results = defaultdict(lambda: {
    "valid": True,
    "failed_checks": set(),
    "remediations": set(),
    "avg_time": 0.0
})

# Leer duración por batch
batch_times = {}
if os.path.exists(timing_file):
    with open(timing_file, encoding="utf-8") as tf:
        for line in tf:
            parts = line.strip().split(",")
            if len(parts) == 2:
                batch_name, duration_str = parts
                try:
                    batch_times[batch_name] = float(duration_str)
                except ValueError:
                    continue

# Procesar resultados por lote
for fname in os.listdir(json_dir):
    if not fname.endswith(".json"):
        continue

    json_path = os.path.join(json_dir, fname)
    batch_name = fname.replace(".json", "")
    batch_duration = batch_times.get(batch_name, 0.0)

    with open(json_path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Archivo JSON inválido: {fname}")
            continue

    # Extraer nombres únicos de archivo afectados en este batch
    file_names = set()
    for issue in data.get("Reports", []):
        fpath = issue.get("Object", {}).get("Metadata", {}).get("FilePath", "")
        if fpath:
            file_names.add(os.path.basename(fpath))

    total_files = len(file_names)
    avg_time = round(batch_duration / total_files, 2) if total_files else 0.0

    for fname in file_names:
        results[fname]["avg_time"] = avg_time

    # Procesar errores
    for issue in data.get("Reports", []):
        if "Check" not in issue:
            continue
        fpath = os.path.basename(issue["Object"]["Metadata"].get("FilePath", ""))
        results[fpath]["valid"] = False
        results[fpath]["failed_checks"].add(issue.get("Check", "").strip())
        results[fpath]["remediations"].add(issue.get("Remediation", "").strip())

# Incluir archivos válidos no procesados en ningún batch
for root, _, files in os.walk(input_dir):
    for file in files:
        if file.endswith(".yaml") and file not in results:
            results[file] = {
                "valid": True,
                "failed_checks": set(),
                "remediations": set(),
                "avg_time": 0.0
            }

# Contadores
total = len(results)
valid_count = sum(1 for r in results.values() if r["valid"])
invalid_count = total - valid_count

# Guardar CSV
Path(os.path.dirname(csv_output)).mkdir(parents=True, exist_ok=True)
with open(csv_output, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["file", "valid", "avg_validation_time_ms", "failed_checks", "remediations"])
    for file_name, info in sorted(results.items()):
        writer.writerow([
            file_name,
            str(info["valid"]).lower(),
            round(info["avg_time"], 2),
            "; ".join(sorted(info["failed_checks"])),
            "; ".join(sorted(info["remediations"])),
            
        ])
    writer.writerow([])
    writer.writerow(["VÁLIDOS", "INVÁLIDOS", "TOTAL", "", ""])
    writer.writerow([valid_count, invalid_count, total, "", ""])

# Mostrar resumen
print("\n RESUMEN VALIDATION KubeLinter")
print(f"Total files analizados: {total}")
print(f" Valids (True): {valid_count}")
print(f" Invalids (False): {invalid_count}")
print(f" CSV generado en: {csv_output}")