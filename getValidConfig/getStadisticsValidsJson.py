from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.pysat_metamodel.transformations import FmToPysat
from configurationJSON01 import ConfigurationJSON ## Reader JSON
from valid_config import valid_config_version_json

import os
import json

FM_PATH = '../kubernetes_combined_02.uvl'
ERROR_LOG_FILE = "error_log.txt"


def saveStadistics (file_name, valid_config, csv_data): ## , elements
  """" Función que almacena los datos de las configuraciones validas e inválidas"""
  ## Si alguna de las configuraciones dentro de la lista de confs es False se considera la lista entera False
  #csv_data = []
  csv_data.append([file_name, valid_config])
  print(f"El archivo {file_name} es {valid_config}")

  return csv_data

if __name__ == '__main__':

  fm_model = UVLReader(FM_PATH).transform()
  sat_model = FmToPysat(fm_model).transform()

  json_dir = '../generateConfigs/outputs-json-tester'
  csv_data = []
  for filename in os.listdir(json_dir):
    if filename.endswith(".json"): ## or filename.endswith(".yml")
      file_path = os.path.join(json_dir, filename)
      print(f"Procesando archivo: {file_path}")
      try:
        configuration_reader = ConfigurationJSON(file_path)
        ## Recorrer el directorio y hacer el transform para cada archivo. Guaradar nombre fichero y conf o cogerlo de la conf (modificacion de configurationJSON01)
        configurations = configuration_reader.transform()
        ##validator_element = ValidConfig()
        #validationConf = validator_element.valid_config_version_json(configuration, fm_model,sat_model)
        for i, config in enumerate(configurations):
          validationConf, complete_config = valid_config_version_json(config, fm_model,sat_model)
          if not validationConf: ## La validacion es Falsa
            csv_data.append([config, validationConf]) ## adicion en una lista de los resultados
            continue
            ##saveStadistics(config, validationConf, csv_data)
          print(f'Configuration {i+1}: {config.elements}')
          print(f'Validez del archivo y archivo {file_name}: {valid_config}')
          csv_data.append([file_name, validationConf]) ## adicion en una lista de los resultados

      except FileNotFoundError:
        with open(ERROR_LOG_FILE, "a") as error_log:
          error_log.write(f"Archivo no encontrado: {file_path}\n")
      except Exception as e:
        with open(ERROR_LOG_FILE, "a") as error_log:
          error_log.write(f"Error desconocido en archivo {file_path}: {str(e)}\n")
  print(csv_data)
