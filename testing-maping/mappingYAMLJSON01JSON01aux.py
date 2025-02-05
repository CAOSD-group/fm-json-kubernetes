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

                        simple_props, hierarchical_props, key_value_pairs, root_info = extract_yaml_properties(yaml_data)
                        yaml_data_list.append((filename, yaml_data, simple_props, hierarchical_props, key_value_pairs, root_info))

                except yaml.YAMLError as e:
                    error_log.write(f"Error de YAML en archivo {file_path}: {str(e)}\n")
                except FileNotFoundError:
                    error_log.write(f"Archivo no encontrado: {file_path}\n")
                except Exception as e:
                    error_log.write(f"Error desconocido en archivo {file_path}: {str(e)}\n")
        #print(yaml_data_list)
    return yaml_data_list


def search_features_in_csv(hierarchical_props, key_value_pairs, csv_file):
    """
    Busca coincidencias en el CSV utilizando las listas separadas:
    - Comparación de hierarchical_props con la columna 'Midle'
    - Comparación de key_value_pairs con la columna 'Value'
    """
    feature_map = {}
    #print(feature_map)
    with open(csv_file, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            feature, middle, turned, value = row[0], row[1], row[2], row[3]

            # Buscar coincidencias exactas en la columna 'Midle'
            """for hierarchical_prop in hierarchical_props:
                if middle.strip() and middle in hierarchical_prop:
                    feature_map[hierarchical_prop] = feature
                    print(feature)"""

            if f"_{root_info.get('apiVersion', 'unknown')}_{root_info.get('kind', 'unknown')}_" in feature:
                for hierarchical_prop in hierarchical_props:
                    if middle.strip() and hierarchical_prop.endswith(middle):
                        feature_map[hierarchical_prop] = feature ##donde se agrega el key? si solo esta el feature
                        #found_features.append(feature)
                    
                    for key, yaml_value in key_value_pairs: 
                        if value and str(yaml_value) == value and feature not in feature_map: ## evitar agregar el mismo feature
                            aux_hierchical_value_added = f"{key}_{yaml_value}" ## Se agrega el yaml_value manualmente ya que en la herencia no se adjunta el valor de las propiedades yaml
                            #print(aux_hierchical_value_added)
                            if feature.endswith(aux_hierchical_value_added): ## Quizas se pueda definir mejor la coincidencia pero asi se asegura que el value coincida con el value del yaml
                                #print(f"VALORES DEL VALUE: {value} VALOR DEL YAML: {yaml_value}")
                                #print(f"DEBUG:? {aux_hierchical_value_added}   {feature}   {key}")
                                feature_map[aux_hierchical_value_added] = feature ## Se agrega el feature que tambien coincide el yaml
                                continue
                if value == "-":
                    print("Array detectado")
                    #feature_map[feature] = {"feature_type": "array"}
                    # Generar prefijo con apiVersion y kind si están presentes
                    """version_kind_prefix = f"{root_info.get('apiVersion', 'unknown')}_{root_info.get('kind', 'unknown')}_"
                    feature_key = f"{version_kind_prefix}{key}" if key not in feature_map else key
                    feature_map[feature_key] = {"type": "array", "feature": feature}"""
                    print("El feature map es:")
                    print(feature_map)
                ##feature_map["arr"] = "[]"

                ## Marcar array para agregar a la estructura del yaml_data
                        #feature_map[key] = feature  
                        #and feature not in feature_map[key]
                        #if feature.endswith(aux_hierchical_value_added):
                            #print(f"Los value key pares son: {key_value_pairs}")
                            #found_features.append(feature)
                            #feature_map[key] = feature
                            #print()
                            #print(f"Feature map key {feature_map[key]}")
            # Comparar clave-valor en el YAML con el valor del CSV
            """for key, yaml_value in key_value_pairs:
                if value.strip() and str(yaml_value) == value.strip():
                    feature_map[key] = feature"""
        print(f"El mapa entero es: {feature_map}")
    return feature_map


def apply_feature_mapping(yaml_data, feature_map, hierarchical_props, auxFeaturesAddedList):
    """
    Aplica el mapeo de features al YAML reemplazando las claves por los nombres de features.
    """
    if isinstance(yaml_data, dict) and feature_map is not None:
    
        new_data = {}
        mapped_key = {}
        #print(f"INICIO MAP {feature_map.items()}")
        feature_nested = {}
        
        #aux_nested = False ## añadido dentro del primer bucle
        for key, value in yaml_data.items():
            #print(f"{key}   {value}")
            #print(feature_map.get(value))
            aux_key_value = f"{key}_{value}"
            aux_nested = False ## Se asiga a False dentro del bucle para que no se sobreasigne
            for key_features, value_features in feature_map.items(): ## O cambiamos los tipo a Type/Value_features
                #print("iTERACIONES")
                #print(f"{key}   {value_features}")
                if key_features.endswith(key) and value_features not in auxFeaturesAddedList: ## Rama para mapear las propiedades sin notaciones especiales
                    #print(f"{key}   {value_features}")
                    if value_features in auxFeaturesAddedList:
                        print(f"YA ESTOY EN LA LISTA {value_features}")
                    ## Se crea una lista auxiliar con los features ya agregados para no agregar por error un feature ya visto. Hay algunas keys que se llaman igual y se puede dar el caso
                    auxFeaturesAddedList.add(value_features)
                    key = value_features                                                                                                                             
                    continue ### Actualmente no influye
                ##Probando a agregar un sub-nivel nuevo que represente la seleccion del valor TCP como la diseñada para el modelo del feature
                elif value == value_features.split("_")[-1] and value_features not in auxFeaturesAddedList: ## and key in value_features #and value_features.endswith(key_features)
                    if value_features.endswith(key_features): ## Quizas redundante pero puede servir para una mejor comprobación
                        print(f"VALORES SEGUNDO IF {value_features}  {key_features}     {key}")
                        print(f"Soy un valor del Value: {value_features}")
                        feature_nested[value_features] = value
                        aux_nested = True
                        auxFeaturesAddedList.add(value_features)
                    else:
                        aux_nested  = False

            mapped_key = feature_map.get(key, key)
            if aux_nested: # Probando para añadir los features de valores seleccionados (añternatives)
                print("HAY ALGUNA REPRESENTACION?¿")
                print(feature_nested)
                new_data[mapped_key] = feature_nested
            else:
                new_data[mapped_key] = apply_feature_mapping(value, feature_map, hierarchical_props, auxFeaturesAddedList) if isinstance(value, (dict, list)) else value

        return new_data

    elif isinstance(yaml_data, list):
        print(f"YAML DATA ELIF {yaml_data}")
        return [apply_feature_mapping(item, feature_map, hierarchical_props, auxFeaturesAddedList) for item in yaml_data]

    return yaml_data


# Ruta de la carpeta donde están los archivos YAML
yaml_directory = './generateConfigs/files_yamls'

# Leer YAMLs y extraer propiedades
yaml_data_list = read_yaml_files_from_directory(yaml_directory)

# Ruta del archivo CSV
csv_file_path = './generateConfigs/kubernetes_mapping_features_part01.csv'

# Preparar estructura para JSON
output_data = []

for filename, yaml_data, simple_props, hierarchical_props, key_value_pairs, root_info in yaml_data_list:
    print(f"\nProcesando archivo: {filename}")
    auxFeaturesAddedList = set()
    feature_map = search_features_in_csv(hierarchical_props, key_value_pairs, csv_file_path)
    updated_config = apply_feature_mapping(yaml_data, feature_map, hierarchical_props, auxFeaturesAddedList)
    yaml_entry = {
        "filename": filename,
        "apiVersion": root_info.get("apiVersion", "N/A"),
        "kind": root_info.get("kind", "N/A"),
        "config": updated_config
    }
    output_data.append(yaml_entry)

# Guardar la salida en JSON
output_json_path = './generateConfigs/output_features02.json'

with open(output_json_path, 'w', encoding='utf-8') as json_file:
    json.dump(output_data, json_file, ensure_ascii=False, indent=4)

print(f"Resultados guardados en: {output_json_path}")
