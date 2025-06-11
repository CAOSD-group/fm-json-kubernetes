#!/bin/bash

INPUT_DIR="./small"
RESULTS_DIR="./results_trivy"
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
  output_file="$RESULTS_DIR/${batch_id}.txt"

  # Ejecuta Trivy por cada archivo del batch individualmente
  mkdir -p tmp_tf_files
  while read -r yaml_file; do
    cp "$yaml_file" tmp_tf_files/
  done < "$batch_file"

  echo "Procesando lote: $batch_id"
  start_time=$(date +%s%3N)

  ./trivy.exe config tmp_tf_files > "$output_file" 2>/dev/null

  end_time=$(date +%s%3N)
  duration_ms=$((end_time - start_time))
  echo "$batch_id,$duration_ms" >> "$TIMING_FILE"
  
  # Limpiar directorio temporal
  rm -rf tmp_tf_files

  echo "Lote $batch_id completado → Resultado en: $output_file"
done

# Ejecuta el análisis en Python
python trivy_summary.py

# Limpieza
rm batch_* all_yaml_files.txt