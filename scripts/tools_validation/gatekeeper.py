from pathlib import Path
from collections import defaultdict
import csv
import re
# Rutas fijas (puedes modificarlas directamente aquí si cambias carpetas)
input_dir = Path("./results_gatekeeper")
yaml_dir = Path("./small")
csv_output = './results/gatekeeper/validation_results.csv'

results = defaultdict(lambda: {"valid": True, "failures": []})

# Expresión regular para capturar la línea final
#summary_re = re.compile(r"pass:\s*(\d+),\s*fail:\s*(\d+),\s*warn:\s*(\d+),\s*error:\s*(\d+),\s*skip:\s*(\d+)")

# Regex
file_marker = re.compile(r"^##### FILE: (.+) #####$")
violation_re = re.compile(r"violation|deny|constraint", re.IGNORECASE)

# Procesamos todos los archivos batch de resultados
for result_file in input_dir.rglob("*.txt"):
    with open(result_file, encoding="utf-8") as f:
        current_file = None
        for line in f:
            line = line.strip()

            # Detecta nuevo archivo
            match = file_marker.match(line)
            if match:
                current_file = match.group(1)
                continue

            if current_file is None:
                continue

            # Guarda errores específicos
            if violation_re.search(line):
                results[current_file]["valid"] = False
                results[current_file]["failures"].append(line)

            """# Detecta resumen final
            summary = summary_re.search(line)
            if summary and int(summary.group(2)) > 0:  # fail > 0
                results[current_file]["valid"] = False"""

# Agrega archivos válidos no reportados
all_yaml_files = {file.name for file in yaml_dir.rglob("*.yaml")}
for yaml_file in all_yaml_files:
    if yaml_file not in results:
        results[yaml_file] = {"valid": True, "failures": []}

# Cuenta
true_count = 0
false_count = 0

# Escribe el CSV
Path(csv_output).parent.mkdir(parents=True, exist_ok=True)

with open(csv_output, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["file", "valid", "issues"])

    for file_name, info in sorted(results.items()):
        is_valid = info["valid"]
        issues = "; ".join(info["failures"])

        writer.writerow([file_name, is_valid, issues])

        if is_valid:
            true_count += 1
        else:
            false_count += 1

    writer.writerow([])
    writer.writerow(["TOTAL_VALID", true_count])
    writer.writerow(["TOTAL_INVALID", false_count])

# Reporte final por consola
print(f" Archivos válidos (True): {true_count}")
print(f" Archivos inválidos (False): {false_count}")
print(f" Resultados guardados en: {csv_output}")