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
                        
                        if value == "-":
                            feature_map[hierarchical_prop] =  {"feature_type": "array", "feature": feature}
                            #print(f"Array Detectado CSV {feature}")
                            #print("El feature map es:")
                            #print(feature_map[hierarchical_prop])
                        else:
                            ## Ejecucion normal
                            feature_map[hierarchical_prop] = feature
                    
                    aux_hierchical_maps = feature.rsplit("_", 1)[0] ### Se omite la última parte del feature para hacer posible la comparacion con el hierarchical_prop y filtrar los relacionados
                    #print(aux_hierchical_maps)
                    ## Condiciones donde se busca capturar los features de mapas nombrados en los YAMLS
                    if middle.strip() and turned == "KeyMap" and feature not in feature_map and aux_hierchical_maps.endswith(hierarchical_prop): ## and aux_hierchical_maps.endswith(middle)
                        ##aux_hierchical_maps = feature.rsplit("_", 1)[0]
                        aux_hierchical_maps_key = f"{hierarchical_prop}_KeyMap" ## Se crea manualmente el _KeyMap porque no viene en los YAMLS
                        #print(aux_hierchical_maps)
                        #print(turned)
                        #print (f"EL PROP PARA MAPS: {aux_hierchical_maps_key}")
                        #print (f"EL AUX HIERCHICAL PARA MAPS: {aux_hierchical_maps}")
                        feature_map[aux_hierchical_maps_key] = feature
                    elif middle.strip() and turned == "ValueMap" and feature not in feature_map and aux_hierchical_maps.endswith(hierarchical_prop): ## and aux_hierchical_maps.endswith(middle)
                        aux_hierchical_maps_value = f"{hierarchical_prop}_ValueMap" ## Se crea manualmente el _ValueMap porque no viene en los YAMLS
                        #print(f"El aux VALUE ES: {aux_hierchical_maps_value}")
                        feature_map[aux_hierchical_maps_value] = feature
                    elif middle.strip() and turned == "StringValue" and feature not in feature_map and aux_hierchical_maps.endswith(hierarchical_prop): ## Nueva adición para añadir los StringValue que aparezcan en la lista de features
                        aux_hierchical_arr_string = f"{hierarchical_prop}_StringValue" ## Se crea manualmente el _StringValue porque es un feature personalizado del modelo. Se usa para referirse a los arrays de strings
                        #print(f"El aux VALUE ES: {aux_hierchical_maps_value}")
                        print(f"Array de Strings: {feature} {hierarchical_prop} {aux_hierchical_arr_string}")
                        feature_map[aux_hierchical_arr_string] = feature
                    elif middle.strip() and turned == "asString" and feature not in feature_map and aux_hierchical_maps.endswith(hierarchical_prop): ## Nueva adición para añadir los StringValue que aparezcan en la lista de features
                        aux_hierchical_as_string = f"{hierarchical_prop}_asString" ## Se crea manualmente el _StringValue porque es un feature personalizado del modelo. Se usa para referirse a los arrays de strings
                        #print(f"El aux VALUE ES: {aux_hierchical_maps_value}")
                        print(f"Seleccion de tipo String: {feature} {hierarchical_prop} {aux_hierchical_as_string}")
                        feature_map[aux_hierchical_as_string] = feature
                    elif middle.strip() and turned == "asNumber" and feature not in feature_map and aux_hierchical_maps.endswith(hierarchical_prop): ## Nueva adición para añadir los StringValue que aparezcan en la lista de features
                        aux_hierchical_as_number = f"{hierarchical_prop}_asNumber" ## Se crea manualmente el _StringValue porque es un feature personalizado del modelo. Se usa para referirse a los arrays de strings
                        #print(f"El aux VALUE ES: {aux_hierchical_maps_value}")
                        print(f"Seleccion de tipo Number: {feature} {hierarchical_prop} {aux_hierchical_as_number}")
                        feature_map[aux_hierchical_as_number] = feature
                        ## Falta opcion asInteger

                    """if turned == "KeyMap" and aux_hierchical_maps.endswith(middle) and feature not in feature_map: ##  or turned == "ValueMap"
                        if turned == "KeyMap":
                            aux_hierarchical_prop_key = "{hierarchical_prop}_KeyMap"
                            feature_map[aux_hierarchical_prop_key] = feature
                        if turned == "ValueMap":
                            print(f"NO ME EJECUTO?")

                            aux_hierarchical_prop_value = "{hierarchical_prop}_ValueMap"
                            feature_map[aux_hierarchical_prop_value] = feature
                        print(f"FEATURES QUE SON MAPAS: {feature}")"""
                    
                    for key, yaml_value in key_value_pairs: 
                        if value and str(yaml_value) == value and feature not in feature_map: ## evitar agregar el mismo feature
                            aux_hierchical_value_added = f"{key}_{yaml_value}" ## Se agrega el yaml_value manualmente ya que en la herencia no se adjunta el valor de las propiedades yaml
                            #print(aux_hierchical_value_added)
                            if feature.endswith(aux_hierchical_value_added): ## Quizas se pueda definir mejor la coincidencia pero asi se asegura que el value coincida con el value del yaml
                                #print(f"VALORES DEL VALUE: {value} VALOR DEL YAML: {yaml_value}")
                                #print(f"DEBUG:? {aux_hierchical_value_added}   {feature}   {key}")
                                feature_map[aux_hierchical_value_added] = feature ## Se agrega el feature que tambien coincide el yaml
                                continue
                #if value == "-":
                    #print("Array detectado")
                    #feature_map[feature] = {"feature_type": "array"}
                    # Generar prefijo con apiVersion y kind si están presentes
                    """version_kind_prefix = f"{root_info.get('apiVersion', 'unknown')}_{root_info.get('kind', 'unknown')}_"
                    feature_key = f"{version_kind_prefix}{key}" if key not in feature_map else key
                    feature_map[feature_key] = {"type": "array", "feature": feature}
                    print("El feature map es:")
                    print(feature_map)
                    """

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

