#### Versión del script de desarrollo sin comentarios del mapeo de esquemas de kubernetes json a uvl. #####
### @author: bfl699 @group: caosd
import json
import re
from collections import deque

# Importar el procesador de restricciones
from analisisScript01 import generar_constraintsDef
##global feature_aux_original_type
#from analisisScriptNpl01conMain import generar_constraintsDef
class SchemaProcessor:
    def __init__(self, definitions):
        self.definitions = definitions # Un diccionario que organiza las descripciones en tres categorías:
        self.resolved_references = {}
        self.seen_references = set()
        self.seen_features = set() ## Añadir condicion a las refs vistas para no omitir refs ya vistas
        self.processed_features = set()
        self.constraints = []  # Lista para almacenar las dependencias como constraints
        #Prueba pila para las referencias ciclicas
        #self.stact_refs = []
        self.feature_aux_original_type = ""
        # Se inicializa un diccionario para almacenar descripciones por grupo
        self.descriptions = {
            'values': [], 
            'restrictions': [],
            'dependencies': []

        }
        self.is_cardinality = False
        self.is_deprecated = False
        self.seen_descriptions = set()

        # Patrones para clasificar descripciones en categorías de valores, restricciones y dependencias
        self.patterns = {
            'values': re.compile(r'^\b$', re.IGNORECASE), # values are|valid|supported|acceptable|can be
            'restrictions': re.compile(r'If the operator is|template.spec.restartPolicy|conditions may not be|Details about a waiting|TCPSocket is NOT|must be between|Note that this field cannot be set when|valid port number|must be in the range|must be greater than|are mutually exclusive properties|Must be set if type is|field MUST be empty if|must be non-empty if and only if|only if type|\. Required when|required when scope|\. At least one of|a least one of|Exactly one of|resource access request|datasetUUID is|succeededIndexes specifies|Represents the requirement on the container|ResourceClaim object in the same namespace as this pod|indicates which one of|may be non-empty only if|Minimum value is|Value must be non-negative|minimum valid value for|in the range 1-', re.IGNORECASE),### If the operator is|must be between|   # \. Required when|required when scope  ## the currently supported values are(valores) allowed||conditions|should|must be|cannot be|if[\s\S]*?then|only|never|forbidden|disallowed            'dependencies': re.compile(r'^\b$', re.IGNORECASE) ## (requires|if[\s\S]*?only if|only if) # depends on ningun caso especial, quitar relies on: no hay casos, contingent upon: igual = related to
            'dependencies': re.compile(r'^\b$', re.IGNORECASE) ## (requires|if[\s\S]*?only if|only if) # depends on ningun caso especial, quitar relies on: no hay casos, contingent upon: igual = related to

        }

        ## 'restrictions': re.compile(r'If the operator is|template.spec.restartPolicy|conditions may not be|Details about a waiting|Sleep represents|must be between|Note that this field cannot be set when|valid port number|must be in the range|must be greater than|are mutually exclusive properties|Must be set if type is|field MUST be empty if|must be non-empty if and only if|only if type|\. Required when|required when scope|\. At least one of|a least one of|Exactly one of|resource access request|datasetUUID is|succeededIndexes specifies|Represents the requirement on the container|ResourceClaim object in the same namespace as this pod|indicates which one of|may be non-empty only if|Minimum value is|Value must be non-negative|minimum valid value for|in the range 1-', re.IGNORECASE),### If the operator is|must be between|   # \. Required when|required when scope  ## the currently supported values are(valores) allowed||conditions|should|must be|cannot be|if[\s\S]*?then|only|never|forbidden|disallowed

        # Lista de parte de nombres de features que se altera el tipo de dato a Boolean para la compatibilidad con las constraints y uvl. ### Los que se cambian para añadir un nivel mas que represente el String que se omite al cambiar el tipo a Boolean
        self.boolean_keywords = ['AppArmorProfile_localhostProfile', 'appArmorProfile_localhostProfile', 'seccompProfile_localhostProfile', 'SeccompProfile_localhostProfile', 'IngressClassList_items_spec_parameters_namespace',
                        'IngressClassParametersReference_namespace', 'IngressClassSpec_parameters_namespace', 'IngressClass_spec_parameters_namespace','_tolerations_value','_Toleration_value', '_clientConfig_url', '_WebhookClientConfig_url',
                        '_succeededIndexes', '_succeededCount', 'source_resourceClaimName', '_ClaimSource_resourceClaimName', '_resourceClaimTemplateName', '_datasetUUID', '_datasetName']  # Lista para modificar a otros posibles tipos de los features (Cambiado del original por la compatibilidad) ##
        #### probar porque no se cambian cosas de string en las descripciones pero si en el modelo:, 'conditions_status'
        # Lista de expresiones regulares para casos en que la lista anterior necesite de más precisión para solo alterar el tipo en los parametros requeridos
        self.boolean_keywords_regex = [r'.*_paramRef_name$', r'.*_ParamRef_name$'] ## , r'.*_paramRef_selector$', r'.*_ParamRef_selector$'


        # Definición de tramos de features con configuraciones específicas para la compatibilidad con las restricciones # os.name
        self.special_features_config = [ '_template_spec_', '_Pod_spec_', '_PodList_items_spec_', '_core_v1_PodSpec_', '_PodTemplateSpec_spec_', '_v1_PodSecurityContext_'
                                       , '_v1_Container_securityContext_', '_v1_EphemeralContainer_securityContext_', '_v1_SecurityContext_']
        
            # Aquí se pueden añadir más configuraciones de características especiales

    def sanitize_name(self, name):
        """Reemplaza caracteres no permitidos en el nombre con guiones bajos y asegura que solo haya uno con ese nombre"""
        return name.replace("-", "_").replace(".", "_").replace("$", "")

    def sanitize_type_data(self, type_data):
        if type_data in ['array']: ## modificar para que en array se guarde un estado diferente a tener en cuenta => cardinality
            self.is_cardinality = True ## Etiqueta para saber que hay que agregar cardinality [1..*]
            type_data = 'Boolean'
        elif type_data in ['Object', 'object']: ## Boolean por defecto
            type_data = 'Boolean'
            self.is_cardinality = True ## Por si falla el else del properties ## Ajuste para que en object se genere un cardinality...
        elif type_data in ['number', 'Number']:
            type_data = 'Integer'
            #self.is_cardinality = True ## Por si falla el else del properties // No deberia de marcarse el type:number como cardinality
        elif type_data == 'Boolean':
            type_data = ''
        return type_data

    def resolve_reference(self, ref):
        """Resuelve una referencia a su esquema real dentro de las definiciones."""
        if ref in self.resolved_references: # Se comprueba si la referencia ya ha sido resuelta
            return self.resolved_references[ref]

        parts = ref.strip('#/').split('/') # Se divide la referencia en partes
        schema = self.definitions

        try: # Se añade el try para tratar de tener más control sobre la posible omisión de referencias
            for part in parts: # Se recorren las partes de la referencia para encontrar el esquema
                schema = schema.get(part, {})
                if not schema:
                    print(f"Warning: No se pudo resolver la siguiente referencia: {ref}") # Se usa para comprobar si hay alguna referencia que se pierde y no se procesa
                    return None

            self.resolved_references[ref] = schema
            return schema
        except Exception as e:
            print("Error al resolver la referencia: {ref}: {e}")
            return None

    def is_valid_description(self, feature_name, description):
        """Verifica si una descripción es válida (No muy corta y sin repeticiones) para analizarla después en busca de restricciones"""
        if len(description) < 10:
            print(description)
            return False
        # Crear una clave única combinando el nombre del feature y la descripción
        description_key = f"{feature_name}:{description}"
        if description_key in self.seen_descriptions:
            return False
        self.seen_descriptions.add(description_key)
        return True

    def is_required_based_on_description(self, description):
        """Determina si una propiedad es obligatoria basándose en si aparece Required al final de su descripción"""
        return description.strip().endswith("Required.")

    def extract_values(self, description):
        """Extrae valores que están entre comillas u otros delimitadores, solo si se encuentran ciertas palabras clave"""
        palabras_patrones_minus = ['values are', 'following states', '. must be', 'implicitly inferred to be', 'the currently supported reasons are', '. can be', 'it can be in any of following states',
                                   'valid options are', 'a value of `', 'the supported types are', 'valid operators are', 'status of the condition,', 'status of the condition.',
                                    'type of the condition.', 'status of the condition (', 'node address type', 'should be one of', 'will be one of', 'means that requests that', 'only valid values',
                                    'a volume should be', 'the metric type is', 'valid policies are'] ## , 'condition. known conditions are' # Probando para añadir 2 en vez de solo 1 descr
        ## . must be provoca muchas agregaciones de un solo valor ya que hay varias constraints que coinciden con esa expresion... definir mejor en un futuro si son necesarias los valores unitarios
        ## Patrones que se han quitado por 'repetitivos': , 'possible values are', , 'the currently supported values are', 'expected values are'
        palabras_patrones_may = ['Supports', 'Type of job condition', 'Status of the condition for', 'Type of condition', '. One of', 'Host Caching mode', 'This may be set to', 'Supported values:',
                                'completions are tracked. It can be', 'Services can be', 'this API group are'] ## 'values are', ## Type pendiente de sumar Healthy
        
        if not any(keyword in description.lower() for keyword in palabras_patrones_minus) and not any(keyword in description for keyword in palabras_patrones_may): # , '. Must be' , 'allowed valures are'
            return None
        #if 'onPodConditions, but not both,' in description.lower(): ### Por si hace falta evitar alguna descripcion mas especifica
        #    return None
        #if not any (keyword in description for keyword in palabras_patrones_may):
        #    return None ### Se deberia de hacer lista de valores tambien? status of the condition, 07/11 - mayoria de valores, True, False, Unknown. | condition. Known conditions are: patron para agregar una descrip y obtener sus valores(se busca 1 solo)
        
        value_patterns = [

            # Captura valores entre comillas escapadas o no escapadas
            re.compile(r'\\?["\'](.*?)\\?["\']'), #### Aparte de los que habian de antes, captura A value of `\"Exempt\"`...

            #re.compile(r'-\s*([\w]+(?:Resize\w+)):'), ## Patron para los guiones y doble punto al final.
            #re.compile(r'\\?["\'](.*?)\\?["\']'),  # Captura valores entre comillas simples o dobles, escapadas o no
            
            #re.compile(r'-\s*[\'"]?([\w\s]+)[\'"]?\s*:'),  ### Antiguo patron usado pero cogia valores numericos y raros como https, 6335 ** No usado
            re.compile(r'-\s*[\'"]?([a-zA-Z/.\s]+[a-zA-Z])[\'"]?\s*:', re.IGNORECASE), # Patron que coge los valores precedidos con un guion y que terminan con dos puntos: #### Expresion que tiene que se modifica en un futuro para evitar capturar "prefixed_keys" (coge frases largas sin que se muestren pero...)
            
            re.compile(r'(?<=Valid values are:)[\s\S]*?(?=\.)'),
            re.compile(r'(?<=Possible values are:)[\s\S]*?(?=\.)'),
            re.compile(r'(?<=Allowed values are)[\s\S]*?(?=\.|\s+Required)', re.IGNORECASE),
            #re.compile(r'(?<=Allowed values are)[`\'"]?([a-zA-Z]+)[`\'"]?(?:\s*,?\s*[`\'"]?([a-zA-Z]+)[`\'"]?)*\s*(?=\.|\s+Required)', re.IGNORECASE),

            re.compile(r'\b(UDP.*?SCTP)\b'),
            re.compile(r'\n\s*-\s+(\w+)\s*\n', re.IGNORECASE), ## caso suelto Infeasible, Pending...
            #re.compile(r'\n\s*-\s+([A-Za-z]+)\s*\n', re.IGNORECASE), ## caso suelto Infeasible, Pending...
            re.compile(r'\b(Localhost|RuntimeDefault|Unconfined)\b'), ### Valid options are:
            ###re.compile(r'(?<=Valid options are:)*?(\b[a-zA-Z]+\b)\s*-\s', re.IGNORECASE),
            #re.compile(r'(?:\n\s*)?([a-zA-Z]+)\s*-\s'),
            re.compile(r'\b(Retain|Delete|Recycle)\b'), ## Prueba añadir valores persistentVolumeReclaimPolicy, quizas general pero no afecta ahora mismo a otros valores con descripciones. Modificado a que tenga en cuenta las mayus
            re.compile(r'(?<=The currently supported values are\s)([a-zA-Z\s,]+)(?=\.)', re.IGNORECASE),
            #re.compile(r'(?<=The currently supported values are)[\w\s](?=\.)'),

            re.compile(r'(?<=Valid operators are\s)([A-Za-z\s,]+)(?=\.)', re.IGNORECASE),
            re.compile(r'\b(Gt|Lt)\b'),
            ###re.compile(r'(?<=Valid operators are\s)([A-Za-z\s,]+(?:,\s)?(?:Gt,\sand\sLt)?)(?=\.)', re.IGNORECASE), ## Expresion para añadir los valores de "Valid operators are" en operator

            re.compile(r'(?<=Acceptable values are:)([A-Za-z\s,]+)(?=\()'), ### Grupo para añadir los valores de "Acceptable values are:"
            
            re.compile(r'(?<=status of the condition, one of\s)([a-zA-Z\s,]+)(?=\.)', re.IGNORECASE), ## True, False, Unknown, expr: 'status of the condition,'
            re.compile(r'(?<=Type of job condition,\s)([a-zA-Z\s,]+)(?=\.)'), ## Complete or Failed, expr: 'Type of job condition'
            ### status of the condition. Can be (7)
            re.compile(r'(?<=status of the condition. Can be\s)([a-zA-Z\s,]+)(?=\.)'), ## Variante del anterior patron: Can be True, False, Unknown.. expr arriba: 'status of the condition.'
            ### Valid value: \"Healthy\" he omitido el resultado de valores con 1 solo valor pero este si define que solo tiene una posible opcion...
            re.compile(r'(?<=Types include\s)([a-zA-Z\s,]+)(?=\.)'), ## Patron para una unica descripcion: Established, NamesAccepted and Terminating 'type of the condition.' (2)
            
            re.compile(r'(?<=status of the condition \()([a-zA-Z\s,]+)(?=\))'), ## caso unico de valores (1 descr): (True, False, Unknown), expr: 'status of the condition (' (1)
            re.compile(r'(?<=Node address type, one of\s)([a-zA-Z\s,]+)(?=\.)'), ## Patron para una  descripcion: Hostname, ExternalIP or InternalIP 'node address type' (1)
            re.compile(r'(?<=. One of\s)([a-zA-Z\s,]+)(?=\.)'), ## Patron para una  descripcion: [Always, Never, IfNotPresent], Never, PreemptLowerPriority, [Always, OnFailure, Never], \"Success\" or \"Failure\" '. One of' (6)
            re.compile(r'(?<=Host Caching mode:\s)([a-zA-Z\s,]+)(?=\.)'),
            re.compile(r'(?<=Supported values:\s)([a-zA-Z\s,]+)(?=\.)'), # Supported values: cpu, memory. (87,87)
            
            re.compile(r'\b(Shared|Dedicated|Managed)\b'),
            re.compile(r'(?<=a volume should be\s)([a-zA-Z\s,]+)(?=\.)'), ## for a volume should be ThickProvisioned or ThinProvisioned. (38,38)
            re.compile(r'\b(NonIndexed|Indexed)\b'), # completions are tracked. It can be `NonIndexed` (default) or `Indexed`. (7,7) ## re.compile(r'are tracked\.\s*It can be\s*`([^`]*)`')
                    
            re.compile(r'(?<=the metric type is\s)([a-zA-Z\s,]+)'), ## the metric type is Utilization, Value, or AverageValue", (26,26,26)
            # 
            re.compile(r'(?<=Valid policies are\s)([a-zA-Z\s,]+)(?=\.)') ## Valid policies are IfHealthyBudget and AlwaysAllow. (3,3)

            ## Otros valores agregados por el regex general: Services can be (3,3,3)
            #re.compile(r'(?<=It can be\s)`([a-zA-Z\s,]+)`(?=\.)'),
            # Valid policies are
            #re.compile(r'(?<=kind expected values are\s)([A-Za-z]+)(?=[:,]|$)'),

            ## Host Caching mode
            ## Expresiones agregadas directamente por patrones genericos "[$value]":... 'should be one of', 'will be one of': \"ContainerResource\", \"External\", \"Object\", \"Pods\" or \"Resource\", 'only valid values': 'Apply' and 'Update'
            ##. One of
            ## Node address type, one of 
            ## status of the condition (
            ## Types include
        ]

        values = []
        #add_quotes = False  # Variable para verificar si se necesita añadir comillas
        default_value = self.patterns_process_enum_values_default(description)
        for pattern in value_patterns:

            matches = pattern.findall(description)
            #if matches:
            #    print(f"LOS PRIMEROS MATCHES ENTEROS {matches}")

            for match in matches:
                #print(f"VALORES EXPLORADOS / OBTENIDOS: {match}")  # Debug: Ver los valores separados
                #split_values = re.split(r',\s*|\n', match)
                split_values = re.split(r',\s*|\s+or\s+|\sor|or\s|\s+and\s+|and\s', match)  # Asegurarse de que "or" esté rodeado de espacios ### or\s: soluciona quitar el or en STCP.
                #print(f"Split Values: {split_values}")  # Debug: Ver los valores separados
                for v in split_values:
                    v = v.strip()
                    v = v.replace('*', 'estrella') # Reemplazar '*' por "estrella"
                    v = v.replace('"', '').replace("'", '').replace('`','')  # Elimina comillas dobles, simples y cerradas
                    #print("VALOR ANTES",v)
                    
                    v = v.replace(' ', '_').replace('/', '_')
                    #print("VALOR DESPUES", v)
                    #v = v.replace('/', '_')

                    # Filtrar valores que contienen puntos, corchetes, llaves o que son demasiado largos
                    if v and len(v) <= 24 and not any(char in v for char in {'.', '{', '}', '[', ']',';', ':', 'prefixed_keys'}): # añadido / por problemas con la sintaxis 'yet', ## Agregado prefixed_keys, handled para eliminarlo, no son valores
                        if len(v) >= 20 and '_' in v:                                               #### , 'handled', 'cluster'
                        # Excluir valores con guion bajo y tamaño >= 20
                            print(f"Excluyendo valor: {v}")
                        else:
                        # Agregar el valor si no tiene guion bajo o si es menor a 20 caracteres
                            if v == default_value:
                                v = f"{v} {{default}}"
                            values.append(v)
                        #if ' ' in v:  # Si un valor contiene un espacio, Era para añadir comillas dobles "", => sintaxis
                        #    add_quotes = True
        case_not_none = ['NodePort', f"ClusterIP {{default}}", 'None', 'LoadBalancer', 'ExternalName'] ## Lista donde se agregaba None y no formaba parte del conjunto posible de valores
        case_not_policies = {'IfHealthyBudget', 'AlwaysAllow', 'Ready', 'True', 'Running'} ## Conjunto para evitar definir otra lista y usar set(). Comprobar si falla algo
        case_not_none = set(case_not_none) # Obtener lista sin tener en cuenta el orden
        values = set(values)  # Eliminar duplicados

        if not values or len(values) == 1:
            return None ## valores de tamaño 1 {values}
        
        if case_not_none == values: ## Se busca omitir "_type_None" en el modelo
            values.remove('None')
        elif case_not_policies == values: ## Si hay mas casos generalizar la funcionalidad a una auxiliar con los parametros
            list_policies_to_delete = {'Ready', 'True', 'Running'} ## Conjunto de elementos a borrar de los valores. Se añaden por el regex general "/"/
            values = case_not_policies - list_policies_to_delete
            #for not_policies in list_policies_to_delete:
            #    values.remove({not_policies})

        return values #, add_quotes  # Devuelve los valores y el nombre del feature

    def patterns_process_enum_values_default(self, description):
 
        patterns_default_values = ['defaults to', '. implicitly inferred to be', 'the currently supported reasons are', '. default is'] # 'Defaults to', al comprobar luego con minus en mayuscula no cuenta
        
        if not any(keyword in description.lower() for keyword in patterns_default_values):
            return None
        default_value = ""
        
        default_patterns = [  
            #re.compile(r'(?<=Defaults to\s)(["\']?[\w\s\.\-"\']+["\']?)'),  # Captura con "Defaults to"
            #re.compile(r'(?<=defaults to\s)(["\']?[\w\s\.\-"\']+["\']?)', re.IGNORECASE), ## No tiene en cuenta si es mayus o minis
            re.compile(r'(?<=defaults to\s)(["\']?[\w\s\.\-"\']+?)(?=\.)', re.IGNORECASE),  # Detener captura en el punto literal 
            re.compile(r'(?<=Defaults to\s)(["\']?[\w\s\.\-"\']+["\']?)'), 
            #re.compile(r'(?<=Implicitly inferred to be\s)(["\']?[\w\s\.\-"\']+["\']?)', re.IGNORECASE),
            #re.compile(r'(?<=Implicitly inferred to be\s)["\'](.*?)\\?["\']', re.IGNORECASE), 
            re.compile(r'Implicitly inferred to be\s["\'](.*?)["\']', re.IGNORECASE),
            re.compile(r'default to use\s["\'](.*?)["\'](?=\.)', re.IGNORECASE), #
            re.compile(r'\. Default is\s["\']?(.*?)["\']?(?=\.)', re.IGNORECASE),
            #default to use

            #Implicitly inferred to be
        ]
        
        for pattern in default_patterns:
            matches = pattern.findall(description)
            for match in matches:
                #if len(match) > 30:
                #    split_value = match.split('.')[0]
                    #value = split_value[0]
                #if not 'ext4' in match:
                #    print("PALABRAS COGIDAS: ", match)
                first_part = match.split('.')[0]  # Solo tomamos lo que está antes del primer punto
                v = first_part.strip().replace('"', '').replace("'", '').replace('.', '').strip()
                #if not 'ext4' in v:
                #    print("PALABRAS YA PROCESADAS: ", v)
                if v == '*': ## caso en el que el valor por defecto es "*" y no se puede representar ese caracter: se cambia por "estrella"
                    v = 'estrella'
                # Aplicar restricciones: longitud y tipo de valor
                if v and len(v) <= 50 : #and (v.isalpha() or v.isdigit() or v in {"true", "false", "null", "0", "1"})
                    #default_value.append(v)
                    default_value = v
                    #print("VALOR AÑADIDO: ",default_value)
        if not default_value:
            #print("Valores que no son por defecto ",default_value)
            return None
        #print("Estos son los valores:: ",default_value)
        
        return default_value

    def contains_non_ascii(self, text): ##Busqueda de caracteres ascii en las doc
        non_ascii_chars = {c for c in text if ord(c) > 127}  # Busca caracteres > 127
        special_chars = {'\r', '\n'}  # Lista de caracteres específicos a detectar

        found_specials = {c for c in text if c in special_chars}  # Detecta \r y \n

        return non_ascii_chars, found_specials

    def categorize_description(self, description, feature_name, type_data):
        """Categoriza la descripción según los patrones predefinidos."""
        
        if not self.is_valid_description(description, feature_name):
            return False
        
        # Verificar si el feature_name tiene configuración especial y ajustar type_data
        #if any(special_name in feature_name for special_name in self.special_features_config) and ('Note that this field cannot be set when' in description or 'Exactly one of' in description):
        #    type_data = 'Boolean' ## Descripciones unicamente
    
            #if special_name in feature_name:

        if type_data == '':
            type_data = 'Boolean'
        
        #if ' {default ' in feature_name: ### Parte añadida para evitar que se agregue el {default X} como parte del nombre en la descripcion y mantener el original (Mantener formato por las comprobaciones de nombres)
            #    feature_name = re.sub(r'\s*\{default\s\d+\}', '', feature_name)
        feature_name_descriptions = ""
        if "cardinality" in feature_name:
            feature_name_descriptions = feature_name.split(" cardinality")[0]
        elif "{" in feature_name:
            feature_name_descriptions = feature_name.split(" {")[0]
        else:
            feature_name_descriptions = feature_name

        # Entrada de descripción con datos del tipo para mejorar la precisión de las reglas
        description_entry = {
        "feature_name": feature_name_descriptions,
        "description": description,
        "type_data":type_data  # Adición tipo para tener el tipo de dato para las restricciones ### 'Boolean' 
    }
        for category, pattern in self.patterns.items():
            if pattern.search(description):
                #self.descriptions[category].append((feature_name, description))
                self.descriptions[category].append((description_entry))
                return True
        
        return False

    def clean_description(description): ## Funcion para eliminar caracteres no válidos en la doc y en el analisis de flamapy
        # Eliminar puntos y otros caracteres innecesarios ## PENDIENTE SUSTITUIS POR LOS REPLACE DE CADA DESCRIPCION
        cleaned_description = description.replace('\n', '').replace('`', '').replace("´", '') \
                                        .replace("'", "_").replace('{', '').replace('}', '') \
                                        .replace('"', '').replace("\\", "_").replace(".", "").replace("//","_") ## replace("\\", "_").replace(".", "") //
        return cleaned_description

    """ Tratamiendo de tipos de propiedades, oneOf y enum"""
    def process_oneOf(self, oneOf, full_name, type_feature):
        """
        Procesa la estructura 'oneOf' y genera subcaracterísticas basadas en los tipos de datos posibles que tiene para seleccionar una de los 2.
        """

        feature = {
            'name': full_name,
            'type': type_feature,  # Lo ponemos como 'optional' ya que puede ser uno de varios tipos 'optional'
            'description': f"Feature based on oneOf in {full_name}",    
            'sub_features': [],
            'type_data': 'Boolean'  # Aquí definimos el tipo (por ejemplo: String, Number) ## Omitir Bool
        }
        # Procesar cada opción dentro de 'oneOf'
        for option in oneOf:
            if 'type' in option: # 'type' in option:
                option_type_data = option['type'].capitalize()  # Captura el tipo (por ejemplo: string, number, integer)
                sanitized_name = full_name.replace(" cardinality [1..*]", "") ## Adicion para quitar el cardinality de la herencia del nombre

                if ' {default ' in sanitized_name: ### Parte añadida para evitar que se agregue el {default X} como parte del nombre para algunos sub-features generando un error: feature_name_{default X}_asType
                    sanitized_name = re.sub(r'\s*\{.*?\}', '', sanitized_name) # Se borra todo el contenido dentro de los corchetes y el espacio ## sanitized_name = re.sub(r'\s*\{default\s\d+\}', '', sanitized_name)
                # Crear subfeature con el nombre adecuado
                aux_description_sub_feature = f"Sub-feature added of type {option_type_data}"

                sub_feature = {
                    'name': f"{sanitized_name}_as{option_type_data} {{doc '{aux_description_sub_feature}'}}", ##  ## quizas mas adelante definir una descr personalizada para el sub_feature
                    'type': 'alternative',  # Por defecto, se añade como alternative
                    'description': aux_description_sub_feature,
                    'sub_features': [],
                    'type_data': self.sanitize_type_data(option_type_data)
                }

                # Añadir la subfeature a la lista de sub_features del feature principal
                feature['sub_features'].append(sub_feature)

        return feature
    
    def process_enum_defaultInte(self, property, full_name, description): ## AGREGAR modificaciones default false, true
        """ Agrega en el nombre del feature el valor por defecto que tiene. Comprueba si el feature tiene la caracteristica enum y añade el contenido de este al valor por defecto"""
        patterns_default_values_numbers = ['defaults to', 'default value is', 'default to', 'default false', 'Default is false', 'is \"false', 'is \"true'] # Grupo alternativo al anterior para definir los patrones que tienen Integers por defecto o grupos similares
        default_integer = 0
        default_bool = False
        #cleaned_description = description.replace('\n', '').replace('`', '').replace("´", '').replace("'", "_")
        default_full_name = ''
        if 'enum' in property and property['enum']:
            #default_name = property.get('enum',[])
            #default_full = default_name[0]
            cleaned_description = description.replace('\n', '').replace('`', '').replace("´", '').replace("'", "_").replace('{','').replace('}','').replace('"', '').replace("\\", "_").replace(".", "").replace("//","_") ## Saneamiento de las descripciones con los caracteres que causan conflicto y errores en el formato uvls
            cleaned_description = ''.join(c for c in cleaned_description if ord(c) < 128)

            default_value = property['enum'][0]
            default_full_name = f"{full_name} {{default '{default_value}', doc '{cleaned_description}'}}"
            default_bool = True
            #print("VALOR EN EL METODO",default_full_name)
            #property['name'] = default_full_name # Opcion de pasar el parametro modificado del property
            return default_full_name, default_bool

            #print("Estos son los valores:: ",default_value)
        if any(keyword in description.lower() for keyword in patterns_default_values_numbers):
            default_patterns = [
                re.compile(r'(?<=Defaults to\s)(\d+)(?=\D|$)', re.IGNORECASE), # (\d+)[\s\.] ## omite el 600s de progressDeadlineSeconds / pendiente (\d+)(?=\D|$) / --Hecho probando con re.IGNORECASE
                re.compile(r'(?<=Default value is\s)(\d+)(?=\D|$)', re.IGNORECASE),
                re.compile(r'(?<=Default to\s)(\d+)(?=\D|$)'), # (\d+)[\s\.] ## Prueba insercion mas default.. agregados agregados 250 default 10 y varios... 0 => 20
                #re.compile(r'Defaults to (\d+)', re.IGNORECASE), ## probar cual es mejor default value is 1 ## agregado casos donde no se tenia en cuenta el default minus
                re.compile(r'(?<=Default to\s)([\w\s\.])(?=\.)'), ## *** PENDIENTE: definiendo el patron para capturar los true/false*** # Detener captura en el punto literal  (["\']?[\w\s\.\-"\']+?)
                #re.compile(r'(?<=default to\s)([\w\s\.])(?=\.)', re.IGNORECASE), ## *** PENDIENTE: definiendo el patron para capturar los true/false*** # Detener captura en el punto literal  (["\']?[\w\s\.\-"\']+?)
                ## Default is \"*\". (7) para añadir mas default normales
            ]
            cleaned_description = description.replace('\n', '').replace('`', '').replace("´", '').replace("'", "_").replace('{','').replace('}','').replace('"', '').replace("\\", "_").replace(".", "").replace("//","_") ## Saneamiento de las descripciones con los caracteres que causan conflicto y errores en el formato uvls
            cleaned_description = ''.join(c for c in cleaned_description if ord(c) < 128)

            for pattern in default_patterns:
                matches = pattern.search(description)
                if matches:
                    default = matches.group(1)
                    #print("MATCH ENCONTRADO",default)  ["\'](.*?)\\?["\']
                    if 'true' == default or 'false' == default:
                        print(f"BOOLEANOS ENCONTRADOS {default}")
                    default_integer = default
                    if default_integer == '0644':
                        default_integer = 644
                    #default_full_name = f"{full_name} {{default {default_integer}}}"
                    default_full_name = f"{full_name} {{default {default_integer}, doc '{cleaned_description}'}}"
                    default_bool = True
                    #return default_full_name, default_bool
            
            pattern_defaults = re.compile(r'Default is\s+\\?"(true|false)\\?"') ## Patron para el default is con comillas escapadas en las descripciones 
            match = pattern_defaults.search(description)

            if match: ## Si coincide se agrega tambien en los features coincidentes Default is \"true\" y Default is \"false\".
                default_boolean = match.group(1)
                default_bool = True
                default_full_name = f"{full_name} {{default {default_boolean}, doc '{cleaned_description}'}}"
                #print(f"EL PATRON Y LA DESCRIPCION SON {description}: {match} \n {cleaned_description}")

            if 'Default to false' in description or 'defaults to false' in description.lower() or 'default false' in description.lower() or 'Default is false' in description:
                default_bool = True
                if 'defaults to false' in description.lower() and "deprecated." in description.lower(): ## Caso especifico donde tenia un default y es deprecated
                    default_full_name = f"{full_name} {{default false, deprecated, doc '{cleaned_description}'}}"
                else:    
                    default_full_name = f"{full_name} {{default false, doc '{cleaned_description}'}}"
                #if '\"is false"' in description:
                #    print(cleaned_description)
            elif 'Default to true' in description or 'defaults to true' in description.lower(): ## or 'Default is \"t' in description deprecated. 
                default_bool = True
                default_full_name = f"{full_name} {{default true, doc '{cleaned_description}'}}"

            if default_full_name != '':
                return default_full_name, default_bool
                
        return full_name, default_bool

    def update_type_data(self, full_name, feature_type_data, description): ## sino probar con full_name
    # Cambia el tipo de dato a 'Boolean' si el nombre del feature o sub_feature contiene algún fragmento en boolean_keywords
        abstract_bool = False
        self.feature_aux_original_type = ''

        if any(keyword in full_name for keyword in self.boolean_keywords) and not full_name.endswith('nameStr') and not full_name.endswith('valueInt'): ### and not full_name.endswith('StringValue') ## De momento no se comprobo que hiciese falta (todos son string)
            self.feature_aux_original_type = feature_type_data
            ## io_k8s_api_core_v1_PodSecurityContext_seccompProfile
            #print ("Tipo de dato original: ", self.feature_aux_original_type)
            feature_type_data = 'Boolean'
            #full_name = f"{full_name} {{abstract}}"
            abstract_bool = True

        ## Adición de una comprobación necesaria para el uso de las adiciones String/integer correctamente
        if any(special_name in full_name for special_name in self.special_features_config) and 'Note that this field cannot be set when' in description and not full_name.endswith('nameStr') and not full_name.endswith('valueInt'):
            self.feature_aux_original_type = feature_type_data ## Se aplica una logica similar al primer if para guardar el aux y luego comprobar si es distinto de bool 
            #print ("Tipo de dato original en SPECIAL List: ", self.feature_aux_original_type)
            feature_type_data = 'Boolean'
            if self.feature_aux_original_type != 'boolean' and self.feature_aux_original_type != feature_type_data and self.feature_aux_original_type != '': ## hay tipos que son vacios y luego se definen por defecto como bool
                abstract_bool = True
            ## Por siacaso que no afecte tampoco a StringValue
            #    print(f"EL TIPO DE DATO DEL AUXILIAR ES: {self.feature_aux_original_type}")

        # Verificar coincidencias con expresiones regulares
        for pattern in self.boolean_keywords_regex:
            if re.search(pattern, full_name) and not full_name.endswith('nameStr') and not full_name.endswith('valueInt'): ## Para mantener el tipo original del feature
                self.feature_aux_original_type = feature_type_data
                feature_type_data = 'Boolean'
                abstract_bool = True
                #print("LOS TIPOS DEL REGEX SON",self.feature_aux_original_type)

                #print(f"Coincidencia de expresión regular encontrada: {full_name}")
        if full_name == 'io_k8s_api_core_v1_PodSecurityContext_seccompProfile':
            print(f"PRUEBA FINAL DE CON QUE SALE DE CARA A VALUES {self.feature_aux_original_type}")    
        return feature_type_data, abstract_bool
                

    def parse_properties(self, properties, required, parent_name="", depth=0, local_stack_refs=None):
        if local_stack_refs is None:
            local_stack_refs = []  # Crear una nueva lista para esta rama

        mandatory_features = [] # Grupo de propiedades obligatorias
        optional_features = [] # Grupo de propiedades opcionales
        abstract_bool = False ## Propiedad que define si un feature es abstracto o no
        
        queue = deque([(properties, required, parent_name, depth)])

        while queue:
            current_properties, current_required, current_parent, current_depth = queue.popleft()
            #self.is_cardinality = False

            for prop, details in current_properties.items():
                sanitized_name = self.sanitize_name(prop)
                full_name = f"{current_parent}_{sanitized_name}" if current_parent else sanitized_name

                if full_name in self.processed_features:
                    continue

                self.is_cardinality = False ## SE INICIE CON FALSE : se delimita en los tipos
                self.is_deprecated = False
                bool_added_value = False ## Added para tratar de evitar duplicacion de alternative y mandatory, values y stringValue
                # Verificar si la propiedad es requerida basado en su descripción
                description = details.get('description', '')
                is_required_by_description = self.is_required_based_on_description(description)
                feature_type = 'mandatory' if prop in current_required or is_required_by_description else 'optional'
                # Parseo de los tipos de datos y de los no válidos
                feature_type_data = details.get('type', 'Boolean')
                feature_type_data = self.sanitize_type_data(feature_type_data) 
                # *** Aquí llamamos a process_enum para modificar el nombre si tiene un enum ***
                full_name, default_bool = self.process_enum_defaultInte(details, full_name, description) ## Modificacion del name para añadir default Integer
                #full_name = self.patterns_process_enum(description, full_name) ##PROBANDO

                if self.is_cardinality and 'cardinality' in full_name: ## Bloque de condiciones para agregar el cardinality a los features de tipo array y marcarlos o desmarcarlos para eliminar la etiqueta
                    full_name = full_name.replace(" cardinality [1..*]", "")
                    if 'unstructured key value map' in description:
                        full_name = f"{full_name} cardinality [0..*]"
                    else:
                        full_name = f"{full_name} cardinality [1..*]"
                elif self.is_cardinality and not 'cardinality' in full_name:
                    if 'unstructured key value map' in description:
                        full_name = f"{full_name} cardinality [0..*]"
                    else:
                        full_name = f"{full_name} cardinality [1..*]"
                else:
                    self.is_cardinality = False ## Para evitar casos en que se mantenga el cardinality del anterior feature
                    full_name = full_name.replace(" cardinality [1..*]", "")
                    full_name = full_name.replace(" cardinality [0..*]", "")

                #description = details.get('description', '')
                if description:
                    feature_type_data, abstract_bool = self.update_type_data(full_name, feature_type_data, description) ### Modificion para que en descriptions_01.json se cambie de String a Boolean si coincide con el nombre
                    self.categorize_description(description, full_name, feature_type_data) # categorized = 
                    cleaned_description = description.replace('\n', '').replace('`', '').replace("´", '').replace("'", "_").replace('{','').replace('}','').replace('"', '').replace("\\", "_").replace(".", "").replace("//","_") ## Saneamiento de las descripciones con los caracteres que causan conflicto y errores en el formato uvl
                    cleaned_description = ''.join(c for c in cleaned_description if ord(c) < 128)

                    #contains_non_ascii(cleaned_description) ## Ejecucion prueba
                    # Comprobar caracteres no ASCII y específicos
                    #text = "Ejemplo con ñ, á, é, í, ó, ú y saltos de línea.\nOtro más.\r"
                    non_ascii, specials = self.contains_non_ascii(cleaned_description)
                    # Mostrar resultados
                    if non_ascii or specials:
                        print(f"Caracteres no ASCII encontrados: {non_ascii}")
                        print(f"Caracteres especiales encontrados: {specials}")
                        # Ejemplo de texto con caracteres especiales
                    res = bool(re.match(r'^[\x00-\x7F]*$', cleaned_description))
                    if not res:
                        print(f"Caracteres no ASCII encontrados: {cleaned_description}")
                        print(str(res))

                    if "DEPRECATED:" in cleaned_description or "deprecated." in cleaned_description.lower() or "This field is deprecated," in cleaned_description or "deprecated field" in cleaned_description:
                        self.is_deprecated = True ## Probar si no altera algun otro etiquetado de los features
                        
                    if not default_bool and not abstract_bool and not self.is_deprecated: # Condición agregada para agregar el atributo doc a features que no sean default ni abstract
                        full_name = f"{full_name} {{doc '{cleaned_description}'}}"
                        self.is_deprecated = False
                    elif self.is_deprecated and not default_bool:
                        full_name = f"{full_name} {{deprecated, doc '{cleaned_description}'}}"
                        self.is_deprecated = False
                #else:
                    #print(f"No hay descripcion para la propiedad y feature: {sanitized_name} {full_name}")
                    #cleaned_description = "Auto doc generate for not put empty Strings No descripcion in schemas JSON"

                feature = {                  
                    'name': full_name if not abstract_bool else f"{full_name} {{abstract, doc '{cleaned_description}'}}", ## Añadir {abstract} a los features creados para tener mejor definición de las constraints
                    'type': feature_type,
                    'description': description,
                    'sub_features': [],
                    'type_data': '' if feature_type_data == 'Boolean' else feature_type_data ## String ##
                }
                #countArrays = countArrays + countLocal
                #print(f"El numero de arrays es: {countArrays}")
                full_name = re.sub(r'\s*\{.*?\}', '', full_name)
                # Procesar referencias
                # Extraer y añadir valores como subfeatures
                extracted_values = self.extract_values(description)
                bool_added_value = bool(extracted_values)

                if '$ref' in details:
                    ref = details['$ref']
                    # boolonOf = False # Prueba omision de refs con oneOf

                    # Verificar si ya está en la pila local de la rama actual (es decir, un ciclo)
                    if ref in local_stack_refs:
                        #print(f"*****Referencia cíclica detectada: {ref}. Saltando esta propiedad****")
                        # Si es un ciclo, saltamos esta propiedad pero seguimos procesando otras
                        continue
                    
                    # Añadir la referencia a la pila local
                    local_stack_refs.append(ref)
                    ref_schema = self.resolve_reference(ref)

                    if ref_schema:
                        ## Lineas no necesarias en esta implementacion: se usarian en omision de las refs (V_1.0)
                        ref_name = self.sanitize_name(ref.split('/')[-1])
                        #self.constraints.append(f"{full_name} => {ref_name}")
                        #feature_type = 'mandatory' ## feature_type principal del feature

                        if 'properties' in ref_schema:
                            sub_properties = ref_schema['properties']
                            sub_required = ref_schema.get('required', [])
                            # Llamada recursiva con la pila local específica de esta rama
                            sub_mandatory, sub_optional = self.parse_properties(sub_properties, sub_required, full_name, current_depth + 1, local_stack_refs)
                            # Añadir subfeatures
                            feature['sub_features'].extend(sub_mandatory + sub_optional)

                            ## Adicion de propiedades que pueden ser null/empty {}
                            if full_name.endswith('emptyDir') or full_name.endswith('EmptyDirVolumeSource'): ## Captura de las propiedades con "emptyDir" y el esquema principal "EmptyDirVolumeSource".
                                feature['sub_features'].append({ ## Adición en el último nivel de las referencias a los esquemas simples que no tinenen properties
                                'name': f"{full_name}_isEmpty {{doc 'Added option to select when emptyDir is empty declared {{}} '}}", # RefName Aparte {full_name}_{ref_name}: Nombre de los esquemas simples indexados para mantener referencias a estos esquemas
                                'type': 'optional', #mandatory, al ser referencias a esquemas simple no se tiene un type. Por defecto se deja mandatory pero puede ser optional
                                'description': f"{{doc 'Added option to select when emptyDir is empty declared {{}} '}}", # ref_schema.get('description', ''),
                                'sub_features': [],
                                'type_data': '' # Se deja el tipo de dato que tenga el esquema simple ## Por defecto para la compatibilidad en los esquemas simples y la propiedad del feature
                            })


                        elif 'oneOf' in ref_schema:
                            feature_type = 'mandatory' if prop in current_required or is_required_by_description else 'optional'
                            oneOf_feature = self.process_oneOf(ref_schema['oneOf'], self.sanitize_name(f"{full_name}"), feature_type) #_{ref_oneOf}
                            feature_sub = oneOf_feature['sub_features']
                            # Agregar la referencia que contiene la caracteristica oneOf
                            feature['sub_features'].extend(feature_sub)

                        else:
                            # Si no hay 'properties', procesarlo como un tipo simple
                            # Determinar si la referencia es 'mandatory' u 'optional'
                            #feature_type = 'mandatory' if prop in current_required else 'optional'
                            sanitized_ref = self.sanitize_name(ref_name.split('_')[-1]) # ref_name = self.sanitize_name(ref.split('/')[-1])
                            # Agregar la referencia procesada como un tipo simple
                            aux_description_simples_schemas = ref_schema.get('description', '')
                            aux_description_simples_schemas_sanitized = aux_description_simples_schemas.replace('\n', '').replace('`', '').replace("´", '').replace("'", "_").replace('{','').replace('}','').replace('"', '').replace("\\", "_").replace(".", "").replace("//","_") ## Saneamiento de las descripciones con los caracteres que causan conflicto y errores en el formato uvl
                            aux_description_simples_schemas_sanitized = ''.join(c for c in aux_description_simples_schemas_sanitized if ord(c) < 128)

                            type_data_schemas_refs_simple = self.sanitize_type_data(ref_schema.get('type', ''))
                            feature['sub_features'].append({ ## Adición en el último nivel de las referencias a los esquemas simples que no tinenen properties
                                'name': f"{full_name}_{sanitized_ref} {{doc '{aux_description_simples_schemas_sanitized}'}}",  # RefName Aparte {full_name}_{ref_name}: Nombre de los esquemas simples indexados para mantener referencias a estos esquemas
                                'type': 'optional', #mandatory, al ser referencias a esquemas simple no se tiene un type. Por defecto se deja mandatory pero puede ser optional
                                'description': f"{aux_description_simples_schemas}", # ref_schema.get('description', ''),
                                'sub_features': [],
                                'type_data': type_data_schemas_refs_simple, # Se deja el tipo de dato que tenga el esquema simple ## Por defecto para la compatibilidad en los esquemas simples y la propiedad del feature
                            })
                            #print(f"Referencias simples detectadas: {ref}")
                            if full_name.endswith('creationTimestamp'): ## Adicion de una sub-property bool para "aceptar" los valores null de creation en el modelo
                                feature['sub_features'].append({ ## Adición en el último nivel de las referencias a los esquemas simples que no tinenen properties
                                'name': f"{full_name}_isNull {{doc 'Added option to select when creationTimestamp is empty declared: null'}}", # RefName Aparte {full_name}_{ref_name}: Nombre de los esquemas simples indexados para mantener referencias a estos esquemas
                                'type': 'optional',
                                'description': f"{{doc 'Added option to select when creationTimestamp is empty declared: null'}}",
                                'sub_features': [],
                                'type_data': '' 
                            })
                            elif full_name.endswith('fieldsV1'): ## Adicion de una sub-property bool para "aceptar" los valores empty en el modelo
                                feature['sub_features'].append({ ## Adición en el último nivel de las referencias a los esquemas simples que no tinenen properties
                                'name': f"{full_name}_isEmpty02 {{doc 'Added option to select when fieldsV1 is empty declared: {{}}'}}", # RefName Aparte {full_name}_{ref_name}: Nombre de los esquemas simples indexados para mantener referencias a estos esquemas
                                'type': 'optional', 
                                'description': f"{{doc 'Added option to select when fieldsV1 is empty declared: {{}}'}}", 
                                'sub_features': [],
                                'type_data': '' 
                            })                    
                    local_stack_refs.pop() # Eliminar la referencia de la pila  local al salir de esta rama

                # Procesar ítems en arreglos o propiedades adicionales
                elif 'items' in details:
                    items = details['items']
                    if '$ref' in items:
                        ref = items['$ref']
                        # Verificar si ya está en la pila local de la rama actual (es decir, un ciclo)
                        if ref in local_stack_refs:
                            #print(f"*****Referencia cíclica detectada en items: {ref}. Saltando esta propiedad****")
                            continue

                        # Añadir la referencia a la pila local
                        local_stack_refs.append(ref)
                        ref_schema = self.resolve_reference(ref)

                        if ref_schema:
                            ## Linea no necesaria en esta implementacion: se usarian en omision de las refs (V_1.0)
                            ref_name = self.sanitize_name(ref.split('/')[-1])
                            #self.constraints.append(f"{full_name} => {ref_name}")
                            #feature_type = 'mandatory'

                            if 'properties' in ref_schema:
                                #sub_item_properties = ref_schema['properties']
                                #sub_item_required = ref_schema.get('required', [])
                                #sub_mandatory, sub_optional = self.parse_properties(sub_properties, sub_required, full_name, current_depth + 1, local_stack_refs) ## Otra manera de hacerlo
                                item_mandatory, item_optional = self.parse_properties(ref_schema['properties'], ref_schema.get('required', []), full_name, current_depth + 1, local_stack_refs)
                                feature['sub_features'].extend(item_mandatory + item_optional)
                            else:
                                # Si no hay 'properties', procesarlo como un tipo simple
                                #feature_type = 'mandatory' if prop in current_required else 'optional' # Determinar si la referencia es 'mandatory' u 'optional'  #sanitized_ref = self.sanitize_name(ref_name.split('_')[-1]) # ref_name = self.sanitize_name(ref.split('/')[-1])
                                sanitized_ref = self.sanitize_name(ref_name.split('_')[-1]) # ref_name = self.sanitize_name(ref.split('/')[-1])
                                full_name = full_name.replace(" cardinality [1..*]", "") ## Agregado para omitir el cardinality cuando no corresponde...
                                #print(f"ITEMS SIMPLES REFS {full_name}_{sanitized_ref}") ## Comprobar Referencias simples
                                aux_description_items_schemas = ref_schema.get('description', '')
                                #print(aux_description_items_schemas)
                                aux_description_items_sanitized = aux_description_items_schemas.replace('\n', '').replace('`', '').replace("´", '').replace("'", "_").replace('{','').replace('}','').replace('"', '').replace("\\", "_").replace(".", "").replace("//","_") ## Saneamiento de las descripciones con los caracteres que causan conflicto y errores en el formato uvl
                                aux_description_items_sanitized = ''.join(c for c in aux_description_items_sanitized if ord(c) < 128)

                                # Agregar la referencia procesada como un tipo simple
                                feature['sub_features'].append({
                                    'name': f"{full_name}_{sanitized_ref} {{doc '{aux_description_items_sanitized}'}}", ## RefName Aparte {full_name}_{ref_name}
                                    'type': 'optional',  # Se deja como optional por defecto (Varia segun la interpretación que se le quiera dar)
                                    'description': aux_description_items_sanitized,
                                    'sub_features': [],
                                    'type_data': '' ## Por defecto para la compatibilidad en los esquemas simples y la propiedad del feature: Boolean
                                })
                        # Eliminar la referencia de la pila local al salir de esta rama
                        local_stack_refs.pop()
                    elif 'type' in items and self.is_cardinality: ## Adición para generar el nodo hoja con el tipo de dato que se referencia en items
                        #print("Deberia de aplicarse al tener un type en items")
                        type_data_items = items['type']
                        full_name = full_name.replace(" cardinality [1..*]", "") ## Agregado para omitir el cardinality cuando no corresponde...

                        if type_data_items == 'string' and not bool_added_value:
                            aux_description_string_items = f"Added String mandatory for complete structure Array in the model The modified is not in json but provide represents, Array of Strings: StringValue"
                            feature['sub_features'].append({
                                'name': f"{full_name}_StringValue {{doc '{aux_description_string_items}'}}", ## RefName Aparte {full_name}_{ref_name}
                                'type': 'mandatory',
                                'description': aux_description_string_items, #f"Added String mandatory for adding the structure Array in the model: StringValue",
                                'sub_features': [],
                                'type_data': 'String'
                            })
                        elif type_data_items == 'integer': ### Adicion vista en el mapeo de yamls a json con los features
                            #full_name = full_name.replace(" cardinality [1..*]", "") ## Agregado para omitir el cardinality cuando no corresponde...
                            aux_description_string_items = f"Added Integer mandatory for complete structure Array in the model The modified is not in json but provide represents, Array of Integers: IntegerValue"
                            feature['sub_features'].append({
                                'name': f"{full_name}_IntegerValue {{doc '{aux_description_string_items}'}}", ## RefName Aparte {full_name}_{ref_name}
                                'type': 'mandatory',
                                'description': aux_description_string_items, #f"Added String mandatory for adding the structure Array in the model: StringValue",
                                'sub_features': [],
                                'type_data': 'Integer'
                            })
                        else:
                            print("Tipo de dato en array no controlado. Exclusion de tipos, no compatibilidad.")
                # Procesar propiedades adicionales
                elif 'additionalProperties' in details:
                    additional_properties = details['additionalProperties']
                    if '$ref' in additional_properties:
                        ref = additional_properties['$ref']
                        
                        # Verificar si ya está en la pila local de la rama actual (es decir, un ciclo)
                        if ref in local_stack_refs:
                            #print(f"*****Referencia cíclica detectada en additionalProperties: {ref}. Saltando esta propiedad****")
                            continue

                        # Añadir la referencia a la pila local
                        local_stack_refs.append(ref)
                        ref_schema = self.resolve_reference(ref)

                        if ref_schema:
                            ## Linea no necesaria en esta implementacion: se usarian en omision de las refs (V_1.0)
                            ref_name = self.sanitize_name(ref.split('/')[-1]) 
                            #self.constraints.append(f"{full_name} => {ref_name}")
                            #feature_type = 'mandatory'

                            if 'properties' in ref_schema:
                                item_mandatory, item_optional = self.parse_properties(ref_schema['properties'], [], full_name, current_depth + 1, local_stack_refs)
                                # ref_schema.get('required', []) se añade solo 1 linea mas al modelo ==> 1 mandatory unicamente
                                feature['sub_features'].extend(item_mandatory + item_optional)
                            elif 'oneOf' in ref_schema:
                                #feature_type = 'mandatory' if prop in current_required or is_required_by_description else 'optional'
                                full_name = full_name.replace(" cardinality [1..*]", "")
                                oneOf_feature = self.process_oneOf(ref_schema['oneOf'], self.sanitize_name(f"{full_name}"), feature_type) #_{ref_oneOf}
                                feature_sub = oneOf_feature['sub_features']
                                # Agregar la referencia que contiene la caracteristica oneOf
                                feature['sub_features'].extend(feature_sub)
                            else:
                                # Si no hay 'properties', procesarlo como un tipo simple  #### Creo que aqui ocurre un paso del cardinality ** AJUSTAR
                                #feature_type = 'mandatory' if prop in current_required else 'optional' # Determinar si la referencia es 'mandatory' u 'optional'                                sanitized_ref = self.sanitize_name(ref_name.split('_')[-1]) # ref_name = self.sanitize_name(ref.split('/')[-1])

                                sanitized_ref = self.sanitize_name(ref_name.split('_')[-1]) # ref_name = self.sanitize_name(ref.split('/')[-1])
                                full_name = full_name.replace(" cardinality [1..*]", "") ## Agregado para omitir el cardinality cuando no corresponde...
                                #print(f"ADDIOTIONAL ITEMS SIMPLES REFS {full_name}_{sanitized_ref}")
                                aux_description_additional_schemas = ref_schema.get('description', '')
                                aux_description_additional_sanitized = aux_description_additional_schemas.replace('\n', '').replace('`', '').replace("´", '').replace("'", "_").replace('{','').replace('}','').replace('"', '').replace("\\", "_").replace(".", "").replace("//","_") ## Saneamiento de las descripciones con los caracteres que causan conflicto y errores en el formato uvl
                                aux_description_additional_sanitized  = ''.join(c for c in aux_description_additional_sanitized if ord(c) < 128)

                                # Agregar la referencia procesada como un tipo simple
                                feature['sub_features'].append({
                                    'name': f"{full_name}_{sanitized_ref} {{doc '{aux_description_additional_sanitized}'}}", ##  RefName Aparte {full_name}_{ref_name}
                                    'type': 'optional', ## Se deja como optional por defecto (Varia segun la interpretación que se le quiera dar)
                                    'description': aux_description_additional_schemas, # ref_schema.get('description', '')
                                    'sub_features': [],
                                    'type_data': '' ## Por defecto para la compatibilidad en los esquemas simples y la propiedad del feature: Boolean
                                })

                        # Eliminar la referencia de la pila local al salir de esta rama
                        local_stack_refs.pop()
                    ### PRUEBA PARA GENERAR EL ARRAY DENTRO DE ADDITIONAL E ITEMS
                    elif 'items' in additional_properties and self.is_cardinality: ## Adición para generar el nodo hoja con el tipo de dato que se referencia en items
                        #print("Deberia de aplicarse al tener un type en items")
                        items = additional_properties['items']
                        type_data_additional_items = items['type'] ## Tipo de dato items dentro de additionalProperties

                        if type_data_additional_items == 'string' and not bool_added_value:
                            full_name = full_name.replace(" cardinality [1..*]", "") ## Agregado para omitir el cardinality cuando no corresponde...
                            aux_description_string_AP_items = f"Added String mandatory for complete structure Array in the model into AdditionalProperties array Array of Strings: StringValue"
                            feature['sub_features'].append({
                                'name': f"{full_name}_StringValueAdditional {{doc '{aux_description_string_AP_items}'}}", ## RefName Aparte {full_name}_{ref_name}
                                'type': 'mandatory',
                                'description': aux_description_string_AP_items, #f"Added String mandatory for adding the structure Array in the model: StringValue",
                                'sub_features': [],
                                'type_data': 'String' ## Por defecto para la compatibilidad en los esquemas simples y la propiedad del feature: Boolean
                            })
                    elif 'type' in additional_properties and self.is_cardinality:
                        #elif 'type' in items and self.is_cardinality: ## Adición para generar el nodo hoja con el tipo de dato que se referencia en items
                        #print("Deberia de aplicarse al tener un type en items")
                        type_data_additional_properties = additional_properties['type']
                        #description_additional_properties = additional_properties['description']
                        #aux_description_additional_properties = ref_schema.get('description', '')
                        #print(description)

                        if type_data_additional_properties == 'string' and not bool_added_value:
                            full_name = full_name.replace(" cardinality [1..*]", "") ## Agregado para omitir el cardinality cuando no corresponde...
                            full_name = full_name.replace(" cardinality [0..*]", "")
                            aux_description_string_properties = f"Added String mandatory for complete structure Object in the model The modified is not in json but provide represents, Array of Strings: StringValue"
                            aux_description_maps_properties = f"Added Map for complete structure Object in the model The modified is not in json but provide represents, Array of pairs key, value: ValueMap, KeyMap"
                            list_local_features_maps = ['Map of', 'matchLabels is a map of', 'label keys and values'] ## 'unstructured key value map',
                            #print(f" EN PRINCIPIO SE EJECUTAR N+ MAPASSS {full_name}" )
                            if any(wordMap in description for wordMap in list_local_features_maps): ## Opcion para añadir los sub-features como mapas
                                feature['sub_features'].append({
                                'name': f"{full_name}_KeyMap {{doc 'key: {aux_description_maps_properties}'}}", ## RefName Aparte {full_name}_{ref_name}
                                'type': 'mandatory',
                                'description': aux_description_maps_properties, #f"Added String mandatory for adding the structure Array in the model: StringValue",
                                'sub_features': [],
                                'type_data': 'String' ## Por defecto para la compatibilidad en los esquemas simples y la propiedad del feature: Boolean
                                })
                                feature['sub_features'].append({
                                'name': f"{full_name}_ValueMap {{doc 'value: {aux_description_maps_properties}'}}", ## RefName Aparte {full_name}_{ref_name}
                                'type': 'mandatory',
                                'description': aux_description_maps_properties, #f"Added String mandatory for adding the structure Array in the model: StringValue",
                                'sub_features': [],
                                'type_data': 'String' ## Por defecto para la compatibilidad en los esquemas simples y la propiedad del feature: Boolean
                                })
                            elif 'unstructured key value map' in description:
                                ## Caso especial de objeto que puede ser null/optional
                                feature['sub_features'].append({
                                'name': f"{full_name}_KeyMap {{doc 'key: {aux_description_maps_properties}'}}", ## RefName Aparte {full_name}_{ref_name}
                                'type': 'optional',
                                'description': aux_description_maps_properties, #f"Added String mandatory for adding the structure Array in the model: StringValue",
                                'sub_features': [],
                                'type_data': 'String' ## Por defecto para la compatibilidad en los esquemas simples y la propiedad del feature: Boolean
                                })
                                feature['sub_features'].append({
                                'name': f"{full_name}_ValueMap {{doc 'value: {aux_description_maps_properties}'}}", ## RefName Aparte {full_name}_{ref_name}
                                'type': 'optional',
                                'description': aux_description_maps_properties, #f"Added String mandatory for adding the structure Array in the model: StringValue",
                                'sub_features': [],
                                'type_data': 'String' ## Por defecto para la compatibilidad en los esquemas simples y la propiedad del feature: Boolean
                                })                                
                            else:        
                                feature['sub_features'].append({ ## Caso por si hay alguna estruc buscada sin las expresiones de mapa
                                    'name': f"{full_name}_StringValueAdditional {{doc '{aux_description_string_properties}'}}", ## RefName Aparte {full_name}_{ref_name}
                                    'type': 'mandatory',
                                    'description': aux_description_string_properties, #f"Added String mandatory for adding the structure Array in the model: StringValue",
                                    'sub_features': [],
                                    'type_data': 'String' ## Por defecto para la compatibilidad en los esquemas simples y la propiedad del feature: Boolean
                                })

                # Extraer y añadir valores como subfeatures
                #extracted_values = self.extract_values(description)
                ## Todos los valores que se extraen son "String", para facilitar la representacion de los valores prestablecidos se cambia el tipo a Boolean
                if extracted_values:
                    ## details['type_data'] = 'Boolean' ## Esto es para acceder al tipo del ESQUEMA
                    feature['type_data'] = '' ## Se accede al tipo de dato del FEATURE actual: De Boolean a vacio '' 
                    #full_name_value = f"{full_name}_{value}" ### ÑFALLA EN LOS VALORES
                    full_name = full_name.replace(" cardinality [1..*]", "") ## Por si se pasa el cardinality en algun punto ### Proabando añadir cardinality
                    #value_sanitized_name = re.sub(r'\s*\{.*?\}', '', full_name)
                    #bool_added_value = True
                    for value in extracted_values:
                        bool_default_value = False
                        if ('{default' in value): ## Condicion para comprobar si alguno de los valores es default, se marcan y se elimina el default para agregarlo en conjunto con doc
                            bool_default_value = True
                            value = value.replace(" {default}", "") ## Se elimina el {default} y se marca para añadirlo en conjunto con la doc

                        full_name_value = f"{full_name}_{value}"
                        if '_Healthy' in full_name_value: ### Comprobacion para omitir valores que no se deberian de agregar en el modelo
                            print("OMITIENDO HEALTHY", full_name_value)
                            continue
                        aux_description_value = f"Specific value: {value}"

                        feature['sub_features'].append({
                            'name': f"{full_name_value} {{default, doc '{aux_description_value}'}}" if bool_default_value else f"{full_name_value} {{doc '{aux_description_value}'}}",
                            'type': 'alternative', # Todos los valores suelen ser alternatives (Elección de solo uno)
                            'description': aux_description_value,
                            'sub_features': [],
                            'type_data': ''  # Boolean por defecto: se cambia a vacio
                        })
                else:
                    if (any(keyword in full_name for keyword in self.boolean_keywords) or any(re.search(keyword, full_name) for keyword in self.boolean_keywords_regex) or any(special_name in full_name for special_name in self.special_features_config) and 'Note that this field cannot be set when' in description): ## and not full_name.endswith('_name')
                    ## se agrega "not extracted_values" para no sobreescribir el tipo alternativo con la adición de un hijo String abierto. Ya que si hay valores que lo definen, solo se puede seleccionar entre los predefinidos
                    #return 'Boolean'  and not extracted_values
                        #print("El tipo de dato es: ", self.feature_aux_original_type)
                        full_name = full_name.replace(" {abstract}", "")
                        aux_description_mandatory = f"Added String mandatory for changing booleans of boolean_keywords: {self.feature_aux_original_type} *_name"
                        #if full_name == 'io_k8s_api_core_v1_PodSecurityContext_seccompProfile':
                        #    print(f"EL NOMBRE Y TIPO DEL FEATURE AUXILIAR EN COINCIDENCIA ES: {self.feature_aux_original_type}")
                        if self.feature_aux_original_type == 'String' or self.feature_aux_original_type == 'string': ## Se comprueba con el valor original del feature. Para añadir el sub-feature como String o Integer
                            feature['sub_features'].append({
                            'name': f"{full_name}_nameStr {{doc '{aux_description_mandatory}'}}", #f"{full_name}_nameStr",
                            'type': 'mandatory', # Todos los valores suelen ser alternatives (Elección de solo uno)
                            'description': aux_description_mandatory, #f"Added String mandatory for changing booleans of boolean_keywords: String *_name",
                            'sub_features': [],
                            'type_data': 'String'  # String por defecto: se necesita un feature abierto para poder introducir un campo de texto
                        })
                        elif self.feature_aux_original_type == 'Integer' or self.feature_aux_original_type == 'integer':
                            feature['sub_features'].append({
                            'name': f"{full_name}_valueInt {{doc '{aux_description_mandatory}'}}", #f"{full_name}_valueInt",
                            'type': 'mandatory', # Todos los valores suelen ser alternatives (Elección de solo uno)
                            'description': aux_description_mandatory, #f"Added Integer mandatory for changing booleans of boolean_keywords: Integer *_name",
                            'sub_features': [],
                            'type_data': 'Integer'  # Integer por defecto: se necesita un feature abierto para poder introducir un entero positivo
                        })
                        #elif self.feature_aux_original_type == '' or self.feature_aux_original_type == 'Boolean' or self.feature_aux_original_type == 'boolean':
                        #    print("continue")

                # Procesar propiedades anidadas
                if 'properties' in details:
                    sub_properties = details['properties']
                    sub_required = details.get('required', [])
                    value_sanitized_name = re.sub(r'\s*\{.*?\}', '', full_name)
                    sub_mandatory, sub_optional = self.parse_properties(sub_properties, sub_required, value_sanitized_name, current_depth + 1, local_stack_refs)
                    feature['sub_features'].extend(sub_mandatory + sub_optional)
                
                #else: ##Parte para definir las propiedades anidadas que son simples* Probar
                    #sub_required = details.get('required', [])
                    #sub_mandatory, sub_optional = self.parse_properties([], sub_required, full_name, current_depth + 1, local_stack_refs)
                    #feature['sub_features'].extend(sub_mandatory + sub_optional)
                   

                if feature_type == 'mandatory':
                    mandatory_features.append(feature)
                else:
                    optional_features.append(feature)

                self.processed_features.add(full_name)

        #print(f"El numero de arrays es: {countArrays}")
        return mandatory_features, optional_features
            
    def save_descriptions(self, file_path):

        print(f"Saving descriptions to {file_path}...")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.descriptions, f, indent=4, ensure_ascii=False)
        print("Descriptions saved successfully.")

    def save_constraints(self, file_path):

        print(f"Saving constraints to {file_path}...")
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write("constraints\n") # Quitar para las pruebas con flamapy. Quitado: Restricciones obtenidas de las referencias:
            for constraint in self.constraints:
                f.write(f"\t{constraint}\n")
        print("Constraints saved successfully.")

