import yaml
import csv
import os
import json

from datetime import datetime, timezone


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

    if isinstance(data, dict): ### and first_add: ## Modificado por el cambio en kind en otras partes del programa...
        for key, value in data.items():
            new_key = f"{parent_key}_{key}" if parent_key else key
            # Guardar valores clave (apiVersion y kind) para determinar el contexto
            if key in ['apiVersion', 'kind']:
                if '/' in value and not '.' in value:
                    value = value.replace('/', '_')
                elif '.' in value and '/': ## Caso en el que el valor de la version contenga puntos '.' se usa solo la segunda parte separada por la barra lateral '/' que donota la versión dentro de los esquemas
                    aux_value = value.split('/') ## Como se representa en los esquemas api_rbac_v1_, caso en los yaml: rbac.authorization.k8s.io/v1
                    print(f"EL AUX VALUE SEPARADO ES {aux_value}")
                    value = aux_value[1]
                    print(value)
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
    #context_info = {}
    error_log_path = './error_log.txt'

    with open(error_log_path, 'w', encoding='utf-8') as error_log:
        for filename in os.listdir(directory_path):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                file_path = os.path.join(directory_path, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as yaml_file:
                        # yaml_data = yaml.safe_load(yaml_file)
                        yaml_documents = list(yaml.safe_load_all(yaml_file))  # Cargar múltiples documentos
                        #if yaml_data is None:
                        if not yaml_documents:
                            error_log.write(f"Archivo vacío o no válido: {file_path}\n")
                            continue

                        for index, yaml_data in enumerate(yaml_documents):
                            if yaml_data is None:
                                error_log.write(f"Documento vacío en {file_path}, índice {index}\n")
                                continue

                            ## Extraer propiedades    
                            simple_props, hierarchical_props, key_value_pairs, root_info = extract_yaml_properties(yaml_data)
                            ## Se guarda el nombre con indice si hay varios elementos
                            yaml_data_list.append((filename, index, yaml_data, simple_props, hierarchical_props, key_value_pairs, root_info))
                            #yaml_data_list.append((filename, yaml_data, simple_props, hierarchical_props, key_value_pairs, root_info))

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
                        print(f"Array de Strings: {feature} {hierarchical_prop} {aux_hierchical_arr_string} {key}   {value}")
                        feature_map[aux_hierchical_arr_string] = feature
                    ## StringValueAdditional: Array de Strings que se añade de manera diferente en el script principal del modelo.
                    elif middle.strip() and turned == "StringValueAdditional" and feature not in feature_map and aux_hierchical_maps.endswith(hierarchical_prop): ## Nueva adición para añadir los StringValue que aparezcan en la lista de features
                        aux_hierchical_arr_string_additional = f"{hierarchical_prop}_StringValueAdditional" ## Se crea manualmente el _StringValue porque es un feature personalizado del modelo. Se usa para referirse a los arrays de strings
                        #print(f"El aux VALUE ES: {aux_hierchical_maps_value}")
                        print(f"Array de Strings Additional: {feature} {hierarchical_prop} {aux_hierchical_arr_string_additional}")
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
                    
                    for key, yaml_value in key_value_pairs:
                        if value and str(yaml_value) == value and feature not in feature_map: ## evitar agregar el mismo feature
                            aux_hierchical_value_added = f"{key}_{yaml_value}" ## Se agrega el yaml_value manualmente ya que en la herencia no se adjunta el valor de las propiedades yaml
                            #print(aux_hierchical_value_added)
                            if feature.endswith(aux_hierchical_value_added): ## Quizas se pueda definir mejor la coincidencia pero asi se asegura que el value coincida con el value del yaml
                                #print(f"VALORES DEL VALUE: {value} VALOR DEL YAML: {yaml_value}")
                                #print(f"DEBUG:? {aux_hierchical_value_added}   {feature}   {key}")
                                feature_map[aux_hierchical_value_added] = feature ## Se agrega el feature que tambien coincide el yaml
                                continue

            # Comparar clave-valor en el YAML con el valor del CSV
            """for key, yaml_value in key_value_pairs:
                if value.strip() and str(yaml_value) == value.strip():
                    feature_map[key] = feature"""
        print(f"El mapa entero es: {feature_map}")
    return feature_map

def extract_key_value_mappings(value, value_features, feature_map): ## Posible encapsulamiento de las funciones para mejorar la legibilidad
    key_values = []
    aux_feature_maps = value0_features.rsplit("_", 1)[0]
    aux_feature_value = f"{aux_feature_maps}_ValueMap"
    for map_key, map_value in value.items():
        key_values.append({
            value_features: map_key,
            aux_feature_value: map_value
        })
    return key_values

def apply_feature_mapping(yaml_data, feature_map, auxFeaturesAddedList):
    """
    Aplica el mapeo de features al YAML reemplazando las claves por los nombres de features.
    """
    #print(f"El mapa entero es: {feature_map}")
    if isinstance(yaml_data, dict) and feature_map is not None:
        #print(feature_map.items())
        new_data = {}
        feature_nested = {}
        feature_type_value = {}
        mapped_key = {}
        feature_map_key_value = {}
        #feature_type_array = {}
        possible_type_data = ['asString', 'asNumber', 'asInteger']
        print(f"Yaml data completo: {yaml_data.items()}")
        for key, value in yaml_data.items():
            original_key = key ## copia de la clave original

            aux_nested = False ## boolean para determinar si una propiedad tiene un feature value
            aux_array = False ## boolean para determinar si una propiedad contiene un array o es un array de features
            aux_maps = False ## marca para determinar los mapas
            aux_str_values = False
            aux_value_type = False
            aux_value_type_array = False
            
            if isinstance(value, datetime): ## Comprobacion de si alguno de los valores es de tipo Time RCF 3339
                value = value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
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
                        #auxFeaturesAddedList.add(value_features["feature"]) ### Omitido temporalmente por la omision en arrays de arrays que se genera de features ya agregados/vistos de los yaml
                        ##feature_arr = [value_features["feature"]]
                        #new_data[value_features["feature"]] = [] ## se queda vacio
                        key = value_features["feature"]
                        aux_array = True
                        #continue
                ### Nueva adicion: StringValue para representar los arrays de Strings. En features se localizan por el _StringValue o _StringValueAdditional
                ## Seguir un tratamiento similar que con los mapas. Parte final del feature
                elif isinstance(value, list) and key_features.endswith("StringValue") and isinstance(value_features, str) and "StringValue" == value_features.split("_")[-1]: ## Prueba add StringValue ## and value_features not in auxFeaturesAddedList
                    aux_key_last_before_map = value_features.split("_")[-2]
                    str_values = []
                    print(f"SE EJECUTA PRIMER VALUE LIST {key}   {value_features}")
                    #print(value)
                    if value and key.endswith(aux_key_last_before_map) and key_features.endswith(f"{aux_key_last_before_map}_StringValue"):### and value.get("key") in value_features  ## key coge los valores del feature mapeado
                        print(f"SE EJECUTA DE NUEVO IF NUEVO    {key}  {value_features}")
                        for str_value in value:
                            print(value)
                            print(f"{str_value}   {key} {value_features}   {aux_key_last_before_map}")
                            #aux_feature_value = f"{aux_feature_str_value}_ValueMap"
                                #if value_features.endswith(key_features):
                            str_values.append({ ## , aux_feature_value: map_value
                                value_features: str_value
                            })
                            #auxFeaturesAddedList.add(value_features) ### Omitido temporalmente por la omision en arrays de arrays que se genera de features ya agregados/vistos de los yaml
                        #print(f"EL KEY VALUES ES {key_values}")
                        feature_str_value = str_values
                        aux_str_values = True
                    #else: ## lista vacia
                    #    feature_str_value = [] ## se deja el array vacio porque no hay contenido o '' o ""

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

                ### Adicion seleccion de tipo de feature dependiendo del tipo de dato del valor de las propiedades
                elif any(key_features.endswith(keyword) for keyword in possible_type_data) and isinstance(value_features, str) and value_features not in auxFeaturesAddedList and value_features.endswith(key_features): ## and any(keyword == value_features.split("_")[1] for keyword in possible_type_data) ### isinstance(value, str) and # and key_features.endswith(possible_type_data)
                    ## Definir bien la logica de insercion de los features a añadir... bloque general por el tipo de dato que es value
                    print("Se ha encontrado una coincidencia del tipo de dato") ##and keyword == value_features.split("_")[1]
                    aux_key_last_before_value = value_features.split("_")[-2] ## se obtiene la penultima prop
                    aux_value_last = value_features.rsplit("_", 1)[0]
                    print(f"{key_features}  {value_features} {key} {value}") ##and keyword == value_features.split("_")[1]
                    
                    if key.endswith(aux_key_last_before_value) and aux_value_last.endswith(key): ### and key_features.endswith(f"{aux_key_last_before_value}_asString"): # and value.get("key") in value_features  ## key coge los valores del feature mapeado
                        print(f"SEGUNDA EJECUCION TIPO DE DATOS     {key}   {value_features}    {value}")
                        if isinstance(value, dict):
                            str_types_values = []
                            print("EJECUCION PARA EL ARRAY TIPO DE DATOS")
                            for key_item, value_item in value.items():
                                print(f"PRUEBA EJECUCION FOR   {key_item}    {value_item}  {value_features}")
                                if value_features not in auxFeaturesAddedList:
                                    feature_entry = {}  # Diccionario para cada feature
                                    # Validar que el valor sea coherente con el tipo esperado del feature
                                    if isinstance(value_item, str) and value_features.endswith("asString"): ## and value_features.endswith("asString")
                                        feature_entry[value_features] = f"{key_item}:{value_item}"
                                        print(f"COINCIDENCIA EN EL ARRAY STRING {value_item}    {str_types_values}")
                                    elif isinstance(value_item, int) and value_features.endswith("asInteger"):
                                        feature_entry[value_features] = value_item
                                        print(f"COINCIDENCIA EN EL ARRAY INTEGER {value_item}    {str_types_values}")
                                    elif isinstance(value_item, float) and value_features.endswith("asNumber"):
                                        feature_entry[value_features] = value_item
                                        print(f"COINCIDENCIA EN EL ARRAY DE NUMBER {value_item}    {str_types_values}")

                                    # Agregar el feature encontrado
                                    if feature_entry:
                                        str_types_values.append(feature_entry)
                                        auxFeaturesAddedList.add(value_features)
                                    # Agregar los valores encontrados sin sobrescribir
                            if "feature_type_array" not in locals():
                                feature_type_array = []  # Se inicializa solo si no existe

                            if str_types_values:
                                aux_value_type_array = True
                                feature_type_array.extend(str_types_values)  # Agregar sin sobrescribir
                                ##feature_type_array = str_types_values  # Si está vacío, inicializarlo como lista           
                        else:
                            if isinstance(value, str) and key_features.endswith(f"{aux_key_last_before_value}_asString"):
                                #print("VALOR STRING")
                                feature_type_value[value_features] = value
                                aux_value_type = True
                                auxFeaturesAddedList.add(value_features)
                            elif isinstance(value, int) and key_features.endswith(f"{aux_key_last_before_value}_asInteger"):
                                #print(f"VALOR INTEGER?  {value}")
                                #key = value_features
                                feature_type_value[value_features] = value
                                aux_value_type = True
                                auxFeaturesAddedList.add(value_features)
                            elif isinstance(value, float) and key_features.endswith(f"{aux_key_last_before_value}_asNumber"):
                                #print(f"VALOR NUMBER?  {value}")
                                #key = value_features
                                feature_type_value[value_features] = value
                                aux_value_type = True
                                auxFeaturesAddedList.add(value_features)
                            """elif isinstance(value, datetime):
                                print(f" Valor de la propiedad en Tiempo,   {key}   {value}")
                                #value = value.isoformat()
                                value = value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                                print(f" Valor de la propiedad despues en Time,   {key}   {value}")"""
                # Representación de valores seleccionados, se comprueba si algun valor del yaml coincide con la ultima parte de los features en la lista.
                elif isinstance(value_features, str) and value == value_features.split("_")[-1] and value_features not in auxFeaturesAddedList:
                        if value_features.endswith(key_features):
                            aux_nested = True
                            feature_nested[value_features] = aux_nested ## value: al final se deja el valor booleano ya que el feature agregado es boolean tambien
                            auxFeaturesAddedList.add(value_features)

            mapped_key = feature_map.get(key, key)
            if aux_nested:
                new_data[mapped_key] = feature_nested
            elif aux_str_values: ## prueba add arr of strings
                #print(f"prueba add arr of strings")
                new_data[mapped_key] = feature_str_value
            elif aux_value_type : ## and not aux_array
                #print(f"ME EJECUTO PARA EL FEATURE SIMPLE ARRAY: {mapped_key}    {key}")
                new_data[mapped_key] = feature_type_value
            elif aux_value_type_array:
                print(f"ELIF FINAL NO SE EJECTUA??   {feature_type_array}")
                new_data[mapped_key] = feature_type_array
                ## Probar confi donde se tiene mas de una opcion en el else: chat // falta poder comprobar arrays en la raiz y su recursion si hay mas de una
            elif aux_array or isinstance(value, list): ##  or isinstance(value, list)
                if aux_maps: ## quizas llevar esta condicion a otra parte, es "especial"
                    #print("NO SE EJCUTA?")
                    #print(feature_map_key_value)
                    new_data[mapped_key] = feature_map_key_value
                elif value is None:
                    new_data[mapped_key] = []
                    print(f"Arrays vacios {new_data}")
                else:
                    new_data[mapped_key] = [apply_feature_mapping(item, feature_map, auxFeaturesAddedList) if isinstance(item, (dict, list)) else item for item in value]
                    #print(f" Comprobar salida arr aux: {mapped_key} {new_data}")
                    #new_data[mapped_key] = [apply_feature_mapping(item, feature_map, auxFeaturesAddedList) if isinstance(item, (dict, list)) else item for item in value]

            else:
                new_data[mapped_key] = apply_feature_mapping(value, feature_map, auxFeaturesAddedList) if isinstance(value, (dict, list)) else value

        return new_data

    elif isinstance(yaml_data, list):
        print(f"YAML DATA ELIF {yaml_data}")
        return [apply_feature_mapping(item, feature_map, auxFeaturesAddedList) for item in yaml_data]

    return yaml_data


# Ruta de la carpeta donde están los archivos YAML
yaml_directory = './generateConfigs/files_yamls'

##yaml_directory = '../kubernetes_fm/scripts/download_manifests/YAMLs' ## Testing yamls
## kubernetes_fm\scripts\download_manifests\YAMLs
## ruta de los yamls descargados: C:\projects\kubernetes_fm\scripts\download_manifests\YAMLs
# Leer YAMLs y extraer propiedades
yaml_data_list = read_yaml_files_from_directory(yaml_directory)

# Ruta del archivo CSV
csv_file_path = './generateConfigs/kubernetes_mapping_features_part01.csv'

# Guardar la salida de la carpeta con ficheros JSON 
#output_json_dir = './generateConfigs/outputs_json_mappeds'
output_json_dir = './generateConfigs/outputs-json-tester'

#output_json_path = './generateConfigs/output_features02.json'
os.makedirs(output_json_dir, exist_ok=True)  # Crea la carpeta si no existe

# Preparar estructura para JSONs
#output_data = []

file_count = {}  # Para manejar múltiples documentos

for filename, index, yaml_data, simple_props, hierarchical_props, key_value_pairs, root_info in yaml_data_list:
    ##print(f"\nProcesando archivo: {filename}")
    
    auxFeaturesAddedList = set()
    feature_map = search_features_in_csv(hierarchical_props, key_value_pairs, csv_file_path)
    updated_config = apply_feature_mapping(yaml_data, feature_map, auxFeaturesAddedList)

    yaml_entry = {
        "filename": filename,
        "apiVersion": root_info.get("apiVersion", "N/A"),
        #"kind": root_info.get("kind", "N/A"),
        "config": updated_config
    }
    #output_data.append(yaml_entry)
    # Generar un nombre de archivo JSON basado en el YAML
    base_filename = os.path.splitext(filename)[0]
    if base_filename not in file_count:
        file_count[base_filename] = 0
    file_count[base_filename] += 1 
    
    json_filename = "01-Sin nombre"
    if file_count[base_filename] > 1:
        json_filename = f"{base_filename}_{file_count[base_filename]}.json"
    else:
        json_filename = f"{base_filename}.json" 
    
    print(f"Procesando archivo: {json_filename}")
    #json_filename = os.path.splitext(filename)[0] + ".json"
    output_json_path = os.path.join(output_json_dir, json_filename)
    
#output_json_path = './generateConfigs/output_features02.json'

    with open(output_json_path, 'w', encoding='utf-8') as json_file:
        json.dump(yaml_entry, json_file, ensure_ascii=False, indent=4)
        #json.dump(output_data, json_file, ensure_ascii=False, indent=4)
    print(f"Archivo guardado: {output_json_path}\n")

print(f"Todos los archivos han sido procesados y guardados")
