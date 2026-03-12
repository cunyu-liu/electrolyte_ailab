"""
process_miner_by_patch.py
Batch processor for KG_info_miner.py
Processes all JSON files in a directory one by one and saves individual KG results
"""

import os
import json
import time
from typing import List, Dict, Any
import KG_info_miner as kg_miner

def get_json_files(directory_path: str) -> List[str]:
    """Get all JSON files from directory."""
    json_files = []
    if os.path.exists(directory_path) and os.path.isdir(directory_path):
        for file_name in os.listdir(directory_path):
            if file_name.endswith('.json'):
                json_files.append(os.path.join(directory_path, file_name))
    return sorted(json_files)  # Sort for consistent ordering

def process_single_file(file_path: str, output_dir: str) -> Dict[str, Any]:
    """
    Process a single JSON file through the knowledge graph miner.
    
    Args:
        file_path: Path to the JSON file
        output_dir: Directory to save the resulting KG JSON
    
    Returns:
        The mined knowledge graph
    """
    print(f"\n{'='*60}")
    print(f"Processing: {os.path.basename(file_path)}")
    print(f"{'='*60}")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Load the paper content
    paper_data = kg_miner.retrieve_text_json(file_path)
    
    # If retrieve_text_json returns a dict (single file mode)
    if isinstance(paper_data, dict):
        content_to_process = paper_data
    # If it returns a list (directory mode), take first element
    elif isinstance(paper_data, list) and len(paper_data) > 0:
        content_to_process = paper_data[0]
    else:
        print(f"Warning: No valid content found in {file_path}")
        return {}
    
    # Run the layered miner
    kg_result = kg_miner.test_layered_miner(content_to_process)
    
    # Generate output filename
    base_name = os.path.basename(file_path).replace('.json', '')
    output_filename = f"KG_{base_name}.json"
    output_path = os.path.join(output_dir, output_filename)
    
    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(kg_result, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved knowledge graph to: {output_path}")
    
    # Analyze and print stats
    stats = kg_miner.analyze_graph(kg_result)
    print(f"  Entities: {stats['entities']}, Attributes: {stats['attributes']}, Relations: {stats['relations']}")
    print(f"  Entity Types: {', '.join(stats['entity_types'])}")
    
    return kg_result

def process_all_files(directory_path: str, output_dir: str) -> List[Dict[str, Any]]:
    """
    Process all JSON files in the directory one by one.
    
    Args:
        directory_path: Path to directory containing JSON files
        output_dir: Directory to save all KG JSON files
    
    Returns:
        List of all mined knowledge graphs
    """
    json_files = get_json_files(directory_path)
    
    if not json_files:
        print(f"No JSON files found in: {directory_path}")
        return []
    
    print(f"Found {len(json_files)} JSON files to process:")
    for i, file_path in enumerate(json_files, 1):
        print(f"  {i}. {os.path.basename(file_path)}")
    
    all_results = []
    
    for i, file_path in enumerate(json_files, 1):
        print(f"\n{'#'*60}")
        print(f"Processing file {i} of {len(json_files)}")
        print(f"{'#'*60}")
        
        try:
            start_time = time.time()
            result = process_single_file(file_path, output_dir)
            processing_time = time.time() - start_time
            
            all_results.append({
                "file": os.path.basename(file_path),
                "kg": result,
                "processing_time_seconds": round(processing_time, 2)
            })
            
            print(f"\n✓ Completed in {processing_time:.2f} seconds")
            
            # Small delay between files to avoid rate limiting
            if i < len(json_files):
                print("Waiting 2 seconds before next file...")
                time.sleep(2)
                
        except Exception as e:
            print(f"\n✗ Error processing {file_path}: {e}")
            continue
    
    # Save summary of all processing
    if all_results:
        summary = {
            "total_files_processed": len(all_results),
            "files": [r["file"] for r in all_results],
            "processing_times": {
                r["file"]: r["processing_time_seconds"] for r in all_results
            }
        }
        
        summary_path = os.path.join(output_dir, "processing_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"BATCH PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Processed {len(all_results)} files")
        print(f"Results saved to: {output_dir}")
        print(f"Summary saved to: {summary_path}")
    
    return all_results

def main():
    """Main execution function."""
    # Configuration - Updated output directory
    input_directory = "/Users/java304/Desktop/KG_builder_process_by_batch/paper_text_json_cleaned"
    output_directory = "/Users/java304/Desktop/KG_builder_process_by_batch/eval_output_json"
    
    print("="*60)
    print("BATCH KNOWLEDGE GRAPH MINER")
    print("="*60)
    print(f"Input directory: {input_directory}")
    print(f"Output directory: {output_directory}")
    print("="*60)
    
    # Process all files
    process_all_files(input_directory, output_directory)

if __name__ == "__main__":
    main()