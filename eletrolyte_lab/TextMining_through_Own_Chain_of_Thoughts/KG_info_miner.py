"""
KG_info_miner.py
Simple Knowledge Graph Miner for Battery Electrolyte Research
"""

import json
import random
import requests
from typing import Dict, Any, List, Set, Union
from time import sleep

# ====================
# SCHEMA DEFINITIONS
# ====================

entity_relationships = {
    "RESEARCH_PAPER": {
        "Electrolyte": "REPORTS",
        "Ionic_Conductivity_Property": "CONTAINS_DATA_ON",
    },

    "Electrolyte": {
        "Ionic_Conductivity_Property": "MEASUREMENT",
        "Polymers": "CONSISTS_OF",
        "Monomers": "CONSISTS_OF",
        "Salts": "CONSISTS_OF",
        "Additives": "CONSISTS_OF",
        "Initiators": "CONSISTS_OF",
    },
}

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

entity_schemas = {
    "RESEARCH_PAPER": {
        "doi": "string",
        "title": "string",
        "year": "integer",
        "ionic_property_focus": "boolean",
        "keywords": ["array", "of", "strings"]
    },

    "Electrolyte": {
        "name": "string",
        "type": "string (Liquid, Solid, Quasi-solid, Composite, Polymer, Gel, etc)",
        "description": "string",
    },

    "Ionic_Conductivity_Property": {
        "Type_of_ions":"string(Li+, Na+, K+, Zn2+,Cs etc.)",
        "ionic_conductivity_value": "string",
        "ionic_conductivity_unit": "string",
    },

    "Polymers": {
        "name": "string",
        "cas": "string",
        "smiles": "string",
        "Abbreviation": "string",
        "Polimerzation_Temperature": "string",
        "Polimerzation_Time": "string"
    },
   "Monomers": {
        "name": "string",
        "cas": "string",
        "smiles": "string",
        "Abbreviation": "string",
    },
    "Salts": {
        "name": "string",
        "cas": "string",
        "smiles": "string",
        "Abbreviation": "string",
    },
    "Additives": {
        "name": "string",
        "cas": "string",
        "smiles": "string",
        "Abbreviation": "string",
    },
    "Initiators": {
        "name": "string",
        "cas": "string",
        "smiles": "string",
        "Abbreviation": "string",
    },
}


# ====================
# HELPER FUNCTIONS
# ====================

def get_entity_base_name(key: str) -> str:
    """Extract base entity name from key."""
    import re
    
    for entity in entity_schemas.keys():
        # Use exact matching
        pattern = re.compile(r'^' + re.escape(entity) + r'_\d+$')
        if pattern.match(key):
            return entity
        
    return ""

def is_entity_key(key: str) -> bool:
    """Check if a key represents an entity (not attribute or relation)."""
    base_name = get_entity_base_name(key)
    return (base_name in entity_schemas and 
            "_ATTR" not in key and 
            not any(f"_{rel}" in key for rel in relationship_attributes.keys()))

def is_relation_key(key: str) -> bool:
    """Check if a key represents a relationship."""
    for rel_type in relationship_attributes.keys():
        if f"_{rel_type}" in key:
            return True
    return False

def get_relation_type_from_key(key: str) -> str:
    """Extract relation type from key (e.g., 'ELECTROLYTE_1_REPORTS_ON' -> 'REPORTS_ON')."""
    import re
    
    # Find the pattern: underscore, digits, underscore, then everything else
    match = re.search(r'_(\d+)_(.+)$', key)
    
    if match:
        # Get everything after _number_
        candidate = match.group(2)
        
        # Check if this exactly matches any relation type
        if candidate in relationship_attributes:
            return candidate
    
    return ""

