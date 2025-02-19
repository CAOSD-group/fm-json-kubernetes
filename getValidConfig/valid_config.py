# This script checks whether a configuration (given as a list of keys) is valid according to a feature model.

from flamapy.metamodels.configuration_metamodel.models import Configuration
from flamapy.metamodels.fm_metamodel.models import FeatureModel, Feature
from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.pysat_metamodel.models import PySATModel
from flamapy.metamodels.pysat_metamodel.transformations import FmToPysat
from flamapy.metamodels.pysat_metamodel.operations import PySATSatisfiableConfiguration

from configurationJSON01 import ConfigurationJSON ## clase Reader JSON


FM_PATH = '../kubernetes_combined_02.uvl'


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


"""def valid_config(configuration: list[str], fm_model: FeatureModel, sat_model: PySATModel) -> bool: ## En vez de pasarle (configuration: list[str] le pasamos la lista del JSON que generamos en la Conf del JSON
    #Given a list of features representing a configuration, checks whether the configuration ## modificar valid para poder pasarle mi lista por parametro
    #is satisfiable (valid) according to the provided SAT model.
    config = Configuration(elements={e: True for e in configuration})
    config = complete_configuration(config, fm_model)
    config.set_full(True)
    satisfiable_op = PySATSatisfiableConfiguration()
    satisfiable_op.set_configuration(config)
    return satisfiable_op.execute(sat_model).get_result(), config.get_selected_elements()"""


def valid_config_version_json(configuration_json: Configuration, fm_model: FeatureModel, sat_model: PySATModel) -> bool: ## En vez de pasarle (configuration: list[str] le pasamos la lista del JSON que generamos en la Conf del JSON
    """Given a list of features representing a configuration, checks whether the configuration ## modificar valid para poder pasarle mi lista por parametro
    is satisfiable (valid) according to the provided SAT model."""
    config = complete_configuration(configuration_json, fm_model) ## la conf deberia de ser completa ya (en principio)
    config.set_full(True)
    satisfiable_op = PySATSatisfiableConfiguration()
    satisfiable_op.set_configuration(config)
    return satisfiable_op.execute(sat_model).get_result(), config.get_selected_elements()

def inizialize_model(model_path):
    fm_model = UVLReader(model_path).transform()
    sat_model = FmToPysat(fm_model).transform()
    return fm_model, sat_model

