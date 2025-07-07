"""
This script processes YAML manifest files by categorizing them into size-based buckets
and filtering out malformed or custom resource definitions (CRDs).

The processed files are then copied into appropriately named output directories.

Usage:
    Run this script after downloading Kubernetes manifest YAMLs to classify and organize them.

Directories:
    input_dir: Path to raw YAMLs.
    output_dir: Path where categorized YAMLs will be saved.
"""

import os
import shutil
import yaml
from datetime import datetime
from hashlib import md5

input_dir = '../kubernetes_fm/scripts/download_manifests/YAMLs02' ## Process
output_dir = '../resources/yamls_agrupation'

# Definitions of size groups: 0-5 kb, 5-25 kb...
buckets = {
    'tiny': (0, 5 * 1024), 
    'small': (5 * 1024, 25 * 1024),
    'medium': (25 * 1024, 100 * 1024),
    'large': (100 * 1024, 512 * 1024),
    'huge': (512 * 1024, float('inf')),
}
used_names = set()

def prepare_output_dirs():
    """
    Create output directories for each size bucket and special categories.

    This includes folders for errors, missing API/kind, and custom resources.
    """
    for bucket in list(buckets.keys()) + ['errores', 'no_apiversion_kind', 'custom_resources']:
        os.makedirs(os.path.join(output_dir, bucket), exist_ok=True)

def has_invalid_content(content):
    """
    Check if the content contains patterns indicating invalid templating.

    Args:
        content (str): The YAML file content.

    Returns:
        bool: True if invalid patterns are found.
    """
    return '{{' in content or '}}' in content or '#@' in content

def is_custom_resource(doc):
    """
    Determine if a YAML document represents a CustomResourceDefinition (CRD).

    Args:
        doc (dict): Parsed YAML document.

    Returns:
        bool: True if the document is a CRD.
    """
    return doc.get('kind') == 'CustomResourceDefinition'


def get_unique_name(dest_folder, fname, index, content):
    """
    Generate a unique file name for storing processed YAML documents.

    If the name already exists, a hash of the content is appended.

    Args:
        dest_folder (str): Target directory.
        fname (str): Original file name.
        index (int): Document index in multi-doc files.
        content (str): Content used to generate a hash if needed.

    Returns:
        str: A unique file name.
    """

    base, ext = os.path.splitext(fname) # Separates the base name from the extension
    fname_modify = f"{base}_{index}{ext}" if index > 0 else f"{base}{ext}"

    if fname_modify in used_names: ## Check if the candidate is already on the global list.
        hash_id = md5(content.encode()).hexdigest()[:8]
        fname_modify = f"{base}_{hash_id}_{index}{ext}" if index > 0 else f"{base}_{hash_id}{ext}"

    used_names.add(fname_modify)
    print(f"VALORES fname2: {fname_modify}  {fname} {index}")

    return fname_modify

def get_size_bucket(content):
    """
    Determine the size category for a YAML document based on byte size.

    Args:
        content (str): YAML content as string.

    Returns:
        str: One of the predefined size bucket names.
    """

    ## size_bytes = len(content.encode('utf-8'))
    size_bytes = len(content.encode('utf-8'))
    for bucket_name, (min_b, max_b) in buckets.items():
        if min_b <= size_bytes < max_b:
            return bucket_name
    return 'huge'
    
def has_valid_api_and_kind(doc):
    """
    Validate that the YAML document has both apiVersion and kind defined.

    Args:
        doc (dict): Parsed YAML document.

    Returns:
        bool: True if both fields are present and non-null.
    """

    return (
        isinstance(doc, dict) and
        bool(doc.get('apiVersion')) and
        bool(doc.get('kind')) and
        doc.get('apiVersion') != 'N/A' and
        doc.get('kind') != 'N/A'
    )
