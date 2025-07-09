import os
import sys
import shutil
import subprocess

def main():
  if len(sys.argv) < 2:
    print("❌ You must provide a version, e.g. v1.30.2")
    sys.exit(1)

  version = sys.argv[1]
  uvl_path = f"../../variability_model/ci_k8s_models/{version}/kubernetes_combined.uvl".replace("\\", "/")
  log_path = f"../../variability_model/ci_k8s_models/{version}/validation_log.txt".replace("\\", "/")
  temp_script = "tmp_valid_config.py"

  if not os.path.exists(uvl_path):
    print(f"❌ Model not found: {uvl_path}")
    sys.exit(1)

  # Copy validation script
  original_script = "../../scripts/tools_validation/feature_model_validation/valid_config.py"
  shutil.copy(original_script, temp_script)

  # Replace static path in copy
  with open(temp_script, "r", encoding="utf-8") as file:
    lines = file.readlines()

  with open(temp_script, "w", encoding="utf-8") as file:
    for line in lines:
      stripped = line.strip()
      # Eliminar línea de importación no usada
      if stripped.startswith("from configurationJSON01 import ConfigurationJSON"):
        continue
      if stripped.startswith("FM_PATH ="):
        indent = line[:line.index("FM_PATH")]
        file.write(f"{indent}FM_PATH = '{uvl_path}'\n")
      else:
        file.write(line)

  print(f"🧪 Validating model for {version}...")
  result = subprocess.run([sys.executable, temp_script], capture_output=True, text=True)

  with open(log_path, "w", encoding="utf-8") as log_file:
    log_file.write(result.stdout)
    log_file.write(result.stderr)

  # Check result
  if "Valid?: True" in result.stdout:
    print("✅ Model is valid.")
  else:
    print("❌ Model is NOT valid.")

  os.remove(temp_script)

if __name__ == "__main__":
  main()