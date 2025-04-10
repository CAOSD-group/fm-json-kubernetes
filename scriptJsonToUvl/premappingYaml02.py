            try:
                with open(src_path, 'r', encoding='utf-8') as yaml_file:
                    raw_content = yaml_file.read()

                # Separar por documentos
                raw_docs = [doc.strip() for doc in raw_content.split('---') if doc.strip()]
                parsed_docs = []
                errores_locales = 0

                for i, raw_doc in enumerate(raw_docs):
                    try:
                        doc = yaml.safe_load(raw_doc)
                        parsed_docs.append((i, doc, raw_doc))
                    except Exception as e:
                        errores += 1
                        errores_locales += 1
                        log.write(f"[ERROR] {fname}, documento {i}: {str(e)}\n")
                        with open(os.path.join(output_dir, 'errores', f"{os.path.splitext(fname)[0]}_doc{i}_error.yaml"), 'w', encoding='utf-8') as f:
                            f.write(raw_doc)

                if not parsed_docs:
                    log.write(f"[VACÍO] {fname}\n")
                    continue

                # Caso 1: sólo un documento válido → copiar archivo original completo si pasa validaciones
                if len(parsed_docs) == 1:
                    _, doc, _ = parsed_docs[0]
                    content = yaml.dump(doc, sort_keys=False)
                    bucket = get_size_bucket(content)

                    if has_invalid_content(raw_content):
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

                # Caso 2: múltiples documentos → procesar individualmente
                for i, (doc_index, doc, raw_doc) in enumerate(parsed_docs):
                    total_files_declarations += 1

                    if not isinstance(doc, dict):
                        log.write(f"[INVALIDO] Documento no mapeable en {fname}, índice {doc_index}\n")
                        errores += 1
                        continue

                    content = yaml.dump(doc, sort_keys=False)
                    bucket = get_size_bucket(content)
                    unique_name = get_unique_name(os.path.join(output_dir, bucket), fname, i, content)

                    if has_invalid_content(raw_doc):
                        with open(os.path.join(output_dir, 'errores', unique_name), 'w', encoding='utf-8') as f:
                            f.write(raw_doc)
                        log.write(f"[INVALIDO] {fname}, índice {doc_index} → errores\n")
                        errores += 1
                        continue

                    if not has_valid_api_and_kind(doc):
                        with open(os.path.join(output_dir, 'no_apiversion_kind', unique_name), 'w', encoding='utf-8') as f:
                            f.write(content)
                        log.write(f"[SIN META] {fname}, índice {doc_index} → no_apiversion_kind\n")
                        sin_meta += 1
                        continue

                    if is_custom_resource(doc):
                        with open(os.path.join(output_dir, 'custom_resources', unique_name), 'w', encoding='utf-8') as f:
                            f.write(content)
                        log.write(f"[CRD OMITIDO] {fname}, índice {doc_index} → custom_resources\n")
                        custom_count += 1
                        continue

                    with open(os.path.join(output_dir, bucket, unique_name), 'w', encoding='utf-8') as f:
                        f.write(content)
                    log.write(f"[OK] {fname}, índice {doc_index} → {bucket}\n")