def load_json_file(file_path):

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def properties_to_uvl(feature_list, indent=1):

    uvl_output = ""
    indent_str = '\t' * indent
    boolean_keywords = ['AppArmorProfile_localhostProfile', 'appArmorProfile_localhostProfile', 'seccompProfile_localhostProfile', 'SeccompProfile_localhostProfile', 'IngressClassList_items_spec_parameters_namespace',
                        'IngressClassParametersReference_namespace', 'IngressClass_spec_parameters_namespace', 'IngressClassSpec_parameters_namespace'] ## Agregados Ingress...Custom por restriccion ***
    for feature in feature_list:
        type_str = f"{feature['type_data'].capitalize()} " if feature['type_data'] else "Boolean " ### Espacio para no ponerlo en el uvl_output
        """if type_str == 'Boolean':
            print("EL TIPO DE DATO ES:", type_str)
            type_str == ''
            feature['type_data'] == ''"""
        if type_str == 'Boolean ':
            type_str = ''
            #feature['type_data'] = ''

        if any(keyword in feature['name'] for keyword in boolean_keywords) and not feature['name'].endswith('nameStr'): #### Caso especifico 002-localhostProfile String a Boolean / Agregado el mantener String los features agregados en la rama Boolean
            #print(f"COINCIDENCIA CON NOMBRES EN:{feature['name']} Los tipos son... {type_str}")
            type_str = ''
        #if (keyword in feature['name'] for keyword in boolean_keywords)  
        #    type_str = 'String '
        if feature['sub_features']:
            
            uvl_output += f"{indent_str}{type_str}{feature['name']}\n"  # {type_str} opcional si se necesita ## 
            # uvl_output += f"{indent_str}\t{feature['type']}\n" opcional si se necesita
            # Separar características obligatorias y opcionales
            sub_mandatory = [f for f in feature['sub_features'] if f['type'] == 'mandatory']
            sub_optional = [f for f in feature['sub_features'] if f['type'] == 'optional']
            sub_alternative = [f for f in feature['sub_features'] if f['type'] == 'alternative']

            if sub_mandatory:
                uvl_output += f"{indent_str}\tmandatory\n"
                uvl_output += properties_to_uvl(sub_mandatory, indent + 2)
            if sub_optional:
                uvl_output += f"{indent_str}\toptional\n"
                uvl_output += properties_to_uvl(sub_optional, indent + 2)
            if sub_alternative:
                uvl_output += f"{indent_str}\talternative\n"
                uvl_output += properties_to_uvl(sub_alternative, indent + 2)
        else:
            uvl_output += f"{indent_str}{type_str}{feature['name']}\n"  # {type_str} opcional si se necesita {{abstract}} 
    return uvl_output

