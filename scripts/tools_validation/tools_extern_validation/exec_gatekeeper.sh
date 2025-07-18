#!/bin/bash

INPUT_DIR="../../../resources/yamls_agrupation/yamls-tools-files"
RESULTS_DIR="../../../resources/results_data_tools/results_gatekeeper"
#POLICIES_DIR="./gatekeeper-library/library/general/block-endpoint-edit-default-role"
POLICIES_DIR="../../../resources/policies_tools/policies_gatekeeper/general_custom"

BATCH_SIZE=800

mkdir -p "$RESULTS_DIR"

# Lista todos los YAML y los guarda en un archivo temporal
find "$INPUT_DIR" -type f \( -name '*.yaml' \) > all_yaml_files.txt

# Divide en lotes de 1000
split -l "$BATCH_SIZE" all_yaml_files.txt batch_

# Procesa cada lote
for batch_file in batch_*; do
  batch_id=$(basename "$batch_file")
  output_file="$RESULTS_DIR/$batch_id.txt"

  echo "Procesando lote: $batch_id"
  echo "" > "$output_file"  # Vacía o crea el archivo de resultados del lote

  while read -r yaml_file; do
    file_name=$(basename "$yaml_file")

    echo "→ Validando $yaml_file"

    echo "##### FILE: $file_name #####" >> "$output_file"
    gator test --filename="$yaml_file" --filename="$POLICIES_DIR" >> "$output_file" 2>&1
    echo "" >> "$output_file"

  done < "$batch_file"

  echo "Lote $batch_id completado → Resultado en: $output_file"
done

# Ejecuta el procesamiento final en Python
python gatekeeper.py

# Limpieza temporal
rm batch_* all_yaml_files.txt
