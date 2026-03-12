"""
assign_id_to_entities_fixed.py
FIXED VERSION - Add unique IDs to entities in knowledge graph JSON file.
"""

import json
import os
import uuid
from typing import Dict, Any, Set, List

# Define relationship attributes (as provided)
relationship_attributes = {
    "REPORTS": {
        "description": "string",
        "section_in_paper": "string",
    },

    "MEASUREMENT": {
        "Temperature_condition": "string",
    },

    "CONSISTS_OF": {
        "concentration": "string",
        "ratio": "string",
        "role": "string (SOLVENT, SALT, ADDITIVE, POLYMER, MONOMER,Initiators)"
    },
    "CONTAINS_DATA_ON": {
        "description": "integer",
        "data_location": "string"
    },
}

def is_entity_to_process(key: str) -> bool:
    """
    Check if a key represents an entity that needs an ID assigned.
    Returns True for keys ending with '_ATTR' or '_RELATION' where RELATION is a relation type.
    """
    # Check for _ATTR suffix
    if key.endswith('_ATTR'):
        return True
    
    # Check for relation suffixes from relationship_attributes
    for rel_type in relationship_attributes.keys():
        if key.endswith(f'_{rel_type}'):
            return True
    
    return False

def add_ids_to_graph_fixed(graph: Dict[str, Any], existing_ids: Set[str] = None, parent_dict: Dict[str, Any] = None, parent_key: str = None) -> tuple[Dict[str, Any], Set[str]]:
    """
    Recursively traverse the knowledge graph and add unique IDs to entities.
    FIXED VERSION that properly updates dictionaries.
    """
    if existing_ids is None:
        existing_ids = set()
    
    # Create a list of keys to avoid dictionary modification issues
    keys_to_process = list(graph.keys())
    
    for key in keys_to_process:
        value = graph[key]
        
        # Check if this is an entity that needs an ID
        if is_entity_to_process(key) and isinstance(value, dict):
            # Generate a unique ID
            new_id = str(uuid.uuid4())
            while new_id in existing_ids:
                new_id = str(uuid.uuid4())
            
            existing_ids.add(new_id)
            
            # Add ID to the entity
            if "id" not in value:
                # Insert id at the beginning
                new_value = {"id": new_id}
                new_value.update(value)
                graph[key] = new_value
            else:
                # Update existing id
                value["id"] = new_id
        
        # Recursively process nested dictionaries
        if isinstance(value, dict):
            add_ids_to_graph_fixed(value, existing_ids, graph, key)
    
    return graph, existing_ids

def process_single_file(input_file_path: str, output_file_path: str) -> bool:
    """
    Process a single JSON file to add IDs to entities.
    Returns True if successful, False otherwise.
    """
    try:
        # Load the knowledge graph
        with open(input_file_path, 'r', encoding='utf-8') as f:
            knowledge_graph = json.load(f)
        
        # Add IDs to entities
        knowledge_graph_with_ids, all_ids = add_ids_to_graph_fixed(knowledge_graph)
        
        # Save the modified knowledge graph
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(knowledge_graph_with_ids, f, indent=2)
        
        return True, len(all_ids)
    except Exception as e:
        print(f"  Error processing {os.path.basename(input_file_path)}: {e}")
        return False, 0

def main():
    # Directory paths
    input_dir = "/Users/java304/Desktop/KG_builder_process_by_batch/eval_output_json"
    output_dir = "/Users/java304/Desktop/KG_builder_process_by_batch/eval_output_json_with_ids"
    
    # Check if input directory exists
    if not os.path.exists(input_dir):
        print(f"Error: Input directory not found at {input_dir}")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all JSON files in input directory
    json_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return
    
    print(f"Found {len(json_files)} JSON files to process in {input_dir}")
    print(f"Output will be saved to {output_dir}")
    
    successful_count = 0
    total_ids_generated = 0
    
    # Process each JSON file
    for json_file in json_files:
        input_file_path = os.path.join(input_dir, json_file)
        
        # Create output filename: XXXX_with_id.json
        base_name = os.path.splitext(json_file)[0]
        output_file_name = f"{base_name}_with_id.json"
        output_file_path = os.path.join(output_dir, output_file_name)
        
        print(f"\nProcessing: {json_file} -> {output_file_name}")
        
        success, ids_count = process_single_file(input_file_path, output_file_path)
        
        if success:
            successful_count += 1
            total_ids_generated += ids_count
            print(f"  ✓ Successfully generated {ids_count} IDs")
        else:
            print(f"  ✗ Failed to process")
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"PROCESSING SUMMARY")
    print(f"{'='*50}")
    print(f"Total files processed: {len(json_files)}")
    print(f"Successfully processed: {successful_count}")
    print(f"Failed to process: {len(json_files) - successful_count}")
    print(f"Total IDs generated: {total_ids_generated}")
    print(f"Output directory: {output_dir}")

if __name__ == "__main__":
    main()