def trace_parent_hierarchy(graph: Dict[str, Any], target_key: str) -> Dict[str, Any]:
    """
    Simple parent tracing without modifying recursion_miner.
    This searches through the graph to find parents.
    """
    result = {}
    
    def _find_and_collect(d, target, current_path=None, parent_dict=None):
        if current_path is None:
            current_path = []
        if parent_dict is None:
            parent_dict = d
        
        for key, value in d.items():
            # If we found the target
            if key == target:
                # Collect parent information along the path
                # We need to navigate through the graph to get each parent's level
                current_parent_level = graph
                for i, path_key in enumerate(current_path):
                    if path_key in current_parent_level:
                        # Extract info for this parent from its own level
                        parent_info = {}
                        parent_attr_key = f"{path_key}_ATTR"
                        if parent_attr_key in current_parent_level:
                            parent_info["attributes"] = current_parent_level[parent_attr_key]
                        
                        # Find relations in this parent's level
                        for rel_key, rel_value in current_parent_level.items():
                            if is_relation_key(rel_key) and rel_key.startswith(path_key + "_"):
                                if "relations" not in parent_info:
                                    parent_info["relations"] = {}
                                rel_type = get_relation_type_from_key(rel_key)
                                parent_info["relations"][rel_type] = rel_value
                        
                        result[path_key] = parent_info
                        
                        # Move down to next level for next parent
                        current_parent_level = current_parent_level.get(path_key, {})
                
                # Also collect target's own information from its parent level
                target_parent_level = graph
                for path_key in current_path:
                    target_parent_level = target_parent_level.get(path_key, {})
                
                target_info = {}
                target_attr_key = f"{target}_ATTR"
                if target_attr_key in target_parent_level:
                    target_info["attributes"] = target_parent_level[target_attr_key]
                
                for rel_key, rel_value in target_parent_level.items():
                    if is_relation_key(rel_key) and rel_key.startswith(target + "_"):
                        if "relations" not in target_info:
                            target_info["relations"] = {}
                        rel_type = get_relation_type_from_key(rel_key)
                        target_info["relations"][rel_type] = rel_value
                
                result[target] = target_info
                return True
            
            # Recursively search
            if isinstance(value, dict) and not key.endswith("_ATTR") and not is_relation_key(key):
                if _find_and_collect(value, target, current_path + [key], d):
                    return True
        
        return False
    
    _find_and_collect(graph, target_key)
    return result

def parent_hierarchy_info_fuser(path_to_current: Dict[str, Any]) -> str:
    """
    Combine parent hierarchy information into a coherent sentence using DeepSeek API.
    Reads all attributes directly from the path info.
    """
    if not path_to_current:
        return "No parent hierarchy information available."
    
    # Prepare ALL attribute information for the prompt
    hierarchy_details = []
    entities = list(path_to_current.keys())
    
    for i, entity in enumerate(entities):
        info = path_to_current[entity]
        entity_details = f"Entity: {entity}\n"
        
        # Add ALL attribute values directly from the info
        if "attributes" in info and info["attributes"]:
            attrs = info["attributes"]
            if isinstance(attrs, dict) and attrs:
                # Convert all attributes to string format
                attr_items = []
                for attr_name, attr_value in attrs.items():
                    if isinstance(attr_value, (str, int, float, bool)):
                        attr_items.append(f"{attr_name}: {attr_value}")
                    elif isinstance(attr_value, list):
                        # Handle lists (like key_features)
                        attr_items.append(f"{attr_name}: {', '.join(str(v) for v in attr_value)}")
                
                if attr_items:
                    entity_details += f"Attributes: {'; '.join(attr_items)}\n"
        
        # For entities except the last one, find the relation to the next entity
        if i < len(entities) - 1:
            next_entity = entities[i + 1]
            # Find the relation that connects this entity to the next one
            if "relations" in info and info["relations"]:
                # Look for relation that starts with this entity and connects to next
                for rel_type, rel_data in info["relations"].items():
                    # Check if this relation likely connects to the next entity
                    entity_details += f"Connects to next via: {rel_type}\n"
                    break  # Just take the first relation
        
        hierarchy_details.append(entity_details.strip())
    
    # Create a focused prompt
    prompt = f"""
I have a knowledge graph hierarchy about battery electrolyte research. 
Please create ONE coherent sentence that describes this parent-child chain naturally.

Hierarchy details (from parent to child):
{chr(10).join('---' + chr(10) + detail + chr(10) for detail in hierarchy_details)}

Rules:
1. Start with the first (root) entity
2. Use the relationship type mentioned in "Connects to next via:" to connect to the next entity
3. Include ALL the attribute values mentioned in "Attributes:" for context
4. Make it sound like natural scientific narrative
5. Only ONE sentence, flowing from parent to child
6. Include actual data values (names, numbers, descriptions) from attributes

Example based on actual data: 
If attributes are "title: Advanced Electrolyte for Lithium-Ion Batteries", include that
If attributes are "common_name: LP30; description: Standard commercial carbonate-based electrolyte", include those

Output ONLY the single sentence, no additional text or explanations.
"""
    
    print(f"\n[Fusing hierarchy with {len(entities)} entities]")
    
    print(f"Hierarchy details being sent: {hierarchy_details}") # Add this for debugging
    
    response = call_deepseek_api(prompt)
    
    print(f"Raw API response: {response}")  # Add this for debugging
    
    # Clean the response
    response = response.strip()
    if response.startswith('"') and response.endswith('"'):
        response = response[1:-1]
    
    return response