"""import os
import shutil
import yaml
from datetime import datetime
from hashlib import md5

input_dir = './generateConfigs/files_yamls'
output_dir = './yamls_agrupations'

buckets = {
    'tiny': (0, 5 * 1024), 
    'small': (5 * 1024, 25 * 1024),
    'medium': (25 * 1024, 100 * 1024),
    'large': (100 * 1024, 512 * 1024),
    'huge': (512 * 1024, float('inf')),
}

used_names = set()

def prepare_output_dirs():
    for folder in list(buckets.keys()) + ['errors', 'invalids', 'customs']:
        os.makedirs(os.path.join(output_dir, folder), exist_ok=True)

def has_invalid_syntax(content):
    return '{{' in content or '}}' in content or '#@' in content

def has_valid_metadata(doc):
    return isinstance(doc, dict) and doc.get('apiVersion') and doc.get('kind')

def is_custom_resource_definition(doc):
    return doc.get('kind') == 'CustomResourceDefinition'

def get_size_bucket(content):
    size_bytes = len(content.encode('utf-8'))
    for bucket, (min_b, max_b) in buckets.items():
        if min_b <= size_bytes < max_b:
            return bucket
    return 'huge'

def get_unique_name(dest_folder, base_name, index, content, original_ext, total_docs_in_file):
    if total_docs_in_file == 1:
        fname = f"{base_name}{original_ext}"
    else:
        fname = f"{base_name}_doc{index}{original_ext}"

    path = os.path.join(dest_folder, fname)
    if fname not in used_names and not os.path.exists(path):
        used_names.add(fname)
        return fname

    hash_id = md5(content.encode()).hexdigest()[:8]
    fname = f"{base_name}_doc{index}_{hash_id}{original_ext}"
    used_names.add(fname)
    return fname

def main():
    prepare_output_dirs()
    log_path = os.path.join(output_dir, 'preprocess_log.txt')

    total_docs = 0
    saved_docs = 0
    skipped_docs = 0
    custom_docs = 0
    error_files = 0

    with open(log_path, 'w', encoding='utf-8') as log:
        log.write(f"Inicio: {datetime.now()}\n\n")

        for fname in os.listdir(input_dir):
            if not fname.endswith(('.yaml', '.yml')):
                continue

            src_path = os.path.join(input_dir, fname)
            base_name, ext = os.path.splitext(fname)

            try:
                with open(src_path, 'r', encoding='utf-8') as yaml_file:
                    #content = yaml_file.read() ## prueba directametnte con el contenido de los archivos
                    yaml_documents = list(yaml.safe_load_all(yaml_file)) # content
                    valid_docs = []
                    if not yaml_documents:
                        return None  # Archivo vacío o inválido
                
                # Verificar cuáles documentos son válidos
                for i, doc in enumerate(yaml_documents): ## Se recorren los docs del yaml independientemete si hay una o mas declaraciones

                    if not isinstance(doc, dict):
                        log.write(f"[INVALIDO] Documento vacío o no mapeable en {fname}, índice {i}\n")
                        skipped_docs += 1
                        continue

                    yaml_str = yaml.dump(doc, sort_keys=False)

                    if has_invalid_syntax(yaml_str):
                        log.write(f"[INVALIDO] Saltado por sintaxis en documento {i}: {fname}\n")
                        skipped_docs += 1
                        continue

                    if not has_valid_metadata(doc):
                        log.write(f"[INVALIDO] Documento sin metadata válida en {fname}, índice {i}\n")
                        skipped_docs += 1
                        continue

                    valid_docs.append((i, doc, yaml_str))

                if not valid_docs:
                    skipped_docs += 1
                    continue

                for idx, (i, doc, yaml_str) in enumerate(valid_docs):
                    if is_custom_resource_definition(doc):
                        folder = 'customs'
                        file_name = get_unique_name(os.path.join(output_dir, folder), base_name, i, yaml_str, ext, len(valid_docs))
                        path = os.path.join(output_dir, folder, file_name)
                        with open(path, 'w', encoding='utf-8') as f_out:
                            f_out.write(yaml_str)
                        log.write(f"[CRD OMITIDO] {fname} → {file_name}\n")
                        custom_docs += 1
                        total_docs += 1
                        continue

                    bucket = get_size_bucket(yaml_str)
                    file_name = get_unique_name(os.path.join(output_dir, bucket), base_name, i, yaml_str, ext, len(valid_docs))
                    path = os.path.join(output_dir, bucket, file_name)
                    with open(path, 'w', encoding='utf-8') as out_file:
                        out_file.write(yaml_str)
                    log.write(f"[OK] {fname} → {file_name} ({bucket})\n")
                    saved_docs += 1
                    total_docs += 1

            except Exception as e:
                log.write(f"[ERROR] {fname}: {str(e)}\n")
                error_files += 1

        log.write("\n--- RESUMEN ---\n")
        log.write(f"Total documentos procesados: {total_docs + skipped_docs + custom_docs}\n")
        log.write(f"Documentos guardados: {saved_docs}\n")
        log.write(f"Documentos omitidos (inválidos): {skipped_docs}\n")
        log.write(f"CRDs movidos a carpeta 'customs': {custom_docs}\n")
        log.write(f"Archivos con errores: {error_files}\n")
        log.write(f"Fin: {datetime.now()}\n")

    print(f"✅ Preprocesamiento finalizado. Archivos válidos guardados en '{output_dir}'")

if __name__ == '__main__':
    main()"""
