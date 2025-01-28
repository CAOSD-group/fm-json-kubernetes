import yaml
import csv
import os
import json


def extract_yaml_properties(data, parent_key='', root_info=None, first_add=True):
    """
    Extrae las propiedades del YAML en tres listas:
    - Propiedades simples (para comparación con Turned)
    - Propiedades jerárquicas (para comparación con Midle)
    - Pares clave-valor para comparaciones más precisas
    """
    simple_props = []
    hierarchical_props = []
    key_value_pairs = []
    if root_info is None:
        root_info = {}

    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}_{key}" if parent_key else key
            # Guardar valores clave (apiVersion y kind) para determinar el contexto
            if key in ['apiVersion', 'kind']:
                if '/' in value:
                    value = value.replace('/', '_')
                root_info[key] = value
            simple_props.append(key)

            if isinstance(value, (dict, list)):
                sub_simple, sub_hierarchical, sub_kv_pairs, _ = extract_yaml_properties(value, new_key, root_info, first_add=False)
                simple_props.extend(sub_simple)
                hierarchical_props.extend(sub_hierarchical)
                hierarchical_props.append(new_key)  # Se agregan los valores despues de la recursión
                key_value_pairs.extend(sub_kv_pairs)
            else:
                hierarchical_props.append(new_key)
                key_value_pairs.append((new_key, value))  # Guardar clave y valor

    elif isinstance(data, list):
        for item in data:
            sub_simple, sub_hierarchical, sub_kv_pairs, _ = extract_yaml_properties(item, parent_key, root_info, first_add=False)
            simple_props.extend(sub_simple)
            hierarchical_props.extend(sub_hierarchical)
            key_value_pairs.extend(sub_kv_pairs)

    # Si tenemos apiVersion y kind, añadimos prefijo al feature para mejorar precisión
    if 'apiVersion' in root_info and 'kind' in root_info and first_add:
        prefix = f"{root_info['apiVersion']}_{root_info['kind']}"
        hierarchical_props = [f"{prefix}_{prop}" for prop in hierarchical_props]
        key_value_pairs = [(f"{prefix}_{key}", value) for key, value in key_value_pairs]

    return simple_props, hierarchical_props, key_value_pairs, root_info


def read_yaml_files_from_directory(directory_path):
    """
    Lee todos los archivos YAML en un directorio y extrae propiedades.
    """
    all_simple_props = set()
    all_hierarchical_props = set()
    all_key_value_pairs = set()
    context_info = {}
    error_log_path = './error_log.txt'

    with open(error_log_path, 'w', encoding='utf-8') as error_log:
        for filename in os.listdir(directory_path):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                file_path = os.path.join(directory_path, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as yaml_file:
                        yaml_data = yaml.safe_load(yaml_file)
                        if yaml_data is None:
                            error_log.write(f"Archivo vacío o no válido: {file_path}\n")
                            continue

                        simple_props, hierarchical_props, key_value_pairs, root_info = extract_yaml_properties(yaml_data)
                        all_simple_props.update(simple_props)
                        all_hierarchical_props.update(hierarchical_props)
                        all_key_value_pairs.update(key_value_pairs)
                        context_info[filename] = root_info

                except yaml.YAMLError as e:
                    error_log.write(f"Error de YAML en archivo {file_path}: {str(e)}\n")
                except FileNotFoundError:
                    error_log.write(f"Archivo no encontrado: {file_path}\n")
                except Exception as e:
                    error_log.write(f"Error desconocido en archivo {file_path}: {str(e)}\n")

    return list(all_simple_props), list(all_hierarchical_props), list(all_key_value_pairs), context_info


def search_features_in_csv(simple_props, hierarchical_props, key_value_pairs, csv_file, root_info):
    """
    Busca coincidencias en el CSV utilizando las listas separadas:
    - Comparación de simple_props con la columna 'Turned'
    - Comparación de hierarchical_props con la columna 'Midle'
    - Comparación de key_value_pairs con la columna 'Value'
    """
    found_features = []

    with open(csv_file, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            feature, middle, turned, value = row[0], row[1], row[2], row[3]

            # Filtrar el CSV por apiVersion y kind
            if f"_{root_info['apiVersion']}_{root_info['kind']}_" in feature:

                # Buscar coincidencias exactas en la columna 'Midle'
                for hierarchical_prop in hierarchical_props:
                    if middle.strip() and hierarchical_prop.endswith(middle):
                        found_features.append(feature)
                    for key, yaml_value in key_value_pairs:
                        if value and str(yaml_value) == value:
                            aux_hierchical_value_added = f"{key}_{yaml_value}"
                            if feature.endswith(aux_hierchical_value_added):
                                found_features.append(feature)

    return list(set(found_features))  # Eliminar duplicados


# Ruta de la carpeta donde están los archivos YAML
yaml_directory = './testing-maping/files_yamls/'

# Leer YAMLs y extraer propiedades
simple_props, hierarchical_props, key_value_pairs, context_info = read_yaml_files_from_directory(yaml_directory)

print("Propiedades simples extraídas del YAML:", simple_props)
print("Propiedades jerárquicas extraídas del YAML:", hierarchical_props)
print("Pares clave-valor extraídos del YAML:", key_value_pairs)
print("Contexto de los YAML:", context_info)

# Buscar coincidencias en el CSV basado en apiVersion y kind
csv_file_path = './testing-maping/kubernetes_mapping_features_part01.csv'

# Preparar estructura para JSON
output_data = []

for filename, root_info in context_info.items():
    print(f"\nProcesando archivo: {filename}")
    features_found = search_features_in_csv(simple_props, hierarchical_props, key_value_pairs, csv_file_path, root_info)
    yaml_entry = {
        "filename": filename,
        "apiVersion": root_info.get("apiVersion", "N/A"),
        "kind": root_info.get("kind", "N/A"),
        "found_features": features_found
    }
    output_data.append(yaml_entry)

# Guardar la salida en JSON
output_json_path = './testing-maping/output_features.json'

with open(output_json_path, 'w', encoding='utf-8') as json_file:
    json.dump(output_data, json_file, ensure_ascii=False, indent=4)

print(f"Resultados guardados en: {output_json_path}")
