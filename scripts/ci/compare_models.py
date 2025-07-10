import sys
import os
from pathlib import Path
from flamapy.metamodels.fm_metamodel.transformations import UVLReader

def extract_features_constraints(uvl_path):
    model = UVLReader(str(uvl_path)).transform()
    features = set(f.name for f in model.get_features())
    constraints = set(str(c) for c in model.get_constraints())
    return features, constraints

def generate_changelog(current, previous, diff_dir):
    added_features = sorted(current['features'] - previous['features'])
    removed_features = sorted(previous['features'] - current['features'])

    added_constraints = sorted(current['constraints'] - previous['constraints'])
    removed_constraints = sorted(previous['constraints'] - current['constraints'])

    with open(diff_dir / "changelog.md", "w", encoding="utf-8") as f:
        f.write(f"# 🔄 Feature Model Changes\n\n")
        f.write(f"## 📂 Features Added ({len(added_features)})\n")
        for feat in added_features:
            f.write(f"- ✚ `{feat}`\n")
        f.write(f"\n## 🗑️ Features Removed ({len(removed_features)})\n")
        for feat in removed_features:
            f.write(f"- ➖ `{feat}`\n")
        f.write(f"\n## ⚠ Constraints Added ({len(added_constraints)})\n")
        for con in added_constraints:
            f.write(f"- `{con}`\n")
        f.write(f"\n## ❌ Constraints Removed ({len(removed_constraints)})\n")
        for con in removed_constraints:
            f.write(f"- `{con}`\n")
    print(f"✅ Changelog saved to: {diff_dir / 'changelog.md'}")

def main():
    if len(sys.argv) < 2:
        print("❌ Provide current version (e.g. v1.30.3)")
        sys.exit(1)

    current_version = sys.argv[1]
    base_dir = Path("../../variability_model/ci_k8s_models")
    model_file = "kubernetes_combined.uvl"

    current_path = base_dir / current_version / model_file
    versions = sorted([d.name for d in base_dir.iterdir() if (base_dir / d / model_file).exists()])
    if current_version not in versions:
        print("❌ Current version not found.")
        sys.exit(1)

    idx = versions.index(current_version)
    if idx == 0:
        print("ℹ️ No previous version to compare.")
        sys.exit(0)

    previous_version = versions[idx - 1]
    previous_path = base_dir / previous_version / model_file

    print(f"🔍 Comparing:\n- Previous: {previous_version}\n- Current: {current_version}")
    current_data = {}
    previous_data = {}

    try:
        current_data['features'], current_data['constraints'] = extract_features_constraints(current_path)
        previous_data['features'], previous_data['constraints'] = extract_features_constraints(previous_path)
    except Exception as e:
        print(f"❌ Error loading models: {e}")
        sys.exit(1)

    diff_dir = base_dir / f"diffs/{current_version}_vs_{previous_version}"
    diff_dir.mkdir(parents=True, exist_ok=True)

    generate_changelog(current_data, previous_data, diff_dir)

if __name__ == "__main__":
    main()