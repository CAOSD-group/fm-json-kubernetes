from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.pysat_metamodel.transformations import FmToPysat
from configurationJSON01 import ConfigurationJSON  # Reader JSON
from valid_config import valid_config_version_json

import os
import csv

FM_PATH = '../kubernetes_combined_02.uvl'
JSON_DIR = '../generateConfigs/outputs-json-tester'
ERROR_LOG_FILE = "error_log.txt"
csv_ouput_file = "config_validation_results.csv"

open(ERROR_LOG_FILE, "w").close() 

def save_statistics(csv_data, output_file):
  """Guarda los resultados en un archivo CSV."""
  valid_count = sum(1 for _, valid in csv_data if valid is True)
  invalid_count = sum(1 for _, valid in csv_data if valid is False or valid == "Error")

  with open(output_file, mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Filename", "Valid"])
    writer.writerows(csv_data)
    writer.writerow(["Total Valid", valid_count])
    writer.writerow(["Total Invalid", invalid_count])

  print(f"Resultados guardados en {output_file}")
  print(f"Total de archivos válidos: {valid_count}")
  print(f"Total de archivos inválidos: {invalid_count}")  

def count_valid_invalid(csv_data):
    """Cuenta el número de archivos válidos e inválidos."""
    valid_count = sum(1 for _, valid in csv_data if valid is True)
    invalid_count = sum(1 for _, valid in csv_data if valid is False or valid == "Error")
    print(f"Total de archivos válidos: {valid_count}")
    print(f"Total de archivos inválidos: {invalid_count}")

def process_file(filepath, fm_model, sat_model):
  """Procesa un solo archivo JSON y devuelve los resultados de validación."""
  #results = []
  try:
    print(f"Procesando archivo: {filepath}")
    configuration_reader = ConfigurationJSON(filepath)
    configurations = configuration_reader.transform()
    file_valid = True

    for i, config in enumerate(configurations): ## Comprobacion de cada configuracion de cada achivo
      valid, complete_config = valid_config_version_json(config, fm_model, sat_model)
      print(f'Configuración {i+1}: {config.elements} -> Válida: {valid}')
      if not valid:
        file_valid = False
        break # Si hay una sola conf inválida se considera el archivo entero inválido ## continue
      ##results.append([os.path.basename(filepath), i + 1, valid])  # Guardamos nombre y resultado
      print(f"Error en la lectura del archivo? {os.path.basename(filepath)}")
      #print(f"Diferencias con el filepath normal: {file_path}")

    return [os.path.basename(filepath), file_valid] ##results

  except FileNotFoundError:
    with open(ERROR_LOG_FILE, "a") as error_log:
      error_log.write(f"Archivo no encontrado: {os.path.basename(filepath)}\n")
    return [os.path.basename(filepath), "Error"]

  except Exception as e:
    with open(ERROR_LOG_FILE, "a") as error_log:
      error_log.write(f"Error desconocido en archivo {os.path.basename(filepath)}: {str(e)}\n")
    return [os.path.basename(filepath), "Error"]  # Marcar como error
  ##return [os.path.basename(filepath), file_valid] ##results


def validate_all_configs(directory, fm_model, sat_model):
  """Recorre el directorio de JSONs, valida las configuraciones y guarda los resultados."""
  csv_data = []

  for filename in os.listdir(directory):
    if filename.endswith(".json"):  # Solo procesar JSON
      print(f"Filename: {filename}")
      file_path = os.path.normpath(os.path.join(directory, filename))     ## os.path.join(directory, filename)
      print(f"Array csv que se va insertando y el file_path: {csv_data} {file_path}")
      result = process_file(file_path, fm_model, sat_model)
      csv_data.append(result)
  
  save_statistics(csv_data, csv_ouput_file)

if __name__ == '__main__':
  fm_model = UVLReader(FM_PATH).transform()
  sat_model = FmToPysat(fm_model).transform()

  validate_all_configs(JSON_DIR, fm_model, sat_model)