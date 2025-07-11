#!/bin/bash

INPUT_DIR="../../../resources/yamls_agrupation/yamls-tools-files"
RESULTS_DIR="../../../resources/results_data_tools/results_checkov1"
BATCH_SIZE=300
TIMING_FILE="$RESULTS_DIR/batch_times.txt"

mkdir -p "$RESULTS_DIR"
rm -f "$TIMING_FILE"

# Buscar archivos YAML
find "$INPUT_DIR" -type f \( -name "*.yaml" -o -name ".*.yaml" \) > all_yaml_files.txt

# Dividir en lotes
split -l $BATCH_SIZE all_yaml_files.txt batch_

# Procesar lotes
for batch_file in batch_*; do
  batch_id=$(basename "$batch_file")
  output_file="$RESULTS_DIR/$batch_id.txt"
  error_log="$RESULTS_DIR/${batch_id}_errors.log"

  if [ -s "$output_file" ]; then
    echo " Lote $batch_id ya procesado. Saltando..."
    continue
  fi

  echo " Procesando lote: $batch_id"
  start_time=$(date +%s%3N)

  temp_dir="$RESULTS_DIR/temp_$batch_id"
  mkdir -p "$temp_dir"
  > "$error_log"

  mapfile -t files < "$batch_file"
  for file in "${files[@]}"; do
    echo " 🧪 Analizando archivo: $file"
    fname=$(basename "$file")
    temp_output="$temp_dir/${fname}.txt"
    stderr_output="$temp_dir/${fname}.err"

    checkov -f "$file" --framework kubernetes > "$temp_output" 2> "$stderr_output"
    exit_code=$?

    if [ "$exit_code" -eq 0 ] && [ -s "$temp_output" ]; then
      echo "    $fname procesado correctamente"
    else
      echo "    Error al procesar $fname"
      {
        echo "Archivo: $file"
        echo "Código de salida: $exit_code"
        echo "---- STDERR ----"
        cat "$stderr_output"
        echo "----------------------------"
      } >> "$error_log"
      rm -f "$temp_output"
    fi
    rm -f "$stderr_output"
  done

  # Combinar todos los resultados válidos en un archivo
  valid_files=("$temp_dir"/*.txt)
  if [ -e "${valid_files[0]}" ]; then
    for temp_file in "${valid_files[@]}"; do
      cat "$temp_file" >> "$output_file"
      echo -e "\n----------------------------\n" >> "$output_file"
    done
    echo " Lote $batch_id completado → Resultado en: $output_file"
  else
    echo "  Todos los archivos del lote $batch_id fallaron. No se generó salida."
    rm -f "$output_file"
  fi

  rm -rf "$temp_dir"

  end_time=$(date +%s%3N)
  duration_ms=$((end_time - start_time))
  echo "$batch_id,$duration_ms" >> "$TIMING_FILE"
done

# Ejecutar procesamiento en Python
python checkov.py

# Limpieza temporal
rm batch_* all_yaml_files.txt