def generate_uvl_from_definitions(definitions_file, output_file, descriptions_file):

    definitions = load_json_file(definitions_file) # Cargar el archivo de definiciones JSON
    processor = SchemaProcessor(definitions) # Inicializar el procesador de esquemas con las definiciones cargadas
    uvl_output = "namespace KubernetesTest1\nfeatures\n\tKubernetes {abstract}\n\t\toptional\n" # Iniciar la estructura base del archivo UVL {{abstract}}

    # Procesar cada definición en el archivo JSON
    for schema_name, schema in definitions.get('definitions', {}).items():
        root_schema = schema.get('properties', {})
        #{{doc '{cleaned_description}'}}
        required = schema.get('required', [])
        #type_str_feature = 'Boolean' ## Por defecto al no tener definido un tipo los features principales se les pone como Boolean
        #print(f"Processing schema: {schema_name}")
        mandatory_features, optional_features = processor.parse_properties(root_schema, required, processor.sanitize_name(schema_name)) # Obtener características obligatorias y opcionales
        
        schema_description_aux = schema.get('description', "") ## Se obtienen las descripciones de los esquemas principales para mostrarlas tambien
        if schema_description_aux:
            cleaned_description = schema_description_aux.replace('\n', '').replace('`', '').replace("´", '').replace("'", "_").replace('{','').replace('}','').replace('"', '').replace("\\", "_").replace(".", "").replace("//","_") ## Saneamiento de las descripciones con los caracteres que causan conflicto y errores en el formato uvl
            cleaned_description = ''.join(c for c in cleaned_description if ord(c) < 128)
            non_ascii, specials = processor.contains_non_ascii(cleaned_description)
            # Mostrar resultados
            if non_ascii or specials:
                print(f"Caracteres no ASCII encontrados: {non_ascii}")
                print(f"Caracteres especiales encontrados: {specials}")
        else:
            #print(f"No hay descripcion para la propiedad y feature: {root_schema} {schema_name}")
            cleaned_description = "Auto doc generate for not add empty Strings No descripcion in schemas JSON"  
        
        # Agregar las características obligatorias y opcionales al archivo UVL
        if mandatory_features:
            uvl_output += f"\t\t\t{processor.sanitize_name(schema_name)} {{doc '{cleaned_description}'}}\n" # {type_str_feature+' '} ## Omitiendo el tipo Boolean de los features 
            uvl_output += f"\t\t\t\tmandatory\n"
            uvl_output += properties_to_uvl(mandatory_features, indent=5)

            if optional_features:
                uvl_output += f"\t\t\t\toptional\n"
                uvl_output += properties_to_uvl(optional_features, indent=5)
        elif optional_features:
            uvl_output += f"\t\t\t{processor.sanitize_name(schema_name)} {{doc '{cleaned_description}'}}\n" # {type_str_feature+' '} ## Omitiendo el tipo Boolean de los features 
            uvl_output += f"\t\t\t\toptional\n"
            uvl_output += properties_to_uvl(optional_features, indent=5)
        # Ajuste adicion esquemas simples
        if not root_schema: ## Para tener en cuenta los esquemas que no tienen propiedades: como los RawExtension, JSONSchemaPropsOrBool, JSONSchemaPropsOrArray que solo tienen descripcion
            if 'oneOf' in schema:
                #print(f"Procesando oneOf en {schema_name}")
                oneOf_feature = processor.process_oneOf(schema['oneOf'], processor.sanitize_name(schema_name), type_feature='optional')
                if oneOf_feature:
                    uvl_output += properties_to_uvl([oneOf_feature], indent=3) 
            else:
                uvl_output += f"\t\t\t{processor.sanitize_name(schema_name)} {{doc '{cleaned_description}'}}\n" # {type_str_feature+' '} ## Omitiendo Bool
                #print("Schemas sin propiedades:",schema_name)

    # Guardar el archivo UVL generado
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(uvl_output)
    print(f"UVL output saved to {output_file}")

    # Guardar las descripciones extraídas
    processor.save_descriptions(descriptions_file)
    
    # Guardar las restricciones en el archivo UVL
    processor.save_constraints(output_file)

# Rutas de archivo relativas
definitions_file = '../../resources/kubernetes-json-v1.30.2/_definitions.json'
output_file = '../../variability_model/kubernetes_combined_04.uvl'
descriptions_file = '../../resources/model_generation/descriptions_01.json'



# Generar archivo UVL y guardar descripciones
generate_uvl_from_definitions(definitions_file, output_file, descriptions_file)

# Generar las restricciones UVL y agregarlas al final del archivo
restrictions = generar_constraintsDef(descriptions_file)
with open(output_file, 'a', encoding='utf-8') as f_out:
    f_out.write("\nconstraints\n")
    for restrict in restrictions:
        f_out.write(f"\t{restrict}\n")

print(f"Modelo UVL y restricciones guardados en {output_file}")