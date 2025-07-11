# External Tool Validation Framework

This module handles the execution and comparison of several third-party tools used to validate Kubernetes YAML configuration files.

---

## Table of Contents

- [Overview](#overview)
- [Process](#process)
  - [1. Tool Execution](#1-tool-execution)
  - [2. Result Aggregation](#2-result-aggregation)
- [Tools Analyzed](#tools-analyzed)
- [Result Format](#result-format)
- [Remarks and Notes](#remarks-and-notes)

---

## Overview

This part of the project automates the validation of a large set of Kubernetes YAML configuration files using a variety of static analysis tools.

Scripts included:
- A **Bash script** to execute tools in batches over the YAML set.
- A **Python script** to parse their outputs and generate a summarized CSV file with metrics.

---

## Process

### 1. Tool Execution

YAML files (located in `/yamls_complete/`, ~227K files) are validated using CLI tools, one at a time or in batch mode.

Some tools require:
- Predefined policy sets (e.g., Kyverno, Gatekeeper)
- Local schema resolution (e.g., kubeconform)
- Specific output format configuration

### 2. Result Aggregation

After execution:
- Output is collected and filtered
- Results are stored in a CSV with fields like:

```csv
filename,tool_name,result,time
config1.yaml,kube-linter,true,0.4
config2.yaml,kube-score,false,0.2
```

---

## Tools Analyzed

| Tool              | Result Summary                              | Notes                              |
|------------------|----------------------------------------------|------------------------------------|
| **kube-linter**   | ~98k valid / 128k invalid                    | Reliable, policy-based             |
| **kube-score**    | ~70k valid / 156k invalid                    | Policy-driven, moderate speed      |
| **kyverno**       | ~1.2k valid / 592 invalid                    | Slow, policy-required              |
| **kubeconform**   | ~223k valid / 3.9k invalid                   | Schema validator, fast             |
| **polaris**       | ~90k valid / 136k invalid                    | Linter with internal policies      |
| **datree**        | Deprecated (mid 2023)                        | Not recommended                    |
| **conftest**      | ~117k valid / 109k invalid                   | Rego-based                         |
| **terrascan**     | ~83k valid / 143k invalid                    | Needs `-i k8s` flag for use        |
| **trivy**         | ~82k valid / 144k invalid                    | Powerful but selective             |
| **checkov**       | Incomplete                                  | SCA/scan hybrid                    |
| **kubevious**     | Deprecated / UI-focused                     | Not practical CLI use              |
| **kubernetes-validate** | Implemented                          | JSON Schema validator              |
| **kubeval**       | Deprecated                                  | Not recommended                    |

---

## Result Format

Each YAML file is tracked with:

- **Validation result** (`true` / `false`)
- **Time taken**
- **Tool used**
- **Batch ID (if applicable)**

> Results are exported in `resources/results_external_validation.csv` (or similar).

---

## Remarks and Notes

- Tools like **Kyverno** and **Gatekeeper** require external policy definitions. These were sourced from their official repositories.
- Some tools (e.g., Polaris) output summary data only, making per-file analysis difficult.
- Some validations were filtered post-processing due to incorrect or incomplete outputs (e.g., Kyverno batch timeouts).
- Tools marked **deprecated** were excluded from final benchmarking.

This module provides a baseline reference for **external YAML validation behavior** and serves as comparison against our internal tool.