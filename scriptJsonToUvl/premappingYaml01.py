import os
import shutil
import yaml
from datetime import datetime
from hashlib import md5

input_dir = '../kubernetes_fm/scripts/download_manifests/YAMLs02'
#input_dir = './generateConfigs/files_yamls'
##input_dir = '../files_yamls_dowload/yamls-tester'

output_dir = './yamls_agrupation' ## /tester

# Clasificación por tamaño: 0-5 kb, 5-25 kb...
buckets = {
    'tiny': (0, 5 * 1024), 
    'small': (5 * 1024, 25 * 1024),
    'medium': (25 * 1024, 100 * 1024),
    'large': (100 * 1024, 512 * 1024),
    'huge': (512 * 1024, float('inf')),
}
used_names = set()

# Crea todas las carpetas necesarias
def prepare_output_dirs():
    for bucket in list(buckets.keys()) + ['errores', 'no_apiversion_kind', 'custom_resources']:
        os.makedirs(os.path.join(output_dir, bucket), exist_ok=True)

# Detecta contenido inválido
def has_invalid_content(content):
        return '{{' in content or '}}' in content or '#@' in content

# Detecta CRDs o recursos personalizados
def is_custom_resource(doc):
        return doc.get('kind') == 'CustomResourceDefinition' ## Si kind coincide con el tipo CRD se descarta


# Genera nombre único, si hay coincidencia se agrega una generacion por hash
def get_unique_name(dest_folder, fname, index, content):

    base, ext = os.path.splitext(fname) ## Separa el nombre base de la extension
    fname_modify = f"{base}_{index}{ext}" if index > 0 else f"{base}{ext}"

    if fname_modify in used_names: ## Se comprueba si el candidato ya esta en la lista global
        hash_id = md5(content.encode()).hexdigest()[:8]
        fname_modify = f"{base}_{hash_id}_{index}{ext}" if index > 0 else f"{base}_{hash_id}{ext}"

    used_names.add(fname_modify)
    print(f"VALORES fname2: {fname_modify}  {fname} {index}")

    return fname_modify

# Determina bucket de tamaño
def get_size_bucket(content):
    ## size_bytes = len(content.encode('utf-8'))
    size_bytes = len(content.encode('utf-8'))
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
    log_file_path = os.path.join(output_dir, 'preprocess_log.txt') ## Usar normalizacion? os.path.normpath

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
                    # Verificación de templating
                if has_invalid_content(raw_content):
                    shutil.copy(src_path, os.path.join(output_dir, 'errores', fname))
                    log.write(f"[TEMPLATE OMITIDO] {fname} contiene templating → omitido\n")
                    continue
                # Separación por documentos YAML estándar
                yaml_documents = list(yaml.safe_load_all(raw_content))

                if not yaml_documents:
                    log.write(f"[VACÍO] {fname}\n")
                    continue

                #  Caso 1: solo un documento válido → copiar
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

                #  Caso 2: múltiples documentos → procesar individualmente
                for i, doc in enumerate(yaml_documents):
                    total_files_declarations += 1

                    content = yaml.dump(doc, sort_keys=False)
                    bucket = get_size_bucket(content)
                    unique_name = get_unique_name(os.path.join(output_dir, bucket), fname, i, content)

                    if not isinstance(doc, dict): ## Omision de archivos vacíos o sin contenido: solo comentarios etc
                        with open(os.path.join(output_dir, 'errores', unique_name), 'w', encoding='utf-8') as f: ## Agregado para guardar archivos con los errores...
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
