from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.pysat_metamodel.transformations import FmToPysat
from configurationJSON01 import ConfigurationJSON  # Reader JSON
from valid_config import valid_config_version_json

import time  # Libreria para calcular los tiempos de procesamiento

import os
import csv

FM_PATH = '../../variability_model/kubernetes_combined_04.uvl'
##JSON_DIR = '../generateConfigs/outputs-json-tester'
##JSON_DIR = '../generateConfigs/outputs_json_mappeds09'
#JSON_DIR = '../generateConfigs/outputs_no_validkinds_versions'

json_base_directory = '../../resources/generateConfigs' ## Pendiente unificar salida de invalidKindsVersions a la misma carpeta donde se generen los json
json_folders = ['outputs_json_mappeds11', 'invalidKindsVersions01' ] ## Arr con los 2 paths de directorios a revisar
#JSON_DIR_INVALIDAS_KINDS_VERSIONS = '../yamls_agrupation/tester/invalidKindsVersions'

ERROR_LOG_FILE = "error_log_mappeds03_11_3.txt"
csv_ouput_file = "config_validation_results03_3_json11_FirstConfig.csv"

#open(ERROR_LOG_FILE, "w").close() ## Se limpia el archivo
VALIDATE_ONLY_FIRST_CONFIG = True ## Usar version de validacion unitaria o total


