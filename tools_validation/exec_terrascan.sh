#!/bin/bash

INPUT_DIR="./small"
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

  # Crear directorio temporal y copiar archivos del lote
  mkdir -p tmp_tf_files
  while read -r yaml_file; do
    cp "$yaml_file" tmp_tf_files/
  done < "$batch_file"

  # Ejecutar Terrascan en el directorio temporal
  ./terrascan.exe scan -d tmp_tf_files -i k8s -o json > "$output_file" 2>/dev/null

  # Limpiar directorio temporal
  rm -rf tmp_tf_files

  end_time=$(date +%s%3N)
  duration_ms=$((end_time - start_time))
  echo "$batch_id,$duration_ms" >> "$TIMING_FILE"

  echo "Lote $batch_id completado → Resultado en: $output_file"
done

# Ejecuta el análisis en Python
python terrascan.py

# Limpieza
rm batch_* all_yaml_files.txt