def retrieve_text_json(file_or_dir_path: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Simple version that handles both files and directories.
    Returns either a single dict or a list of dicts.
    """
    import os
    
    # Check if path exists
    if not os.path.exists(file_or_dir_path):
        print(f"Error: Path does not exist: {file_or_dir_path}")
        return {"title": "Path not found", "content": ""}
    
    # If it's a directory, process all JSON files
    if os.path.isdir(file_or_dir_path):
        print(f"Path is a directory. Looking for JSON files in: {file_or_dir_path}")
        
        # Get list of JSON files
        json_files = []
        for file in os.listdir(file_or_dir_path):
            if file.endswith('.json'):
                json_files.append(os.path.join(file_or_dir_path, file))
        
        if not json_files:
            print(f"No JSON files found in directory: {file_or_dir_path}")
            return []
        
        print(f"Found {len(json_files)} JSON files:")
        for i, f in enumerate(json_files, 1):
            print(f"  {i}. {os.path.basename(f)}")
        
        # Process each file
        results = []
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Simple extraction - adjust based on your JSON structure
                title = data.get("title", os.path.basename(json_file))
                content = data.get("content", data.get("text", json.dumps(data, indent=2)))
                
                results.append({
                    "title": title,
                    "content": str(content) if not isinstance(content, str) else content,
                    "filename": os.path.basename(json_file)
                })
                
                print(f"  ✓ Loaded: {title}")
                
            except Exception as e:
                print(f"  ✗ Error loading {json_file}: {e}")
        
        return results
    
    else:
        # It's a file
        try:
            with open(file_or_dir_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Simple extraction
            title = data.get("title", os.path.basename(file_or_dir_path))
            content = data.get("content", data.get("text", json.dumps(data, indent=2)))
            
            result = {
                "title": title,
                "content": str(content) if not isinstance(content, str) else content
            }
            
            print(f"Loaded: {title} ({len(result['content'])} chars)")
            return result
            
        except Exception as e:
            print(f"Error loading {file_or_dir_path}: {e}")
            return {"title": "Error", "content": ""}


# ====================
# DEEPSEEK API CONFIGURATION
# ====================

API_KEY = "XXXXXXXXXXXXXXXX"
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"

def call_deepseek_api(prompt: str, max_retries: int = 3) -> str:
    """Call DeepSeek API with the given prompt."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that extracts structured information from research papers about battery electrolytes. Always output valid JSON without Markdown formatting."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 2000
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{BASE_URL}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result["choices"][0]["message"]["content"]
                
                # Clean the response
                if raw_response.startswith("```json"):
                    raw_response = raw_response[7:]
                elif raw_response.startswith("```"):
                    raw_response = raw_response[3:]
                if raw_response.endswith("```"):
                    raw_response = raw_response[:-3]
                
                return raw_response.strip()
                
        except Exception as e:
            print(f"Request failed (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                sleep(2)
    
    return '{"error": "API call failed"}'

# ====================
# CORE MINING FUNCTIONS
# ====================

def get_entity_schema(entity_type: str) -> Dict[str, Any]:
    """Get schema for an entity type, including extended schemas."""
    if entity_type not in entity_schemas:
        return {}
    
    schema = entity_schemas[entity_type].copy()
    
    if "extends" in schema:
        base_type = schema["extends"]
        if base_type in entity_schemas:
            base_schema = entity_schemas[base_type].copy()
            if "extends" in base_schema:
                del base_schema["extends"]
            schema = {**base_schema, **schema}
    
    if "extends" in schema:
        del schema["extends"]
    
    return schema

def get_relation_schema(relation_type: str) -> Dict[str, str]:
    """Get schema for a relationship type."""
    return relationship_attributes.get(relation_type, {}).copy()


def modelchat_entity_check(parent_hierarchy_info: str, paper_text: str, next_entity: str) -> bool:
    """
    Check the if the entity been discussed in paper
    """
    prompt = f"""
As an electrochemical materials researcher, analyze if this paper contains information relevant to '{next_entity}'.
Apply your domain knowledge to identify technical synonyms, abbreviations, and related concepts.
Consider both direct mentions and contextually equivalent descriptions.

Paper excerpt: {paper_text}
The background information of target {next_entity} which we want to check: {parent_hierarchy_info}

Analysis: Based on your expertise in this field, is the paper discussing or relevant to '{next_entity}'?
Answer only YES or NO after a brief justification.

Output format:
Justification: [1-2 sentences]
Answer: [YES/NO]
"""
    
    response = call_deepseek_api(prompt)
    print(f"Entity Check for '{next_entity}': {response[:200]}...")
    
    # Extract the response
    response_lower = response.lower()
    
    if "answer: yes" in response_lower or "\nyes\n" in response_lower:
        return True
    if "answer: no" in response_lower or "\nno\n" in response_lower:
        return False
    
    # In case there is no "yes" or "no".
    return any(keyword in response_lower for keyword in ["yes", "contains", "mentions", "discusses", "relevant"])

def modelchat_prompt_combinator(parent_hierachy_info, paper_text, next_entity: str, next_relation: str) -> Dict[str, Any]:
    """
    Generate prompts and get response from model for entity-relation pairs.
    Now uses paper content and parent hierarchy information to extract accurate values.
    """
    entity_schema = get_entity_schema(next_entity)
    relation_schema = get_relation_schema(next_relation)
    
    print(f"\nExtracting {next_entity} with {next_relation} from paper content...")
    print(f"Paper text preview: {paper_text[:200]}...")  # Add this
    print(f"Background: {parent_hierachy_info[:100]}...")
    
    
    prompt = f"""
You are extracting structured information about battery electrolytes from scientific research papers.
Your task is to read the research paper and fill out attribute values for {next_entity} and {next_relation}.

RESEARCH PAPER CONTENT:
{paper_text}

BACKGROUND INFORMATION (condition for extraction):
{parent_hierachy_info}

ENTITY TYPE: {next_entity}
ENTITY ATTRIBUTES to fill (use "N/A" for values not mentioned in the paper):
{json.dumps(entity_schema, indent=2)}

RELATIONSHIP TYPE: {next_relation}
RELATIONSHIP ATTRIBUTES to fill (use "N/A" for values not mentioned in the paper):
{json.dumps(relation_schema, indent=2)}

INSTRUCTIONS:
1. Read the research paper carefully
2. Extract ALL information mentioned in this paper about {next_entity} and its relationship {next_relation} by taking the background information of {next_entity} into account
3. Fill ONLY the values that are explicitly mentioned in the research paper
4. For values NOT mentioned, use "N/A" (do not guess or make up values)
5. If you find multiple instances of the same entity with different attribute values, generate multiple pairs


IMPORTANT RULES:
- Do NOT guess or make up any values
- Use "N/A" for any attribute not explicitly mentioned
- Only extract information that matches the background/condition provided
- If no information matches, return empty JSON: {{"{next_entity}": {{}}}}

OUTPUT FORMAT - PURE JSON ONLY:
If you find matching information, output:
{{
  "{next_entity}": {{
    "{next_entity}_1": {{...filled entity attributes...}},
    "{next_relation}_1": {{...filled relationship attributes...}},
    "{next_entity}_2": {{...filled entity attributes...}},  # If multiple instances exist
    "{next_relation}_2": {{...filled relationship attributes...}}  # If multiple instances exist
  }}
}}

If NO matching information is found, output:
{{"{next_entity}": {{}}}}

EXAMPLES:
For ELECTROLYTE with CONTAINS relation (if mentioned in paper):
- ELECTROLYTE_1: {{"id": "LP30", "common_name": "LP30", "electrolyte_type": "liquid", "description": "Standard carbonate electrolyte", ...}}
- CONTAINS_1: {{"concentration": "1.0", "concentration_unit": "M", "role": "conducting_salt", "supplier": "Sigma-Aldrich", ...}}

For attributes NOT mentioned in paper:
- "first_reported_year": "N/A"
- "hazard_level": "N/A"
- "purity": "N/A"

Now extract information from the research paper based on the background information provided.
OUTPUT ONLY THE JSON, NO OTHER TEXT.
"""
    
    print(f"\nExtracting {next_entity} with {next_relation} from paper content...")
    print(f"Background: {parent_hierachy_info[:100]}...")
    
    response_text = call_deepseek_api(prompt)
    
    try:
        response_dict = json.loads(response_text)
        # Ensure the response has the expected structure
        if next_entity in response_dict:
            return response_dict
        else:
            # If response doesn't have the entity key, wrap it
            return {next_entity: response_dict}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Raw response: {response_text[:500]}")
        return {next_entity: {}}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {next_entity: {}}

def recursion_miner(paper_content, test_graph: Dict[str, Any], current_dict: Dict[str, Any], visited: Set[str] = None) -> None:
    """
    Recursively mine knowledge graph layer by layer.
    """
    if visited is None:
        visited = set()
    
    # Process each key in current dictionary
    for key in list(current_dict.keys()):
        # Skip if not an entity key or already visited
        if not is_entity_key(key) or key in visited:
            continue
        
        visited.add(key)
        current_entity = get_entity_base_name(key)
        
        # Get relationships for this entity
        if current_entity in entity_relationships:
            for next_entity, relation_type in entity_relationships[current_entity].items():
                # Trace the path backwards - use the actual key, not just entity type
                path_to_current = trace_parent_hierarchy(test_graph, key)
                # Fuse hierarchy into descriptive sentence
                fused_sentence = parent_hierarchy_info_fuser(path_to_current)
                print(f"\n=== At recursion level: {key} ===")
                print(f"Hierarchy: {fused_sentence}")
                
                # FIRST: Check if entity exists in paper given the context
                print(f"Checking if paper contains {next_entity} information...")
                entity_exists = modelchat_entity_check(fused_sentence, paper_content, next_entity)
                
                if not entity_exists:
                    print(f"  → No {next_entity} information found in paper. Skipping.")
                    continue
                
                # SECOND: Only if entity exists, extract detailed information
                print(f"  → {next_entity} information found. Extracting details...")
                response = modelchat_prompt_combinator(fused_sentence, paper_content, next_entity, relation_type)
                
                if next_entity in response:
                    response_data = response[next_entity]
                    
                    # Find how many pairs in response
                    pairs = {}
                    for resp_key, resp_value in response_data.items():
                        if resp_key.startswith(f"{next_entity}_"):
                            # Entity data
                            pair_num = resp_key.split("_")[-1]
                            pairs.setdefault(pair_num, {})["entity"] = resp_value
                        elif resp_key.startswith(f"{relation_type}_"):
                            # Relation data
                            pair_num = resp_key.split("_")[-1]
                            pairs.setdefault(pair_num, {})["relation"] = resp_value
                    
                    # Add pairs to current dictionary
                    for pair_num, pair_data in pairs.items():
                        if "entity" in pair_data and "relation" in pair_data:
                            entity_key = f"{next_entity}_{pair_num}"
                            attr_key = f"{entity_key}_ATTR"
                            rel_key = f"{entity_key}_{relation_type}"
                            
                            # Add to current level
                            current_dict[key][entity_key] = {}
                            current_dict[key][attr_key] = pair_data["entity"]
                            current_dict[key][rel_key] = pair_data["relation"]
                            
                            # Recursively process new entity
                            recursion_miner(paper_content, test_graph,
                                {entity_key: current_dict[key][entity_key]},
                                visited.copy()
                            )

# ====================
# MAIN EXECUTION
# ====================

def test_layered_miner(pdf_text_json):
    """Test the layered mining approach."""
    print("\n" + "="*60)
    print("LAYERED KNOWLEDGE GRAPH MINER")
    print("="*60)
    
    # Initialize with research paper
    test_graph = {
        "RESEARCH_PAPER_1": {},
        "RESEARCH_PAPER_1_ATTR": {
                "title": pdf_text_json["title"],
                "doi": "10.1234/advanced_electrolyte"
        }
    }
    
    print("\n1. Starting Graph:")
    print(json.dumps(test_graph, indent=2))
    
    print("\n2. Mining layers...")
    recursion_miner(pdf_text_json["content"],test_graph,test_graph)
    
    print("\n3. Final Graph Structure:")
    print_structure_simple(test_graph)
    
    # Save to file
    output_file = "knowledge_graph_layered.json"
    with open(output_file, 'w') as f:
        json.dump(test_graph, f, indent=2)
    
    print(f"\n4. Saved to: {output_file}")
    
    return test_graph

def print_structure_simple(d, indent=0):
    """Print dictionary structure in simple tree format."""
    for key, value in d.items():
        prefix = "  " * indent
        
        if is_entity_key(key):
            print(f"{prefix}{key} [ENTITY]")
        elif is_relation_key(key):
            rel_type = get_relation_type_from_key(key)
            print(f"{prefix}{key} [RELATION: {rel_type}]")
        elif key.endswith("_ATTR"):
            print(f"{prefix}{key} [ATTRIBUTES]")
        else:
            print(f"{prefix}{key}")
        
        if isinstance(value, dict):
            print_structure_simple(value, indent + 1)

def analyze_graph(graph):
    """Analyze the knowledge graph."""
    stats = {
        "entities": 0,
        "attributes": 0,
        "relations": 0,
        "entity_types": set()
    }
    
    def count_items(d):
        for key, value in d.items():
            if is_entity_key(key):
                stats["entities"] += 1
                stats["entity_types"].add(get_entity_base_name(key))
            elif key.endswith("_ATTR"):
                stats["attributes"] += 1
            elif is_relation_key(key):
                stats["relations"] += 1
            
            if isinstance(value, dict):
                count_items(value)
    
    count_items(graph)
    stats["entity_types"] = list(stats["entity_types"])
    
    return stats

if __name__ == "__main__":
    # Run the miner
    paper_text = retrieve_text_json("/Users/java304/Desktop/KG_builder/paper_text_json_cleaned")
    result = test_layered_miner(paper_text[0])
    
    # Show analysis
    stats = analyze_graph(result)
    print("\n" + "="*60)
    print("GRAPH ANALYSIS")
    print("="*60)
    print(f"Total Entities: {stats['entities']}")
    print(f"Total Attributes: {stats['attributes']}")
    print(f"Total Relations: {stats['relations']}")
    print(f"Entity Types: {', '.join(stats['entity_types'])}")
    
    # Show preview
    print("\n" + "="*60)
    print("GRAPH PREVIEW (first 1000 chars)")
    print("="*60)
    print(json.dumps(result, indent=2)[:1000] + "...")
