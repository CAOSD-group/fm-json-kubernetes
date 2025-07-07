#!/bin/bash

INPUT_DIR="../../resources/yamls_agrupation/yamls-tools-files"
RESULTS_DIR="../../resources/results_data_tools/results_kubeLinter01"
BATCH_SIZE=800
TIMING_FILE="$RESULTS_DIR/batch_times.txt"

mkdir -p "$RESULTS_DIR"
rm -f "$TIMING_FILE"

# Listar todos los YAML
find "$INPUT_DIR" -type f -name "*.yaml" > all_yaml_files.txt

# Verificación
total_files=$(wc -l < all_yaml_files.txt)
echo "Total YAMLs detectados: $total_files"

# Dividir en lotes
split -l "$BATCH_SIZE" all_yaml_files.txt batch_

# Procesar cada lote
for batch_file in batch_*; do
  batch_id=$(basename "$batch_file")
  output_file="$RESULTS_DIR/${batch_id}.json"

  echo "Procesando lote: $batch_id"
  start_time=$(date +%s%3N)

  TMP_DIR=$(mktemp -d)
  while read -r yaml_file; do
    [ -f "$yaml_file" ] && cp "$yaml_file" "$TMP_DIR/"
  done < "$batch_file"

  file_count=$(find "$TMP_DIR" -type f -name "*.yaml" | wc -l)
  if [ "$file_count" -eq 0 ]; then
    echo "{}" > "$output_file"
    echo "$batch_id,0" >> "$TIMING_FILE"
    rm -rf "$TMP_DIR"
    continue
  fi

  # Ejecutar kube-linter
  kube-linter lint "$TMP_DIR" --format json > "$output_file" 2>/dev/null

  end_time=$(date +%s%3N)
  duration_ms=$((end_time - start_time))
  echo "$batch_id,$duration_ms" >> "$TIMING_FILE"

  echo "Lote $batch_id completado → Resultado: $output_file"
  rm -rf "$TMP_DIR"
done

# Ejecutar análisis en Python
python kube-linter.py

# Limpieza
rm batch_* all_yaml_files.txt