## Kube linter exec to folder manifest validation

import json
import csv
from pathlib import Path
from collections import defaultdict

json_dir = Path('results_kubeLinter_json')
csv_output = './results/kube-linter/validation_results01.csv'
timing_file = json_dir / "batch_times.txt"

# Estructura: file -> {valid, failed_checks[], remediations[], avg_time}
results = defaultdict(lambda: {
    "valid": True,
    "failed_checks": set(),
    "remediations": set(),
    "avg_time": 0.0
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

# Procesar resultados por lote
for json_file in json_dir.glob("*.json"):
    batch_name = json_file.stem
    batch_duration = batch_times.get(batch_name, 0.0)

    with open(json_file, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Archivo JSON inválido: {json_file}")
            continue

    # Extraer todos los nombres de archivos únicos en este batch
    file_names = set()
    for issue in data.get("Reports", []):
        fpath = issue.get("Object", {}).get("Metadata", {}).get("FilePath", "")
        if fpath:
            file_names.add(Path(fpath).name)

    # Calcular tiempo medio por archivo en este batch
    avg_time = round(batch_duration / len(file_names), 4) if file_names else 0.0

    # Asignar tiempo a todos los archivos del batch (con y sin errores)
    for fname in file_names:
        results[fname]["avg_time"] = avg_time

    # Procesar errores (invalids)
    for issue in data.get("Reports", []):
        if "Check" not in issue:
            continue
        fpath = Path(issue["Object"]["Metadata"].get("FilePath", "")).name
        results[fpath]["valid"] = False
        results[fpath]["failed_checks"].add(issue.get("Check", "").strip())
        results[fpath]["remediations"].add(issue.get("Remediation", "").strip())

# Incluir archivos válidos que no aparecen en JSON
input_dir = Path('./small')

for file in input_dir.rglob("*.yaml"):
    fname = file.name
    if fname not in results:
        results[fname] = {
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
Path(csv_output).parent.mkdir(parents=True, exist_ok=True)
with open(csv_output, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["file", "valid", "failed_checks", "remediations", "avg_validation_time_ms"])
    for file_name, info in sorted(results.items()):
        writer.writerow([
            file_name,
            info["valid"],
            "; ".join(sorted(info["failed_checks"])),
            "; ".join(sorted(info["remediations"])),
            round(info["avg_time"], 4)
        ])
    writer.writerow([])
    writer.writerow(["VÁLIDOS", "INVÁLIDOS", "TOTAL", "", ""])
    writer.writerow([valid_count, invalid_count, total, "", ""])

print("\n RESUMEN VALIDATION kube-linter")
print(f"Total files analizados: {total}")
print(f" Valids (True): {valid_count}")
print(f" Invalids (False): {invalid_count}")
