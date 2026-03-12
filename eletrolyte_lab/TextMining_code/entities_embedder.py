import os
import pandas as pd
import glob
import pickle
import numpy as np
from pathlib import Path
import hashlib

# For embeddings - using SentenceTransformers (you can change to OpenAI or other models)
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    print("Warning: SentenceTransformers not installed. Using simple hash-based embeddings.")
    print("Install with: pip install sentence-transformers")
    EMBEDDING_AVAILABLE = False

class EntityEmbedder:
    def __init__(self, model_name='all-MiniLM-L6-v2', storage_dir='./entity_embeddings'):
        """
        Initialize the entity embedder.
        
        Args:
            model_name: Name of the SentenceTransformer model to use
            storage_dir: Directory to store embeddings and metadata
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # Initialize embedding model if available
        self.model = None
        self.use_simple_embeddings = False
        
        if EMBEDDING_AVAILABLE:
            try:
                print(f"Loading embedding model: {model_name}")
                self.model = SentenceTransformer(model_name)
                print("Model loaded successfully.")
            except Exception as e:
                print(f"Error loading model: {e}")
                print("Falling back to simple embeddings.")
                self.use_simple_embeddings = True
        else:
            print("Using simple hash-based embeddings (for demonstration).")
            print("For better results, install: pip install sentence-transformers")
            self.use_simple_embeddings = True
    
    def embed_text(self, text):
        """Convert text to embedding vector"""
        if self.model and not self.use_simple_embeddings:
            # Use SentenceTransformer
            return self.model.encode(text, convert_to_numpy=True)
        else:
            return False
    
    def process_entities(self, directory_path, use_fused=True):
        """
        Process all CSV files in the directory and create embeddings.
        
        Args:
            directory_path (str): Path to the directory containing CSV files
            use_fused (bool): If True, look for fused CSV files first
        
        Returns:
            dict: Dictionary with entity_id as key and (embedding, metadata) as value
        """
        # Try to use fused entities directory if requested
        if use_fused:
            fused_dir = "/Users/java304/Desktop/KG_builder_process_by_batch/entities_info_fused"
            if os.path.exists(fused_dir):
                print(f"Using fused entities from: {fused_dir}")
                directory_path = fused_dir
            else:
                print(f"Fused directory not found at {fused_dir}, using original directory")
        
        # Get all CSV files except relations_extracted.csv
        csv_files = glob.glob(os.path.join(directory_path, "*.csv"))
        csv_files = [f for f in csv_files if "relations_extracted.csv" not in f]
        
        if not csv_files:
            print(f"No CSV files found in {directory_path}")
            return {}
        
        processed_entities = {}
        
        for file_path in csv_files:
            # Get the base filename without extension
            file_name = os.path.basename(file_path)
            entity_type = os.path.splitext(file_name)[0]
            
            try:
                # Read the CSV file
                df = pd.read_csv(file_path)
                
                # Check if there are enough columns
                if len(df.columns) < 1:  # At least ID column
                    print(f"Skipping {file_name}: Not enough columns")
                    continue
                
                print(f"\nProcessing {file_name}...")
                print(f"  Total rows: {len(df)}")
                
                # Check if first column is 'id'
                if df.columns[0] != 'id':
                    print(f"  Warning: First column is '{df.columns[0]}', expected 'id'")
                
                # Process each row
                for idx, row in df.iterrows():
                    # Skip rows with missing ID
                    if pd.isna(row.iloc[0]):
                        continue
                    
                    # Get the ID from first column
                    entity_id = str(row.iloc[0]).strip()
                    
                    # Skip empty IDs
                    if not entity_id:
                        continue
                    
                    # Start building the string with entity type
                    entity_string = f"type: {entity_type}"
                    
                    # Add all attributes from all columns
                    for i in range(len(row)):
                        column_name = df.columns[i]
                        
                        # Skip the id column in the entity string (already included in metadata)
                        if column_name == 'id':
                            continue
                        
                        value = row.iloc[i]
                        
                        # Skip NaN values and empty strings
                        if pd.isna(value):
                            continue
                        
                        value_str = str(value).strip()
                        if not value_str:
                            continue
                        
                        # Add attribute to string
                        entity_string += f", {column_name}: {value_str}"
                    
                    # Create embedding
                    embedding = self.embed_text(entity_string)
                    
                    # Store metadata
                    metadata = {
                        'entity_id': entity_id,
                        'entity_string': entity_string,
                        'source_file': file_name,
                        'entity_type': entity_type,
                        'embedding_dim': len(embedding) if embedding is not False else 0
                    }
                    
                    # Store in dictionary
                    processed_entities[entity_id] = {
                        'embedding': embedding,
                        'metadata': metadata
                    }
                
                print(f"  Processed {len(processed_entities) - sum(1 for k in processed_entities if k.startswith('temp_'))} entities from {file_name}")
                
            except Exception as e:
                print(f"Error processing {file_name}: {e}")
                import traceback
                traceback.print_exc()
        
        return processed_entities
    
    def save_embeddings(self, entities_dict, filename='entity_embeddings.pkl'):
        """Save embeddings and metadata to disk"""
        save_path = self.storage_dir / filename
        
        # Prepare data for saving
        save_data = {
            'embeddings': [],
            'ids': [],
            'metadata': []
        }
        
        valid_count = 0
        for entity_id, data in entities_dict.items():
            embedding = data['embedding']
            if embedding is False or embedding is None:
                print(f"Warning: No embedding for entity {entity_id}, skipping")
                continue
            
            save_data['embeddings'].append(embedding)
            save_data['ids'].append(entity_id)
            save_data['metadata'].append(data['metadata'])
            valid_count += 1
        
        if not save_data['embeddings']:
            print("No valid embeddings to save!")
            return None
        
        # Convert to numpy arrays for efficiency
        save_data['embeddings'] = np.array(save_data['embeddings'])
        
        # Save to file
        with open(save_path, 'wb') as f:
            pickle.dump(save_data, f)
        
        print(f"\nSaved {valid_count} embeddings to {save_path}")
        print(f"Embedding shape: {save_data['embeddings'].shape}")
        
        return save_path
    
    def load_embeddings(self, filename='entity_embeddings.pkl'):
        """Load embeddings from disk"""
        load_path = self.storage_dir / filename
        
        if not load_path.exists():
            print(f"No embeddings found at {load_path}")
            return None
        
        with open(load_path, 'rb') as f:
            loaded_data = pickle.load(f)
        
        print(f"\nLoaded {len(loaded_data['ids'])} embeddings from {load_path}")
        print(f"Embedding shape: {loaded_data['embeddings'].shape}")
        
        return loaded_data
    
    def search_similar(self, query, embeddings_data, top_k=5):
        """
        Simple semantic search for similar entities.
        
        Args:
            query: Search query string
            embeddings_data: Loaded embeddings data
            top_k: Number of results to return
        
        Returns:
            list: Top-k similar entities with scores
        """
        if embeddings_data is None:
            print("No embeddings data loaded.")
            return []
        
        # Create query embedding
        query_embedding = self.embed_text(query)
        if query_embedding is False:
            print("Failed to create query embedding")
            return []
        
        # Calculate cosine similarity
        embeddings = embeddings_data['embeddings']
        
        # Normalize embeddings for cosine similarity
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        emb_norms = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        # Calculate similarities
        similarities = np.dot(emb_norms, query_norm)
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Prepare results
        results = []
        for idx in top_indices:
            results.append({
                'entity_id': embeddings_data['ids'][idx],
                'score': float(similarities[idx]),
                'metadata': embeddings_data['metadata'][idx]
            })
        
        return results

def main():
    # Configuration - CHANGE THIS to use fused entities
    entities_dir = "/Users/java304/Desktop/KG_builder_process_by_batch/entities_info_fused"  # Updated to use fused entities
    storage_dir = "./entity_embeddings"
    
    print("="*60)
    print("ENTITY EMBEDDER - USING FUSED ENTITIES")
    print("="*60)
    
    # Initialize embedder
    print("Initializing Entity Embedder...")
    embedder = EntityEmbedder(
        model_name='all-MiniLM-L6-v2',  # Small, efficient model
        storage_dir=storage_dir
    )
    
    # Process entities and create embeddings
    print(f"\nProcessing entities from: {entities_dir}")
    entities = embedder.process_entities(entities_dir, use_fused=True)
    
    if not entities:
        print("No entities processed. Exiting.")
        return
    
    print(f"\nSuccessfully processed {len(entities)} entities.")
    
    # Save embeddings to disk
    print("\nSaving embeddings to disk...")
    save_path = embedder.save_embeddings(entities)
    
    if save_path:
        print("\n" + "="*50)
        print("SETUP COMPLETE!")
        print("="*50)
        print("\nYour embeddings are now stored and ready for semantic search.")
        print(f"\nFiles created:")
        print(f"1. Embeddings data: {storage_dir}/entity_embeddings.pkl")
        
        # Verify the embeddings work
        print(f"\nVerifying embeddings...")
        loaded_data = embedder.load_embeddings()
        if loaded_data:
            print(f"✓ Successfully loaded {len(loaded_data['ids'])} embeddings")
            print(f"  Sample entity IDs: {loaded_data['ids'][:3] if len(loaded_data['ids']) >= 3 else loaded_data['ids']}")
    else:
        print("\nFailed to save embeddings!")

if __name__ == "__main__":
    main()