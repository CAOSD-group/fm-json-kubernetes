# This script checks whether a configuration (given as a list of keys) is valid according to a feature model.

from flamapy.metamodels.configuration_metamodel.models import Configuration
from flamapy.metamodels.fm_metamodel.models import FeatureModel, Feature
from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.pysat_metamodel.models import PySATModel
from flamapy.metamodels.pysat_metamodel.transformations import FmToPysat
from flamapy.metamodels.pysat_metamodel.operations import PySATSatisfiableConfiguration

from configurationJSON01 import ConfigurationJSON ## clase Reader JSON


FM_PATH = '../../variability_model/kubernetes_combined_04.uvl'

def get_all_parents(feature: Feature) -> list[str]:
    parent = feature.get_parent()
    return [] if parent is None  else [parent.name] + get_all_parents(parent)


def get_all_mandatory_children(feature: Feature) -> list[str]:
    children = []
    for child in feature.get_children():
        if child.is_mandatory():
            children.append(child.name)
            children.extend(get_all_mandatory_children(child))
    return children


def complete_configuration(configuration: Configuration, fm_model: FeatureModel) -> Configuration:
    """Given a partial configuration completes it by adding the parent's features and
    children's features that must be included because of the tree relationships of the 
    provided FM model."""
    configs_elements = dict(configuration.elements)
    for element in configuration.get_selected_elements():
        feature = fm_model.get_feature_by_name(element)
        if feature is None:
            raise Exception(f'Error: the element "{element}" is not present in the FM model.')
        children = {child: True for child in get_all_mandatory_children(feature)}
        parents = {parent: True for parent in get_all_parents(feature)}
        for parent in parents:
            parent_feature = fm_model.get_feature_by_name(parent)
            parent_children = get_all_mandatory_children(parent_feature)
            children.update({child: True for child in parent_children})
        configs_elements.update(children)
        configs_elements.update(parents)
    return Configuration(configs_elements)

def valid_config_version_json(configuration_json: Configuration, fm_model: FeatureModel, sat_model: PySATModel) -> bool: ## En vez de pasarle (configuration: list[str] le pasamos la lista del JSON que generamos en la Conf del JSON
    """Given a list of features representing a configuration, checks whether the configuration ## modificar valid para poder pasarle mi lista por parametro
    is satisfiable (valid) according to the provided SAT model."""
    #print("Before completion:", configuration_json.get_selected_elements())
    config = complete_configuration(configuration_json, fm_model)
    #print("After completion:", config.get_selected_elements())
    config.set_full(True)
    satisfiable_op = PySATSatisfiableConfiguration() 
    satisfiable_op.set_configuration(config) ## Se usa un Solver SAT
    return satisfiable_op.execute(sat_model).get_result(), config.get_selected_elements()

def inizialize_model(model_path):
    fm_model = UVLReader(model_path).transform()
    sat_model = FmToPysat(fm_model).transform()
    return fm_model, sat_model

def main(configuration, fm_model, sat_model, cardinality):
    error = ''
    try:
        valid, complete_config = valid_config_version_json(configuration, fm_model, sat_model) ## valid_config
        # If the configuration is not valid but contains cardinality, we consider it valid (we do this because within a feature with a cardinality 
        # of more than 1, there could be an alternative feature, choosing one of the options each time and causing a validation error).
        if not valid and cardinality == True:
            valid = True
    except Exception as e:
        valid = False
        error = str(e)
    return valid, error, complete_config


if __name__ == '__main__':
    # You need the model in SAT
    #fm_model = UVLReader(FM_PATH).transform()
    #sat_model = FmToPysat(fm_model).transform()

    # You need the configuration as a list of features   
    """configuration_reader = ConfigurationJSON(path_json)
    configurations = configuration_reader.transform()

    ##elements = listJson
    for i, config in enumerate(configurations):
        #configuration = configuration_reader.transform()
        # Call the valid operation
        valid, complete_config = valid_config_version_json(config, fm_model, sat_model)
        #if valid == False:
        #    print("FALSE GENERAL ")
        # Output the result
        print(f"CONF VALID? {valid} \n")

        print(f'Configuration {i+1}: {config.elements}  {valid}')"""