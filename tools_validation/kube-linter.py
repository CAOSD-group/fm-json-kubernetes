## Kube linter exec to folder manifest validation

import json
import csv
from pathlib import Path
from collections import defaultdict

json_dir = Path('results_json')   #"./results_json/batch_aa.json"
csv_output = './results/kube-linter/validation_results.csv'

# Estructura: file -> {valid, failed_checks[], remediations[]}
results = defaultdict(lambda: {"valid": True, "failed_checks": set(), "remediations": set()})

for json_file in json_dir.glob("*.json"):
    with open(json_file, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Archivo JSON inválido: {json_file}")
            continue
    
    #data = json.loads(content)
    for issue in data.get("Reports", []):
        #print(issue)
        # Ruta del archivo afectado (normalizada)
        if not "Check" in issue:
            print("No se deberia de recorrer")
            continue

        print("SE DEBERIA DE EJECUTAR")
        file_path = Path(issue["Object"]["Metadata"].get("FilePath", "")).name
        print(f"El path del directorio {file_path}")
        check = issue.get("Check", "").strip()
        remediation = issue.get("Remediation", "").strip()
        print(f"El path del directorio {check}  {remediation}")

        results[file_path]["valid"] = False
        results[file_path]["failed_checks"].add(check)
        results[file_path]["remediations"].add(remediation)

## Obtener todos los nombres de los ficheros para mostrar los True**
all_yaml_files = set()
input_dir = Path('./small')

for file in input_dir.rglob("*.yaml"):
    all_yaml_files.add(file.name)

# Asegurar que los archivos sin errores también estén en `results`
for yaml_file in all_yaml_files:
    if yaml_file not in results:
        results[yaml_file] = {"valid": True, "failed_checks": set(), "remediations": set()}


# Escribir CSV final
with open(csv_output, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["file", "valid", "failed_checks", "remediations"])
    print(f"Salto")
    for file_name, info in sorted(results.items()):
        writer.writerow([
            file_name,
            info["valid"],
            "; ".join(sorted(info["failed_checks"])),
            "; ".join(sorted(info["remediations"]))
        ])
