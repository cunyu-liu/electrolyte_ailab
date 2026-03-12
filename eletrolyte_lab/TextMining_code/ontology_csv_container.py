import json
import os
import csv
from pathlib import Path

def load_ontology(file_path):
    """Load ontology from JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def create_csv_files(ontology_data, output_dir):
    """Create CSV files for entities and relationships"""
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process entity schemas
    if 'entity_schemas' in ontology_data:
        for entity_name, attributes in ontology_data['entity_schemas'].items():
            create_entity_csv(entity_name, attributes, output_dir)
    
    # Process relationship attributes
    if 'relationship_attributes' in ontology_data:
        for rel_name, attributes in ontology_data['relationship_attributes'].items():
            create_entity_csv(rel_name, attributes, output_dir, is_relationship=True)

def create_entity_csv(entity_name, attributes, output_dir, is_relationship=False):
    """Create a CSV file for a specific entity or relationship"""
    
    # Clean entity name for filename
    clean_name = entity_name.replace(" ", "_").replace("-", "_")
    
    # Create CSV file path
    csv_file_path = os.path.join(output_dir, f"{clean_name}.csv")
    
    # Prepare headers
    headers = ['id']
    
    # Add attributes to headers
    for attr_name, attr_type in attributes.items():
        headers.append(attr_name)
    
    # Write CSV file
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
    
    print(f"Created CSV file: {csv_file_path} with headers: {headers}")

def main():
    # Define file paths
    ontology_path = "/Users/java304/Desktop/KG_builder_process_by_batch/ontology_v2.json"
    output_dir = "/Users/java304/Desktop/KG_builder_process_by_batch/entities_info"
    
    # Check if ontology file exists
    if not os.path.exists(ontology_path):
        print(f"Error: Ontology file not found at {ontology_path}")
        return
    
    try:
        # Load ontology
        print(f"Loading ontology from: {ontology_path}")
        ontology_data = load_ontology(ontology_path)
        
        # Create CSV files
        print(f"Creating CSV files in: {output_dir}")
        create_csv_files(ontology_data, output_dir)
        
        print("\nCSV files created successfully!")
        
        # Print summary
        entity_count = len(ontology_data.get('entity_schemas', {}))
        rel_count = len(ontology_data.get('relationship_attributes', {}))
        print(f"Total entities processed: {entity_count}")
        print(f"Total relationships processed: {rel_count}")
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()