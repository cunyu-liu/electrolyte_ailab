#!/usr/bin/env python3
"""
Query Chunker using DeepSeek API
Splits user queries based on ontology-defined categories
"""

import json
import os
import re
from typing import Dict, List, Any, Optional
import requests

class OntologyBasedQueryChunker:
    def __init__(self, ontology_path: str, deepseek_api_key: str):
        """
        Initialize chunker with ontology and DeepSeek API
        
        Args:
            ontology_path: Path to ontology JSON file
            deepseek_api_key: DeepSeek API key
        """
        self.ontology_path = ontology_path
        self.api_key = deepseek_api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        
        # Load ontology
        self.ontology = self._load_ontology()
        
        # Extract entity categories from ontology
        self.entity_categories = self._extract_entity_categories()
        
        # Extract relationship types
        self.relationship_types = self._extract_relationship_types()
        
        # Extract entity attributes
        self.entity_attributes = self._extract_entity_attributes()
        
    def _load_ontology(self) -> Dict[str, Any]:
        """Load and validate ontology JSON"""
        if not os.path.exists(self.ontology_path):
            raise FileNotFoundError(f"Ontology file not found: {self.ontology_path}")
        
        with open(self.ontology_path, 'r', encoding='utf-8') as f:
            ontology = json.load(f)
        
        # Basic validation
        required_sections = ["entity_schemas", "relationship_attributes"]
        for section in required_sections:
            if section not in ontology:
                raise ValueError(f"Missing required section in ontology: {section}")
        
        return ontology
    
    def _extract_entity_categories(self) -> List[str]:
        """Extract all entity categories from ontology"""
        entity_schemas = self.ontology.get("entity_schemas", {})
        return list(entity_schemas.keys())
    
    def _extract_relationship_types(self) -> List[str]:
        """Extract all relationship types from ontology"""
        relationship_attrs = self.ontology.get("relationship_attributes", {})
        return list(relationship_attrs.keys())
    
    def _extract_entity_attributes(self) -> Dict[str, List[str]]:
        """Extract attributes for each entity category"""
        entity_schemas = self.ontology.get("entity_schemas", {})
        entity_attributes = {}
        
        for entity_type, schema in entity_schemas.items():
            attributes = list(schema.keys())
            entity_attributes[entity_type] = attributes
        
        return entity_attributes
    
    def _create_chunking_prompt(self, query: str) -> str:
        """
        Create prompt for DeepSeek API based on ontology structure
        """
        # Create a natural language description of entity categories
        entity_descriptions = []
        for entity_type, attributes in self.entity_attributes.items():
            attr_list = ", ".join(attributes[:5])  # Show first 5 attributes
            desc = f"- {entity_type}: Can have attributes like {attr_list}"
            entity_descriptions.append(desc)
        
        entity_descriptions_text = "\n".join(entity_descriptions)
        
        # Create relationship descriptions
        relationship_descriptions = []
        for rel_type in self.relationship_types:
            if rel_type in self.ontology.get("relationship_attributes", {}):
                attrs = list(self.ontology["relationship_attributes"][rel_type].keys())
                attr_list = ", ".join(attrs[:3])
                rel_desc = f"- {rel_type}: Can have attributes like {attr_list}"
                relationship_descriptions.append(rel_desc)
        
        relationship_descriptions_text = "\n".join(relationship_descriptions)
        
        prompt = f"""You are an expert query analyzer for battery electrolyte research.
Your task is to split the user's query into logical chunks based on the ontology structure.

ONTOLOGY STRUCTURE:
Entity Categories:
{entity_descriptions_text}

Relationship Types:
{relationship_descriptions_text}

USER QUERY: "{query}"

INSTRUCTIONS:
1. Analyze the query to identify mentions of different entity types (Electrolyte, Polymers, Salts, etc.)
2. Split the query where it naturally transitions between different aspects or entity types
3. Each chunk should be self-contained and focus on a specific aspect
4. Do not break chemical names or technical terms
5. Keep performance specifications with their relevant entities
6. Each chunk should be a meaningful piece that could be processed independently
7. Return ONLY the chunks in JSON format, nothing else

EXAMPLES:
Input: "Design a fluorinated ether-based electrolyte with lithium bis(fluorosulfonyl)imide (LiFSI) salt for high-voltage NMC811 cathodes (>4.5V) that maintains >80% capacity retention after 500 cycles at 1C rate"
Output: {{
  "query_1": "Design a fluorinated ether-based electrolyte",
  "query_2": "with lithium bis(fluorosulfonyl)imide (LiFSI) salt",
  "query_3": "for high-voltage NMC811 cathodes (>4.5V)",
  "query_4": "that maintains >80% capacity retention after 500 cycles at 1C rate"
}}

Input: "Find polymer electrolytes with PEO polymer and LiTFSI salt showing ionic conductivity >1 mS/cm at 60°C"
Output: {{
  "query_1": "Find polymer electrolytes",
  "query_2": "with PEO polymer and LiTFSI salt",
  "query_3": "showing ionic conductivity >1 mS/cm at 60°C"
}}

NOW PROCESS THIS QUERY:
Return your response as a JSON object with keys "query_1", "query_2", etc., each containing a chunk of the query."""
        
        return prompt
    
    def _call_deepseek_api(self, prompt: str) -> Optional[Dict[str, str]]:
        """
        Call DeepSeek API to get chunked query
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert in battery electrolyte research and query analysis. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # Try to find JSON-like structure
                json_str = content.strip()
                if json_str.startswith('{') and json_str.endswith('}'):
                    return json.loads(json_str)
                else:
                    return None
                    
        except Exception:
            return None
    
    def _fallback_chunking(self, query: str) -> Dict[str, str]:
        """
        Fallback chunking method when API fails
        Uses ontology-aware heuristics
        """
        chunks = {}
        chunk_num = 1
        
        # Try to split on common technical boundaries
        split_points = [
            r'\s+that\s+',
            r'\s+with\s+',
            r'\s+for\s+',
            r'\s+showing\s+',
            r'\s+having\s+',
            r'\s+exhibiting\s+',
            r'\s+at\s+',
            r',\s+(?=[A-Z])',  # Comma followed by capital letter (likely new clause)
        ]
        
        parts = [query]
        for pattern in split_points:
            new_parts = []
            for part in parts:
                if re.search(pattern, part, re.IGNORECASE):
                    split_result = re.split(pattern, part, flags=re.IGNORECASE)
                    # Add the split word back to each part except first
                    for i, split_part in enumerate(split_result):
                        split_part = split_part.strip()
                        if split_part:
                            if i > 0:
                                # Add back the split word (that, with, for, etc.)
                                match = re.search(pattern, part, re.IGNORECASE)
                                if match:
                                    split_word = match.group().strip()
                                    split_part = f"{split_word} {split_part}"
                            new_parts.append(split_part)
                else:
                    new_parts.append(part)
            parts = new_parts
        
        # Filter and format chunks
        for part in parts:
            if part and len(part.split()) >= 2:  # Minimum 2 words
                chunks[f"query_{chunk_num}"] = part.strip()
                chunk_num += 1
        
        if not chunks:
            chunks = {"query_1": query}
        
        return chunks
    
    def chunk_query(self, query: str) -> Dict[str, str]:
        """
        Main method to chunk a query using DeepSeek API with ontology awareness
        
        Args:
            query: User query string
            
        Returns:
            Dictionary with chunked queries {query_1: chunk1, query_2: chunk2, ...}
        """
        if not query or not query.strip():
            return {"query_1": ""}
        
        query = query.strip()
        
        # For very short queries, don't chunk
        if len(query.split()) <= 5:
            return {"query_1": query}
        
        # Create prompt based on ontology
        prompt = self._create_chunking_prompt(query)
        
        # Call DeepSeek API
        api_result = self._call_deepseek_api(prompt)
        
        if api_result and isinstance(api_result, dict):
            # Validate and clean the API result
            cleaned_result = {}
            for key, value in api_result.items():
                if isinstance(value, str) and value.strip():
                    cleaned_result[key] = value.strip()
            
            if cleaned_result:
                return cleaned_result
        
        # Fallback to heuristic chunking
        return self._fallback_chunking(query)


def chunk_query_to_list(query: str, ontology_path: str, api_key: str) -> List[str]:
    """
    Main function to import and use - takes a query and returns list of chunks
    
    Args:
        query: User query string
        ontology_path: Path to ontology JSON file
        api_key: DeepSeek API key
        
    Returns:
        List of chunked queries ['query_1', 'query_2', ...]
    """
    # Initialize chunker
    chunker = OntologyBasedQueryChunker(ontology_path, api_key)
    
    # Get chunked results
    chunk_dict = chunker.chunk_query(query)
    
    # Convert dictionary to sorted list
    chunks = []
    for i in range(1, len(chunk_dict) + 1):
        key = f"query_{i}"
        if key in chunk_dict:
            chunks.append(chunk_dict[key])
    
    return chunks

