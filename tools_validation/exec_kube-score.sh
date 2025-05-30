#!/bin/bash

INPUT_DIR="./manifests_yamls" #small
RESULTS_DIR="./results_kube-score"
BATCH_SIZE=1000

mkdir -p "$RESULTS_DIR"

# Lista todos los YAML y los guarda en un archivo temporal
find "$INPUT_DIR" -type f \( -name '*.yaml' -o -name '*.yml' \) > all_yaml_files.txt

# Divide en lotes de 1000
split -l "$BATCH_SIZE" all_yaml_files.txt batch_

# Ejecutar kube-linter por lote
for batch_file in batch_*; do
  batch_id=$(basename "$batch_file")
  mapfile -t files < "$batch_file"
  ./kube-score/kube-score.exe score "${files[@]}" > "$RESULTS_DIR/$batch_id.txt"
  #xargs -a "$batch_file" /c/Users/CAOSD/go/bin/kube-linter lint --format json >> "$RESULTS_DIR/$batch_id.json"
  echo "Procesado lote $batch_id con ${#files[@]} archivos"
done

python kube-score.py

# Limpieza
rm batch_* all_yaml_files.txt
