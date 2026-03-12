import json
import os
import csv
from pathlib import Path
import re


def sort_entities_to_csv(json_file_path):
    """Extract all entities from JSON and write to CSV files by category"""
    
    # Define file paths - using relative paths based on input JSON path
    json_path = json_file_path
    base_dir = os.path.dirname(json_path)
    ontology_path = "/Users/java304/Desktop/KG_builder_process_by_batch/ontology_v2.json" ########## USER CUSTOMISED HERE ###########
    entities_dir = "/Users/java304/Desktop/KG_builder_process_by_batch/entities_info"  ########## USER CUSTOMISED HERE ###########
    
    print(f"Processing file: {json_path}")
    
    # Load JSON data
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Load ontology to get valid entity and relationship types
    with open(ontology_path, 'r') as f:
        ontology = json.load(f)
    
    # Get valid entity types from ontology
    valid_entity_types = list(ontology.get('entity_schemas', {}).keys())
    valid_relationship_types = list(ontology.get('relationship_attributes', {}).keys())
    
    print(f"Valid entity types from ontology: {valid_entity_types}")
    print(f"Valid relationship types from ontology: {valid_relationship_types}")
    
    # Create relationship endings by adding underscore prefix
    relationship_endings = [f'_{rel_type}' for rel_type in valid_relationship_types]
    
    # Dictionary to store entities by category
    entities_by_category = {}
    
    # Function to recursively process the JSON
    def process_node(node, path=""):
        if not isinstance(node, dict):
            return
        
        # Look for _ATTR entries at this level
        for key, value in node.items():
            if isinstance(value, dict):
                # Check if this is an _ATTR entry
                if key.endswith('_ATTR'):
                    # Get base name (without _ATTR)
                    base_name = key[:-5]
                    
                    # Determine category from base_name
                    # e.g., "ELECTROLYTE_1" -> "ELECTROLYTE", "Anode_1" -> "Anode"
                    category = None
                    
                    # Try to extract category by removing trailing numbers and underscores
                    # Pattern to match entity name with number (e.g., "ELECTROLYTE_1", "Anode_1")
                    match = re.match(r'^([A-Za-z_]+?)(?:_\d+)?$', base_name)
                    if match:
                        potential_category = match.group(1)
                        
                        # Check if this matches a valid entity type from ontology
                        # Try exact match first
                        if potential_category in valid_entity_types:
                            category = potential_category
                        else:
                            # Try uppercase version
                            potential_category_upper = potential_category.upper()
                            if potential_category_upper in valid_entity_types:
                                category = potential_category_upper
                            else:
                                # Try to find partial match
                                for valid_type in valid_entity_types:
                                    if valid_type.lower() == potential_category.lower():
                                        category = valid_type
                                        break
                    
                    # Only process if we found a valid category
                    if category:
                        # Initialize category if not exists
                        if category not in entities_by_category:
                            entities_by_category[category] = []
                        
                        # Add entity to category
                        entities_by_category[category].append({
                            'base_name': base_name,
                            'attributes': value,
                            'path': path
                        })
                    else:
                        print(f"  Warning: Skipping entity '{base_name}' - no matching ontology category found")
                
                # Also check for relationship entries to extract their attributes
                # Relationship entries end with relationship types from ontology
                else:
                    for ending in relationship_endings:
                        if key.endswith(ending):
                            # This is a relationship entity
                            relationship_type = ending[1:]  # Remove leading underscore
                            
                            # Verify this is a valid relationship type
                            if relationship_type in valid_relationship_types:
                                # Extract base name (remove relationship suffix)
                                base_name = key[:-len(ending)]
                                
                                # Add as a relationship entity
                                if relationship_type not in entities_by_category:
                                    entities_by_category[relationship_type] = []
                                
                                entities_by_category[relationship_type].append({
                                    'base_name': base_name + ending,
                                    'attributes': value,
                                    'path': path,
                                    'is_relationship': True,
                                    'relationship_type': relationship_type
                                })
                            break
                
                # Recurse into nested structures
                process_node(value, f"{path}.{key}")
    
    # Start processing
    print("Processing JSON to extract entities...")
    process_node(data)
    
    # Write entities to CSV files by category
    print(f"\nWriting entities to CSV files in: {entities_dir}")
    
    for category, entities in entities_by_category.items():
        # Create CSV file path
        csv_file_path = os.path.join(entities_dir, f"{category}.csv")
        
        # Check if CSV file already exists (created by ontology_csv_container.py)
        if not os.path.exists(csv_file_path):
            print(f"  Warning: CSV file {category}.csv doesn't exist. Skipping...")
            continue
        
        # Read existing headers from CSV file
        existing_headers = []
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            try:
                existing_headers = next(reader)
            except StopIteration:
                print(f"  Warning: CSV file {category}.csv is empty. Skipping...")
                continue
        
        print(f"  Processing {category}.csv with headers: {existing_headers}")
        
        # Read existing data from CSV
        existing_data = {}
        try:
            with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if 'id' in row and row['id']:
                        existing_data[row['id']] = row
        except Exception as e:
            print(f"  Error reading {category}.csv: {e}")
            continue
        
        # Process new entities
        new_entities_count = 0
        for entity in entities:
            entity_id = entity['attributes'].get('id', '')
            
            # Skip if no ID
            if not entity_id or entity_id == 'N/A':
                print(f"    Warning: Entity {entity['base_name']} has no valid ID, skipping...")
                continue
            
            # Skip if entity already exists in CSV
            if entity_id in existing_data:
                print(f"    Entity {entity_id} already exists in {category}.csv, skipping...")
                continue
            
            # Create new row with only existing headers
            new_row = {header: '' for header in existing_headers}
            new_row['id'] = entity_id
            
            # Fill in attributes that match existing headers
            if isinstance(entity['attributes'], dict):
                for attr_key, attr_value in entity['attributes'].items():
                    if attr_key in existing_headers:
                        # Convert non-string values to string
                        if not isinstance(attr_value, str):
                            attr_value = str(attr_value)
                        new_row[attr_key] = attr_value
                    else:
                        # Attribute not in CSV headers - skip it
                        pass
            
            # Add the new entity
            existing_data[entity_id] = new_row
            new_entities_count += 1
        
        # Write updated CSV with only existing headers
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=existing_headers)
            writer.writeheader()
            
            for row_data in existing_data.values():
                # Ensure all headers are present in the row (should already be)
                writer.writerow(row_data)
        
        print(f"  - Updated {category}.csv with {new_entities_count} new entities (total: {len(existing_data)})")
    
    print(f"\nTotal categories processed: {len(entities_by_category)}")
    total_entities = sum(len(entities) for entities in entities_by_category.values())
    print(f"Total entities found: {total_entities}")
    
    # List any ontology entity types that weren't found
    missing_entity_types = set(valid_entity_types) - set(entities_by_category.keys())
    if missing_entity_types:
        print(f"\nNote: The following entity types from ontology were not found in the data:")
        for missing_type in missing_entity_types:
            print(f"  - {missing_type}")
    
    missing_relationship_types = set(valid_relationship_types) - set(entities_by_category.keys())
    if missing_relationship_types:
        print(f"\nNote: The following relationship types from ontology were not found in the data:")
        for missing_type in missing_relationship_types:
            print(f"  - {missing_type}")
    
    return entities_by_category


