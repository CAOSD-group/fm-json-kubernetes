## Table of Contents

- [Table of Contents](#table-of-contents)
- [fm-json-kubernetes](#fm-json-kubernetes)
  - [Description](#description)
  - [How to use it](#how-to-use-it)
  - [Using the scripts](#using-the-scripts)
    - [Requirements](#requirements)
    - [Download and install](#download-and-install)
    - [Execution](#execution)- [Execution](#execution)
  - [Architecture and repository structure](#architecture-and-repository-structure)
  - [References and third-party tools](#references-and-third-party-tools)

---

## Description

**fm-json-kubernetes** is an automated pipeline for extracting a variability model from Kubernetes’ OpenAPI JSON schemas. It produces a [UVL (Universal Variability Language)](https://universal-variability-language.github.io/) feature model representing configuration options and their constraints.

The pipeline includes:
- Schema parsing and property mapping
- Rule-based constraint generation
- UVL model synthesis
- YAML-to-feature mapping and configuration validation using [Flamapy](https://www.flamapy.org/)

It is designed for research, analysis, and validation scenarios where formal modeling of complex system configurations (like Kubernetes) is required.

---

## How to use it

The usage involves two main steps:
1. Obtain a version of the Kubernetes `_definitions.json` schema (e.g., using the `scriptGetRepoVersion.sh`)
2. Run the main conversion script to generate the `.uvl` feature model

YAML configurations can then be mapped and validated against the model.

## Using the scripts

### Requirements

- [Python 3.9+](https://www.python.org/)
- [Flamapy](https://www.flamapy.org/)
- Git (to clone schema versions)
- Bash or PowerShell for script execution

---

### Download and install

1. Install [Python 3.9+](https://www.python.org/)

2. Clone this repository and enter the project folder:
git clone https://github.com/your-user/fm-json-kubernetes
cd fm-json-kubernetes

3. Create a virtual environment:

python -m venv env

4. Activate the environment:

In Linux: source env/bin/activate

In Windows: .\env\Scripts\Activate

5. Install the dependencies:

pip install -r requirements.txt


### Exectuion

To obtain the Kubernetes JSON schema. You can use the included script:
./scriptJsonToUvl/scriptGetRepoVersion.sh

Edit the line inside to specify the version (e.g., v1.30.2).

The convert0.py script is the entry point operation for...
Run the main feature model generator with:

python scriptJsonToUvl/convert01Large.py

Make sure to configure the correct path to the _definitions.json file at the bottom of the script:

python
definitions_file = '../kubernetes-json-v1.30.2/v1.30.2/_definitions.json'


#### Output files:


kubernetes_combined_02.uvl: Final synthesized feature model

descriptions_01.json: File containing grouped and parsed feature descriptions


## Architecture and repository structure

The overall workflow is visualized below:

![Schema updated](https://github.com/user-attachments/assets/4d97bee9-67b7-4c47-8b32-a040f17d2dd1)

Pipeline stages:

convert01Large.py: Parses JSON schemas and builds the UVL model

mappingUVC.csv: CSV mapping between YAML keys and UVL features

mappingYAMLJSON.py: Converts YAMLs to JSON candidates for validation

getStatisticsValid.py + valid_config.py: Run validation and generate result CSVs

Key folders:

/scriptJsonToUvl/: Main scripts and utilities

/v.30.2/: Example Kubernetes schema inputs

/resources/: Images, diagrams, and result data



## References and third-party software

Flamapy: SPL analysis and validation framework

Universal Variability Language (UVL)

Kubernetes JSON Schemas