def main(configuration, fm_model, sat_model, cardinality):
    error = ''
    try:
        valid, complete_config = valid_config(configuration, fm_model, sat_model)
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
    fm_model = UVLReader(FM_PATH).transform()
    sat_model = FmToPysat(fm_model).transform()

    # You need the configuration as a list of features
    #elements = ['Pizza', 'Topping', 'Mozzarella', 'Dough', 'Sicilian', 'Size', 'Normal']
    #elements = ['STRATEGY_type', 'VOLUMEMOUNTS_subPath', 'CONTAINERS_livenessProbe', 'VOLUMEMOUNTS_mountPath', 'LIVENESSPROBE_httpGet', 'CONTAINERS_readinessProbe', 'CONTAINERS_ENV_valueFrom', 'VOLUMEMOUNTS_name', 'configMap', 'CONTAINERS_ports', 'CONTAINERS_PORTS_name', 'LIVENESSPROBE_initialDelaySeconds', 'LIVENESSPROBE_HTTPGET_port', 'LIVENESSPROBE_failureThreshold', 'METADATA_namespace', 'kind', 'METADATA_labels', 'CONTAINERS_imagePullPolicy', 'READINESSPROBE_httpGet', 'PODSPEC_containers', 'CONTAINERS_SECURITYCONTEXT_seccompProfile', 'CONTAINERS_name', 'apiVersion', 'CONTAINERS_SECCOMPROFILE_type', 'VOLUMES_name', 'CONTAINERS_env', 'SELECTOR_matchLabels', 'CONTAINERS_PORTS_protocol', 'fieldRef', 'metadata', 'TEMPLATE_METADATA_annotations', 'CONFIGMAP_name', 'PODSPEC_enableServiceLinks', 'CONTAINERS_ENV_value', 'CONTAINERS_CAPABILITIES_drop', 'DEPLOYMENTSPEC_template', 'PODSPEC_Volumes', 'DEPLOYMENTSPEC_selector', 'LIVENESSPROBE_timeoutSeconds', 'CONTAINERS_image', 'CONTAINERS_SECURITYCONTEXT_allowPrivilegeEscalation', 'DEPLOYMENTSPEC_strategy', 'READINESSPROBE_HTTPGET_path', 'CONTAINERS_SECURITYCONTEXT_capabilities', 'CONTAINERS_volumeMounts', 'DeploymentSpec', 'FIELDREF_fieldPath', 'READINESSPROBE_HTTPGET_port', 'DEPLOYMENTSPEC_revisionHistoryLimit', 'LIVENESSPROBE_HTTPGET_path', 'DEPLOYMENTSPEC_TEMPLATE_metadata', 'DEPLOYMENTSPEC_replicas', 'CONTAINERS_PORTS_containerPort', 'CONTAINERS_securityContext', 'METADATA_name', 'PODSPEC_automountServiceAccountToken', 'PodSpec', 'emptyDir', 'TEMPLATE_METADATA_labels', 'CONTAINERS_ENV_name', 'KIND_Deployment', 'GROUP_apps', 'VERSION_v1', 'STRATEGY_TYPE_RollingUpdate', 'IMAGEPULLPOLICY_ifNotPresent', 'CONTAINERS_SECCOMPROFILE_Type_RuntimeDefault', 'PROTOCOL_TCP', 'PROTOCOL_UDP', 'Group', 'Version', 'spec', 'Kubernetes resource object', 'LIVENESSPROBE_exec', 'LIVENESSPROBE_EXEC_command', 'LIVENESSPROBE_grpc', 'LIVENESSPROBE_GRPC_port', 'LIVENESSPROBE_periodSeconds', 'LIVENESSPROBE_successThreshold', 'LIVENESSPROBE_tcpSocket', 'LIVENESSPROBE_TCPSOCKET_port', 'READINESSPROBE_exec', 'READINESSPROBE_EXEC_command', 'READINESSPROBE_failureThreshold', 'READINESSPROBE_grpc', 'READINESSPROBE_GRPC_port', 'READINESSPROBE_initialDelaySeconds', 'READINESSPROBE_periodSeconds', 'READINESSPROBE_successThreshold', 'READINESSPROBE_tcpSocket', 'READINESSPROBE_TCPSOCKET_port', 'READINESSPROBE_timeoutSeconds', 'VOLUMES_type', 'LABELS_key', 'LABELS_value', 'MATCHLABELS_key', 'MATCHLABELS_value', 'TEMPLATE_METADATA_ANNOTATIONS_key', 'TEMPLATE_METADATA_ANNOTATIONS_value', 'DEPLOYMENTSPEC_TEMPLATE_podspec', 'CONTAINERS_removedCapabilities', 'TEMPLATE_METADATA_LABELS_key', 'TEMPLATE_METADATA_LABELS_value', 'Workloads_APIs', 'maxUnavailable']
    ## elements = ['io_k8s_api_apps_v1_Deployment_spec_replicas', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_livenessProbe_initialDelaySeconds', 'io_k8s_api_apps_v1_Deployment_spec_template', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_livenessProbe', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_readinessProbe_httpGet_port', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_image', 'io_k8s_api_apps_v1_Deployment_spec', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_readinessProbe', 'io_k8s_api_apps_v1_Deployment_spec_template_spec', 'io_k8s_api_apps_v1_Deployment_spec_template_metadata_labels', 'io_k8s_api_apps_v1_Deployment_spec_template_metadata', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_ports_containerPort', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_readinessProbe_httpGet_path', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_readinessProbe_periodSeconds', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_readinessProbe_initialDelaySeconds', 'io_k8s_api_apps_v1_Deployment_metadata_name', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_livenessProbe_httpGet_port', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_readinessProbe_httpGet', 'io_k8s_api_apps_v1_Deployment_spec_selector_matchLabels', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_livenessProbe_periodSeconds', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_livenessProbe_httpGet', 'io_k8s_api_apps_v1_Deployment_apiVersion', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_livenessProbe_httpGet_path', 'io_k8s_api_apps_v1_Deployment_kind', 'io_k8s_api_apps_v1_Deployment_metadata', 'io_k8s_api_apps_v1_Deployment_spec_selector', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_ports', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers', 'io_k8s_api_apps_v1_Deployment_spec_template_spec_containers_name']
    #elements = ['io_k8s_api_core_v1_Pod_metadata_name', 'io_k8s_api_core_v1_Pod_spec_containers_name', 'io_k8s_api_core_v1_Pod_spec_containers_image', 'io_k8s_api_core_v1_Pod_spec_containers_ports_containerPort', 'io_k8s_api_core_v1_Pod_spec', 'io_k8s_api_core_v1_Pod_metadata', 'io_k8s_api_core_v1_Pod_apiVersion', 'io_k8s_api_core_v1_Pod_spec_containers', 'io_k8s_api_core_v1_Pod_spec_containers_ports', 'io_k8s_api_core_v1_Pod_kind']
    path_json = '../generateConfigs/outputs_json_mappeds/example_PersistentVolumeClaim.json' ## scriptJsonToUvl/generateConfigs/outputs_json_mappeds/example_deployment02.json
    configuration_reader = ConfigurationJSON(path_json)
    configurations = configuration_reader.transform()

    ##elements = listJson
    for i, config in enumerate(configurations):
        #configuration = configuration_reader.transform()
        valid, complete_config = valid_config_version_json(config, fm_model, sat_model)
        print(f'Configuration {i+1}: {config.elements}  {valid}')

    # Call the valid operation
    #valid, complete_config = valid_config(elements, fm_model, sat_model)


    # Output the result
    #print(f'Valid? {valid}')
    #print(f"Conf completa {complete_config}")

    # Another example of a partial configuration
    #elements = ['Mozzarella', 'Sicilian', 'Big']
    #valid = valid_config(elements, fm_model, sat_model)
    #print(f'Valid? {valid}')

    # Another example of a invalid configuration
    #elements = ['Topping', 'Mozzarella', 'Dough', 'Sicilian', 'Size']
    #valid = valid_config(elements, fm_model, sat_model)
    #print(f'Valid? {valid}')
