#!/bin/bash

INPUT_DIR="./small"
RESULTS_DIR="./results_kubeLinter_json"
BATCH_SIZE=1000
TIMING_FILE="./results_kubeLinter_json/batch_times.txt"

mkdir -p "$RESULTS_DIR"

# Lista todos los YAML y los guarda en un archivo temporal
find "$INPUT_DIR" -type f \( -name '*.yaml' -o -name '*.yml' \) > all_yaml_files.txt

# Divide en lotes de 1000
split -l "$BATCH_SIZE" all_yaml_files.txt batch_

# Ejecutar kube-linter por lote
for batch_file in batch_*; do
  batch_id=$(basename "$batch_file")
  mapfile -t files < "$batch_file"
  start_time=$(date +%s) ## Start time counter
  kube-linter lint "${files[@]}" --format json > "$RESULTS_DIR/$batch_id.json"
  end_time=$(date +%s) ## End time counter
  duration=$((end_time - start_time))
  echo "$batch_id,$duration" >> "$TIMING_FILE"
  #xargs -a "$batch_file" /c/Users/CAOSD/go/bin/kube-linter lint --format json >> "$RESULTS_DIR/$batch_id.json"
  echo "Procesado lote $batch_id con ${#files[@]} archivos"
done

python kube-linter.py

# Limpieza
rm batch_* all_yaml_files.txt


#!/bin/bash

# Crear carpeta de resultados si no existe
mkdir -p results/kube-linter

# Definir ruta absoluta a los manifiestos
YAML_DIR="manifests_yamls"
RESULT_FILE="results/kube-linter/raw_output_01.json"

echo "[INFO] Ejecutando KubeLinter..."

# Ejecutar kube-linter directamente y guardar resultado en formato JSON
kube-linter lint "$YAML_DIR" --format json > "$RESULT_FILE"

# Validar que el archivo de salida no esté vacío
if [ ! -s "$RESULT_FILE" ]; then
  echo "[ERROR] El archivo $RESULT_FILE está vacío. Falló la ejecución de KubeLinter o no hay manifiestos."
  exit 1
fi

# Ejecutar procesamiento con Python
python kube-linter.py

echo "[✓] Proceso completado. Archivos generados en results/kube-linter/"



#!/bin/bash

# Crear carpeta de resultados si no existe
mkdir -p results/kube-linter
##VOLUME_PATH=$(pwd -W 2>/dev/null || pwd)
#VOLUME_PATH='C:/Users/CAOSD/projects/tools_validation/manifests_yamls'
VOLUME_PATH=$(cd manifests_yamls && pwd | sed 's|/c/|C:/|')

# Ejecutar KubeLinter con Docker
echo "[INFO] Ejecutando KubeLinter..."
#docker run --rm -v "${VOLUME_PATH}:/manifests_yamls" stackrox/kube-linter:latest lint C:/Users/CAOSD/projects/tools_validation/manifests_yamls --format json > results/kube-linter/raw_output.json ## /manifests:/manifests

#docker run --rm -v "$VOLUME_PATH:/manifests_yamls" stackrox/kube-linter:latest lint /manifests_yamls --format json > results/kube-linter/raw_output.json

#docker run -v /path/to/files/you/want/to/lint:/dir -v /path/to/config.yaml:/etc/config.yaml stackrox/kube-linter lint /dir --config /etc/config.yaml

#docker run -v c/Users/CAOSD/projects/tools_validation/manifests_yamls:/manifests stackrox/kube-linter lint /manifests --format json > results/kube-linter/raw_output.json
docker run --rm -v "$VOLUME_PATH:/manifests" stackrox/kube-linter lint /manifests --format json > results/kube-linter/raw_output.json


#docker run -v "C:\Users\CAOSD\projects\tools_validation\manifests_yamls:/manifests" stackrox/kube-linter lint /manifests --format json > results/kube-linter/raw_output.json

#/path/to/config.yaml:/etc/config.yaml
# Validar que el archivo de salida no esté vacío
if [ ! -s results/kube-linter/raw_output.json ]; then
  echo "[ERROR] El archivo raw_output.json está vacío. Falló la ejecución de KubeLinter o no hay manifiestos."
  exit 1
fi

python kube-linter.py

echo "[✓] Proceso completado. Archivos generados en results/kube-linter/"






#!/bin/bash

# Crear carpeta de resultados si no existe
mkdir -p results/kube-linter

# Definir ruta absoluta a los manifiestos
YAML_DIR="manifests_yamls"
RESULT_FILE="results/kube-linter/raw_output.json"

echo "[INFO] Ejecutando KubeLinter..."

# Ejecutar kube-linter directamente y guardar resultado en formato JSON
kube-linter lint "$YAML_DIR" --format json > "$RESULT_FILE"

# Validar que el archivo de salida no esté vacío
if [ ! -s "$RESULT_FILE" ]; then
  echo "[ERROR] El archivo $RESULT_FILE está vacío. Falló la ejecución de KubeLinter o no hay manifiestos."
  exit 1
fi

# Ejecutar procesamiento con Python
python kube-linter.py

echo "[✓] Proceso completado. Archivos generados en results/kube-linter/"