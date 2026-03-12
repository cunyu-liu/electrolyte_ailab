import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase
import json
from datetime import datetime
import os
import requests
import glob
import sys

# Add the directory containing query_chunker.py to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ==================== CONFIGURATION ====================
# Neo4j Configuration
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "XXXXXXXXXXXXXXXXXXX"

# Subgraph Configuration - CHANGE THIS ONE VALUE TO CONTROL HOP LEVEL
MAX_HOPS = 2  # Change this to 1, 2, 3, etc. for different hop levels

# DeepSeek API Configuration
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = "XXXXXXXXXXXXXXXXXXXXXXXX"  # Replace with your actual API key

# Query Chunker Configuration
ONTOLOGY_PATH = "/Users/java304/Desktop/KG_builder_process_by_batch/ontology_v2.json"  # Update this path to your ontology file

# Directory paths
SUMMARY_DIR = "/Users/java304/Desktop/KG_builder_process_by_batch/searched_results_in_json"
# =======================================================

class Neo4jSubgraphRetriever:
    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD):
        """Initialize Neo4j connection"""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def close(self):
        """Close the Neo4j driver"""
        if self.driver:
            self.driver.close()
    
    def test_connection(self):
        """Test connection to Neo4j"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                return result.single()["test"] == 1
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            return False
    
    def get_subgraph_for_entity(self, entity_id, max_hops=MAX_HOPS):
        """
        Retrieve subgraph centered on a specific entity ID
        Returns nodes and relationships up to max_hops away
        """
        print(f"Searching for entity ID: {entity_id}")
        
        # First try a simple query without APOC
        try:
            print("Trying method 1...")
            # Method 1: Simple MATCH query for connections using only 'id'
            query = f"""
            MATCH (start {{id: $entity_id}})-[r*1..{max_hops}]-(connected)
            RETURN start, collect(DISTINCT connected) as connected_nodes, 
                collect(DISTINCT r) as relationships
            """
            
            with self.driver.session() as session:
                result = session.run(query, entity_id=entity_id)
                record = result.single()
                
                if record and record["start"]:
                    print(f"Found subgraph with {len(record['connected_nodes'])} nodes using method 1")
                    return self._process_query_result(record, entity_id)
                else:
                    print("Method 1 found no results")
                
        except Exception as e:
            print(f"Method 1 failed: {e}")
        
        # Method 2: Alternative approach
        try:
            print("Trying method 2...")
            subgraph = self._get_subgraph_alternative(entity_id, max_hops)
            if subgraph["nodes"]:
                print(f"Found subgraph with {len(subgraph['nodes'])} nodes using method 2")
            return subgraph
        except Exception as e:
            print(f"Method 2 failed: {e}")
        
        return {"nodes": [], "relationships": []}
        
    def get_entity_details(self, entity_id):
        """Get details about a specific entity by ID"""
        query = """
        MATCH (n {id: $entity_id})
        RETURN n.id as id, labels(n) as labels, properties(n) as properties
        """
        
        with self.driver.session() as session:
            result = session.run(query, entity_id=entity_id)
            record = result.single()
            
            if record:
                return {
                    "id": record["id"],
                    "labels": record["labels"],
                    "properties": record["properties"]
                }
        return None
    
    def _process_query_result(self, record, entity_id):
        """Process query result from Neo4j"""
        nodes_dict = {}
        relationships_dict = {}
        
        # Add start node
        start_node = record["start"]
        node_props = dict(start_node)
        node_props.pop('id', None)
        nodes_dict[start_node.id] = {
            "id": start_node.id,
            "labels": list(start_node.labels),
            "properties": node_props
        }
        
        # Add connected nodes
        connected_nodes = record["connected_nodes"]
        for node in connected_nodes:
            if node and node.id not in nodes_dict:
                node_props = dict(node)
                node_props.pop('id', None)
                nodes_dict[node.id] = {
                    "id": node.id,
                    "labels": list(node.labels),
                    "properties": node_props
                }
        
        # Add relationships
        relationships_list = record["relationships"]
        for rel_list in relationships_list:
            for rel in rel_list:
                if rel and rel.id not in relationships_dict:
                    rel_props = dict(rel)
                    rel_props.pop('id', None)
                    relationships_dict[rel.id] = {
                        "id": rel.id,
                        "type": rel.type,
                        "start_node_id": rel.start_node.id,
                        "end_node_id": rel.end_node.id,
                        "properties": rel_props
                    }
        
        return {
            "nodes": list(nodes_dict.values()),
            "relationships": list(relationships_dict.values())
        }
    
    def _get_subgraph_alternative(self, entity_id, max_hops=MAX_HOPS):
        """Alternative method using queries for each hop level"""
        all_nodes = {}
        all_relationships = {}
        
        # For each hop level, execute a separate query
        for hops in range(1, max_hops + 1):
            try:
                query = f"""
                MATCH (start {{id: $entity_id}})-[r*{hops}]-(connected)
                RETURN start, connected, r
                """
                
                with self.driver.session() as session:
                    result = session.run(query, entity_id=entity_id)
                    
                    for record in result:
                        # Process start node
                        start_node = record["start"]
                        if start_node and start_node.id not in all_nodes:
                            node_props = dict(start_node)
                            node_props.pop('id', None)
                            all_nodes[start_node.id] = {
                                "id": start_node.id,
                                "labels": list(start_node.labels),
                                "properties": node_props
                            }
                        
                        # Process connected node
                        connected_node = record["connected"]
                        if connected_node and connected_node.id not in all_nodes:
                            node_props = dict(connected_node)
                            node_props.pop('id', None)
                            all_nodes[connected_node.id] = {
                                "id": connected_node.id,
                                "labels": list(connected_node.labels),
                                "properties": node_props
                            }
                        
                        # Process relationships
                        rels = record["r"]
                        for rel in rels:
                            if rel and rel.id not in all_relationships:
                                rel_props = dict(rel)
                                rel_props.pop('id', None)
                                all_relationships[rel.id] = {
                                    "id": rel.id,
                                    "type": rel.type,
                                    "start_node_id": rel.start_node.id,
                                    "end_node_id": rel.end_node.id,
                                    "properties": rel_props
                                }
                                
            except Exception as e:
                print(f"Error at hop {hops}: {e}")
                continue
        
        # Also get nodes with no relationships (just the start node if isolated)
        if not all_nodes:
            try:
                query = """
                MATCH (start {id: $entity_id})
                RETURN start
                """
                
                with self.driver.session() as session:
                    result = session.run(query, entity_id=entity_id)
                    record = result.single()
                    
                    if record and record["start"]:
                        start_node = record["start"]
                        node_props = dict(start_node)
                        node_props.pop('id', None)
                        all_nodes[start_node.id] = {
                            "id": start_node.id,
                            "labels": list(start_node.labels),
                            "properties": node_props
                        }
            except Exception as e:
                print(f"Error getting isolated node: {e}")
        
        return {
            "nodes": list(all_nodes.values()),
            "relationships": list(all_relationships.values())
        }


def load_embeddings_and_model(embeddings_path='./entity_embeddings/entity_embeddings.pkl',
                             model_name='all-MiniLM-L6-v2'):
    """Load embeddings and initialize the SentenceTransformer model"""
    try:
        # Load the SentenceTransformer model
        print(f"Loading SentenceTransformer model: {model_name}")
        model = SentenceTransformer(model_name)
        print("Model loaded successfully.")
        
        # Load embeddings
        with open(embeddings_path, 'rb') as f:
            embeddings_data = pickle.load(f)
        
        print(f"Loaded {len(embeddings_data['ids'])} embeddings")
        print(f"Embedding dimension: {embeddings_data['embeddings'].shape[1]}")
        
        return model, embeddings_data
        
    except FileNotFoundError:
        print(f"Error: Embeddings file not found at {embeddings_path}")
        print("Please run entities_embedder.py first to create embeddings.")
        return None, None
    except Exception as e:
        print(f"Error loading: {e}")
        return None, None


def search_entities(query, model, embeddings_data, top_k=5):
    """Search for similar entities using SentenceTransformer"""
    if model is None or embeddings_data is None:
        return []
    
    # Create query embedding
    query_embedding = model.encode(query, convert_to_numpy=True)
    
    # Get data
    embeddings = embeddings_data['embeddings']
    ids = embeddings_data['ids']
    metadata = embeddings_data['metadata']
    
    # Calculate cosine similarity
    query_norm = query_embedding / np.linalg.norm(query_embedding)
    emb_norms = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    similarities = np.dot(emb_norms, query_norm)
    
    # Get top results
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    results = []
    for idx in top_indices:
        entity_text = metadata[idx]['entity_string']
        if len(entity_text) > 100:
            display_text = entity_text[:97] + "..."
        else:
            display_text = entity_text
        
        results.append({
            'id': ids[idx],
            'score': float(similarities[idx]),
            'text': display_text,
            'full_text': entity_text
        })
    
    return results


def display_search_results(query, results):
    """Display search results"""
    print("\n" + "=" * 80)
    print(f"SEMANTIC SEARCH RESULTS")
    print(f"Query: {query}")
    print("=" * 80)
    
    if not results:
        print("No results found.")
        return
    
    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"  ID: {result['id']}")
        print(f"  Score: {result['score']:.6f}")
        print(f"  Entity: {result['text']}")
        print("-" * 80)


def display_subgraph_summary(subgraph, entity_id, result_num):
    """Display a summary of the subgraph"""
    print(f"\n{'=' * 80}")
    print(f"SUBGRAPH {result_num} SUMMARY")
    print(f"Entity ID: {entity_id}")
    print(f"{'=' * 80}")
    
    if not subgraph["nodes"]:
        print("No subgraph found for this entity.")
        return
    
    # Count node types
    node_types = {}
    for node in subgraph["nodes"]:
        for label in node["labels"]:
            node_types[label] = node_types.get(label, 0) + 1
    
    # Count relationship types
    rel_types = {}
    for rel in subgraph["relationships"]:
        rel_types[rel["type"]] = rel_types.get(rel["type"], 0) + 1
    
    print(f"\nSUBGRAPH STATISTICS:")
    print(f"   Total Nodes: {len(subgraph['nodes'])}")
    print(f"   Total Relationships: {len(subgraph['relationships'])}")
    
    if node_types:
        print(f"\nNODE TYPES:")
        for label, count in node_types.items():
            print(f"   {label}: {count} nodes")
    
    if rel_types:
        print(f"\nRELATIONSHIP TYPES:")
        for rel_type, count in rel_types.items():
            print(f"   {rel_type}: {count} relationships")
    
    # Show sample data
    print(f"\nSAMPLE NODES:")
    sample_count = min(3, len(subgraph["nodes"]))
    for i, node in enumerate(subgraph["nodes"][:sample_count], 1):
        if node["labels"]:
            label_str = node["labels"][0]
        else:
            label_str = "No Label"
        
        if node["properties"]:
            first_prop_key = list(node["properties"].keys())[0]
            first_prop_value = str(node["properties"][first_prop_key])
            if len(first_prop_value) > 50:
                first_prop_value = first_prop_value[:47] + "..."
            print(f"   {i}. {label_str}: {first_prop_key} = {first_prop_value}")
        else:
            print(f"   {i}. {label_str} (no properties)")


def display_subgraph_detailed(subgraph, entity_id, result_num):
    """Display detailed subgraph information"""
    print(f"\n{'=' * 80}")
    print(f"SUBGRAPH {result_num} DETAILED VIEW")
    print(f"Entity ID: {entity_id}")
    print(f"{'=' * 80}")
    
    if not subgraph["nodes"]:
        print("No subgraph found for this entity.")
        return
    
    print(f"\nNODES ({len(subgraph['nodes'])}):")
    print("-" * 80)
    
    for i, node in enumerate(subgraph["nodes"], 1):
        print(f"\nNode {i} (Internal ID: {node['id']}):")
        print(f"  Labels: {', '.join(node['labels'])}")
        if node["properties"]:
            print(f"  Properties ({len(node['properties'])}):")
            for key, value in node["properties"].items():
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:97] + "..."
                print(f"    {key}: {value_str}")
        else:
            print(f"  Properties: None")
    
    if subgraph["relationships"]:
        print(f"\nRELATIONSHIPS ({len(subgraph['relationships'])}):")
        print("-" * 80)
        
        for i, rel in enumerate(subgraph["relationships"], 1):
            print(f"\nRelationship {i} (Internal ID: {rel['id']}):")
            print(f"  Type: {rel['type']}")
            print(f"  From Node ID: {rel['start_node_id']}")
            print(f"  To Node ID: {rel['end_node_id']}")
            if rel["properties"]:
                print(f"  Properties ({len(rel['properties'])}):")
                for key, value in rel["properties"].items():
                    value_str = str(value)
                    # Clean up any weird characters
                    value_str = value_str.strip().rstrip('?')
                    if len(value_str) > 100:
                        value_str = value_str[:97] + "..."
                    print(f"    {key}: {value_str}")
            else:
                print(f"  Properties: None")


def create_summary_prompt(subgraph, search_result, query):
    """
    Create a simple prompt for DeepSeek API based on subgraph data
    """
    # Extract node information in a clean format
    nodes_text = "NODES INFORMATION:\n"
    for node in subgraph["nodes"]:
        nodes_text += f"- Node ID: {node['id']}\n"
        nodes_text += f"  Labels: {', '.join(node['labels'])}\n"
        if node["properties"]:
            nodes_text += "  Properties:\n"
            for key, value in node["properties"].items():
                # Convert value to string, clean it up
                value_str = str(value).replace('\n', ' ').replace('\r', ' ').strip()
                nodes_text += f"    {key}: {value_str}\n"
        nodes_text += "\n"
    
    # Extract relationship information
    relationships_text = "RELATIONSHIPS INFORMATION:\n"
    for rel in subgraph["relationships"]:
        relationships_text += f"- Relationship ID: {rel['id']}\n"
        relationships_text += f"  Type: {rel['type']}\n"
        relationships_text += f"  From Node ID: {rel['start_node_id']} to Node ID: {rel['end_node_id']}\n"
        if rel["properties"]:
            relationships_text += "  Properties:\n"
            for key, value in rel["properties"].items():
                value_str = str(value).replace('\n', ' ').replace('\r', ' ').strip()
                relationships_text += f"    {key}: {value_str}\n"
        relationships_text += "\n"
        
    
    # Construct a simple, direct prompt
    prompt = f"""Based on the following knowledge graph data, write a comprehensive and logical description in the style of a research paper abstract.