def load_processed_files(csv_file_path):
    processed = set()
    if os.path.exists(csv_file_path):
        with open(csv_file_path, mode="r", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # Saltar cabecera
            for row in reader:
                if row and row[0].endswith(".json"):  # Asegura que sea una fila válida de datos
                    processed.add(row[0])
    return processed


def process_file(filepath, fm_model, sat_model):
  """Procesa un solo archivo JSON y devuelve los resultados de validación."""
  #results = []
  try:
    print(f"Procesando archivo: {filepath}")
    
    if 'invalidKindsVersions' in os.path.normpath(filepath):
      ## proceso de return con el error decidido y demas...
      return [os.path.basename(filepath), "Invalid (Kind, Version)", "-", "-", "-", "-", "La version y/o kind en el archivo estan fuera del esquema de Kubernetes."]
      #return [os.path.basename(filepath), "Error"]

    start_conf_time = time.time()  # Inicio del tiempo de mapeo
    configuration_reader = ConfigurationJSON(filepath)
    configurations = configuration_reader.transform()
    end_conf_time = time.time()  # Fin del tiempo de mapeo
    conf_time = round(end_conf_time - start_conf_time, 5)  # Row T conf: Tiempo de mapeo de confs en segundos
    num_confs = len(configurations)  # Row Nº Confs: Número de configuraciones del fichero
    #num_features = 0 ## Agregar num de features de cada file, uno lineal con los del archivo o total con la suma de los features en cada conf...
    # Si hay configuraciones, tomamos la primera para contar sus features
    num_features = len(configurations[0].elements) if configurations else 0

    ## Cada el de la lista conf es un feature (complete_list) o tratar con las confs y obtener el total de features?
    file_valid = True
    
    if VALIDATE_ONLY_FIRST_CONFIG:
        config = configurations[0] ## Se obtiene la primera configuracion

        start_validation_time = time.time()  # Inicio del tiempo de validación
        valid, complete_config = valid_config_version_json(config, fm_model, sat_model)
        end_validation_time = time.time()  # Fin del tiempo de validación
        validation_time = round(end_validation_time - start_validation_time, 4)  # Row T val: Tiempo de validación en segundos
        file_valid = valid
        print(f'Configuración 1 (única validada): -> Válida: {valid}')
    else:
      start_validation_time = time.time()  # Inicio del tiempo de validación
      for i, config in enumerate(configurations): ## Comprobacion de cada configuracion de cada achivo
        valid, complete_config = valid_config_version_json(config, fm_model, sat_model)
        print(f'Configuración {i+1}:  -> Válida: {valid}') ## {config.elements} 
        if not valid:
          file_valid = False
          break # Si hay una sola conf inválida se considera el archivo entero inválido ## continue
        ##results.append([os.path.basename(filepath), i + 1, valid])  # Guardamos nombre y resultado
        #print(f"Diferencias con el filepath normal: {file_path}")
      end_validation_time = time.time()  # Fin del tiempo de validación
      validation_time = round(end_validation_time - start_validation_time, 4)  # Row T val: Tiempo de validación en segundos
    return [os.path.basename(filepath), file_valid, num_features, num_confs, conf_time, validation_time, "Todas las Configuraciones validas" if file_valid else "Alguna Configuracion invalida"] ##results

  except FileNotFoundError:
    with open(ERROR_LOG_FILE, "a") as error_log:
      error_log.write(f"Archivo no encontrado: {os.path.basename(filepath)}\n")
    return [os.path.basename(filepath), "Error", "-", "-", "-", "-", "Exeption Error archivo no encontrado"] #return [os.path.basename(filepath), "Error"]

  except Exception as e:
    with open(ERROR_LOG_FILE, "a") as error_log:
      error_log.write(f"Error desconocido en archivo {os.path.basename(filepath)}: {str(e)}\n")
    return [os.path.basename(filepath), "Error", "-", "-", "-", "-", "Exeption Error no contemplado"] ##results
  ##return [os.path.basename(filepath), file_valid] ##results


def validate_all_configs(directory, fm_model, sat_model ,writer, processed_files):
  """Recorre el directorio de JSONs, valida las configuraciones y guarda los resultados."""
  valid_count = 0
  invalid_count = 0
  error_count = 0
  for filename in os.listdir(directory):
    if filename in processed_files:
      print(f"Archivo ya en la lista de resultados")
      continue
    if not filename.endswith(".json"):  # Solo procesar JSON
      print("Solo se procesan archivos json")
      continue

    #print(f"Filename: {filename}")
    file_path = os.path.normpath(os.path.join(directory, filename))     ## os.path.join(directory, filename)
    result = process_file(file_path, fm_model, sat_model)
    #print(f"Array csv que se va insertando y el file_path: {result} {file_path}")
    writer.writerow(result)  # Escribir en el CSV linea por linea
    ##csv_data.append(result)

    valid_field = str(result[1]).strip().lower()
    if valid_field == 'true':
      valid_count += 1
    if valid_field == 'false':
      invalid_count += 1
    else:
      error_count += 1

  return valid_count, invalid_count, error_count

# Lista generadora que procesa YAMLs de todas las carpetas válidas
def iterate_all_paths(json_base_directory, json_folders, fm_model, sat_model):
    for folder in json_folders:
        json_path = os.path.normpath(os.path.join(json_base_directory, folder))
        if os.path.isdir(json_path):
            validate_all_configs(json_path, fm_model, sat_model)
            #yield from read_yaml_files_from_directory(bucket_path)
            #return json_path

if __name__ == '__main__':

  fm_model = UVLReader(FM_PATH).transform()
  sat_model = FmToPysat(fm_model).transform()
  print(f"Cargando y procesando el modelo")
  valid_count, invalid_count, error_count = 0, 0, 0 ## Valid: nº true, invalid: nº false, error: nº errores
  list_processed_files = load_processed_files(csv_ouput_file)

  writhe_name_rows = not os.path.exists(csv_ouput_file) or os.stat(csv_ouput_file).st_size == 0

  with open(csv_ouput_file, mode="a", newline="") as file:
    writer = csv.writer(file)
    
    if writhe_name_rows: ## Write header rows if csv not exist before
      writer.writerow(["Filename", "Valid", "Features", "Configurations", "TimeConf", "TimeVal", "DescriptionAgrupation"])  # Escribir cabecera del CSV

    for folder in json_folders:
      json_path = os.path.normpath(os.path.join(json_base_directory, folder))
      print(f"JSON PATH {json_path}")
      if os.path.isdir(json_path):
        valid_num, invalid_num, error_num =  validate_all_configs(json_path, fm_model, sat_model, writer, list_processed_files)
        valid_count = valid_count + valid_num
        invalid_count = invalid_count + invalid_num
        error_count = error_count + error_num

    writer.writerow(["Total Valid", valid_count])
    writer.writerow(["Total Invalid", invalid_count])
    writer.writerow(["Total Error", error_count])

    print(f"\n Total de archivos válidos: {valid_count}")
    print(f" Total de archivos inválidos: {invalid_count}")
    print(f" Total de archivos inválidos: {error_count}")

    print(f"Resultados guardados en {csv_ouput_file}")

  ##iterate_all_paths(json_base_directory, json_folders, fm_model, sat_model)
  #json_dir = iterate_all_paths
  #validate_all_configs(JSON_DIR, fm_model, sat_model)