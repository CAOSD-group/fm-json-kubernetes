#!/bin/bash

INPUT_DIR="./manifests_yamls"
RESULTS_DIR="./results_terrascan"
BATCH_SIZE=800
TIMING_FILE="$RESULTS_DIR/batch_times.txt"

mkdir -p "$RESULTS_DIR"

# Lista todos los YAML
find "$INPUT_DIR" -type f -name "*.yaml" > all_yaml_files.txt

# Divide en lotes
split -l $BATCH_SIZE all_yaml_files.txt batch_

# Procesa cada lote
for batch_file in batch_*; do
  batch_id=$(basename "$batch_file")
  output_file="$RESULTS_DIR/${batch_id}.json"

  echo "Procesando lote: $batch_id"
  start_time=$(date +%s%3N)

  # Crear archivo temporal con la lista de archivos del batch
  batch_list=$(mktemp)
  cat "$batch_file" > "$batch_list"

  # Ejecutar Terrascan directamente sobre la lista de archivos con -f
  # Terrascan soporta opción -f para pasar archivos individuales
  echo "Archivos en lote ($batch_id):"
  ./terrascan.exe scan -d "$batch_file" -i k8s -o json > "$output_file"

  end_time=$(date +%s%3N)
  duration_ms=$((end_time - start_time))
  echo "$batch_id,$duration_ms" >> "$TIMING_FILE"

  echo "Lote $batch_id completado → Resultado en: $output_file"

  rm "$batch_list"
done

# Ejecuta el análisis en Python
python terrascan.py

# Limpieza
rm batch_* all_yaml_files.txt