#Cambiar a version dividida en grupos y ajuste de optional
import json
from collections import deque

class SchemaProcessor:
    def __init__(self, definitions):
        self.definitions = definitions
        self.resolved_references = {}
        self.processed_features = {}
        self.seen_references = set()
        self.descriptions = {}
        self.seen_descriptions = set()

    def sanitize_name(self, name):
        """Replace non-alphanumeric characters with underscores and ensure uniqueness."""
        return name.replace("-", "_").replace(".", "_").replace("$", "")

    def resolve_reference(self, ref):
        """Resolve a JSON reference and return the referenced schema."""
        if ref in self.resolved_references:
            return self.resolved_references[ref]

        parts = ref.strip('#/').split('/')
        schema = self.definitions
        for part in parts:
            schema = schema.get(part, {})
            if not schema:
                return None
        
        self.resolved_references[ref] = schema
        return schema

    def is_valid_description(self, description):
        """Check if the description is valid (not too short and not repetitive)."""
        if len(description) < 10:
            return False
        if description in self.seen_descriptions:
            return False
        self.seen_descriptions.add(description)
        return True
    
    def parse_properties(self, properties, required, parent_name="", depth=0):
        mandatory_features = []
        optional_features = []
        queue = deque([(properties, required, parent_name, depth)])

        while queue:
            current_properties, current_required, current_parent, current_depth = queue.popleft()
            for prop, details in current_properties.items():
                sanitized_name = self.sanitize_name(prop)
                full_name = f"{current_parent}_{sanitized_name}" if current_parent else sanitized_name

                if full_name in self.processed_features:
                    continue

                feature_type = 'mandatory' if prop in current_required else 'optional'

                feature = {
                    'name': full_name,
                    'type': feature_type,
                    'description': details.get('description', ''),
                    'sub_features': [],
                }

                # Handle references
                if '$ref' in details:
                    if details['$ref'] in self.seen_references:
                        continue
                    self.seen_references.add(details['$ref'])
                    ref_schema = self.resolve_reference(details['$ref'])
                    if ref_schema and 'properties' in ref_schema:
                        sub_properties = ref_schema['properties']
                        sub_required = ref_schema.get('required', [])
                        sub_mandatory_features, sub_optional_features = self.parse_properties(sub_properties, sub_required, full_name, current_depth + 1)
                        feature['sub_features'].extend(sub_mandatory_features + sub_optional_features)
                
                elif 'items' in details:
                    items = details['items']
                    if '$ref' in items:
                        if items['$ref'] in self.seen_references:
                            continue
                        self.seen_references.add(items['$ref'])
                        ref_schema = self.resolve_reference(items['$ref'])
                        if ref_schema and 'properties' in ref_schema:
                            item_properties = self.parse_properties(ref_schema['properties'], [], full_name, current_depth + 1)
                            feature['sub_features'].extend(item_properties)
                    else:
                        item_required = items.get('required', [])
                        item_type = 'mandatory' if full_name in item_required else 'optional'
                        feature['sub_features'].append({
                            'name': f"{full_name}_items",
                            'type': item_type,
                            'description': 'Items in the array',
                            'sub_features': [],
                        })

                if 'properties' in details:
                    sub_properties = details['properties']
                    sub_required = details.get('required', [])
                    sub_mandatory_features, sub_optional_features = self.parse_properties(sub_properties, sub_required, full_name, current_depth + 1)
                    feature['sub_features'].extend(sub_mandatory_features + sub_optional_features)

                if feature_type == 'mandatory':
                    mandatory_features.append(feature)
                else:
                    optional_features.append(feature)

                self.processed_features[full_name] = feature

        return mandatory_features, optional_features

def save_descriptions(self, file_path):
    """Save the collected descriptions to a JSON file."""
    print(f"Saving descriptions to {file_path}...")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(self.descriptions, f, indent=4, ensure_ascii=False)
    print("Descriptions saved successfully.")

def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def properties_to_uvl(feature_list, indent=1):
    uvl_output = ""
    indent_str = '\t' * indent
    for feature in feature_list:
        if isinstance(feature, dict) and 'sub_features' in feature:
            if feature['sub_features']:
                uvl_output += f"{indent_str}{feature['name']}\n"
                uvl_output += f"{indent_str}\t{feature['type']}\n"
                uvl_output += properties_to_uvl(feature['sub_features'], indent + 2)
            else:
                uvl_output += f"{indent_str}{feature['name']}\n"  # {{abstract}}
    return uvl_output

def generate_uvl_from_definitions(definitions_file, output_file, descriptions_file):
    definitions = load_json_file(definitions_file)
    processor = SchemaProcessor(definitions)
    uvl_output = "namespace KubernetesTest1\n\nfeatures\n\tKubernetes\n"

    # Process the entire definitions as features under Kubernetes
    for schema_name, schema in definitions.get('definitions', {}).items():
        root_schema = schema.get('properties', {})
        required = schema.get('required', [])
        print(f"Processing schema: {schema_name}")  # Debugging line
        mandatory_features, optional_features = processor.parse_properties(root_schema, required, processor.sanitize_name(schema_name))
        
        # Add features to UVL based on the rules
        if mandatory_features:
            uvl_output += f"\t{processor.sanitize_name(schema_name)}\n"
            uvl_output += f"\t\tmandatory\n"
            uvl_output += properties_to_uvl(mandatory_features, indent=3)
        
        if optional_features:
            if not mandatory_features:
                uvl_output += f"\t{processor.sanitize_name(schema_name)}\n"
            uvl_output += f"\t\toptional\n"
            uvl_output += properties_to_uvl(optional_features, indent=3)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(uvl_output)

    processor.save_descriptions(descriptions_file)

    print(f"UVL file saved as {output_file}")
    print(f"Descriptions file saved as {descriptions_file}")

# Example usage
definitions_file = 'C:/projects/investigacion/kubernetes-json-v1.30.2/v1.30.2/_definitions.json'
output_file = 'C:/projects/investigacion/scriptJsonToUvl/kubernetes_combined_sinDatos.uvl'
descriptions_file = 'C:/projects/investigacion/scriptJsonToUvl/descriptions_sinDatos.json'

# Generate UVL file from definitions
generate_uvl_from_definitions(definitions_file, output_file, descriptions_file)