def sort_entities_relations_to_csv(json_file_path, csv_writer=None, relation_counter=None, first_file=False):
    """Improved version with better pattern matching for relationships"""
    
    # Define file paths
    json_path = json_file_path
    
    # Load JSON data
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Load ontology to get relationship types
    ontology_path = "/Users/java304/Desktop/KG_builder_process_by_batch/ontology_v2.json"  ########## USER CUSTOMISED HERE ###########
    with open(ontology_path, 'r') as f:
        ontology = json.load(f)
    
    # Get relationship types from ontology
    # They are the keys in relationship_attributes
    relationship_types = list(ontology.get('relationship_attributes', {}).keys())
    
    # Create relationship endings by adding underscore prefix
    relationship_endings = [f'_{rel_type}' for rel_type in relationship_types]
    
    # Initialize csvfile variable
    csvfile = None
    
    # If this is the first file and we need to create the CSV writer
    if first_file and csv_writer is None:
        # Use the fixed entities_info directory path
        csv_path = "/Users/java304/Desktop/KG_builder_process_by_batch/entities_info/relations_extracted.csv"  ########## USER CUSTOMISED HERE ###########
        csvfile = open(csv_path, 'w', newline='', encoding='utf-8')
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['entity_id_start', 'entity_id_end', 'relation_id', 'relationship_type'])
        print(f"Created CSV file at: {csv_path}")
        relation_counter = 0
    
    if csv_writer is None:
        print("WRONG: CSV writer not initialised")
        return None, None, 0
    
    # Helper function to extract IDs
    def extract_id(entity_data):
        """Extract id from entity data, return None if not found"""
        if isinstance(entity_data, dict):
            if 'id' in entity_data:
                return entity_data['id']
        return None
    
    # Function to recursively process the JSON
    def process_node(node, path=""):
        nonlocal relation_counter
        
        if not isinstance(node, dict):
            return
        
        # Look for _ATTR entries at this level
        for key, value in node.items():
            if key.endswith('_ATTR') and isinstance(value, dict):
                # This is an attribute entry - could be start or end entity
                entity_id = extract_id(value)
                
                if entity_id:
                    # Get base name (without _ATTR)
                    base_name = key[:-5]
                    
                    # Check if base entity exists at same level
                    if base_name in node and isinstance(node[base_name], dict):
                        base_entity = node[base_name]
                        
                        # Now look for relationships and other entities within base_entity
                        for sub_key, sub_value in base_entity.items():
                            if sub_key.endswith('_ATTR'):
                                # Found another entity's attributes
                                sub_entity_id = extract_id(sub_value)
                                
                                if sub_entity_id:
                                    # Now look for relationships between base_entity and sub_entity
                                    # Relationship keys would be like sub_base_RELATIONSHIP
                                    sub_base = sub_key[:-5]  # Remove _ATTR
                                    
                                    # Check for relationship entries
                                    for rel_key, rel_value in base_entity.items():
                                        # Check if this is a relationship entry (contains sub_base and ends with relationship pattern)
                                        if sub_base in rel_key and any(rel_key.endswith(ending) for ending in relationship_endings):
                                            rel_id = extract_id(rel_value)
                                            
                                            if rel_id:
                                                # Found a complete relation!
                                                csv_writer.writerow([entity_id, sub_entity_id, rel_id, rel_key])
                                                relation_counter += 1
                                                print(f"Found relation: {entity_id} -> {sub_entity_id} via {rel_key} ({rel_id})")
            
            # Recurse into nested structures
            if isinstance(value, dict):
                process_node(value, f"{path}.{key}")
    
    # Start processing
    process_node(data)
    
    return csv_writer, csvfile, relation_counter

