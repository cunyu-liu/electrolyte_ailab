import pandas as pd
import json
from neo4j import GraphDatabase
import os

class Neo4jKGImporter:
    def __init__(self, uri, user, password, data_dir, ontology_file="ontology_v2.json"):
        """
        Initialize Neo4j connection
        
        Args:
            uri: Neo4j database address
            user: username
            password: password
            data_dir: directory containing data files
            ontology_file: ontology file name
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.data_dir = data_dir
        self.ontology = None
        self.entities = {}  # store entity data
        self.relations = {}  # store relationship entity data
        self.load_ontology(ontology_file)
    
    def load_ontology(self, ontology_file):
        """Load ontology file"""
        try:
            with open(os.path.join(self.data_dir, ontology_file), 'r') as f:
                self.ontology = json.load(f)
            print(f"Successfully loaded ontology: {ontology_file}")
            
        except Exception as e:
            print(f"Failed to load ontology: {e}")
            self.ontology = {}
    
    def find_entity_csv_files(self):
        """Find and load all entity CSV files"""
        print("\nFinding entity CSV files...")
        
        if self.ontology and 'entity_schemas' in self.ontology:
            entity_types = list(self.ontology['entity_schemas'].keys())
            print(f"Ontology defines {len(entity_types)} entity types")
        else:
            # If no ontology file, scan all CSV files
            entity_types = []
        
        # Scan all CSV files in directory
        csv_files = [f for f in os.listdir(self.data_dir) 
                    if f.endswith('.csv') and 'relation' not in f.lower()]
        
        for csv_file in csv_files:
            entity_name = csv_file.replace('.csv', '')
            file_path = os.path.join(self.data_dir, csv_file)
            
            try:
                df = pd.read_csv(file_path)
                self.entities[entity_name] = df
                print(f"Loaded entity: {entity_name} ({len(df)} records)")
            except Exception as e:
                print(f"Failed to load {csv_file}: {e}")
    
    def find_relation_csv_files(self):
        """Find and load relationship entity CSV files"""
        print("\nFinding relationship entity CSV files...")
        
        # Get relationship types from ontology
        if self.ontology and 'relationship_attributes' in self.ontology:
            relation_types = list(self.ontology['relationship_attributes'].keys())
            print(f"Ontology defines {len(relation_types)} relationship types")
        else:
            relation_types = []
        
        # Scan for possible CSV files
        for relation_type in relation_types:
            possible_files = [
                f"{relation_type}.csv",
                f"{relation_type.lower()}.csv",
                f"{relation_type.replace('_', '').lower()}.csv"
            ]
            
            for filename in possible_files:
                file_path = os.path.join(self.data_dir, filename)
                if os.path.exists(file_path):
                    try:
                        df = pd.read_csv(file_path)
                        self.relations[relation_type] = df
                        print(f"Loaded relationship entity: {relation_type} ({len(df)} records)")
                        break
                    except Exception as e:
                        print(f"Failed to load {filename}: {e}")
    
    def create_entities_in_neo4j(self):
        """Create entity nodes in Neo4j"""
        print("\nCreating entity nodes...")
        
        with self.driver.session() as session:
            for entity_type, df in self.entities.items():
                print(f"  Creating {entity_type} nodes...")
                
                # Ensure there is an id column
                if 'id' not in df.columns and len(df.columns) > 0:
                    print(f"    Warning: file {entity_type}.csv doesn't have 'id' column, trying to use first column")
                    # Try to find ID column
                    for col in df.columns:
                        if 'id' in col.lower() or col.lower() == 'uuid':
                            df = df.rename(columns={col: 'id'})
                            break
                    else:
                        # If not found, use first column
                        df = df.rename(columns={df.columns[0]: 'id'})
                
                # Batch create nodes
                batch_size = 100
                for i in range(0, len(df), batch_size):
                    batch = df.iloc[i:i+batch_size]
                    
                    for _, row in batch.iterrows():
                        # Prepare node properties
                        properties = {}
                        for col, value in row.items():
                            if pd.isna(value):  # Skip null values
                                continue
                            
                            # Ensure value is string type
                            if isinstance(value, (int, float)):
                                properties[col] = str(value)
                            else:
                                properties[col] = str(value).strip()
                        
                        if 'id' not in properties:
                            print(f"    Warning: Skipping row: no ID")
                            continue
                        
                        # Create node
                        query = f"""
                        CREATE (n:{entity_type} {{id: $id}})
                        SET n = $properties
                        """
                        
                        try:
                            session.run(query, 
                                      id=str(properties['id']), 
                                      properties=properties)
                        except Exception as e:
                            print(f"    Warning: Failed to create node: {properties['id'][:8]}... - {e}")
    
    def create_relations_from_extracted_file(self):
        """Create relationships from extracted relationship file, with relationship properties"""
        print("\nCreating relationship connections...")
        
        # Find relationship extraction file
        relations_file = None
        for filename in os.listdir(self.data_dir):
            if 'relation' in filename.lower() and 'extracted' in filename.lower():
                relations_file = os.path.join(self.data_dir, filename)
                break
        
        if not relations_file:
            print("Failed: No relationship extraction file found (containing 'relation' and 'extracted')")
            return
        
        try:
            relations_df = pd.read_csv(relations_file)
            print(f"Loaded relationship extraction file: {len(relations_df)} relationships")
            
            # Display column names for debugging
            print(f"  File columns: {list(relations_df.columns)}")
        except Exception as e:
            print(f"Failed to load relationship extraction file: {e}")
            return
        
        # Process relationship data
        with self.driver.session() as session:
            processed_count = 0
            error_count = 0
            
            for _, row in relations_df.iterrows():
                try:
                    # Get relationship data - key modification: get relationship_type from relations_extracted.csv
                    start_id = None
                    end_id = None
                    relation_id = None
                    relationship_type = None  # New variable
                    
                    # Try to identify columns
                    for col in row.index:
                        col_lower = col.lower()
                        if 'start' in col_lower:
                            start_id = str(row[col])
                        elif 'end' in col_lower or 'target' in col_lower:
                            end_id = str(row[col])
                        elif 'relation' in col_lower and 'id' in col_lower:
                            relation_id = str(row[col])
                        elif 'relationship_type' in col_lower:  # New: get relationship type
                            relationship_type = str(row[col])
                    
                    # If not identified, try to get by position
                    if not all([start_id, end_id, relation_id]):
                        if len(row) >= 3:
                            start_id = str(row.iloc[0])
                            end_id = str(row.iloc[1])
                            relation_id = str(row.iloc[2])
                            if len(row) >= 4:  # Fourth column might be relationship_type
                                relationship_type = str(row.iloc[3])
                        else:
                            error_count += 1
                            continue
                    
                    # If relationship_type not found, try to find from column names
                    if not relationship_type:
                        for col in row.index:
                            if 'type' in col.lower():
                                relationship_type = str(row[col])
                                break
                    
                    # Find relationship attributes
                    relation_attributes = self.find_relation_attributes(relation_id)
                    
                    # Key modification: add relationship_type to attributes
                    if relationship_type:
                        relation_attributes['relationship_type'] = relationship_type
                    
                    # Create relationship with attributes
                    self.create_relationship_with_attributes(
                        session, start_id, end_id, relation_id, relation_attributes
                    )
                    
                    processed_count += 1
                    
                    # Show progress
                    if processed_count % 100 == 0:
                        print(f"    Processed {processed_count} relationships...")
                        
                except Exception as e:
                    error_count += 1
                    if error_count <= 5:  # Only show first 5 errors
                        print(f"    Warning: Failed to process relationship: {e}")
            
            print(f"Completed: Successfully processed {processed_count} relationships, failed {error_count}")

    def create_relationship_with_attributes(self, session, start_id, end_id, relation_id, attributes):
        """Create relationship with attributes"""
        # Get relationship type - should now get correct type from attributes
        relation_type = attributes.get('relationship_type', 
                                    attributes.get('relation_type', 
                                                    attributes.get('type', 'RELATED_TO')))
        
        # Clean relationship type to be suitable as Neo4j relationship type
        # Remove spaces and special characters, but keep original meaning
        clean_type = ''.join(c if c.isalnum() else '_' for c in relation_type)
        clean_type = clean_type.upper()
        
        # Build property dictionary
        rel_properties = {'relation_id': relation_id}
        
        # Add all attributes
        for key, value in attributes.items():
            if key not in ['relation_type', 'relationship_type', 'type']:
                rel_properties[key] = value
        
        print(f"    Creating relationship: {start_id[:8]}... -[{clean_type}]-> {end_id[:8]}...")
        
        # Create relationship query
        query = f"""
        MATCH (start {{id: $start_id}})
        MATCH (end {{id: $end_id}})
        CREATE (start)-[r:`{clean_type}` $properties]->(end)
        RETURN r
        """
        
        try:
            result = session.run(query, 
                            start_id=start_id, 
                            end_id=end_id, 
                            properties=rel_properties)
            result.consume()  # Ensure query execution
        except Exception as e:
            # If failed, try using generic relationship type
            print(f"    Warning: Failed to use dynamic relationship type: {e}, using generic type instead")
            query_fallback = """
            MATCH (start {id: $start_id})
            MATCH (end {id: $end_id})
            CREATE (start)-[r:RELATIONSHIP $properties]->(end)
            RETURN r
            """
            session.run(query_fallback, 
                    start_id=start_id, 
                    end_id=end_id, 
                    properties=rel_properties)
    
    def find_relation_attributes(self, relation_id):
        """Find attributes based on relationship ID in all relationship entity files"""
        attributes = {}
        
        # Add debug output to see what's happening
        print(f"    Looking for relation_id: {relation_id}")
        
        # Check relationship entity files first
        for relation_type, df in self.relations.items():
            if 'id' in df.columns:
                # Find matching relationship ID
                matches = df[df['id'].astype(str) == str(relation_id)]
                if not matches.empty:
                    # Get attributes
                    row = matches.iloc[0]
                    for col in df.columns:
                        if col != 'id' and not pd.isna(row[col]):
                            attributes[col] = str(row[col])
                    
                    # Add relationship type information
                    attributes['relation_type'] = relation_type
                    print(f"      Found in relationship entity: {relation_type}")
                    return attributes
        
        # NEW: Also check ALL entity files for matching ID
        for entity_name, df in self.entities.items():
            if 'id' in df.columns:
                matches = df[df['id'].astype(str) == str(relation_id)]
                if not matches.empty:
                    row = matches.iloc[0]
                    for col in df.columns:
                        if col != 'id' and not pd.isna(row[col]):
                            attributes[col] = str(row[col])
                    
                    attributes['source_entity'] = entity_name
                    print(f"      Found in entity: {entity_name}")
                    return attributes
        
        print(f"      Warning: No attributes found for relation_id: {relation_id}")
        return attributes
        
    
    def create_indexes_and_constraints(self):
        """Create indexes and constraints"""
        print("\nCreating indexes and constraints...")
        
        with self.driver.session() as session:
            # Create ID indexes for all entity types
            for entity_type in self.entities.keys():
                try:
                    # Create uniqueness constraint
                    constraint_query = f"""
                    CREATE CONSTRAINT IF NOT EXISTS 
                    FOR (n:{entity_type}) 
                    REQUIRE n.id IS UNIQUE
                    """
                    session.run(constraint_query)
                    
                    # Create index
                    index_query = f"""
                    CREATE INDEX IF NOT EXISTS 
                    FOR (n:{entity_type}) 
                    ON (n.id)
                    """
                    session.run(index_query)
                    
                    print(f"Created indexes and constraints for {entity_type}")
                    
                except Exception as e:
                    print(f"Warning: Failed to create indexes/constraints for {entity_type}: {e}")
    
    def validate_data(self):
        """Validate data integrity"""
        print("\n" + "="*50)
        print("Data Validation")
        print("="*50)
        
        print(f"Entity files: {len(self.entities)}")
        for name, df in self.entities.items():
            print(f"  {name}: {len(df)} records")
        
        print(f"\nRelationship entity files: {len(self.relations)}")
        for name, df in self.relations.items():
            print(f"  {name}: {len(df)} records")
        
        # Count total nodes
        total_entities = sum(len(df) for df in self.entities.values())
        print(f"\nTotal entity nodes: {total_entities}")
    
    def visualize_kg(self):
        """Provide visualization suggestions"""
        print("\n" + "="*60)
        print("Knowledge Graph Construction Completed!")
        print("="*60)
        
        print("\nRun the following queries in Neo4j Browser (http://localhost:7474):")
        
        print("\n1. View knowledge graph statistics:")
        print("""
        // View all node types and counts
        MATCH (n) 
        RETURN labels(n)[0] as entity_type, count(n) as count 
        ORDER BY count DESC
        
        // View all relationship types and counts
        MATCH ()-[r]->() 
        RETURN type(r) as relation_type, count(r) as count
        ORDER BY count DESC
        """)
        
        print("\n2. View knowledge graph structure:")
        print("""
        // View complete knowledge graph (limited)
        MATCH (n)-[r]->(m) 
        RETURN n, r, m 
        LIMIT 50
        
        // View only relationships
        MATCH ()-[r]->() 
        RETURN r 
        LIMIT 30
        """)
        
        print("\n3. Find specific entities and their connections:")
        print(f"""
        // Find entity by specific ID
        MATCH (n {{id: 'Enter entity ID'}})
        RETURN n
        
        // Find all connections of an entity
        MATCH (n {{id: 'Enter entity ID'}})-[r]-(connected)
        RETURN n, r, connected
        """)
        
        print("\n4. Analyze nodes with highest connectivity:")
        print("""
        MATCH (n)
        OPTIONAL MATCH (n)-[r]-()
        WITH n, count(r) as degree
        RETURN n.id as id, labels(n)[0] as type, degree
        ORDER BY degree DESC
        LIMIT 10
        """)
        
        print("\n5. View specific relationship types:")
        print("""
        // View all relationship types
        CALL db.relationshipTypes() YIELD relationshipType
        RETURN relationshipType
        
        // View specific relationship type
        MATCH ()-[r:RELATION_TYPE_NAME]->()
        RETURN r LIMIT 20
        """)
    
    def close(self):
        """Close database connection"""
        self.driver.close()
    
    def import_all(self):
        """Execute complete import process"""
        print("Starting import of knowledge graph data to Neo4j")
        print("=" * 60)
        
        try:
            # 1. Load ontology file
            if not self.ontology:
                print("Warning: No ontology file loaded, will scan all CSV files")
            
            # 2. Find and load entity files
            self.find_entity_csv_files()
            
            if not self.entities:
                print("Error: No entity files found")
                return
            
            # 3. Find and load relationship entity files
            self.find_relation_csv_files()
            
            # 4. Validate data
            self.validate_data()
            
            # 5. Create indexes and constraints
            self.create_indexes_and_constraints()
            
            # 6. Create entity nodes
            self.create_entities_in_neo4j()
            
            # 7. Create relationship connections (with attributes)
            self.create_relations_from_extracted_file()
            
            # 8. Provide visualization suggestions
            self.visualize_kg()
            
            print("\nImport completed successfully!")
            
        except Exception as e:
            print(f"\nError during import: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.close()


# Simplified usage script
if __name__ == "__main__":
    # Configuration parameters
    CONFIG = {
        "uri": "bolt://localhost:7687",
        "user": "neo4j",
        "password": "XXXXXX",  ########### Please change to your password
        "data_dir": "/Users/java304/Desktop/KG_builder_process_by_batch/entities_info",
        "ontology_file": "ontology_v2.json"
    }
    
    print("Battery Knowledge Graph Import Tool")
    print("=" * 40)
    
    # Create importer
    importer = Neo4jKGImporter(**CONFIG)
    
    # Start import
    importer.import_all()
