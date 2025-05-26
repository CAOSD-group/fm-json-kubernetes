from pathlib import Path
from collections import defaultdict
import csv

# Rutas fijas (puedes modificarlas directamente aquí si cambias carpetas)
input_dir = Path("./results_kube-score")
yaml_dir = Path("./manifests_yamls")
csv_output = './results/kube-score/validation_results.csv'
results = defaultdict(lambda: {"valid": True, "findings": []})

# Recorrer todos los txt de resultados
for txt_file in input_dir.glob("*.txt"):
    current_file = None
    with open(txt_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("path="):
                current_file = Path(line.split("=", 1)[1]).name
            elif line.startswith("[CRITICAL]") or line.startswith("[WARNING]"):
                if current_file:
                    results[current_file]["valid"] = False
                    results[current_file]["findings"].append(line)

# Marcar como válidos los manifiestos que no aparecen en los resultados
all_yaml_files = {file.name for file in yaml_dir.rglob("*.yaml")}

for yaml_file in all_yaml_files:
    if yaml_file not in results:
        results[yaml_file] = {"valid": True, "findings": []}

# Guardar CSV
with open(csv_output, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["file", "valid", "issues"])
    for file_name, info in sorted(results.items()):
        writer.writerow([
            file_name,
            info["valid"],
            "; ".join(info["findings"])
        ])
