#!/bin/bash

INPUT_DIR="./small"
RESULTS_DIR="./results_kubeLinter_json"
BATCH_SIZE=800
TIMING_FILE="$RESULTS_DIR/batch_times.txt"

mkdir -p "$RESULTS_DIR"

# Lista todos los YAML y los guarda en un archivo temporal
find "$INPUT_DIR" -type f \( -name '*.yaml' \) > all_yaml_files.txt ## -o -name '*.yml' 

# Divide en lotes de 1000
split -l "$BATCH_SIZE" all_yaml_files.txt batch_

# Ejecutar kube-linter por lote
for batch_file in batch_*; do
  batch_id=$(basename "$batch_file")
  mapfile -t files < "$batch_file"
  #start_time=$(date +%s) ## Start time counter
  start_time=$(date +%s%3N) # milisegundos
  kube-linter lint "${files[@]}" --format json > "$RESULTS_DIR/$batch_id.json"
  end_time=$(date +%s%3N)
  #end_time=$(date +%s) ## End time counter
  duration_ms=$((end_time - start_time))
  echo "$batch_id,$duration_ms" >> "$TIMING_FILE"
  #xargs -a "$batch_file" /c/Users/CAOSD/go/bin/kube-linter lint --format json >> "$RESULTS_DIR/$batch_id.json"
  echo "Procesado lote $batch_id con ${#files[@]} archivos"
done

python kube-linter.py

# Limpieza
rm batch_* all_yaml_files.txt