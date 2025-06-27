#!/bin/bash

INPUT_DIR="./manifests_yamls"
RESULTS_DIR="./results_checkov"
BATCH_SIZE=300
TIMING_FILE="$RESULTS_DIR/batch_times.txt"

mkdir -p "$RESULTS_DIR"
rm -f "$TIMING_FILE"

# Buscar todos los archivos YAML, incluidos ocultos
find "$INPUT_DIR" -type f \( -name "*.yaml" -o -name ".*.yaml" \) > all_yaml_files.txt

# Dividir en lotes
split -l $BATCH_SIZE all_yaml_files.txt batch_

# Ejecutar checkov por lote
for batch_file in batch_*; do
  batch_id=$(basename "$batch_file")
  output_file="$RESULTS_DIR/$batch_id.json"

  echo "Procesando lote: $batch_id"
  start_time=$(date +%s%3N)

  mapfile -t files < "$batch_file"
  checkov -f "${files[@]}" --framework kubernetes -o json > "$output_file" 2>/dev/null

  end_time=$(date +%s%3N)
  duration_ms=$((end_time - start_time))
  echo "$batch_id,$duration_ms" >> "$TIMING_FILE"

  echo " Lote $batch_id completado → Resultado en: $output_file"
done

# Ejecutar procesamiento en Python
python checkov.py

# Limpieza
rm batch_* all_yaml_files.txt