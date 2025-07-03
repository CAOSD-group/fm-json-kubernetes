#!/bin/bash

INPUT_DIR="./small"
INPUT_DIR="../scriptJsonToUvl/yamls_agrupation/yamls-tools-files"
POLICY_DIR="./policy"
RESULTS_DIR="./results_conftest"
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

  # Crea un archivo temporal con los YAML de este lote
  batch_list=$(mktemp)
  while read -r yaml_file; do
    echo "$yaml_file"
  done < "$batch_file" > "$batch_list"

  # Ejecutar Conftest
  ./conftest.exe test $(cat "$batch_list") --policy "$POLICY_DIR" --output json > "$output_file"

  end_time=$(date +%s%3N)
  duration_ms=$((end_time - start_time))
  echo "$batch_id,$duration_ms" >> "$TIMING_FILE"

  echo "Lote $batch_id completado → Resultado en: $output_file"

  rm "$batch_list"
done

# Ejecuta el análisis en Python
python conftest-parser.py

# Limpieza
rm batch_* all_yaml_files.txt