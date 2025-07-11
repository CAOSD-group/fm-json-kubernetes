import os
import sys
import shutil
import subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("❌ You must provide a version, e.g. v1.30.3")
        sys.exit(1)

    version = sys.argv[1]

    """input_path = f"../../resources/ci_k8s_schemas/kubernetes-json-{version}/_definitions.json".replace("\\", "/")
    output_dir = f"../../variability_model/ci_k8s_models/{version}".replace("\\", "/")
    uvl_path = f"{output_dir}/kubernetes_combined.uvl"
    desc_path = f"{output_dir}/descriptions.json"""
    REPO_ROOT = Path(__file__).resolve().parents[2]
    input_path = REPO_ROOT / "resources" / "ci_k8s_schemas" / f"kubernetes-json-{version}" / "_definitions.json"
    output_dir = REPO_ROOT / "variability_model" / "ci_k8s_models" / version
    uvl_path = output_dir / "kubernetes_combined.uvl"
    desc_path = output_dir / "descriptions.json"

    if not os.path.isfile(input_path):
        print(f"❌ Input JSON not found: {input_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # Create temp copy of model_generation directory
    """temp_folder = "../../scripts/ci/tmp_modelgen"
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)
    shutil.copytree("../../scripts/model_generation", temp_folder)"""

    modelgen_src = REPO_ROOT / "scripts" / "model_generation"
    temp_folder = REPO_ROOT / "scripts" / "ci" / "tmp_modelgen"
    if temp_folder.exists():
        shutil.rmtree(temp_folder)
    shutil.copytree(modelgen_src, temp_folder)

    # Update paths in temp convert01.py
    ##temp_script = os.path.join(temp_folder, "convert01.py")
    temp_script = temp_folder / "convert01.py"
    with open(temp_script, "r", encoding="utf-8") as file:
        lines = file.readlines()

    with open(temp_script, "w", encoding="utf-8") as file:
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("definitions_file ="):
                indent = line[:line.index("definitions_file")]
                file.write(f"{indent}definitions_file = '{input_path.as_posix()}'\n")
                ##file.write(f"{indent}definitions_file = '{input_path}'\n")
            elif stripped.startswith("output_file ="):
                indent = line[:line.index("output_file")]
                file.write(f"{indent}output_file = '{uvl_path.as_posix()}'\n")
                ##file.write(f"{indent}output_file = '{uvl_path}'\n")
            elif stripped.startswith("descriptions_file ="):
                indent = line[:line.index("descriptions_file")]
                file.write(f"{indent}descriptions_file = '{desc_path.as_posix()}'\n")
                ##file.write(f"{indent}descriptions_file = '{desc_path}'\n")
            else:
                file.write(line)

    print(f"🚀 Generating model for {version}...")
    ##subprocess.run(["python", temp_script], check=True)
    subprocess.run(["python", str(temp_script)], check=True)

    if uvl_path.exists():##os.path.exists(uvl_path):
        print(f"✅ Model saved to {uvl_path}")
    else:
        print("❌ UVL file was not generated.")
        sys.exit(1)

    shutil.rmtree(temp_folder)
    print("🧹 Temporary files cleaned up.")

if __name__ == "__main__":
    main()