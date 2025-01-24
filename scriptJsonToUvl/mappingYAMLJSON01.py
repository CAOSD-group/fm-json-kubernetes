import yaml
import csv
import os

def extract_yaml_properties(data, parent_key='', root_info=None, first_add = True):
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
            print(new_key)
            # Guardar valores clave (apiVersion y kind) para determinar el contexto
            if key in ['apiVersion', 'kind']:
                print(f"EL VALUE ES: {value}")
                if '/' in value: ## if key in ['apiVersion', 'kind']:
                    value = value.replace('/', '_') 
                    print(f"EL VALUE ES: {value}")
                root_info[key] = value
                print(root_info)
                print("----------key")
            simple_props.append(key)

            if isinstance(value, (dict, list)):
                sub_simple, sub_hierarchical, sub_kv_pairs, _ = extract_yaml_properties(value, new_key, root_info, first_add = False)
                simple_props.extend(sub_simple)
                hierarchical_props.extend(sub_hierarchical)
                hierarchical_props.append(new_key) ## Se agregan los valores despues de la recursión
                #print(f"Evolucion del hierarchical: {hierarchical_props}")
                key_value_pairs.extend(sub_kv_pairs)
            else:
                hierarchical_props.append(new_key)
                print(new_key)
                key_value_pairs.append((new_key, value))  # Guardar clave y valor

    elif isinstance(data, list):
        for item in data: ## debug
            print("ITEMS DEBUG:")
            print(item)
            sub_simple, sub_hierarchical, sub_kv_pairs, _ = extract_yaml_properties(item, parent_key, root_info, first_add = False) ##f"{parent_key}_{index}"
            simple_props.extend(sub_simple)
            hierarchical_props.extend(sub_hierarchical)
            key_value_pairs.extend(sub_kv_pairs)

    # Si tenemos apiVersion y kind, añadimos prefijo al feature para mejorar precisión
    if 'apiVersion' in root_info and 'kind' in root_info and first_add:
        prefix = f"{root_info['apiVersion']}_{root_info['kind']}"
        hierarchical_props = [f"{prefix}_{prop}" for prop in hierarchical_props]
        key_value_pairs = [(f"{prefix}_{key}", value) for key, value in key_value_pairs]
    #print(f"Root info: {root_info}")
    #print(f"Listas: {simple_props}  {hierarchical_props}    {key_value_pairs}")
    return simple_props, hierarchical_props, key_value_pairs, root_info


def read_yaml_files_from_directory(directory_path):
    """
    Lee todos los archivos YAML en un directorio y extrae propiedades.
    """
    all_simple_props = set()
    all_hierarchical_props = set()
    all_key_value_pairs = set()
    context_info = {}

    for filename in os.listdir(directory_path):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            file_path = os.path.join(directory_path, filename)
            with open(file_path, 'r', encoding='utf-8') as yaml_file:
                yaml_data = yaml.safe_load(yaml_file)

                simple_props, hierarchical_props, key_value_pairs, root_info = extract_yaml_properties(yaml_data)

                all_simple_props.update(simple_props)
                all_hierarchical_props.update(hierarchical_props)
                all_key_value_pairs.update(key_value_pairs)

                # Guardar la información de apiVersion y kind para cada archivo
                context_info[filename] = root_info

    return list(all_simple_props), list(all_hierarchical_props), list(all_key_value_pairs), context_info


def search_features_in_csv(simple_props, hierarchical_props, key_value_pairs, csv_file, root_info):
    """
    Busca coincidencias en el CSV utilizando las listas separadas:
    - Comparación de simple_props con la columna 'Turned'
    - Comparación de hierarchical_props con la columna 'Midle'
    - Comparación de key_value_pairs con la columna 'Value'
    """
    found_features = set()

    with open(csv_file, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            feature, middle, turned, value = row[0], row[1], row[2], row[3]
            #print(f"VALUE ES: {value}")
            # Filtrar el CSV por apiVersion y kind
            if f"_{root_info['apiVersion']}_{root_info['kind']}_" in feature:

                # Buscar coincidencias exactas en la columna 'Midle'
                for hierarchical_prop in hierarchical_props:
                    #if middle and middle in hierarchical_prop and hierarchical_prop:
                    if middle.strip() and hierarchical_prop.endswith(middle): ## si se compara con la herencia omitiendo la version // agregar la version al midle
                        print(f"COINCIDENCIA (Midle): {middle} -> {hierarchical_prop}")
                        found_features.add(feature) ## se añade si coincide el final del Middle con la herencia actual (es similar que el middle + la version de apiVersion)
                        for key, yaml_value in key_value_pairs:
                            print("DEBUG: impresion?")
                            aux_feature = f"{middle}_{yaml_value}"
                            if value and str(yaml_value) == value:
                                print(f"Coincidencia del feature-value {feature}")
                                found_features.add(feature)
                            else:
                                print(f"NO HAY COINCIDENCIA {feature}") ### Comprobar coincidencias
                                continue
                    #if value and str(yaml_value) == value and middle in hierarchical_prop:
                    #    print(f"COINCIDENCIA (Value): {value} -> {yaml_value} key:  {key}")
                    #    found_features.add(feature)
                # Buscar coincidencias en la columna 'Value' usando los pares clave-valor
                """for key, yaml_value in key_value_pairs:
                    if f"_{root_info['apiVersion']}_{root_info['kind']}_" in feature and hierarchical_prop.endswith(middle):
                        print(f"Key: {key}  yaml_value: {yaml_value}")
                        aux_feature = f"{middle}_{yaml_value}"
                        if str(yaml_value) == value and feature.endswith(aux_feature):
                            print(f"COINCIDENCIA (Value): {value} -> {yaml_value} key:  {key}")
                            found_features.add(feature)"""
    print(f"LOS FOUND FEATURES SON: {found_features}")
    return list(found_features)


# Ruta de la carpeta donde están los archivos YAML
yaml_directory = './generateConfigs/files_yamls/'

# Leer YAMLs y extraer propiedades
simple_props, hierarchical_props, key_value_pairs, context_info = read_yaml_files_from_directory(yaml_directory)

print("Propiedades simples extraídas del YAML:", simple_props)
print("Propiedades jerárquicas extraídas del YAML:", hierarchical_props)
print("Pares clave-valor extraídos del YAML:", key_value_pairs)
print("Contexto de los YAML:", context_info)

# Buscar coincidencias en el CSV basado en apiVersion y kind
csv_file_path = './generateConfigs/kubernetes_mapping_features_part01.csv'
for filename, root_info in context_info.items():
    print(f"\nProcesando archivo: {filename}")
    features_found = search_features_in_csv(simple_props, hierarchical_props, key_value_pairs, csv_file_path, root_info)
    print("Features encontrados:", features_found)