Query: {query}
Entity: {search_result['text']}

GRAPH DATA:
{nodes_text}
{relationships_text}

Please generate a clear, concise description that explains what this knowledge graph data represents. Focus on:
1. What entities/nodes are present
2. How they are connected through relationships
3. What properties and attributes are important

Write in a natural, flowing paragraph style like you would find in a research paper description. Do not use bullet points or JSON format. Just provide a well-written paragraph that summarizes the information.
Make sure you have clearly described the properties value with clear conditional dependences

Example style: "A research paper titled 'ACSAEM-2020-Ionic Conductive Thermoplastic Polymer Welding Layer for Low ElectrodeSolid Electroly...' (doi: 10.1234/advanced_electrolyte) reports on a composite polymer electrolyte named the PVC−TPU polymer layer. This electrolyte is a composite material consisting of poly(vinylene carbonate) (PVC) and thermoplastic polyurethane (TPU) polymers..."

IMPORTANT: Only use the information provided in the GRAPH DATA above. Do not add any external knowledge."""
    
    return prompt


def call_deepseek_api(prompt, temperature=0.2, max_tokens=1500):
    """
    Call DeepSeek API to generate summary
    """
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system", 
                "content": "You are a helpful assistant that summarizes knowledge graph data into clear, concise descriptions in the style of research paper abstracts. You only use the information provided to you."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"API Error: Status {response.status_code}, Response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return None


def subgraph_fuse_to_sentences(subgraphs, query, search_results):
    """
    Generate comprehensive summaries from subgraphs using DeepSeek API
    and save each summary as a separate JSON file
    """
    print(f"\n{'=' * 80}")
    print(f"GENERATING SUMMARIES USING DEEPSEEK API")
    print(f"Number of subgraphs to process: {len(subgraphs)}")
    print(f"{'=' * 80}")
    
    # Create output directory if it doesn't exist
    output_dir = SUMMARY_DIR
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    all_summaries = []
    
    for i, (subgraph, search_result) in enumerate(zip(subgraphs, search_results), 1):
        print(f"\n{'=' * 80}")
        print(f"Processing subgraph {i}/{len(subgraphs)}")
        print(f"Entity ID: {search_result['id']}")
        print(f"Entity Text: {search_result['text']}")
        print(f"{'=' * 80}")
        
        # Skip if subgraph is empty
        if not subgraph.get("nodes"):
            print("Empty subgraph, skipping...")
            continue
        
        # Prepare the prompt for DeepSeek API
        prompt = create_summary_prompt(subgraph, search_result, query)
        
        # Call DeepSeek API
        print(f"Calling DeepSeek API...")
        summary_text = call_deepseek_api(prompt)
        
        if summary_text:
            # Create a simple JSON structure with the summary
            summary_data = {
                "entity_id": search_result['id'],
                "entity_text": search_result['text'],
                "query": query,
                "summary": summary_text,
                "subgraph_info": {
                    "total_nodes": len(subgraph["nodes"]),
                    "total_relationships": len(subgraph["relationships"]),
                    "node_labels": list(set(label for node in subgraph["nodes"] for label in node["labels"])),
                    "relationship_types": list(set(rel["type"] for rel in subgraph["relationships"]))
                },
                "search_score": search_result['score'],
                "timestamp": str(datetime.now()),
                "max_hops": MAX_HOPS
            }
            
            # Save individual JSON file
            # Clean filename - remove special characters
            clean_entity_id = str(search_result['id']).replace('/', '_').replace('\\', '_').replace(':', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"summary_{clean_entity_id}_{timestamp}.json"
            output_path = os.path.join(output_dir, output_filename)
            
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(summary_data, f, indent=2, ensure_ascii=False)
                print(f"Summary saved to: {output_path}")
                
                # Print a preview of the summary
                preview = summary_text[:200] + "..." if len(summary_text) > 200 else summary_text
                print(f"Summary preview: {preview}")
                
                all_summaries.append(summary_data)
            except Exception as e:
                print(f"Error saving summary file: {e}")
        else:
            print(f"Failed to get summary for entity {search_result['id']}")
    
    # Save consolidated summary file
    if all_summaries:
        consolidated_filename = f"all_summaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        consolidated_path = os.path.join(output_dir, consolidated_filename)
        
        consolidated_data = {
            "query": query,
            "total_summaries": len(all_summaries),
            "summaries": all_summaries,
            "timestamp": str(datetime.now()),
            "max_hops": MAX_HOPS
        }
        
        try:
            with open(consolidated_path, 'w', encoding='utf-8') as f:
                json.dump(consolidated_data, f, indent=2, ensure_ascii=False)
            print(f"\nConsolidated summaries saved to: {consolidated_path}")
        except Exception as e:
            print(f"Error saving consolidated file: {e}")
    
    return all_summaries


def retrieve_and_display_subgraphs(entity_ids, neo4j_retriever, display_mode="summary"):
    """Retrieve and display subgraphs for given entity IDs"""
    print(f"\n{'=' * 80}")
    print(f"RETRIEVING SUBGRAPHS FROM KNOWLEDGE GRAPH (HOP={MAX_HOPS})")
    print(f"Number of entities: {len(entity_ids)}")
    print(f"{'=' * 80}")
    
    # Test Neo4j connection
    print("\nConnecting to Neo4j...")
    if not neo4j_retriever.test_connection():
        print("Failed to connect to Neo4j. Skipping subgraph retrieval.")
        return []
    
    print("Connected to Neo4j successfully")
    
    all_subgraphs = []
    
    for i, entity_id in enumerate(entity_ids, 1):
        print(f"\n{'=' * 80}")
        print(f"Retrieving subgraph {i}/{len(entity_ids)} ({MAX_HOPS}-hop neighbors)")
        print(f"Entity ID: {entity_id}")
        
        # DEBUG: Get entity details before retrieving subgraph
        entity_details = neo4j_retriever.get_entity_details(entity_id)
        if entity_details:
            print(f"Entity details: {entity_details['labels'][0]} - {entity_details.get('properties', {}).get('name', 'No name')}")
        else:
            print(f"Entity not found in database")
        
        print(f"{'=' * 80}")
        
        # Retrieve subgraph with configured hop level
        subgraph = neo4j_retriever.get_subgraph_for_entity(entity_id, max_hops=MAX_HOPS)
        
        if subgraph["nodes"]:
            # Display based on selected mode
            if display_mode == "detailed":
                display_subgraph_detailed(subgraph, entity_id, i)
            else:
                display_subgraph_summary(subgraph, entity_id, i)
            
            # Store subgraph
            subgraph["entity_id"] = entity_id
            all_subgraphs.append(subgraph)
        else:
            print(f"No subgraph found for entity ID: {entity_id}")
            # Add empty subgraph to maintain order
            all_subgraphs.append({"nodes": [], "relationships": [], "entity_id": entity_id})
    
    return all_subgraphs


def retrieve_and_analyze_summaries(query, summary_dir=SUMMARY_DIR):
    """
    Retrieve all summary JSON files from directory and analyze them to recommend electrolytes
    
    Args:
        query: Original user query
        summary_dir: Directory containing summary JSON files
    """
    print(f"\n{'=' * 80}")
    print(f"RETRIEVING AND ANALYZING SUMMARIES")
    print(f"Query: {query}")
    print(f"Directory: {summary_dir}")
    print(f"{'=' * 80}")
    
    # Find all summary JSON files in the directory
    summary_files = glob.glob(os.path.join(summary_dir, "summary_*.json"))
    
    if not summary_files:
        print("No summary files found in the directory.")
        return None
    
    print(f"Found {len(summary_files)} summary files.")
    
    # Read all summaries
    all_summaries = []
    for file_path in summary_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
                all_summaries.append(summary_data)
                print(f"Loaded: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    if not all_summaries:
        print("No valid summary data loaded.")
        return None
    
    # Prepare the prompt for DeepSeek API
    print(f"\nPreparing analysis prompt for DeepSeek API...")
    
    # Format the summaries for the prompt
    formatted_summaries = []
    for i, summary in enumerate(all_summaries, 1):
        formatted_summary = f"""
        [Reference Material {i}]
        Summary:
        {summary.get('summary', 'No summary available')}
        """
        formatted_summaries.append(formatted_summary)
    
    # Join all formatted summaries
    all_summaries_text = "\n".join(formatted_summaries)
    
    # Create the analysis prompt
    analysis_prompt = f"""
    According to the user query: "{query}", you have been provided with the following reference materials from knowledge graph summaries:

    {all_summaries_text}

    TASK:
    Based ONLY on the information provided in these reference materials above, analyze and recommend the most suitable electrolyte.
    
    REQUIREMENTS:
    1. You MUST base your recommendation ONLY on the information provided in the reference materials above.
    2. You MUST NOT use any external knowledge or information not found in the provided references.
    3. If the reference materials do not contain enough information about a specific component, leave it as "N/A".
    4. If no suitable electrolyte can be determined from the references, state this clearly.

    OUTPUT FORMAT:
    Provide your recommendation in EXACTLY this format:
    
    Polymer.Name: [Name of the polymer or "N/A" if not specified]
    Monomers.Name: [Names of monomers or "N/A" if not specified]
    Salts.Name: [Names of salts or "N/A" if not specified]
    Initiators.Name: [Names of initiators or "N/A" if not specified]
    
    ADDITIONAL EXPLANATION (Brief justification based on references):
    [Provide a brief explanation of why this electrolyte was recommended based on the references and MUST specify what is the paper's titles you obtain this recommendation and justification]
    
    IMPORTANT: Only output information that can be directly inferred from the provided reference materials.
    """
    
    print(f"Calling DeepSeek API for analysis...")
    
    # Call DeepSeek API for analysis
    analysis_result = call_deepseek_api(
        prompt=analysis_prompt,
        temperature=0.1,  # Lower temperature for more consistent output
        max_tokens=1000
    )
    
    if analysis_result:
        print(f"\nANALYSIS COMPLETE")
        print(f"\n{'=' * 80}")
        print(f"ELECTROLYTE RECOMMENDATION")
        print(f"{'=' * 80}")
        print(analysis_result)
        
        # Save the analysis result to a file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        analysis_filename = f"electrolyte_recommendation_{timestamp}.txt"
        analysis_path = os.path.join(summary_dir, analysis_filename)
        
        try:
            with open(analysis_path, 'w', encoding='utf-8') as f:
                f.write(f"Query: {query}\n")
                f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Number of References Analyzed: {len(all_summaries)}\n")
                f.write("\n" + "="*60 + "\n")
                f.write(analysis_result)
                f.write("\n" + "="*60 + "\n")
            
            print(f"\nAnalysis saved to: {analysis_path}")
        except Exception as e:
            print(f"Error saving analysis file: {e}")
        
        return analysis_result
    else:
        print("Failed to get analysis from DeepSeek API.")
        return None


def clean_summary_directory():
    """Delete all files in the summary directory before starting a new query"""
    print(f"\nCleaning summary directory: {SUMMARY_DIR}")
    
    # Find all files in the directory (not just JSON)
    all_files = glob.glob(os.path.join(SUMMARY_DIR, "*"))
    
    if not all_files:
        print("No files found to delete.")
        return
    
    deleted_count = 0
    for file_path in all_files:
        try:
            # Skip directories, only delete files
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted: {os.path.basename(file_path)}")
                deleted_count += 1
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")
    
    print(f"Total files deleted: {deleted_count}")


def chunk_query_and_search(query, model, embeddings_data):
    """
    New function: Chunk the query and search for each chunk
    Returns aggregated search results from all chunks
    """
    print(f"\n{'=' * 80}")
    print(f"QUERY CHUNKING AND MULTI-CHUNK SEARCH")
    print(f"{'=' * 80}")
    
    try:
        # Import and use the query chunker
        from query_chunker import chunk_query_to_list
        
        print(f"Original query: '{query}'")
        
        # Chunk the query
        chunks = chunk_query_to_list(query, ONTOLOGY_PATH, DEEPSEEK_API_KEY)
        
        print(f"Query split into {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks, 1):
            print(f"  Chunk {i}: {chunk}")
        
        # Search for each chunk and collect results
        all_search_results = []
        seen_entity_ids = set()  # To avoid duplicates
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\n{'=' * 80}")
            print(f"SEARCHING FOR CHUNK {i}/{len(chunks)}")
            print(f"Chunk: '{chunk}'")
            print(f"{'=' * 80}")
            
            # Search for this chunk
            chunk_results = search_entities(chunk, model, embeddings_data, top_k=3)
            
            # Display results for this chunk
            display_search_results(chunk, chunk_results)
            
            # Add unique results to the aggregated list
            for result in chunk_results:
                if result['id'] not in seen_entity_ids:
                    seen_entity_ids.add(result['id'])
                    # Add chunk information to result
                    result['source_chunk'] = chunk
                    result['chunk_index'] = i
                    all_search_results.append(result)
        
        print(f"\n{'=' * 80}")
        print(f"AGGREGATED SEARCH RESULTS")
        print(f"Total unique entities found: {len(all_search_results)}")
        print(f"{'=' * 80}")
        
        # Sort results by score
        all_search_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Display aggregated results
        for i, result in enumerate(all_search_results, 1):
            print(f"\nResult {i}:")
            print(f"  ID: {result['id']}")
            print(f"  Score: {result['score']:.6f}")
            print(f"  Entity: {result['text']}")
            print(f"  Source chunk: {result['source_chunk']}")
            print("-" * 80)
        
        # Return top results (limit to top 10 to avoid too many subgraphs)
        return all_search_results[:10]
        
    except ImportError as e:
        print(f"Warning: Query chunker not available: {e}")
        print("Falling back to original search method...")
        return search_entities(query, model, embeddings_data, top_k=3)
    except Exception as e:
        print(f"Error in query chunking: {e}")
        print("Falling back to original search method...")
        return search_entities(query, model, embeddings_data, top_k=3)


def main():
    """Main function with integrated query chunking, semantic search and KG retrieval"""
    # Configuration
    embeddings_path = "./entity_embeddings/entity_embeddings.pkl"
    model_name = 'all-MiniLM-L6-v2'
    
    print(f"\n" + "=" * 80)
    print(f"INTEGRATED QUERY CHUNKING, SEMANTIC SEARCH & KNOWLEDGE GRAPH RETRIEVAL")
    print(f"Configuration: MAX_HOPS = {MAX_HOPS}")
    print("=" * 80)
    print("Type your query and press Enter.")
    print("Type 'quit' to exit.")
    print("=" * 80)
    
    # Initialize Neo4j retriever
    neo4j_retriever = Neo4jSubgraphRetriever()
    
    # Load model and embeddings
    model, embeddings_data = load_embeddings_and_model(embeddings_path, model_name)
    
    if model is None or embeddings_data is None:
        return
    
    # Ask for display preference
    display_choice = 1  ############ USER CUSTOMISED ############
    display_mode = "detailed" if display_choice == "2" else "summary"
    
    while True:
        try:
            print("\n" + "-" * 80)
            
            # Clean summary directory BEFORE showing search query prompt
            clean_summary_directory()
            
            query = input("\nSearch query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            if not query:
                print("Please enter a query.")
                continue
            
            # Step 1: Perform query chunking and semantic search for all chunks
            print(f"\nProcessing query: '{query}'")
            results = chunk_query_and_search(query, model, embeddings_data)
            
            if not results:
                print("No results found for your query.")
                continue
            
            # Step 2: Ask if user wants to retrieve subgraphs
            retrieve_choice = 'y'  ############# USER CUSTOMISED #############
            
            if retrieve_choice in ['n', 'no']:
                print("Skipping subgraph retrieval.")
                continue
            
            # Step 3: Extract entity IDs and retrieve subgraphs
            entity_ids = [result['id'] for result in results]
            
            # Retrieve and display subgraphs
            all_subgraphs = retrieve_and_display_subgraphs(entity_ids, neo4j_retriever, display_mode)
            
            # Ask if user wants to generate summaries
            summary_choice = 'y' ############# USER CUSTOMISED #############
            
            if summary_choice not in ['n', 'no']:
                # Generate summaries using DeepSeek API
                summaries = subgraph_fuse_to_sentences(all_subgraphs, query, results)
                
                # Display summary information
                if summaries:
                    print(f"\nGenerated {len(summaries)} summaries")
                    print(f"Saved to: {SUMMARY_DIR}")
                    
                    # Ask if user wants to analyze the summaries
                    analyze_choice = 'y'  ############# USER CUSTOMISED #############
                    
                    if analyze_choice not in ['n', 'no']:
                        # Run the analysis function
                        retrieve_and_analyze_summaries(query)
            
            # # Option to export original results (existing functionality)
            # if all_subgraphs and any(subgraph.get("nodes") for subgraph in all_subgraphs):
            #     export_choice = input("\nExport original subgraph data to JSON file? (y/n): ").strip().lower()
            #     if export_choice in ['y', 'yes']:
            #         filename = input("Enter filename (default: search_results.json): ").strip()
            #         if not filename:
            #             filename = "search_results.json"
                    
            #         try:
            #             export_data = {
            #                 "query": query,
            #                 "search_results": results,
            #                 "subgraphs": all_subgraphs,
            #                 "timestamp": str(datetime.now()),
            #                 "max_hops": MAX_HOPS
            #             }
                        
            #             with open(filename, 'w') as f:
            #                 json.dump(export_data, f, indent=2, default=str)
                        
            #             print(f"Original data exported to {filename}")
            #         except Exception as e:
            #             print(f"Error exporting to file: {e}")
            
            print("\n" + "=" * 80)
            print("Search and retrieval complete!")
            print("=" * 80)
            
        except KeyboardInterrupt:
            print("\n\nExiting.")
            break
        except Exception as e:
            print(f"Error: {e}")
    
    # Close Neo4j connection
    neo4j_retriever.close()
    
def process_query_for_gui(query):
    """
    Process a query for GUI integration
    Returns the electrolyte recommendation text
    """
    # Configuration
    embeddings_path = "./entity_embeddings/entity_embeddings.pkl"
    model_name = 'all-MiniLM-L6-v2'
    
    print(f"\nProcessing query from GUI: '{query}'")
    
    # Initialize Neo4j retriever
    neo4j_retriever = Neo4jSubgraphRetriever()
    
    # Load model and embeddings
    model, embeddings_data = load_embeddings_and_model(embeddings_path, model_name)
    
    if model is None or embeddings_data is None:
        return "Error: Could not load embeddings or model"
    
    try:
        # Step 1: Perform query chunking and semantic search for all chunks
        results = chunk_query_and_search(query, model, embeddings_data)
        
        if not results:
            return "No results found for your query."
        
        # Step 2: Extract entity IDs and retrieve subgraphs
        entity_ids = [result['id'] for result in results]
        
        # Retrieve subgraphs
        all_subgraphs = retrieve_and_display_subgraphs(entity_ids, neo4j_retriever, "summary")
        
        # Clean summary directory before generating summaries
        clean_summary_directory()
        
        # Generate summaries using DeepSeek API
        summaries = subgraph_fuse_to_sentences(all_subgraphs, query, results)
        
        if not summaries:
            return "Could not generate summaries from the knowledge graph."
        
        # Analyze the summaries and get electrolyte recommendation
        analysis_result = retrieve_and_analyze_summaries(query)
        
        # Close Neo4j connection
        neo4j_retriever.close()
        
        if analysis_result:
            return analysis_result
        else:
            return "Could not generate electrolyte recommendation."
            
    except Exception as e:
        print(f"Error in process_query_for_gui: {e}")
        return f"Error processing query: {str(e)}"


if __name__ == "__main__":
    # Check if required packages are installed
    try:
        from neo4j import GraphDatabase
        import requests
    except ImportError as e:
        print(f"Error: Required package not installed: {e}")
        print("Please install missing packages using:")
        print("  pip install neo4j requests")
        exit(1)
    
    try:
        main()  # Keep the original interactive main() when run directly
    except Exception as e:
        print(f"Unexpected error: {e}")
