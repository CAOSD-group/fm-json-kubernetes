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

    def transform(self) -> Configuration:
        json_data = self.get_configuration_from_json(self._path)
        elements = {}
        list_elements = {} ## Variable que guardara las configuraciones si hay más de 1. Listas con mas de 1 valor
        #self.extract_features(json_data["config"], elements)  # Extrae solo la parte relevante
        self.extract_features(json_data["config"], elements, list_elements)
        #print(f"Elementos que se agregan al Configuration: {elements}")

        if list_elements:
            print(f"Hay mas de una configuración en las listas")
            configurations = []
            for key, items in list_elements.items():
                for idx, item in enumerate(items):
                    new_config = elements.copy()  # Se copian los features que ya habian en la config
                    new_config.update(item)  # Se agregan los elementos individuales
                    configurations.append(Configuration(new_config))
            return configurations
        else:
            return Configuration(elements)
        
    def extract_features(self, data, elements, list_elements):
        """ Extrae los features del JSON sin modificar sus claves. """
        #print(f"Data completo {data}")
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
                    elements[key] = True
                    if len(value) == 1:
                        print("NO ME EJECUTO")
                        self.extract_features(value[0], elements, list_elements)
                    elif len(value) > 1:
                        ## Creacion de una confi por cada elemento de la lista
                        print(f"LISTA CON MAS DE UN ELEMENTO")
                        list_elements[key] = []
                        for item in value:
                            temp_elements = {}
                            self.extract_features(item, temp_elements, list_elements)
                            list_elements[key].append(temp_elements)
                            #print(item)


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
    path_json = '../generateConfigs/outputs_json_mappeds/example_PersistentVolumeClaim.json' ## scriptJsonToUvl/generateConfigs/outputs_json_mappeds/example_deployment02.json

    #path_json = '../generateConfigs/outputs_json_mappeds/example_pod01.json'

    #output_json_dir = '../generateConfigs/outputs_json_mappeds'
    configuration_reader = ConfigurationJSON(path_json)
    #print(configuration_reader)

    configurations = configuration_reader.transform()

    #print(f'Configuration: {configuration}')
    #print(configuration.elements)

    # Imprimir todas las configuraciones generadas
    for i, config in enumerate(configurations):
        configuration = configuration_reader.transform()
        print(f'Configuration {i+1}: {config.elements}')

    #print(os.path.exists(path_json))  # Debe imprimir True si el archivo existe
    
    
    #print(os.path.exists(output_json_dir))  # Debe imprimir True si el archivo existe
    ##json_convertion = configuration.get_configuration_from_json(path_json)
    ##print(f"La lista generada en txt es: {json_convertion}")
    #valid, complete_config = valid_config(elements, fm_model, sat_model)

    # Output the result
    #print(f'Valid? {valid}')
