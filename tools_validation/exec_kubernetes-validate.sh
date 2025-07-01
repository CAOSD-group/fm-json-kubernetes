#!/bin/bash

#INPUT_DIR="../scriptJsonToUvl/yamls_agrupation/yamls-tools-files"
INPUT_DIR="./yamls-tools-files"
RESULTS_DIR="./results_kubernetes-validate"
BATCH_SIZE=200
TIMING_FILE="$RESULTS_DIR/batch_times.txt"
VERSION="1.30"

mkdir -p "$RESULTS_DIR"
rm -f "$TIMING_FILE"
rm -f batch_* all_yaml_files.txt 

# 1. List all YAML files and split into batches
find "$INPUT_DIR" -type f -name '*.yaml' > all_yaml_files.txt
split -l "$BATCH_SIZE" all_yaml_files.txt batch_

# 2. Process each batch
for batch_file in batch_*; do
  batch_id=$(basename "$batch_file")
  output_file="$RESULTS_DIR/${batch_id}.txt"

  if [ -s "$output_file" ]; then
    echo "⏩ Lote $batch_id ya procesado. Saltando..."
    continue
  fi
  
  echo "Procesando lote: $batch_id"
  start_time=$(date +%s%3N)

  while read -r yaml_path; do
    fname=$(basename "$yaml_path")
    echo "### path=$fname" >> "$output_file"
    kubernetes-validate -k "$VERSION" "$yaml_path" >> "$output_file" 2>&1
    echo "" >> "$output_file"
  done < "$batch_file"

  end_time=$(date +%s%3N)
  duration_ms=$((end_time - start_time))
  echo "$batch_id,$duration_ms" >> "$TIMING_FILE"

  echo "Lote $batch_id completado → $output_file"
done

# 3. Ejecutar análisis en Python
python kubernetes-validate.py

# Limpieza
rm batch_* all_yaml_files.txt