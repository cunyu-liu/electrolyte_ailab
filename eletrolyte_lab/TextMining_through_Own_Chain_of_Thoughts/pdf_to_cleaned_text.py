#!/usr/bin/env python3
"""
Simple PDF to Text Converter using pdfminer.six
Alternative version with hardcoded directories
"""

import os
import json
from pathlib import Path

# pdfminer.six imports
from pdfminer.high_level import extract_text


def pdf_to_text_simple(pdf_path: str) -> str:
    """Simple text extraction from PDF"""
    try:
        return extract_text(pdf_path)
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return ""


def main_simple(input_dir="XXXXX", output_dir="XXXXX"):
    """
    Simple main function with customizable directories
    
    Args:
        input_dir: Directory containing PDF files
        output_dir: Directory to save JSON files
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each PDF in input directory
    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.pdf'):
            # Get full paths
            pdf_path = os.path.join(input_dir, filename)
            
            # Get title from filename (without .pdf extension)
            title = os.path.splitext(filename)[0]
            
            # Extract text
            content = pdf_to_text_simple(pdf_path)
            
            # Create JSON structure
            json_data = {
                "title": title,
                "content": content
            }
            
            # Save as JSON
            output_file = os.path.join(output_dir, f"{title}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            print(f"Converted: {filename} -> {title}.json")
    
    print(f"\nAll PDFs converted to JSON in '{output_dir}'")


if __name__ == "__main__":
    # You can customize the directories here
    INPUT_DIRECTORY = "/Users/java304/Desktop/KG_builder_process_by_batch/research_paper_store_here"  # Change this to your input directory
    OUTPUT_DIRECTORY = "/Users/java304/Desktop/KG_builder_process_by_batch/paper_text_json_cleaned"  # Change this to your output directory
    
    # Run the conversion
    main_simple(INPUT_DIRECTORY, OUTPUT_DIRECTORY)