import json
import csv
from pathlib import Path
from collections import defaultdict

json_dir = Path('results_kubeconform')
csv_output = './results/kubeconform/validation_results01.csv'
timing_file = json_dir / "batch_times.txt"

results = defaultdict(lambda: {
    "valid": True,
    "status": "valid",
    "msg": "",
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
            "status": status,
            "msg": msg,
            "avg_time": 0.0  # Se sobrescribirá luego con el valor correcto
        }

# Incluir válidos que no están explícitos en los JSON
input_dir = Path('./small')
for file in input_dir.rglob("*.yaml"):
    fname = file.name
    if fname not in results:
        results[fname] = {
            "valid": True,
            "status": "valid",
            "msg": "",
            "avg_time": 0.0
        }

# Estadísticas
total = len(results)
valid_count = sum(1 for r in results.values() if r["valid"])
invalid_count = total - valid_count
print(f"Tiempo de batchs: {batch_times}")

# Aplicar tiempos promedio por bloques (800 archivos por batch)
sorted_items = sorted(results.items())
batch_durations = list(batch_times.values()) 
num_batches = len(batch_durations)

for i, (fname, info) in enumerate(sorted_items):
    batch_index = min(i // 800, num_batches - 1)
    # Manejo del último batch con posible menos de 800
    start = batch_index * 800 # Se calcula cuántos archivos hay en el batch
    end = min(start + 800, len(sorted_items))
    actual_count = end - start # Calcula el rango [start:end] correspondiente al batch actual
    avg_time = round(batch_durations[batch_index] / actual_count, 4) if actual_count else 0.0 ## Asigna el tiempo promedio a cada archivo

    info["avg_time"] = avg_time
    results[fname] = info

# Escribir CSV
Path(csv_output).parent.mkdir(parents=True, exist_ok=True)
with open(csv_output, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["file", "valid", "status", "msg", "avg_validation_time_ms"])

    for i, (file_name, info) in enumerate(sorted(results.items()), 1):
        #if i % 800 == 0:
        #    print(f"Soy múltiplo de 800, número de: {i}")

        writer.writerow([
            file_name,
            info["valid"],
            info["status"],
            info["msg"],
            round(info["avg_time"], 4)
        ])

    writer.writerow([])
    writer.writerow(["VÁLIDOS", "INVÁLIDOS", "TOTAL", "", ""])
    writer.writerow([valid_count, invalid_count, total, "", ""])

print("\n RESUMEN VALIDATION - kubeconform")
print(f"Total archivos analizados: {total}")
print(f" Valids (True): {valid_count}")
print(f" Invalids (False): {invalid_count}")