def main():
    """Main function to run the extraction"""
    print("Starting entity-relation extraction...")
    print("=" * 50)
    
    # Define input directory
    input_dir = "/Users/java304/Desktop/KG_builder_process_by_batch/eval_output_json_with_ids"
    
    # Get all JSON files in the input directory
    json_files = []
    for file in os.listdir(input_dir):
        if file.endswith('.json'):
            json_files.append(os.path.join(input_dir, file))
    
    print(f"Found {len(json_files)} JSON files to process")
    
    # DEBUG: Print all JSON files found
    print("\nDEBUG: JSON files found:")
    for json_file in json_files:
        print(f"  - {os.path.basename(json_file)}")
    
    # Process each JSON file
    csv_writer = None
    csv_file = None
    total_relations = 0
    first_file = True
    
    for i, json_file in enumerate(json_files, 1):
        print(f"\n{'='*50}")
        print(f"Processing file {i}/{len(json_files)}: {os.path.basename(json_file)}")
        print(f"{'='*50}")
        
        # First, extract all entities to CSV files
        sort_entities_to_csv(json_file)
        
        print(f"\n{'='*50}")
        print(f"Extracting relationships from: {os.path.basename(json_file)}")
        print(f"{'='*50}")
        
        # Then extract relationships
        if first_file:
            # For the first file, create the CSV writer
            csv_writer, csv_file, total_relations = sort_entities_relations_to_csv(json_file, None, None, first_file=True)
            first_file = False
        else:
            # For subsequent files, use the existing writer
            csv_writer, _, new_relations = sort_entities_relations_to_csv(json_file, csv_writer, total_relations, first_file=False)
            total_relations = new_relations  # 只更新关系计数
        
        print(f"Total relations so far: {total_relations}")
    
    # Close the CSV file if it was opened
    if csv_file:
        csv_file.close()
        print(f"\nFinal CSV file saved at: /Users/java304/Desktop/KG_builder_process_by_batch/entities_info/relations_extracted.csv")  ########## USER CUSTOMISED HERE ###########
    
    print(f"\n{'='*50}")
    print(f"Processing complete!")
    print(f"Total JSON files processed: {len(json_files)}")
    print(f"Total relations extracted: {total_relations}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