def extract_key_value_mappings(value, value_features, feature_map): ## Posible encapsulamiento de las funciones para mejorar la legibilidad
    key_values = []
    aux_feature_maps = value_features.rsplit("_", 1)[0]
    aux_feature_value = f"{aux_feature_maps}_ValueMap"
    for map_key, map_value in value.items():
        key_values.append({
            value_features: map_key,
            aux_feature_value: map_value
        })
    return key_values

def apply_feature_mapping(yaml_data, feature_map, hierarchical_props, auxFeaturesAddedList):
    """
    Aplica el mapeo de features al YAML reemplazando las claves por los nombres de features.
    """
    #print(f"El mapa entero es: {feature_map}")
    if isinstance(yaml_data, dict) and feature_map is not None:
        #print(feature_map.items())
        new_data = {}
        feature_nested = {}
        mapped_key = {}
        feature_map_key_value = {}
        for key, value in yaml_data.items():
            aux_nested = False ## boolean para determinar si una propiedad tiene un feature value
            aux_array = False ## boolean para determinar si una propiedad contiene un array o es un array de features
            aux_maps = False ## marca para determinar los mapas
            aux_str_values = False
            for key_features, value_features in feature_map.items():
                # Verificar mapeo directo
                #print("NO SE EJECUTA?")
                #last_key_feature = key_features.rsplit("_", 1)[0]
                #print(key_features)
                #print(last_value_feature)
                """if value_features.endswith(key) and value_features not in auxFeaturesAddedList:
                    auxFeaturesAddedList.add(value_features)
                    key = value_features
                    continue"""
                # Lógica normal para valores de tipo string, se cambia el valor del key directamente
                if isinstance(value_features, str) and value_features.endswith(key) and value_features not in auxFeaturesAddedList: ## key_features.endswith(key) # Salida similar
                    auxFeaturesAddedList.add(value_features)
                    key = value_features
                    continue
                # Comprobar arrays u otros features asignados, tratan valores de tipo dict por el tipo de estructura que tienen. Modificacion con el 'feature_type': 'array' 
                elif key_features.endswith(key) and isinstance(value_features, dict) and value_features.get("feature_type") == "array":
                    #print(f"Array detectado para key '{key}': {value_features['feature']}")
                    #print(value_features.items())
                    if value_features["feature"] not in auxFeaturesAddedList:
                        #print(f"{key}   {value}     {yaml_data}")
                        auxFeaturesAddedList.add(value_features["feature"])
                        ##feature_arr = [value_features["feature"]]
                        #new_data[value_features["feature"]] = [] ## se queda vacio
                        key = value_features["feature"]
                        aux_array = True
                        continue
                ### Nueva adicion: StringValue para representar los arrays de Strings. En features se localizan por el _StringValue o _StringValueAdditional
                ## Seguir un tratamiento similar que con los mapas. Parte final del feature
                elif isinstance(value, list) and key_features.endswith("StringValue") and isinstance(value_features, str) and "StringValue" == value_features.split("_")[-1] and value_features not in auxFeaturesAddedList: ## Prueba add StringValue
                    aux_key_last_before_map = value_features.split("_")[-2]
                    str_values = []
                    print(f"SE EJECUTA IF NUEVO {key}   {value_features}")
                    print(value)
                    if key.endswith(aux_key_last_before_map) and key_features.endswith(f"{aux_key_last_before_map}_StringValue"):### and value.get("key") in value_features  ## key coge los valores del feature mapeado
                        print(f"SE EJECUTA DE NUEVO IF NUEVO {value_features}")
                        for str_value in value:
                            print(value)
                            print(f"{str_value}   {key} {value_features}   {aux_key_last_before_map}")
                            #aux_feature_value = f"{aux_feature_str_value}_ValueMap"
                                #if value_features.endswith(key_features):
                            str_values.append({ ## , aux_feature_value: map_value
                                value_features: str_value
                            })
                            auxFeaturesAddedList.add(value_features)
                        #print(f"EL KEY VALUES ES {key_values}")
                        feature_str_value = str_values
                        aux_str_values = True
                elif isinstance(value, dict) and key_features.endswith("KeyMap") and isinstance(value_features, str) and "KeyMap" == value_features.split("_")[-1] and value_features not in auxFeaturesAddedList: ## or "ValueMap" == last_value_feature)
                    #print(f"NO HAY NADA¿ {last_value_feature}") ## value.get("key")
                    #print(f"{key}     {yaml_data}") ## last_key_feature.endswith(key) and 
                    aux_key_last_before_map = value_features.split("_")[-2]
                    #print(f"ELEMENTOS QUE DEBERIAN DE COIONCIDIR: {value_features}  {aux_key_last_before_map}")
                    #print(f"SE EJECUTA IF RARO {key}    {value}     {key_features}     {value_features}")
                    key_values = []
                    #print(value.get("key"))
                    if key.endswith(aux_key_last_before_map) and key_features.endswith(f"{aux_key_last_before_map}_KeyMap"):### and value.get("key") in value_features  ## key coge los valores del feature mapeado
                        #print(f"SE EJECUTA DE NUEVO IF RARO {value_features}")

                        for map_key, map_value in value.items():
                            print(f"{key}   {value} {map_key}   {map_value}")
                            aux_feature_maps = value_features.rsplit("_", 1)[0] ## se obtiene el feature quitando la ultima parte para añadir manualmente el ValueMap
                            aux_feature_value = f"{aux_feature_maps}_ValueMap"
                                #if value_features.endswith(key_features):
                            #print(f"{map_key}   {map_value} {value_features}")
                            #print(f"COINCIDENCIA CON EL FEATURE MAP")
                            key_values.append({
                                value_features: map_key,
                                aux_feature_value: map_value
                            })
                            auxFeaturesAddedList.add(value_features)
                            auxFeaturesAddedList.add(aux_feature_value)

                        #print(f"EL KEY VALUES ES {key_values}")
                        feature_map_key_value = key_values
                        aux_maps = True

                # Representación de valores seleccionados, se comprueba si algun valor del yaml coincide con la ultima parte de los features en la lista.
                elif isinstance(value_features, str) and value == value_features.split("_")[-1] and value_features not in auxFeaturesAddedList:
                        if value_features.endswith(key_features):
                            feature_nested[value_features] = value
                            aux_nested = True
                            auxFeaturesAddedList.add(value_features)

            mapped_key = feature_map.get(key, key)
            if aux_nested:
                new_data[mapped_key] = feature_nested
            elif aux_str_values: ## prueba add arr of strings
                print(f"prueba add arr of strings")
                new_data[mapped_key] = feature_str_value
            elif aux_array or isinstance(value, list): ##  or isinstance(value, list)
                if aux_maps:
                    print("NO SE EJCUTA?")
                    print(feature_map_key_value)
                    new_data[mapped_key] = feature_map_key_value
                else:
                    new_data[mapped_key] = [apply_feature_mapping(item, feature_map, hierarchical_props, auxFeaturesAddedList) if isinstance(item, (dict, list)) else item for item in value]
                    #print(f" Comprobar salida arr aux: {mapped_key} {new_data}")
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
