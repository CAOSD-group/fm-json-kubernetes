# INSTALAR flamapy para obtener los paquetes necesarios
##https://raw.githubusercontent.com/flamapy/flamapy_fw/refs/heads/develop/flamapy/metamodels/configuration_metamodel/transformations/configuration_basic_reader.py
#import csv ## json
import json
import os
from flamapy.core.transformations.text_to_model import TextToModel

from flamapy.metamodels.configuration_metamodel.models.configuration import Configuration
from flamapy.core.utils import file_exists
from flamapy.core.exceptions import ConfigurationNotFound


class ConfigurationJSON(TextToModel):
    @staticmethod
    def get_source_extension() -> str:
        return 'json'

    def __init__(self, path: str) -> None:
        self._path = path

    def transform(self): ##  -> Configuration
        json_data = self.get_configuration_from_json(self._path)
        elements = {}
        list_elements = {} ## Variable que guardara las configuraciones si hay más de 1. Listas con mas de 1 valor
        #self.extract_features(json_data["config"], elements)  # Extrae solo la parte relevante
        self.extract_features(json_data["config"], elements, list_elements)
        #print(f"Elementos que se agregan al Configuration: {elements}")

        if list_elements:
            #return self.generate_combinations(elements, list_elements)
            configurations = self.generate_combinations(elements, list_elements)
            return configurations
    def extract_features(self, data, elements, list_elements):
        """ Extrae los features del JSON sin modificar sus claves. """
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)):  # Datos primitivos
                    #print(f"Elementos value {value}")
                    elements[key] = value
                elif isinstance(value, dict):  # Listas con diccionarios
                    #print(f"Elementos dict 2    {key} {value}")
                    elements[key] = True
                    self.extract_features(value, elements, list_elements)  # Se sigue explorando
                elif isinstance(value, list):  # Listas con diccionarios
                    #print(f"Elementos lista {value}")
                    elements[key] = True ## No se si duplica el key
                    if len(value) > 1:
                        #if key not in list_elements:
                        list_elements[key] = []
                        for item in value:
                            print("Ejecución con mas de un elemento en la lista")
                            temp_elements = {}
                            self.extract_features(item, temp_elements, list_elements)
                            list_elements[key].append(temp_elements)   #list_elements.append([self.extract_single_feature(item) for item in value])
                    #else: ## Solo un elemento o ninguno -- 
                    #    print("Ejecución con un solo elemento de la lista")
                    #    self.extract_features(value[0], elements, list_elements)

    """def extract_single_feature(self, item):
         #Extrae un solo feature de un elemento de lista. 
        feature = {}
        self.extract_features(item, feature, {})
        return feature"""

    def generate_combinations(self, base_config, list_elements):
        """ Genera todas las combinaciones posibles manteniendo la estructura original. """
        
        keys = list(list_elements.keys())
        num_keys = len(keys)
        configurations = []

        def backtrack(index, current_config):
            if index == len(list_elements): ## num_keys
                configurations.append(Configuration(current_config.copy()))
                return
            key = keys[index]
            for option in list_elements[key]:
                current_config.update(option)
                backtrack(index + 1, current_config)
                for key in option.keys():
                    if key in current_config:
                        current_config.pop(key)
        # Iniciamos el backtracking con la configuración base
        backtrack(0, base_config.copy())

        return configurations

    def get_configuration_from_json(self, path: str) -> dict:
        # Returns a list of list 
        if not file_exists(path):
            raise ConfigurationNotFound

        with open(path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)  # Cargar JSON como dict

        return data

if __name__ == '__main__':
    # You need the model in SAT
    #fm_model = UVLReader(FM_PATH).transform()
    #sat_model = FmToPysat(fm_model).transform()
    
    # You need the configuration as a list of features
    #elements = ['Pizza', 'Topping', 'Mozzarella', 'Dough', 'Sicilian', 'Size', 'Normal']
    #path_json = '../generateConfigs/outputs_json_mappeds/example_service01.json' ## scriptJsonToUvl/generateConfigs/outputs_json_mappeds/example_deployment02.json
    path_json = '../generateConfigs/outputs_json_mappeds05/1-metallb5_5.json' ## scriptJsonToUvl/generateConfigs/outputs_json_mappeds/example_deployment02.json

    #path_json = '../generateConfigs/outputs_json_mappeds/example_pod01.json'

    #output_json_dir = '../generateConfigs/outputs_json_mappeds'
    
    #print(f'Configuration: {configurations}')
    #print(configuration.elements)

    # Imprimir todas las configuraciones generadas
    #if len(configurations) > 1:
    
    configuration_reader = ConfigurationJSON(path_json)
    configurations = configuration_reader.transform()

    for i, config in enumerate(configurations):
        configuration = configuration_reader.transform()
        print(f'Configuration {i+1}: {config.elements}')
    
    
    #print(os.path.exists(output_json_dir))  # Debe imprimir True si el archivo existe
    ##json_convertion = configuration.get_configuration_from_json(path_json)
    ##print(f"La lista generada en txt es: {json_convertion}")
    #valid, complete_config = valid_config(elements, fm_model, sat_model)

    # Output the result
    #print(f'Valid? {valid}')
