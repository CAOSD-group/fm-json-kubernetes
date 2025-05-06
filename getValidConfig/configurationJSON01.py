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

                    if all(isinstance(x, dict) for x in value):
                        combined_block = []
                        #print(f"Los values dict there    {value}")
                        if len(value) > 0:
                            for item in value:
                                #print(f"Item:   {item}")
                                static = {}
                                lists = {}
                                aux_lists = {}
                                
                                for k, v in item.items():
                                    #print(f"Key, value de cada item: {k}    {v}")
                                    #base_config[k] = True
                                    if isinstance(v, list):
                                        # Intentar extraer valores primitivos desde dicts
                                        static[k] = True
                                        extracted_values = []
                                        aux_combined_block = []
                                        for item in v:
                                            if isinstance(item, dict):
                                                # Si es un diccionario con un único valor primitivo
                                                #print(f"Soy El item: {item}")
                                                print(f"ITEM VALUE: {item.keys()}  {len(item)}")
                                                if len(item) == 1:
                                                    inner_value = list(item.values())[0] ## Casos donde haya solo 1 elemento en la lista: StringValue, Maps etc
                                                    inner_key = list(item.keys())[0]
                                                    #print(f"Inner key   {inner_key} Inner Value {inner_value} Item:   {item}")
                                                    if isinstance(inner_value, (str, int, float, bool)):
                                                        extracted_values.append(inner_value)
                                                        aux_lists[inner_key] = extracted_values
                                                        print(f"lists:  {lists}")
                                                        #extracted_values.append({inner_key: inner_value,})
                                                else:
                                                    #print(f"Subitem     {subitem} ")
                                                    flat_kv = self.flatten_primitive_kv(item)
                                                    aux_combined_block.append(flat_kv)
                                                    #print(f" Aux combined   {aux_combined_block}")

                                            elif isinstance(item, (str, int, float, bool)):
                                                extracted_values.append(item)
                                        if extracted_values:
                                            lists = aux_lists
                                        if aux_combined_block : ## and len(subitem) > 1
                                            #print(f" Aux combined 2   {aux_combined_block}")  
                                            blocks.append(aux_combined_block)

                                    elif isinstance(v, (str, int, float, bool)):
                                        static[k] = v
    
                                    elif isinstance(v, dict):
                                        print(f"Item segunda iter:   {item}")
                                        self.extract_features(v, static, blocks)

                                if lists: # and caseThree
                                    keys = list(lists.keys())
                                    print(f"Keys de las listas  {keys}")
                                    value_lists = [lists[k] for k in keys]
                                    #print(f"Keys de las listas y values:  {keys}    ")
                                    print(f" VALUE LIST DEL FINAL   {value_lists}")

                                    for prod in product(*value_lists):
                                        merged = {k: prod[i] for i, k in enumerate(keys)}
                                        merged.update(static)
                                        combined_block.append(merged)
                                else:
                                    combined_block.append(static.copy())
                        else:
                            print(f"Un unico elemento en la lista")
                            print(f"Elemento unitario:  {value}")
                            #if isinstance(v, list) and all(isinstance(i, (str, int, float, bool)) for i in v):
                            #    lists[k] = v                        
                            if isinstance(value, (str, int, float, bool)):
                                base_config[key] = value

                        # Agregamos un solo bloque combinado
                        blocks.append(combined_block)
                        base_config[key] = True

                        """elif all(isinstance(x, (str, int, float, bool)) for x in value):
                            # Lista de valores simples
                            blocks.append([{key: v} for v in value])
                            base_config[key] = True"""
        
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
        ##print(f"Resultado final:    {result}")
        return result

    def flatten_primitive_kv(self ,d):
        flat = {}
        for k, v in d.items():
            if isinstance(v, (str, int, float, bool)):
                flat[k] = v
            elif isinstance(v, dict):
                flat[k] = True
                inner = self.flatten_primitive_kv(v)
                flat.update(inner)
        return flat

    def get_configuration_from_json(self, path: str) -> dict:
        if not file_exists(path):
            raise ConfigurationNotFound

        with open(path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)

        return data
        
if __name__ == '__main__':

    #path_json = '../generateConfigs/outputs_json_tester/1-metallb5_5.json' ## scriptJsonToUvl/generateConfigs/outputs_json_mappeds/example_deployment02.json
    path_json = '../generateConfigs/outputs_json_tester/example_deployment02.json'
    ##example_PersistentVolume
    #path_json = '../generateConfigs/outputs_json_mappeds/example_pod01.json'
    
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
