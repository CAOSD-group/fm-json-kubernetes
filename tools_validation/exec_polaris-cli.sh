#!/bin/bash

INPUT_DIR="./small"
RESULTS_DIR="./results_polaris-cli"
# INPUT_DIR="../scriptJsonToUvl/yamls_agrupation/yamls-tools-files"
BATCH_SIZE=800
TIMING_FILE="$RESULTS_DIR/batch_times.txt"

mkdir -p "$RESULTS_DIR"

# Lista todos los YAML y los guarda en un archivo temporal
find "$INPUT_DIR" -type f -name "*.yaml" > all_yaml_files.txt

# Divide en lotes de 800
split -l $BATCH_SIZE all_yaml_files.txt batch_

# Procesa cada lote
for batch_file in batch_*; do
  batch_id=$(basename "$batch_file")
  output_file="$RESULTS_DIR/$batch_id.json"

  echo "Procesando lote: $batch_id"
  start_time=$(date +%s%3N)

  echo "[" > "$output_file"
  first=true

  while read -r yaml_file; do
    echo "→ Validando $yaml_file"
    
  # Ejecutar Polaris y filtrar líneas no deseadas
    result=$(./polaris.exe audit --audit-path "$yaml_file" 2>/dev/null | \
            grep -v "Upload your Polaris findings" | \
            grep -v "polaris audit --audit-path")
    if [ "$first" = true ]; then
      first=false
    else
      echo "," >> "$output_file"
    fi

    echo "$result" >> "$output_file"
  done < "$batch_file"

  echo "]" >> "$output_file"
  #./polaris.exe audit --audit-path "$yaml_file" | grep -v "Upload your Polaris findings" | grep -v "polaris audit --audit-path" >> "$output_file" 2>&1


  #done < "$batch_file"

  end_time=$(date +%s%3N)
  duration_ms=$((end_time - start_time))
  echo "$batch_id,$duration_ms" >> "$TIMING_FILE"

  echo "Lote $batch_id completado → Resultado en: $output_file"
done

# Ejecuta el análisis en Python
python polaris-cli.py

# Limpieza temporal
rm batch_* all_yaml_files.txt