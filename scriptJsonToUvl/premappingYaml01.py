import os
import shutil
import yaml
from datetime import datetime
from hashlib import md5

input_dir = '../kubernetes_fm/scripts/download_manifests/YAMLs02'
output_dir = './yamls_agrupation'

# Clasificación por tamaño: 0-5 kb, 5-25 kb...
buckets = {
    'tiny': (0, 5 * 1024), 
    'small': (5 * 1024, 25 * 1024),
    'medium': (25 * 1024, 100 * 1024),
    'large': (100 * 1024, 512 * 1024),
    'huge': (512 * 1024, float('inf')),
}

# Crea todas las carpetas necesarias
def prepare_output_dirs():
    for bucket in list(buckets.keys()) + ['errores', 'no_apiversion_kind', 'custom_resources']:
        os.makedirs(os.path.join(output_dir, bucket), exist_ok=True)

# Detecta contenido inválido
def has_invalid_content(content):
    if '{{' in content:
        return True
    elif '#@' in content:
        return True
    for line in content.splitlines():
        if line.strip().startswith('##'):
            return True
        if line.strip().startswith('#@'):
            return True
    return False

# Detecta CRDs o recursos personalizados
def is_custom_resource(doc):
    if not isinstance(doc, dict):
        return False
    if doc.get('kind') == 'CustomResourceDefinition':
        return True
    api = doc.get('apiVersion', '')
    return '.' in api ## and not api.startswith('v1') and not api.startswith('apps/')

# Genera nombre único por hash
def get_unique_name(fname, content):
    path = os.path.join(dest_folder, fname)
    if not os.path.exists(path):
        return fname  # Nombre original si no hay colisión
    hash_id = md5(content.encode()).hexdigest()[:8]
    base, ext = os.path.splitext(fname)
    return f"{base}_{hash_id}{ext}"

# Determina bucket de tamaño
def get_size_bucket(size_bytes):
    for bucket_name, (min_b, max_b) in buckets.items():
        if min_b <= size_bytes < max_b:
            return bucket_name
    return 'huge'
    
def has_valid_api_and_kind(doc):
    return (
        isinstance(doc, dict) and
        bool(doc.get('apiVersion')) and
        bool(doc.get('kind')) and
        doc.get('apiVersion') != 'N/A' and
        doc.get('kind') != 'N/A'
    )
def main():
    prepare_output_dirs()
    log_file_path = os.path.normpath(os.path.join(output_dir, 'preprocess_log.txt'))

    total_files = 0
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
                size = os.path.getsize(src_path)

                with open(src_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                bucket = get_size_bucket(size)
                ##unique_name = get_unique_name(fname, content)
                unique_name = get_unique_name(os.path.join(output_dir, bucket), fname, content)

                if has_invalid_content(content):
                    shutil.copy(src_path, os.path.join(output_dir, 'errores', unique_name))
                    log.write(f"[INVALIDO] {fname} tiene '{{' o comentarios con '##'\n")
                    errores += 1
                    continue

                documents = list(yaml.safe_load_all(content))
                ##if not any(isinstance(doc, dict) and 'apiVersion' in doc and 'kind' in doc for doc in documents):
                if not any(has_valid_api_and_kind(doc) for doc in documents):
                    shutil.copy(src_path, os.path.join(output_dir, 'sin_apiversion_kind', unique_name))
                    log.write(f"[SIN META] {fname} no tiene apiVersion/kind\n")
                    sin_meta += 1
                    continue

                if any(is_custom_resource(doc) for doc in documents):
                    shutil.copy(src_path, os.path.join(output_dir, 'custom_resources', unique_name))
                    log.write(f"[CUSTOM] {fname} clasificado como recurso personalizado\n")
                    custom_count += 1
                    continue

                shutil.copy(src_path, os.path.join(output_dir, bucket, unique_name))
                log.write(f"[OK] {fname} → {bucket} ({size} bytes)\n")

            except Exception as e:
                errores += 1
                log.write(f"[ERROR] {fname}: {str(e)}\n")

        log.write("\n--- RESUMEN ---\n")
        log.write(f"Total procesados: {total_files}\n")
        log.write(f"Con errores: {errores}\n")
        log.write(f"Sin apiVersion/kind: {sin_meta}\n")
        log.write(f"Recursos personalizados: {custom_count}\n") ## Omitido por el momento
        log.write(f"Validos clasificados: {total_files - errores - sin_meta - custom_count}\n")
        log.write(f"Fin: {datetime.now()}\n")

    print(f"✅ Preprocesamiento finalizado. Log guardado en: {log_file_path}")

if __name__ == '__main__':
    main()
