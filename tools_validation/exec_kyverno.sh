#!/bin/bash

INPUT_DIR="../scriptJsonToUvl/yamls_agrupation/yamls-tools-files"
#INPUT_DIR="./small"
RESULTS_DIR="./results_kyverno_parallel01"
POLICIES_DIR="./policies/best-practices"
BATCH_SIZE=800
TIMING_FILE="$RESULTS_DIR/batch_times.txt"
THREADS=6

mkdir -p "$RESULTS_DIR"
rm -f "$TIMING_FILE"

find "$INPUT_DIR" -type f -name '*.yaml' > all_yaml_files.txt
split -l "$BATCH_SIZE" all_yaml_files.txt batch_

for batch_file in batch_*; do
  batch_id=$(basename "$batch_file")
  output_file="$RESULTS_DIR/$batch_id.txt"
  tmp_dir="./tmp_outputs_$batch_id"
  mkdir -p "$tmp_dir"

  echo "Procesando lote: $batch_id"
  start_time=$(date +%s%3N)

  cat "$batch_file" | xargs -I{} -P $THREADS bash -c '
    yaml_path="{}"
    fname=$(basename "$yaml_path")
    echo "→ Validando $yaml_path"
    tmpout="'"$tmp_dir"'/$fname.txt"

    echo "##### FILE: $fname #####" > "$tmpout"
    ./kyverno apply "'"$POLICIES_DIR"'" --resource "$yaml_path" >> "$tmpout" 2>&1
    echo "" >> "$tmpout"
  '

  # Unir todos los resultados
  cat "$tmp_dir"/*.txt > "$output_file"

  end_time=$(date +%s%3N)
  duration_ms=$((end_time - start_time))
  echo "$batch_id,$duration_ms" >> "$TIMING_FILE"

  echo " Lote $batch_id completado → Resultado en: $output_file"
  rm -rf "$tmp_dir"
done

python kyverno.py
rm batch_* all_yaml_files.txt