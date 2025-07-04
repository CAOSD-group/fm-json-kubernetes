#!/bin/bash

INPUT_DIR="../scriptJsonToUvl/yamls_agrupation/yamls-tools-files"
#INPUT_DIR="./small"  # Cambia según tu ruta real
RESULTS_DIR="./results_kube-score"
BATCH_SIZE=800
TIMING_FILE="$RESULTS_DIR/batch_times.txt"


mkdir -p "$RESULTS_DIR"
rm -f "$TIMING_FILE"

# Listar todos los YAML y guardarlos
find "$INPUT_DIR" -type f \( -name "*.yaml" \) > all_yaml_files.txt

# Dividir en lotes
split -l $BATCH_SIZE all_yaml_files.txt batch_

# Procesar cada lote
for batch_file in batch_*; do
  batch_id=$(basename "$batch_file")
  output_file="$RESULTS_DIR/${batch_id}.txt"

  mkdir -p tmp_kube_files
  while read -r yaml_path; do
    fname=$(basename "$yaml_path")
    cp "$yaml_path" "tmp_kube_files/$fname"
  done < "$batch_file"

  echo "Procesando lote: $batch_id"
  start_time=$(date +%s%3N)

  for f in tmp_kube_files/*.yaml; do
    [ -e "$f" ] || continue
    echo "### path=$f" >> "$output_file"
    ./kube-score.exe score "$f" >> "$output_file" 2>/dev/null
  done

  end_time=$(date +%s%3N)
  duration_ms=$((end_time - start_time))
  echo "$batch_id,$duration_ms" >> "$TIMING_FILE"

  rm -rf tmp_kube_files
  echo "Lote $batch_id completado → $output_file"
done

# Ejecutar análisis en Python
python kube-score.py

# Limpieza
rm batch_* all_yaml_files.txt