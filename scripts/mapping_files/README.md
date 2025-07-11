# Mapping and Configuration Translation

This module contains the scripts and logic to map YAML configurations into UVL feature model instances. The process enables real-world Kubernetes YAML files to be interpreted and validated against the variability model.

---

## Table of Contents

- [Overview](#overview)
- [Mapping to CSV](#mapping-to-csv)
- [YAML to JSON Conversion](#yaml-to-json-conversion)
- [Obtaining Real YAML Files](#obtaining-real-yaml-files)
- [Implementation Notes](#implementation-notes)
- [Known Issues and Adaptations](#known-issues-and-adaptations)

---

## Overview

This module forms the second step of the overall workflow: **configuration mapping and translation**.

From the generated UVL model, a **CSV mapping file** is created. This file acts as a bridge between YAML properties and feature names from the model. The subsequent scripts use this mapping to **convert YAML files into feature-oriented JSON representations**.

Each YAML input results in a JSON output that maintains:
- The original structure and values.
- A one-to-one mapping between YAML keys and UVL features.

---

## Obtaining Real YAML Files

To acquire the set of real-world Kubernetes YAML configurations used in this module, follow the extraction instructions from the companion project:

👉 [kubernetes_fm - Extracting Real Configurations of Kubernetes from GitHub Repositories](https://github.com/CAOSD-group/kubernetes_fm?tab=readme-ov-file#extracting-real-configurations-of-kubernetes-from-github-repositories)

This external pipeline automates the collection of manifests directly from public GitHub repositories, filtered and prepared for further processing.

---

## Mapping to CSV

- The `mappingUvlCsv.csv` file links model features to their corresponding property names in YAML configurations.
- This is created using a dedicated Python script that scans the model and establishes feature-to-key mappings.
- The goal is to translate real-world YAML values into interpretable feature selections.

---

## YAML to JSON Conversion

The conversion script performs the following:

1. **Reads the structure** of each YAML configuration file.
2. **Looks up** each key using the CSV mapping to find the corresponding feature.
3. **Creates a JSON output** that preserves the original values but with feature-based keys.
4. Supports:
   - Scalar values (`string`, `integer`, `boolean`)
   - Arrays and nested structures
   - Custom extensions and manual annotations from the model

> Output: one JSON file per YAML input, ready for validation.

---

## Implementation Notes

- The conversion uses a recursive parser to handle nested mappings and arrays.
- Keys not found in the CSV are skipped or logged.
- Descriptive features added manually to the model can be completed automatically during JSON generation.

---

## Known Issues and Adaptations

To support wider real-world use:

- **Null or empty values** (`null`, `{}`, `emptyDir`) can now be modeled with boolean features like `isNull` or `isEmpty`.
- **Large-scale YAML validation** is optimized by batch processing and caching known kinds and versions.
- A reference CSV of allowed `(apiVersion, kind)` combinations is generated to identify unsupported files.
- Files with unsupported combinations are moved to a separate folder and marked as invalid automatically.

---

_In the future, support for custom schema extensions may be added by extending the mapping model._
