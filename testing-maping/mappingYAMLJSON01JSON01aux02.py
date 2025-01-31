import yaml
import csv
import os
import json

def extract_yaml_properties(data, parent_key='', root_info=None, first_add=True):
    """
    Extrae las propiedades del YAML manteniendo la jerarquía y creando una estructura anidada.
    """
    result = {}
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

            if isinstance(value, (dict, list)):
                result[key] = extract_yaml_properties(value, new_key, root_info, first_add=False)
            else:
                result[key] = value

    elif isinstance(data, list):
        result = [extract_yaml_properties(item, parent_key, root_info, first_add=False) for item in data]

    return result


def read_yaml_files_from_directory(directory_path):
    """
    Lee todos los archivos YAML en un directorio y extrae propiedades.
    """
    yaml_data_list = []
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

                        structured_data = extract_yaml_properties(yaml_data)
                        yaml_data_list.append((filename, structured_data))

                except yaml.YAMLError as e:
                    error_log.write(f"Error de YAML en archivo {file_path}: {str(e)}\n")
                except FileNotFoundError:
                    error_log.write(f"Archivo no encontrado: {file_path}\n")
                except Exception as e:
                    error_log.write(f"Error desconocido en archivo {file_path}: {str(e)}\n")

    return yaml_data_list


def search_features_in_csv(structured_yaml, csv_file):
    """
    Busca coincidencias en el CSV utilizando la estructura del YAML.
    """
    mapped_features = {}

    def recursive_search(data, path=""):
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}_{key}" if path else key
                if isinstance(value, (dict, list)):
                    recursive_search(value, current_path)
                else:
                    mapped_features[current_path] = value
        elif isinstance(data, list):
            for index, item in enumerate(data):
                current_path = f"{path}[{index}]"
                recursive_search(item, current_path)

    recursive_search(structured_yaml)

    feature_matches = {}

    with open(csv_file, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            feature, middle, turned, value = row[0], row[1], row[2], row[3]

            # Verificar si el feature existe en el YAML mapeado
            for yaml_path, yaml_value in mapped_features.items():
                if middle.strip() and middle in yaml_path:
                    # Si el valor es un guion, interpretarlo como lista
                    if "-" in value:
                        value_array = value.split("-")[1:]
                        feature_matches[yaml_path] = value_array
                    else:
                        feature_matches[yaml_path] = yaml_value
                        #print("FEATURE MATCHES")
                        #print(feature_matches)

    return feature_matches


def build_output_json(yaml_data_list, csv_file):
    """
    Construye el JSON de salida manteniendo la jerarquía YAML y los mapeos de features.
    """
    output_data = []

    for filename, structured_yaml in yaml_data_list:
        features_found = search_features_in_csv(structured_yaml, csv_file)

        # Reinsertar features en la estructura YAML
        def insert_features(data, path_prefix=""):
            if isinstance(data, dict):
                for key, value in data.items():
                    full_path = f"{path_prefix}_{key}" if path_prefix else key
                    if full_path in features_found:
                        if isinstance(value, list):
                            data[key] = [{"MappedFeature": v} for v in features_found[full_path]]
                        else:
                            data[key] = {"MappedFeature": features_found[full_path]}
                    elif isinstance(value, (dict, list)):
                        insert_features(value, full_path)
            elif isinstance(data, list):
                for item in data:
                    insert_features(item, path_prefix)

        insert_features(structured_yaml)

        yaml_entry = {
            "filename": filename,
            "config": structured_yaml
        }
        output_data.append(yaml_entry)

    return output_data


# Ruta de la carpeta donde están los archivos YAML
yaml_directory = './generateConfigs/files_yamls'

# Leer YAMLs y extraer propiedades
yaml_data_list = read_yaml_files_from_directory(yaml_directory)

# Ruta del archivo CSV
csv_file_path = './generateConfigs/kubernetes_mapping_features_part01.csv'

# Construir salida JSON
output_data = build_output_json(yaml_data_list, csv_file_path)

# Guardar la salida en JSON
output_json_path = './generateConfigs/output_features02.json'
with open(output_json_path, 'w', encoding='utf-8') as json_file:
    json.dump(output_data, json_file, ensure_ascii=False, indent=4)

print(f"Resultados guardados en: {output_json_path}")