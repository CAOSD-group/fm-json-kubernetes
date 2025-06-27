#!/bin/bash

## INPUT_DIR="./small" # small
INPUT_DIR="../scriptJsonToUvl/yamls_agrupation/yamls-tools-files"
RESULTS_DIR="./results_polaris-cli"
BATCH_SIZE=800
TIMING_FILE="$RESULTS_DIR/batch_times.txt"

mkdir -p "$RESULTS_DIR"

# Solo si no existe ya
if [ ! -f all_yaml_files.txt ]; then
  find "$INPUT_DIR" -type f -name "*.yaml" > all_yaml_files.txt
fi

# Dividir en lotes si no existen
if ! ls batch_* 1>/dev/null 2>&1; then
  split -l "$BATCH_SIZE" all_yaml_files.txt batch_
fi

for batch_file in batch_*; do
  [ -f "$batch_file" ] || continue
  batch_id=$(basename "$batch_file")
  output_file="$RESULTS_DIR/$batch_id.json"

  echo "Procesando lote: $batch_id"
  start_time=$(date +%s%3N)
  echo "[" > "$output_file"
  first=true

  while read -r yaml_file; do
    result=$(./polaris.exe audit --audit-path "$yaml_file" 2>/dev/null |
      grep -v "Upload your Polaris findings" |
      grep -v "polaris audit --audit-path")

    # Solo agregar si hay contenido JSON válido
    if [[ -n "$result" ]]; then
      if [ "$first" = true ]; then
        first=false
      else
        echo "," >> "$output_file"
      fi
      echo "$result" >> "$output_file"
    fi
  done < "$batch_file"

  echo "]" >> "$output_file"

  end_time=$(date +%s%3N)
  duration_ms=$((end_time - start_time))
  echo "$batch_id,$duration_ms" >> "$TIMING_FILE"

  echo "Lote $batch_id completado → $output_file"
done

# Ejecuta el análisis en Python
python polaris-cli.py

# Limpieza temporal
rm batch_* all_yaml_files.txt