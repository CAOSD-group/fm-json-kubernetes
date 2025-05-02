# INSTALAR flamapy para obtener los paquetes necesarios
##https://raw.githubusercontent.com/flamapy/flamapy_fw/refs/heads/develop/flamapy/metamodels/configuration_metamodel/transformations/configuration_basic_reader.py
#import csv ## json
import json
import os
from flamapy.core.transformations.text_to_model import TextToModel

from copy import deepcopy
from itertools import product
from flamapy.metamodels.configuration_metamodel.models.configuration import Configuration
from flamapy.core.utils import file_exists
from flamapy.core.exceptions import ConfigurationNotFound


class ConfigurationJSON(TextToModel):
    @staticmethod
    def get_source_extension() -> str:
        return 'json'

    def __init__(self, path: str) -> None:
        self._path = path

    def transform(self):
        json_data = self.get_configuration_from_json(self._path)
        base_config = {}
        blocks = []

        self.extract_features(json_data['config'], base_config, blocks)

        configurations = self.generate_combinations(base_config, blocks)
        return configurations

    def extract_features(self, data, base_config, blocks):
        """Extrae valores fijos a base_config y bloques con combinaciones posibles a blocks."""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)):
                    base_config[key] = value
                elif isinstance(value, dict):
                    base_config[key] = True
                    self.extract_features(value, base_config, blocks)

                elif isinstance(value, list):
                    #print(f"Los values con list here    {value}")
                    if not value:
                        continue

                    if all(isinstance(x, dict) for x in value): ## isinstance(value, list) and 
                        combined_block = []
                        #print(f"Los values dict there    {value}")
                        #if len(value) > 0:
                        # Lista de diccionarios: p.ej. addresses
                        for item in value:
                            static = {}
                            lists = {}

                            for k, v in item.items():
                                base_config[k] = True
                                if isinstance(v, list):
                                    for subitem in v:
                                        if isinstance(subitem, dict):
                                            if len(subitem) == 1:
                                                print("No me deberia de ejectutar")
                                                for inner_key, inner_value in subitem.items():
                                                    if isinstance(inner_value, (str, int, float, bool)):
                                                        lists.setdefault(inner_key, []).append(inner_value)
                                            else:
                                                print(f"[DEBUG] Lista con dicts complejos en key={k}")
                                                print(subitem)
                                                nested_static = {}
                                                self.extract_features(subitem, nested_static, blocks)
                                                static.update(nested_static)
                                        elif isinstance(subitem, (str, int, float, bool)):
                                            lists.setdefault(k, []).append(subitem)
                                elif isinstance(v, (str, int, float, bool)):
                                    static[k] = v
                                elif isinstance(v, dict):
                                    print(f"Item segunda iter:   {item}")
                                    self.extract_features(v, static, blocks)

                            if lists:
                                keys = list(lists.keys())
                                value_lists = [lists[k] for k in keys]
                                for prod in product(*value_lists):
                                    merged = {k: prod[i] for i, k in enumerate(keys)}
                                    merged.update(static)
                                    combined_block.append(merged)
                            else:
                                combined_block.append(static.copy())

                        blocks.append(combined_block)  # SOLO AL FINAL DE CADA ITEM
                        base_config[key] = True
                    else:
                        print("Ejecucion no es de dict, creo que es list")

                elif all(isinstance(x, (str, int, float, bool)) for x in value):
                    # Lista de valores simples
                    blocks.append([{key: v} for v in value])
                    base_config[key] = True
        
        elif isinstance(data, list):
            print(f"Data es list")
            #for item in data:
            #    self.extract_features(item, base_config, blocks)

    def generate_combinations(self, base_config, blocks):
        """Combinación total entre todos los bloques, añadiendo base_config fijo."""
        def backtrack(index, current, result):
            if index == len(blocks):
                merged = deepcopy(base_config)
                for partial in current:
                    merged.update(partial)
                result.append(Configuration(merged))
                return

            for option in blocks[index]:
                current.append(option)
                backtrack(index + 1, current, result)
                current.pop()

        result = []
        backtrack(0, [], result)
        print(f"[DEBUG] Total blocks: {len(blocks)}")
        for i, block in enumerate(blocks):
            print(f"[DEBUG] Block {i+1}: {len(block)} options")
        return result

    def get_configuration_from_json(self, path: str) -> dict:
        if not file_exists(path):
            raise ConfigurationNotFound

        with open(path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)

        return data
        
if __name__ == '__main__':
    # You need the model in SAT
    #fm_model = UVLReader(FM_PATH).transform()
    #sat_model = FmToPysat(fm_model).transform()
    
    # You need the configuration as a list of features
    #elements = ['Pizza', 'Topping', 'Mozzarella', 'Dough', 'Sicilian', 'Size', 'Normal']
    #path_json = '../generateConfigs/outputs_json_mappeds/example_service01.json' ## scriptJsonToUvl/generateConfigs/outputs_json_mappeds/example_deployment02.json
    #path_json = '../generateConfigs/outputs_json_tester/1-metallb5_5.json' ## scriptJsonToUvl/generateConfigs/outputs_json_mappeds/example_deployment02.json
    path_json = '../generateConfigs/outputs_json_tester/endpoints01.json'
    ##example_PersistentVolume
    #path_json = '../generateConfigs/outputs_json_mappeds/example_pod01.json'

    #output_json_dir = '../generateConfigs/outputs_json_mappeds'
    
    #print(f'Configuration: {configurations}')
    #print(configuration.elements)

    # Imprimir todas las configuraciones generadas
    #if len(configurations) > 1:
    
    configuration_reader = ConfigurationJSON(path_json)
    configurations = configuration_reader.transform()
    #print(f"Configuraciones que se leen:    {configurations}")
    for i, config in enumerate(configurations):
        configuration = configuration_reader.transform()
        print(f'Configuration {i+1}: {config.elements}')
    
    
    #print(os.path.exists(output_json_dir))  # Debe imprimir True si el archivo existe
    ##json_convertion = configuration.get_configuration_from_json(path_json)
    ##print(f"La lista generada en txt es: {json_convertion}")
    #valid, complete_config = valid_config(elements, fm_model, sat_model)

    # Output the result
    #print(f'Valid? {valid}')