def main():
    """
    Main processing routine. Iterates over input YAML files, parses them,
    checks for issues or CRDs, categorizes them, and writes logs.

    Raises:
        Exceptions are caught and logged individually per file.
    """

    prepare_output_dirs()
    log_file_path = os.path.join(output_dir, 'preprocess_log.txt')

    total_files = 0
    total_files_declarations = 0
    errores = 0
    sin_meta = 0
    custom_count = 0

    with open(log_file_path, 'w', encoding='utf-8') as log:
        log.write(f"Inicio: {datetime.now()}\n\n")

        for fname in os.listdir(input_dir):
            if not fname.endswith(('.yaml', '.yml')):
                continue

            total_files += 1
            src_path = os.path.join(input_dir, fname)

            try:
                with open(src_path, 'r', encoding='utf-8') as yaml_file:
                    raw_content = yaml_file.read()
                    # Verification of templating
                if has_invalid_content(raw_content):
                    shutil.copy(src_path, os.path.join(output_dir, 'errores', fname))
                    log.write(f"[TEMPLATE OMITIDO] {fname} contiene templating → omitido\n")
                    continue
                # Separation by standard YAML documents
                yaml_documents = list(yaml.safe_load_all(raw_content))

                if not yaml_documents:
                    log.write(f"[VACÍO] {fname}\n")
                    continue

                #  Case 1: only one valid document → copy
                if len(yaml_documents) == 1:
                    doc = yaml_documents[0]
                    content = yaml.dump(doc, sort_keys=False)
                    bucket = get_size_bucket(content)

                    if has_invalid_content(content):
                        shutil.copy(src_path, os.path.join(output_dir, 'errores', fname))
                        log.write(f"[INVALIDO] {fname} (único) → errores\n")
                        errores += 1
                        continue

                    if not has_valid_api_and_kind(doc):
                        shutil.copy(src_path, os.path.join(output_dir, 'no_apiversion_kind', fname))
                        log.write(f"[SIN META] {fname} (único) → no_apiversion_kind\n")
                        sin_meta += 1
                        continue

                    if is_custom_resource(doc):
                        shutil.copy(src_path, os.path.join(output_dir, 'custom_resources', fname))
                        log.write(f"[CRD OMITIDO] {fname} (único) → custom_resources\n")
                        custom_count += 1
                        continue

                    shutil.copy(src_path, os.path.join(output_dir, bucket, fname))
                    log.write(f"[OK] {fname} (único) → {bucket}\n")
                    continue

                #  Case 2: multiple documents → process individually
                for i, doc in enumerate(yaml_documents):
                    total_files_declarations += 1

                    content = yaml.dump(doc, sort_keys=False)
                    bucket = get_size_bucket(content)
                    unique_name = get_unique_name(os.path.join(output_dir, bucket), fname, i, content)

                    if not isinstance(doc, dict): ## Omission of empty files or files with no content: only comments etc
                        with open(os.path.join(output_dir, 'errores', unique_name), 'w', encoding='utf-8') as f: ## Added for sabe files with errors...
                            f.write(content)                        
                        log.write(f"[INVALIDO] Documento vacío o no mapeable en {fname}, índice {i}\n")
                        errores += 1
                        continue

                    if not has_valid_api_and_kind(doc):
                        with open(os.path.join(output_dir, 'no_apiversion_kind', unique_name), 'w', encoding='utf-8') as f:
                            f.write(content)
                        log.write(f"[SIN META] {fname}, índice {i} → no_apiversion_kind\n")
                        sin_meta += 1
                        continue

                    if is_custom_resource(doc):
                        with open(os.path.join(output_dir, 'custom_resources', unique_name), 'w', encoding='utf-8') as f:
                            f.write(content)
                        log.write(f"[CRD OMITIDO] {fname}, índice {i} → custom_resources\n")
                        custom_count += 1
                        continue

                    # Documento válido → guardar en bucket
                    with open(os.path.join(output_dir, bucket, unique_name), 'w', encoding='utf-8') as f:
                        f.write(content)
                    log.write(f"[OK] {fname}, índice {i} → {bucket}\n")

            except Exception as e:
                errores += 1
                shutil.copy(src_path, os.path.join(output_dir, 'errores', fname)) ## Agregado para guardar también los errores generales sin contemplar
                log.write(f"[ERROR] {fname}: {str(e)}\n")

        log.write("\n--- RESUMEN ---\n")
        log.write(f"Total procesados: {total_files}\n")
        log.write(f"Total suma procesados mas enumeration: {total_files_declarations}\n") 
        log.write(f"Con errores: {errores}\n")
        log.write(f"Sin apiVersion/kind: {sin_meta}\n")
        log.write(f"Recursos personalizados: {custom_count}\n") ## Omitido por el momento
        log.write(f"Validos clasificados: {total_files - errores - sin_meta - custom_count}\n")
        log.write(f"Fin: {datetime.now()}\n")

    print(f" Preprocesamiento finalizado. Log guardado en: {log_file_path}")

if __name__ == '__main__':
    main()
