import yaml
import csv
import os
import json
import re
from datetime import datetime, timezone, date, time

import gc
import shutil

# Ruta base donde están los buckets clasificados por tamaño
yaml_base_directory = '../../resources/yamls_agrupation' ## Add zip of files?
csv_kinds_versions = '../../resources/mapping_csv/generateConfigs/kinds_versions_detected.csv'
# Buckets válidos
buckets = ['tiny', 'small', 'medium', 'large', 'huge']


def load_kinds_versions(path_csv):
    """
    Obtiene las versiones y kinds admitidas en base al modelo de kubernetes. Se usa para filtrar que archivos mapear/validar
    """
    kinds_versions = set()
    with open(path_csv, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            version = row['Version'].strip() ## group = row['Group'].strip()
            kind = row['Kind'].strip()
            kinds_versions.add((version, kind))
    return kinds_versions


def extract_yaml_properties(data, parent_key='', root_info=None, first_add=True):
    """
    Extrae las propiedades del YAML en tres listas:
    - Propiedades simples (para comparación con Turned)
    - Propiedades jerárquicas (para comparación con Midle)
    - Pares clave-valor para guardar las claves-valores originales y realizar una comparación mas precisa
    """
    simple_props = []
    hierarchical_props = []
    key_value_pairs = []
    
    if root_info is None:
        root_info = {}

    if isinstance(data, dict):
        for key, value in data.items():

            if key is None and value is None: ## Omitir el tipo de casos con declaraciones "name: [ ? ]"
                raise ValueError(f"Clave o valor inválida detectada: {key}: {value}")
            
            new_key = f"{parent_key}_{key}" if parent_key else key
            # Guardar valores clave (apiVersion y kind) para determinar el contexto
            if key in ['apiVersion', 'kind'] and first_add: ## Solo se modifica si es la primera llamada
                if key not in root_info:  # No sobrescribir si ya se definió en el nivel superior   
                    if '/' in value and not '.' in value:
                        value = value.replace('/', '_')
                    elif '.' in value and '/' in value: ## Caso en el que el valor de la version contenga puntos '.' se usa solo la segunda parte separada por la barra lateral '/' que donota la versión dentro de los esquemas
                        aux_value = value.split('/') ## Como se representa en los esquemas api_rbac_v1_, caso en los yaml: rbac.authorization.k8s.io/v1
                        value = aux_value[1]
                    elif '.' in value and not '/' in value:
                        ## No hay una definición de la versión y solo se agrega un grupo o una versión no válida
                        raise ValueError(f"apiVersion sin versión explícita: {value}")

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
    elif 'apiVersion' not in root_info or 'kind' not in root_info and first_add:
        print(f"[WARNING] No se pudo determinar apiVersion/kind en {root_info}")
        return None, None, None, root_info ## Tratar de determinar archivos sin apiVersion kind en el root. También detecta los que no declaran las propiedades al comienzo.
    return simple_props, hierarchical_props, key_value_pairs, root_info


def process_yaml_file(file_path):
    """Procesa un archivo YAML y extrae información relevante."""
    #error_log_path = './error_log_mapping_tester.txt'
    error_log_path = './error_log_mapping_tester_03.txt'
    dict_allowed_kinds_versions = load_kinds_versions(csv_kinds_versions) ## Se cargan los kinds y versions permitidos

    try:
        with open(file_path, 'r', encoding='utf-8') as yaml_file:
            yaml_documents = list(yaml.safe_load_all(yaml_file))
        if not yaml_documents:
            return None  # Archivo vacío o inválido

        for index, yaml_data in enumerate(yaml_documents):
            if yaml_data is None:
                continue
            try:
                root_info = {}  # Reiniciar root_info para cada documento
                simple_props, hierarchical_props, key_value_pairs, root_info = extract_yaml_properties(yaml_data)

                ##if None in (simple_props, hierarchical_props, key_value_pairs):
                ##    continue  # Por si el warning anterior dejó algo inválido
                
                ## Se comprueba si los ficheros a mapear tienen una version y kinds validos sobre el contexto del modelo
                apiVersion =  root_info.get('apiVersion')
                kind = root_info.get('kind')

                if "_" in apiVersion:
                    split_version = apiVersion.split("_")[1]
                    apiVersion = split_version
                if (apiVersion, kind) not in dict_allowed_kinds_versions:
                    print(f"Archivo no valido por version y kind")
                    # Guardar una copia del YAML en formato JSON
                    dest_json_dir = os.path.join(yaml_base_directory, 'invalidKindsVersions01')
                    os.makedirs(dest_json_dir, exist_ok=True)
                    json_name = os.path.basename(file_path).replace('.yaml', '.json')
                    json_path = os.path.join(dest_json_dir, json_name)
                    with open(json_path, 'w', encoding='utf-8') as f_json:
                        json.dump(yaml_data, f_json, indent=2)

                    # Mover el YAML original a otra carpeta
                    dest_yaml_dir = os.path.join(yaml_base_directory, 'invalidKindsVersionsFormatYaml01')
                    os.makedirs(dest_yaml_dir, exist_ok=True)
                    dest_path_file = os.path.join(dest_yaml_dir, os.path.basename(file_path))
                    shutil.move(file_path, dest_path_file)

                    # Log
                    with open(error_log_path, 'a', encoding='utf-8') as error_log:
                        error_log.write(f"[KIND NO VÁLIDO] Falta apiVersion/kind raíz en {file_path} (doc {index})\n")
                    break  # Ya se movió el archivo, no se procesan mas documentos. En principio con continue o break funcionaria igual al haber en su mayoría un unico archivo
                    
                yield (file_path, index, yaml_data, simple_props, hierarchical_props, key_value_pairs, root_info)
                    # yaml_data_list.append((filename, index, yaml_data, simple_props, hierarchical_props, key_value_pairs, root_info))

            except ValueError as ve:
                with open(error_log_path, 'a', encoding='utf-8') as error_log:
                    error_log.write(f"[OMITIDO] {ve} en {file_path}\n")
                # Copia de archivo con error de valor inválido o de apiVersion sin versión
                error_mapping_dir = os.path.join(yaml_base_directory, 'erroresMapeo')
                os.makedirs(error_mapping_dir, exist_ok=True)
                dest_path = os.path.join(error_mapping_dir, os.path.basename(file_path))
                shutil.copy(file_path, dest_path)    
                continue
    except yaml.YAMLError as e:
        with open(error_log_path, 'a', encoding='utf-8') as error_log:
            error_log.write(f"[YAML ERROR] en {file_path}: {str(e)}\n")
        # Copia de archivo con error de YAML
        error_yaml_dir = os.path.join(yaml_base_directory, 'erroresYAML')
        os.makedirs(error_yaml_dir, exist_ok=True)
        dest_path = os.path.join(error_yaml_dir, os.path.basename(file_path))
        shutil.copy(file_path, dest_path)

    except FileNotFoundError:
        with open(error_log_path, 'a', encoding='utf-8') as error_log:
            error_log.write(f"[NOT FOUND] Archivo no encontrado: {file_path}\n")
    except Exception as e:
        with open(error_log_path, 'a', encoding='utf-8') as error_log:
            error_log.write(f"[GENERAL ERROR] en archivo {file_path}: {str(e)}\n")


def read_yaml_files_from_directory(directory_path):
    """Lee archivos YAML en un directorio y los procesa en tiempo real."""

    # Comprobar si el directorio está vacío
    if not any(fname.endswith((".yaml", ".yml")) for fname in os.listdir(directory_path)):
        print(f"[AVISO] Carpeta vacía o sin YAMLs: {directory_path}")
        return  # Se salta esta carpeta y continúa con la siguiente
    
    for filename in os.listdir(directory_path):
        if filename.endswith((".yaml", ".yml")):
            file_path = os.path.join(directory_path, filename)
            yield from process_yaml_file(file_path)  # Generador en lugar de lista.. ## Comprobar file_path: formato raro

            gc.collect()  # Liberar memoria periódicamente

# Lista generadora que procesa YAMLs de todas las carpetas válidas
def iterate_all_buckets(base_dir, bucket_list):
    for bucket in bucket_list:
        bucket_path = os.path.normpath(os.path.join(base_dir, bucket))
        if os.path.isdir(bucket_path):
            yield from read_yaml_files_from_directory(bucket_path)

def convert_all_datetimes(obj):
    if isinstance(obj, dict):
        return {k: convert_all_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_all_datetimes(i) for i in obj]
    elif isinstance(obj, datetime):
        return obj.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    elif isinstance(obj, (date, time)):
        return obj.isoformat() # HH:MM:SS
    return obj

def contains_datetime(obj):
    if isinstance(obj, dict):
        return any(contains_datetime(v) for v in obj.values())
    elif isinstance(obj, list):
        return any(contains_datetime(i) for i in obj)
    return isinstance(obj, (datetime, date, time))


def load_features_csv(csv_path):
    feature_dict = {}
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            #print(row['Midle'], row['Turned'])
            feature_name = row['Feature']
            #feature_dict[row['Feature,Midle,Turned,Value']] = row['some_other_column']  # adapta a tu caso
            feature_dict[feature_name] = {
                "middle": row['Midle'],
                "turned": row['Turned'],
                "value": row['Value']
            }
    return feature_dict

def search_features_in_csv(hierarchical_props, key_value_pairs, csv_dict):
    """
    Busca coincidencias en el CSV utilizando las listas separadas:
    - Comparación de hierarchical_props con la columna 'Midle'
    - Comparación de key_value_pairs con la columna 'Value'
    """
    feature_map = {}
    #print(feature_map)

    for feature, meta in csv_dict.items():
        # Suponiendo que `meta` contiene middle, turned, value separados
        middle, turned, value = meta["middle"], meta["turned"], meta["value"]
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
                    ##print(f"Array de Strings: {feature} {hierarchical_prop} {aux_hierchical_arr_string} {key}   {value}")
                    feature_map[aux_hierchical_arr_string] = feature
                elif middle.strip() and turned == "IntegerValue" and feature not in feature_map and aux_hierchical_maps.endswith(hierarchical_prop): ## Nueva adición para añadir los StringValue que aparezcan en la lista de features
                    aux_hierchical_arr_integer = f"{hierarchical_prop}_IntegerValue" ## Se crea manualmente el _StringValue porque es un feature personalizado del modelo. Se usa para referirse a los arrays de strings
                    #print(f"El aux VALUE ES: {aux_hierchical_maps_value}")
                    #print(f"Array de Integers: {feature} {hierarchical_prop} {aux_hierchical_arr_integer} {key}   {value}")
                    feature_map[aux_hierchical_arr_integer] = feature
                ## StringValueAdditional: Array de Strings que se añade de manera diferente en el script principal del modelo.
                elif middle.strip() and turned == "StringValueAdditional" and feature not in feature_map and aux_hierchical_maps.endswith(hierarchical_prop): ## Nueva adición para añadir los StringValue que aparezcan en la lista de features
                    aux_hierchical_arr_string_additional = f"{hierarchical_prop}_StringValueAdditional" ## Se crea manualmente el _StringValue porque es un feature personalizado del modelo. Se usa para referirse a los arrays de strings
                    #print(f"El aux VALUE ES: {aux_hierchical_maps_value}")
                    ##print(f"Array de Strings Additional: {feature} {hierarchical_prop} {aux_hierchical_arr_string_additional}")
                    feature_map[aux_hierchical_arr_string_additional] = feature
                ## Para agregar la incorporación de los features de tipo de seleccion de dato, se agregan de manera "manual". Cuando haya coincidencia del feature con Turned igual a asString, asNumber o asInteger se agregan si la 
                ## herencia coincide con el feature omitido. Se agrega por la alternatividad del modelo y en la salida se selecciona el que aparece en el JSON. Al no saber el valor que se le agrega a la propiedad no se puede definir
                ## antes el tipo de dato.
                elif middle.strip() and turned == "asString" and feature not in feature_map and aux_hierchical_maps.endswith(hierarchical_prop): ## Nueva adición para añadir los StringValue que aparezcan en la lista de features
                    aux_hierchical_as_string = f"{hierarchical_prop}_asString" ## Se crea manualmente el _StringValue porque es un feature personalizado del modelo. Se usa para referirse a los arrays de strings
                    #print(f"El aux VALUE ES: {aux_hierchical_maps_value}")
                    #print(f"Seleccion de tipo String: {feature} {hierarchical_prop} {aux_hierchical_as_string}")
                    feature_map[aux_hierchical_as_string] = feature
                elif middle.strip() and turned == "asNumber" and feature not in feature_map and aux_hierchical_maps.endswith(hierarchical_prop): ## Nueva adición para añadir los StringValue que aparezcan en la lista de features
                    aux_hierchical_as_number = f"{hierarchical_prop}_asNumber" ## Se crea manualmente el _StringValue porque es un feature personalizado del modelo. Se usa para referirse a los arrays de strings
                    #print(f"Seleccion de tipo Number: {feature} {hierarchical_prop} {aux_hierchical_as_number}")
                    feature_map[aux_hierchical_as_number] = feature
                    ## Falta opcion asInteger
                elif middle.strip() and turned == "asInteger" and feature not in feature_map and aux_hierchical_maps.endswith(hierarchical_prop): ## Nueva adición para añadir los StringValue que aparezcan en la lista de features
                    aux_hierchical_as_integer = f"{hierarchical_prop}_asInteger" ## Se crea manualmente el _StringValue porque es un feature personalizado del modelo. Se usa para referirse a los arrays de strings
                    #print(f"Seleccion de tipo Integer: {feature} {hierarchical_prop} {aux_hierchical_as_integer}")
                    feature_map[aux_hierchical_as_integer] = feature
                elif middle.strip() and turned == "isNull" and feature not in feature_map and aux_hierchical_maps.endswith(hierarchical_prop): ## Nueva adición para añadir los StringValue que aparezcan en la lista de features
                    aux_hierchical_is_null = f"{hierarchical_prop}_isNull" ## Se crea manualmente el _isNull porque es un feature personalizado del modelo. Se usa para referirse a los features con valor null en las propiedades. Se agrega para poder referenciar dicho no valor...
                    #print(f"Seleccion de tipo Null: {feature} {hierarchical_prop} {aux_hierchical_is_null}")
                    feature_map[aux_hierchical_is_null] = feature
                elif middle.strip() and turned == "isEmpty" and feature not in feature_map and aux_hierchical_maps.endswith(hierarchical_prop): ## Nueva adición para añadir los StringValue que aparezcan en la lista de features
                    aux_hierchical_is_empty = f"{hierarchical_prop}_isEmpty" ## Se crea manualmente el _isEmpty porque es un feature personalizado del modelo. Se usa para referirse a los features con valor empty en las propiedades. Se agrega para poder referenciar dicho no valor...
                    #print(f"Seleccion de tipo Empty: {feature} {hierarchical_prop} {aux_hierchical_is_empty}")
                    feature_map[aux_hierchical_is_empty] = feature

                elif middle.strip() and turned == "isEmpty02" and feature not in feature_map and aux_hierchical_maps.endswith(hierarchical_prop): ## Nueva adición para añadir los StringValue que aparezcan en la lista de features
                    aux_hierchical_is_empty = f"{hierarchical_prop}_isEmpty02" ## Se crea manualmente el _isEmpty porque es un feature personalizado del modelo. Se usa para referirse a los features con valor empty en las propiedades. Se agrega para poder referenciar dicho no valor...
                    #print(f"Seleccion de tipo Empty02: {feature} {hierarchical_prop} {aux_hierchical_is_empty}")
                    feature_map[aux_hierchical_is_empty] = feature
                #else:
                #    print(f"Hay props que no se contemplan en el modelo?    {hierarchical_prop}")

                for key, yaml_value in key_value_pairs:
                    #if isinstance(yaml_value, str)
                    if value and str(yaml_value) == value and feature not in feature_map: ## evitar agregar el mismo feature
                        aux_hierchical_value_added = f"{key}_{yaml_value}" ## Se agrega el yaml_value manualmente ya que en la herencia no se adjunta el valor de las propiedades yaml
                        #print(aux_hierchical_value_added)
                        if feature.endswith(aux_hierchical_value_added): ## Quizas se pueda definir mejor la coincidencia pero asi se asegura que el value coincida con el value del yaml
                            #print(f"VALORES DEL VALUE: {value} VALOR DEL YAML: {yaml_value}")
                            #print(f"DEBUG:? {aux_hierchical_value_added}   {feature}   {key}")
                            feature_map[aux_hierchical_value_added] = feature ## Se agrega el feature que tambien coincide el yaml
                            continue
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

def apply_feature_mapping(yaml_data, feature_map, auxFeaturesAddedList, aux_hierchical_prop, mapped_key, aux_bool, depth_mapping = 0):
    """
    Aplica el mapeo de features al YAML reemplazando las claves por los nombres de features.
    """
    #print(f"El mapa entero es: {feature_map}")
    if isinstance(yaml_data, dict) and feature_map is not None: ## lista local para comprobar los demas agregados?
        new_data = {}
        possible_type_data = ['asString', 'asNumber', 'asInteger']
        yaml_with_error_type = False

        for key, value in yaml_data.items():
            aux_nested = False ## boolean para determinar si una propiedad tiene un feature value
            aux_array = False ## boolean para determinar si una propiedad contiene un array o es un array de features
            aux_maps = False ## marca para determinar los mapas
            aux_str_values = False
            aux_value_type = False
            aux_value_type_array = False
            aux_feat_empty = False
            aux_feat_null = False
            list_double_version = {'apps_v1', 'batch_v1', 'autoscaling_v1', 'autoscaling_v2', 'policy_v1', 'core_v1'}
            feature_nested = {} ## Estructura para agregar el value personalizado para definir la coincidencia de los valores predeterminados en el modelo
            feature_type_value = {}
            feature_map_key_value = {} ## batch.v1 ,autoscaling.v1 y autoscaling.v2, policy.v1, core.v1, core.v1.Binding
            feature_type_array = [] ## Features as...
            feature_empty = {}
            feature_null = {}

            if isinstance(value, datetime): ## Comprobacion de si alguno de los valores es de tipo Time RCF 3339
                value = value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            if isinstance(key, str) and key == 'clusterName': ## Se comprueba si alguna key coinciden con 'clusterName' para omitir directamente el campo. Prop no valida en el esquema ni doc
                #print(f"Campo no soportado por el esquema base. Omision de propiedad repetida y no soportada en la v 1.30.2, 1.32...")
                continue
            #print(f"Que valor obtengo?{hierarchical_key}")
            for key_features, value_features in feature_map.items():
               
                # Lógica normal para valores de tipo string, se cambia el valor del key directamente
                if isinstance(value_features, str) and value_features.endswith(key) and value_features not in auxFeaturesAddedList: ## key_features.endswith(key) # Salida similar

                    if key_features.count("_") == 2: # len(auxFeaturesAddedList) < 3 and
                        #print(f"QUE COINCIDENCIAS HAY:  {key}   {key_features}  {value_features} ")
                        key = value_features
                        auxFeaturesAddedList.add(value_features)
                        aux_hierchical_prop.append(key_features)
                            #continue
                    elif key_features.count("_") == 3 and any(version in key_features for version in list_double_version): ## batch.v1 ,autoscaling.v1 y autoscaling.v2, policy.v1, core.v1, core.v1.Binding
                        key = value_features
                        auxFeaturesAddedList.add(value_features)
                        aux_hierchical_prop.append(key_features)
                    elif key_features.count("_") == 3:
                            aux_feature_before_insertion = value_features.rsplit("_", 1)[0]                    
                            if aux_feature_before_insertion in auxFeaturesAddedList:
                                key = value_features
                                #print(f"Valor finalmente insertado en la lista: {key_features}  {value_features}")
                                #print(f"Lista que se inserta en el if: {auxFeaturesAddedList}")
                                auxFeaturesAddedList.add(value_features)                            
                                key = value_features
                                aux_hierchical_prop.append(key_features)
                    else:
                        if any(feature.endswith(key) for feature in auxFeaturesAddedList): ## and aux_feature_before_map not in auxFeaturesAddedList
                            #print(f"Hay mas de un elemento que ya tiene la key")
                            aux_feature_before_insertion = value_features.rsplit("_", 1)[0]
                            feature_aux_depth = re.search(r"[A-Z].*", value_features) ## Regex para capturar el grupo de la primera coincidencia con una letra mayuscula: el kind siempre tiene la primera mayus
                            midle_depth = feature_aux_depth.group(0) ## Es la profundidad del feature más 'real', ya que solo se basa en las propiedades a partir del kind que se han encadenado 

                            if aux_bool and isinstance(mapped_key, str) and mapped_key and depth_mapping == midle_depth.count('_'): ## mapped_key es el padre del arr
                                mapped_key_before = mapped_key.rsplit("_", 1)[0]
                                if aux_bool and mapped_key.count("_") > 2 and mapped_key.count("_") < value_features.count("_") and mapped_key == aux_feature_before_insertion:
                                    key = value_features
                                    auxFeaturesAddedList.add(value_features)
                                    aux_hierchical_prop.append(key_features)
                                elif aux_bool and aux_feature_before_insertion == mapped_key_before: ## nuevo insertado con el depth
                                    key = value_features
                                    auxFeaturesAddedList.add(value_features)
                                    aux_hierchical_prop.append(key_features)
                                else:
                                    continue

                            if aux_feature_before_insertion in auxFeaturesAddedList and not aux_bool: ##aux_feature_before_insertion in auxFeaturesAddedList: ## key_features not in aux_hierchical_prop and 
                                if depth_mapping == midle_depth.count('_'): ## mapped_key.count("_") == value_features.count("_"): ## revisar esto
                                    if mapped_key.rsplit("_", 1)[0] == aux_feature_before_insertion:
                                        key = value_features
                                        auxFeaturesAddedList.add(value_features)
                                        aux_hierchical_prop.append(key_features)
                                elif mapped_key.count("_") > value_features.count("_"):
                                    #print(f"Estructuras diferentes  {mapped_key}    {value_features}")
                                    continue
                            else:
                                continue
                        aux_feature_before_insertion = value_features.rsplit("_", 1)[0]
                        feature_aux_depth = re.search(r"[A-Z].*", value_features) ## Regex para capturar el grupo de la primera coincidencia con una letra mayuscula: el kind siempre tiene la primera mayus
                        midle_depth = feature_aux_depth.group(0)

                        if isinstance(mapped_key, str) and midle_depth.count("_") == depth_mapping: ##  == mapped_key.rsplit("_", 1):
                            aux_mapped_before = mapped_key.rsplit("_", 1)[0]
                            if mapped_key.count("_") > 2 and mapped_key.count("_") < value_features.count("_"): ### CAMBIAR EL CASO YA QUE ESTE NO CAPTURA EL QUE BUSCAMOS
                                feature_mapped_key_depth = re.search(r"[A-Z].*", mapped_key) ## Regex para capturar el grupo de la primera coincidencia con una letra mayuscula: el kind siempre tiene la primera mayus
                                mapped_depth = feature_mapped_key_depth.group(0)
                                if aux_feature_before_insertion == mapped_key: ## mapped_depth.count("_") < midle_depth.count("_"): ##aux_mapped_before in value_features
                                    auxFeaturesAddedList.add(value_features)                          
                                    key = value_features
                                    aux_hierchical_prop.append(key_features)
                                else:
                                    continue
                            elif aux_mapped_before in value_features:
                                auxFeaturesAddedList.add(value_features)                          
                                key = value_features
                                aux_hierchical_prop.append(key_features)
                            else:
                                pass
                        else:
                            continue
                # Comprobar arrays u otros features asignados, tratan valores de tipo dict por el tipo de estructura que tienen. Modificacion con el 'feature_type': 'array' 
                elif key_features.endswith(key) and isinstance(value_features, dict) and value_features.get("feature_type") == "array": ### Comprobando
                    aux_feature_before_insertion = value_features["feature"].rsplit("_", 1)[0]
                    feature_aux_depth = re.search(r"[A-Z].*", value_features["feature"]) ## Regex para capturar el grupo de la primera coincidencia con una letra mayuscula: el kind siempre tiene la primera mayus
                    midle_depth = feature_aux_depth.group(0)
                    mapped_key_before = mapped_key.rsplit("_", 1)[0]

                    if value_features["feature"] not in auxFeaturesAddedList and midle_depth.count("_") == depth_mapping and mapped_key_before in value_features ["feature"]:
                        if mapped_key.count("_") > 2 and mapped_key.count("_") < value_features["feature"].count("_"):
                            if mapped_key == aux_feature_before_insertion:
                                auxFeaturesAddedList.add(value_features["feature"]) ### Omitido temporalmente por la omision en arrays de arrays que se genera de features ya agregados/vistos de los yaml
                                key = value_features["feature"]
                                aux_hierchical_prop.append(key_features)
                                aux_array = True
                            else:
                                continue
                        auxFeaturesAddedList.add(value_features["feature"]) ### Omitido temporalmente por la omision en arrays de arrays que se genera de features ya agregados/vistos de los yaml
                        key = value_features["feature"]
                        print(value_features["feature"])
                        aux_hierchical_prop.append(key_features)
                        print(f"Clave que se añade al mapeo y a la  lista   {key}  ")
                        aux_array = True
                elif isinstance(value, list) and key_features.endswith("StringValue") and  isinstance(value_features, str) and "StringValue" == value_features.split("_")[-1]: ## and value_features not in auxFeaturesAddedList
                    aux_key_last_before_map = value_features.split("_")[-2] ## Se obtiene la penultima prop
                    aux_feature_before_insertion = value_features.rsplit("_", 1)[0] ## se obtiene el value feature menos la ultima insersion

                    str_arr_values = []
                    if value and key == aux_feature_before_insertion and key_features.endswith(f"{aux_key_last_before_map}_StringValue"):### and value.get("key") in value_features  ## key coge los valores del feature mapeado ## key.endswith(aux_key_last_before_map)
                        for str_value in value:
                            str_arr_values.append({ ## , aux_feature_value: map_value
                                value_features: str_value
                            })
                            auxFeaturesAddedList.add(value_features) ### Omitido temporalmente por la omision en arrays de arrays que se genera de features ya agregados/vistos de los yaml
                            aux_hierchical_prop.append(key_features)
                        feature_str_value = str_arr_values
                        aux_str_values = True
                ## Seguir un tratamiento similar que con los mapas. Parte final del feature
                elif isinstance(value, list) and key_features.endswith("IntegerValue") and isinstance(value_features, str) and "IntegerValue" == value_features.split("_")[-1]: ## and value_features not in auxFeaturesAddedList
                    aux_key_last_before_map = value_features.split("_")[-2]
                    aux_feature_before_insertion = value_features.rsplit("_", 1)[0] ## se obtiene el value feature menos la ultima insersion
                    values_arr_int = []
                    if value and key == aux_feature_before_insertion and key_features.endswith(f"{aux_key_last_before_map}_IntegerValue"):### and value.get("key") in value_features  ## key coge los valores del feature mapeado
                        for int_value in value:
                            values_arr_int.append({ ## , aux_feature_value: map_value
                                value_features: int_value
                            })
                            auxFeaturesAddedList.add(value_features) ### Omitido temporalmente por la omision en arrays de arrays que se genera de features ya agregados/vistos de los yaml
                            aux_hierchical_prop.append(key_features)
                        feature_str_value = values_arr_int
                        aux_str_values = True
                elif isinstance(value, dict) and key_features.endswith("StringValueAdditional") and isinstance(value_features, str) and "StringValueAdditional" == value_features.split("_")[-1]: ## and value_features not in auxFeaturesAddedList
                    aux_key_last_before_map = value_features.split("_")[-2]
                    aux_feature_before_insertion = value_features.rsplit("_", 1)[0] ## se obtiene el value feature menos la ultima insersion
                    str_values = []
                    if value and key == aux_feature_before_insertion and key_features.endswith(f"{aux_key_last_before_map}_StringValueAdditional"):### and value.get("key") in value_features  ## key coge los valores del feature mapeado
                        for str_key, str_value in value.items():
                            str_values.append({ ## , aux_feature_value: map_value
                                value_features:f"{str_key}:{str_value}" 
                            })
                        auxFeaturesAddedList.add(value_features) ###  Agregado por comprobacion de la lista
                        aux_hierchical_prop.append(key_features)
                        feature_str_value = str_values
                        aux_str_values = True
                elif isinstance(value, dict) and key_features.endswith("KeyMap") and isinstance(value_features, str) and "KeyMap" == value_features.split("_")[-1] and value_features not in auxFeaturesAddedList: ## or "ValueMap" == last_value_feature)
                    aux_key_last_before_map = value_features.split("_")[-2]
                    aux_feature_before_map = value_features.rsplit("_", 1)[0]
                    key_values = []
                    if key.endswith(aux_key_last_before_map) and key_features.endswith(f"{aux_key_last_before_map}_KeyMap") and key == aux_feature_before_map:# Se realizan varias comprobaciones sobre si es el feature adecuado  ## key obtiene los valores del feature mapeado
                        for map_key, map_value in value.items():
                            aux_feature_maps = value_features.rsplit("_", 1)[0] ## se obtiene el feature quitando la ultima parte para añadir manualmente el ValueMap
                            aux_feature_value = f"{aux_feature_maps}_ValueMap"
                            key_values.append({
                                value_features: map_key,
                                aux_feature_value: map_value
                            })
                            auxFeaturesAddedList.add(value_features)
                            auxFeaturesAddedList.add(aux_feature_value)
                        feature_map_key_value = key_values
                        aux_maps = True

                elif any(key_features.endswith(keyword) for keyword in possible_type_data) and isinstance(value_features, str) and value_features not in auxFeaturesAddedList and value_features.endswith(key_features): ## and any(keyword == value_features.split("_")[1] for keyword in possible_type_data) ### isinstance(value, str) and # and key_features.endswith(possible_type_data)
                    aux_key_last_before_value = value_features.split("_")[-2] ## se obtiene la penultima prop
                    aux_value_last = value_features.rsplit("_", 1)[0]
                    if key == aux_value_last:
                        if isinstance(value, dict):
                            for key_item, value_item in value.items():
                                if value_features not in auxFeaturesAddedList:
                                    feature_entry = {}  # Diccionario para cada feature
                                    # Validar que el valor sea coherente con el tipo esperado del feature
                                    if isinstance(value_item, str) and value_features.endswith("asString"): ## and value_features.endswith("asString")
                                        feature_entry[value_features] = f"{key_item}:{value_item}"
                                    elif isinstance(value_item, int) and value_features.endswith("asInteger"):
                                        feature_entry[value_features] = f"{key_item}:{value_item}"
                                    elif isinstance(value_item, float) and value_features.endswith("asNumber"): ## Pueden haber casos que en la doc se definan como Number pero en el Yaml se introduzca un Int y no se detecte
                                        ## Alternativa para tener en cuenta los Integer y mapearlos a Number si se da el caso. Viceversa para el otro caso.
                                        ## Agrega a la condicion: or (isinstance(value_item, int)
                                        # value_item = float(value_item) if isinstance(value_item, int) else value_item
                                        feature_entry[value_features] = f"{key_item}:{value_item}"
                                    if feature_entry:
                                        feature_type_array.append(feature_entry)
                        
                            if len(feature_type_array) > 0:
                                aux_value_type_array = True
                                auxFeaturesAddedList.add(value_features)
                                aux_hierchical_prop.append(key_features)
                        else:
                            if isinstance(value, str) and key_features.endswith(f"{aux_key_last_before_value}_asString"):
                                feature_type_value[value_features] = value
                                aux_value_type = True
                                auxFeaturesAddedList.add(value_features)
                                aux_hierchical_prop.append(key_features)
                            elif isinstance(value, int) and key_features.endswith(f"{aux_key_last_before_value}_asInteger"):
                                feature_type_value[value_features] = value
                                aux_value_type = True
                                auxFeaturesAddedList.add(value_features)
                                aux_hierchical_prop.append(key_features)
                            elif isinstance(value, float) and key_features.endswith(f"{aux_key_last_before_value}_asNumber"):
                                feature_type_value[value_features] = value
                                aux_value_type = True 
                                auxFeaturesAddedList.add(value_features)
                                aux_hierchical_prop.append(key_features)
                # Representación de valores seleccionados, se comprueba si algun valor del yaml coincide con la ultima parte de los features en la lista.
                elif isinstance(value_features, str) and value == value_features.split("_")[-1] and value_features not in auxFeaturesAddedList:
                    aux_key_last_before_value = value_features.split("_")[-2] ## se obtiene la penultima prop
                    if value_features.endswith(key_features) and key.endswith(aux_key_last_before_value):
                        aux_nested = True
                        feature_nested[value_features] = aux_nested ## value: al final se deja el valor booleano ya que el feature agregado es boolean tambien
                        auxFeaturesAddedList.add(value_features)
                        aux_hierchical_prop.append(key_features)

                elif isinstance(value_features, str) and isinstance(value, dict) and not value and 'isEmpty02' == value_features.split("_")[-1] and value_features not in auxFeaturesAddedList:
                    aux_key_last_before_value = value_features.split("_")[-2] ## se obtiene la penultima prop
                    aux_feature_before_insertion = value_features.rsplit("_", 1)[0] ## se obtiene el value feature menos la ultima insersion
                    if key == aux_feature_before_insertion and value_features.endswith(key_features) and key_features.endswith(f"{aux_key_last_before_value}_isEmpty02"): # and key_features.endswith(f"{aux_key_last_before_map}_StringValueAdditional"):
                        aux_feat_empty = True
                        feature_empty[value_features] = aux_feat_empty ## value: al final se deja el valor booleano ya que el feature agregado es boolean tambien
                        auxFeaturesAddedList.add(value_features)
                        aux_hierchical_prop.append(key_features)
                    
                elif isinstance(value_features, str) and isinstance(value, dict) and not value and 'isEmpty' == value_features.split("_")[-1] and value_features not in auxFeaturesAddedList:
                    aux_key_last_before_value = value_features.split("_")[-2] ## se obtiene la penultima prop
                    aux_feature_before_insertion = value_features.rsplit("_", 1)[0] ## se obtiene el value feature menos la ultima insersion
                    if key == aux_feature_before_insertion and value_features.endswith(key_features) and key_features.endswith(f"{aux_key_last_before_value}_isEmpty"): # and key_features.endswith(f"{aux_key_last_before_map}_StringValueAdditional"):
                        aux_feat_empty = True
                        feature_empty[value_features] = aux_feat_empty ## value: al final se deja el valor booleano ya que el feature agregado es boolean tambien
                        auxFeaturesAddedList.add(value_features)
                        aux_hierchical_prop.append(key_features)

                elif isinstance(value_features, str) and value is None and 'isNull' == value_features.split("_")[-1] and value_features not in auxFeaturesAddedList:
                    aux_key_last_before_value = value_features.split("_")[-2] ## se obtiene la penultima prop
                    aux_feature_before_insertion = value_features.rsplit("_", 1)[0] ## se obtiene el value feature menos la ultima insersion
                    if key == aux_feature_before_insertion and key_features.endswith(f"{aux_key_last_before_value}_isNull"): # and value_features.endswith(key_features):
                        aux_feat_null = True
                        feature_null[value_features] = aux_feat_null ## value: al final se deja el valor booleano ya que el feature agregado es boolean tambien
                        auxFeaturesAddedList.add(value_features)
                        aux_hierchical_prop.append(key_features)

            mapped_key = feature_map.get(key, key)
            aux_arr_key = None
            aux_array_bool = False
            aux_bool_dict = False ## unused
            if aux_nested:
                new_data[mapped_key] = feature_nested
            elif aux_feat_empty:
                new_data[mapped_key] = feature_empty
            elif aux_feat_null:
                new_data[mapped_key] = feature_null
            elif aux_str_values:
                new_data[mapped_key] = feature_str_value
            elif aux_value_type : 
                new_data[mapped_key] = feature_type_value
            elif aux_value_type_array:
                new_data[mapped_key] = feature_type_array
            elif aux_array or isinstance(value, list):
                if aux_maps: 
                    new_data[mapped_key] = feature_map_key_value
                elif value is None:
                    new_data[mapped_key] = []
                else:
                    aux_bool = aux_array
                    try:
                        new_data[mapped_key] = [apply_feature_mapping(item, feature_map, auxFeaturesAddedList.copy(), aux_hierchical_prop, mapped_key, aux_bool, depth_mapping+1) if isinstance(item, (dict, list)) else item for item in value] ## auxFeaturesAddedList: antes de la mod
                    except TypeError as te:
                        print(f"[ERROR DE TIPO] en key {mapped_key} (valor: {value}) - {te}")
                        yaml_with_error_type = True ## To mark yamls with error for revision. Not implemented already
                        with open("./error_log_mapping01Types.log", "w", encoding="utf-8") as error_log:
                            error_log.write(f"[ERROR DE TIPO] en key: {mapped_key}, Valor inválido: {value} - {te}\n")
            else:
                aux_bool = aux_array
                try:
                    new_data[mapped_key] = apply_feature_mapping(value, feature_map, auxFeaturesAddedList, aux_hierchical_prop, mapped_key, aux_bool, depth_mapping+1) if isinstance(value, (dict, list)) else value
                except TypeError as te:
                    yaml_with_error_type = True ## To mark yamls with error for revision. Not implemented already
                    with open("./error_log_mapping01Types.log", "w", encoding="utf-8") as error_log:
                        error_log.write(f"[ERROR DE TIPO] 2º else, en key: {mapped_key}, Valor inválido: {value} - {te}\n")
        return new_data  #, yaml_with_error_type

    elif isinstance(yaml_data, list):
        print(f"YAML DATA ELIF {yaml_data}") ## caso que no suele pasar, 
        return [apply_feature_mapping(item, feature_map, auxFeaturesAddedList, aux_hierchical_prop, mapped_key, aux_bool,depth_mapping+1) for item in yaml_data]


    return yaml_data #, yaml_with_error_type


# Ruta de la carpeta donde están los archivos YAML
## yaml_directory = './generateConfigs/files_yamls'
#yaml_directory = '../kubernetes_fm/scripts/download_manifests/YAMLs02' ## Testing yamls

## ruta de los yamls descargados: C:\projects\kubernetes_fm\scripts\download_manifests\YAMLs
# Leer YAMLs y extraer propiedades

yaml_data_list = iterate_all_buckets(yaml_base_directory, buckets)


# Guardar la salida de la carpeta con ficheros JSON 
##output_json_dir = './generateConfigs/outputs_json_mappeds02'
output_json_dir = '../../resources/mapping_csv/generateConfigs/outputs_json_mappeds'
#output_invalid_kinds_versions = './generateConfigs/outputs_no_validkinds_versions'
#os.makedirs(output_invalid_kinds_versions, exist_ok=True)

##output_json_dir = './generateConfigs/outputs_json_mappeds09'
#output_json_path = './generateConfigs/output_features02.json'
os.makedirs(output_json_dir, exist_ok=True)  # Crea la carpeta si no existe

# Preparar estructura para JSONs
#output_data = []

file_count = {}  # Para manejar múltiples documentos
# Ruta del archivo CSV
#csv_file_path = './generateConfigs/kubernetes_mapping_features_part01.csv'
csv_file_path = '../../respurces/mapping_csv/kubernetes_mapping_properties_features.csv'
csv_dict = load_features_csv(csv_file_path)

for filename, index, yaml_data, simple_props, hierarchical_props, key_value_pairs, root_info in yaml_data_list:
    ##print(f"\nProcesando archivo: {filename}")
    
    auxFeaturesAddedList = set()
    mapped_key = {}
    aux_hierchical = []
    aux_bool = False
    depth_mapping = 1 ## Profundidad tener en cuenta el numero del recorrido recursivo

    feature_map = search_features_in_csv(hierarchical_props, key_value_pairs, csv_dict)
    updated_config = apply_feature_mapping(yaml_data, feature_map, auxFeaturesAddedList, aux_hierchical, mapped_key, aux_bool, depth_mapping)
    base_filename = os.path.splitext(os.path.basename(filename))[0]

    yaml_entry = {
        "filename": f"{base_filename}.yaml",
        "apiVersion": root_info.get("apiVersion", "N/A"),
        #"kind": root_info.get("kind", "N/A"),
        "config": updated_config
    }
    
    if base_filename not in file_count:
        file_count[base_filename] = 0
    file_count[base_filename] += 1 
    
    json_filename = "01-Sin nombre"
    if file_count[base_filename] > 1:
        json_filename = f"{base_filename}_{file_count[base_filename]}.json"
    else:
        json_filename = f"{base_filename}.json" 
    
    print(f"Procesando archivo: {json_filename}")
    output_json_path = os.path.normpath(os.path.join(output_json_dir, json_filename)) ## Se adapta a la salida del SO, estandarizar la ruta / O \

    need_fix_type = contains_datetime(yaml_entry) ## flag para determinar el contenido de los tipos de yaml entry, si hay time, date o datetime se llama a convert_all..
    if need_fix_type:
        yaml_entry = convert_all_datetimes(yaml_entry) ## Funcion para comprobar si hay algun valor con formato datetime en estructuras anidadas que pueda provocar un error
    try:
        with open(output_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(yaml_entry, json_file, ensure_ascii=False, indent=4)
    except TypeError as e:
        with open("./errors_serialization.log", "a", encoding="utf-8") as err_log:
            err_log.write(f"{output_json_path} → {e}\n")
    print(f"Archivo guardado: {output_json_path}\n")

print(f"Todos los archivos han sido procesados y guardados")