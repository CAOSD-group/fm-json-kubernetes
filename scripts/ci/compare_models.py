import sys
from pathlib import Path
from flamapy.metamodels.fm_metamodel.transformations import UVLReader

def normalize_constraint(c: str) -> str:
    return c.replace(" ", "").replace("\t", "").replace("¬", "not").replace("!", "not").lower()

def extract_features_constraints(uvl_path):
    model = UVLReader(str(uvl_path)).transform()
    features = set(f.name for f in model.get_features())
    constraints = set(str(c) for c in model.get_constraints())
    return features, constraints

def generate_outputs(current, previous, diff_dir, current_version, previous_version):
    norm_current_constraints = {normalize_constraint(c): c for c in current['constraints']}
    norm_previous_constraints = {normalize_constraint(c): c for c in previous['constraints']}

    added_features = sorted(current['features'] - previous['features'])
    removed_features = sorted(previous['features'] - current['features'])
    added_constraints = sorted([
        norm_current_constraints[n] for n in norm_current_constraints if n not in norm_previous_constraints
    ])
    removed_constraints = sorted([
        norm_previous_constraints[n] for n in norm_previous_constraints if n not in norm_current_constraints
    ])

    diff_dir.mkdir(parents=True, exist_ok=True)
    md_path = diff_dir / "changelog.md"
    html_path = diff_dir / "changelog.html"

    ### Markdown
    with md_path.open("w", encoding="utf-8") as f:
        f.write(f"# 🔄 Feature Model Changes: {previous_version} → {current_version}\n\n")
        f.write("| 🔍 Type        | ➕ Added | ➖ Removed |\n")
        f.write("|---------------|----------|-------------|\n")
        f.write(f"| 📁 Features    | {len(added_features)} | {len(removed_features)} |\n")
        f.write(f"| 🧩 Constraints | {len(added_constraints)} | {len(removed_constraints)} |\n\n")
        f.write("## 📂 Features Added\n")
        for feat in added_features:
            f.write(f"- ✚ `{feat}`\n")
        f.write("\n## 🗑️ Features Removed\n")
        for feat in removed_features:
            f.write(f"- ➖ `{feat}`\n")
        f.write("\n## ⚠ Constraints Added\n")
        for con in added_constraints:
            f.write(f"- `{con}`\n")
        f.write("\n## ❌ Constraints Removed\n")
        for con in removed_constraints:
            f.write(f"- `{con}`\n")

    ### HTML con collapsibles
    with html_path.open("w", encoding="utf-8") as f:
        f.write(f"""<html><head><meta charset="utf-8">
<title>Changelog {current_version}</title>
<style>
body {{ font-family: Arial, sans-serif; padding: 2em; }}
table {{ border-collapse: collapse; width: 60%; }}
th, td {{ border: 1px solid #ccc; padding: 8px 12px; text-align: center; }}
th {{ background-color: #f4f4f4; }}
summary {{ font-weight: bold; cursor: pointer; margin-top: 1em; }}
.added {{ color: green; }}
.removed {{ color: red; }}
code {{ font-family: monospace; background-color: #f9f9f9; padding: 2px 4px; border-radius: 4px; }}
</style></head><body>
<h1>🔄 Feature Model Changes: {previous_version} → {current_version}</h1>
<table>
<thead><tr><th>🔍 Type</th><th class="added">➕ Added</th><th class="removed">➖ Removed</th></tr></thead>
<tbody>
<tr><td>📁 Features</td><td class="added">{len(added_features)}</td><td class="removed">{len(removed_features)}</td></tr>
<tr><td>🧩 Constraints</td><td class="added">{len(added_constraints)}</td><td class="removed">{len(removed_constraints)}</td></tr>
</tbody></table>
""")
        def collapsible(title, items):
            f.write(f'<details><summary>{title}</summary><ul>')
            for i in items:
                f.write(f'<li><code>{i}</code></li>')
            f.write('</ul></details>')

        collapsible("📂 Features Added", added_features)
        collapsible("🗑️ Features Removed", removed_features)
        collapsible("⚠ Constraints Added", added_constraints)
        collapsible("❌ Constraints Removed", removed_constraints)
        f.write("</body></html>")

    print(f"✅ Changelog saved to:\n- {md_path}\n- {html_path}")

def main():
    if len(sys.argv) < 2:
        print("❌ Provide current version (e.g. v1.32.2)")
        sys.exit(1)

    current_version = sys.argv[1]
    REPO_ROOT = Path(__file__).resolve().parents[2]
    base_dir = REPO_ROOT / "variability_model" / "ci_k8s_models"
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
    try:
        current_data = {}
        previous_data = {}
        current_data['features'], current_data['constraints'] = extract_features_constraints(current_path)
        previous_data['features'], previous_data['constraints'] = extract_features_constraints(previous_path)
        diff_dir = base_dir / "diffs" / f"{current_version}_vs_{previous_version}"
        generate_outputs(current_data, previous_data, diff_dir, current_version, previous_version)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()