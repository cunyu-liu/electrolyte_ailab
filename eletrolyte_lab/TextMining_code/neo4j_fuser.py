#!/usr/bin/env python3
"""
neo4j_fuser_simple.py
Simplified version to fuse duplicate entities in Neo4j based on exact attribute matching.
"""

import json
from neo4j import GraphDatabase
from typing import Dict, List, Any

class Neo4jFuserSimple:
    def __init__(self, uri: str, user: str, password: str, ontology_path: str):
        """
        Initialize the Neo4j fuser.
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.ontology_path = ontology_path
        self.entity_schemas = {}
        self.excluded_attributes = ['id']
        
    def load_ontology(self):
        """Load ontology schema from JSON file."""
        with open(self.ontology_path, 'r') as f:
            ontology = json.load(f)
        
        self.entity_schemas = ontology.get('entity_schemas', {})
        print(f"Loaded ontology with {len(self.entity_schemas)} entity types")
        
    def get_all_entity_labels(self) -> List[str]:
        """Get all entity labels from ontology."""
        return list(self.entity_schemas.keys())
    
    def get_entity_attributes(self, entity_label: str) -> List[str]:
        """Get attribute names for a specific entity type."""
        schema = self.entity_schemas.get(entity_label, {})
        attributes = []
        for attr_name, attr_type in schema.items():
            if isinstance(attr_name, str) and attr_name not in self.excluded_attributes:
                attributes.append(attr_name)
        return attributes
    
    def find_duplicate_entities(self, entity_label: str) -> List[Dict[str, Any]]:
        """
        Find duplicate entities for a given label based on exact attribute matching.
        """
        # Get attributes from ontology (excluding 'id')
        attributes = self.get_entity_attributes(entity_label)
        
        if not attributes:
            print(f"No attributes found for entity: {entity_label}")
            return []
        
        print(f"Using {len(attributes)} attributes for {entity_label}: {attributes}")
        
        # Build query to find duplicates
        attr_match_clauses = []
        for attr in attributes:
            attr_match_clauses.append(f"(n1.{attr} = n2.{attr} OR (n1.{attr} IS NULL AND n2.{attr} IS NULL))")
        
        match_clause = " AND ".join(attr_match_clauses)
        
        query = f"""
        MATCH (n1:{entity_label}), (n2:{entity_label})
        WHERE elementId(n1) < elementId(n2) AND {match_clause}
        RETURN n1, n2, elementId(n1) as n1_elementId, elementId(n2) as n2_elementId
        """
        
        duplicates = []
        with self.driver.session() as session:
            result = session.run(query)
            
            for record in result:
                n1 = dict(record["n1"])
                n2 = dict(record["n2"])
                
                # Filter out excluded attributes
                n1_props = {k: v for k, v in n1.items() if k not in self.excluded_attributes}
                n2_props = {k: v for k, v in n2.items() if k not in self.excluded_attributes}
                
                duplicates.append({
                    "entity_label": entity_label,
                    "entity1_elementId": record["n1_elementId"],
                    "entity2_elementId": record["n2_elementId"],
                    "entity1_props": n1_props,
                    "entity2_props": n2_props
                })
        
        print(f"Found {len(duplicates)} duplicate pairs for {entity_label}")
        return duplicates
    
    def fuse_duplicate_pair(self, entity_label: str, entity1_elementId: str, entity2_elementId: str) -> bool:
        """
        Simple fusion method that redirects relationships and deletes duplicates.
        """
        try:
            with self.driver.session() as session:
                # Step 1: Redirect relationships from entity2 to entity1
                rel_query = f"""
                MATCH (e2:{entity_label}) WHERE elementId(e2) = $entity2_elementId
                OPTIONAL MATCH (e2)-[r_out]->(target)
                OPTIONAL MATCH (source)-[r_in]->(e2)
                RETURN 
                    collect({{type: type(r_out), target: elementId(target), props: properties(r_out)}}) as outgoing,
                    collect({{type: type(r_in), source: elementId(source), props: properties(r_in)}}) as incoming
                """
                
                result = session.run(rel_query, entity2_elementId=entity2_elementId)
                record = result.single()
                
                if record:
                    outgoing = record["outgoing"] or []
                    incoming = record["incoming"] or []
                    
                    # Redirect outgoing relationships
                    for rel in outgoing:
                        if rel["type"] and rel["target"]:
                            session.run(f"""
                                MATCH (e1:{entity_label}) WHERE elementId(e1) = $entity1_elementId
                                MATCH (target) WHERE elementId(target) = $target_elementId
                                MERGE (e1)-[new_rel:{rel['type']}]->(target)
                                SET new_rel = $rel_props
                                """,
                                entity1_elementId=entity1_elementId,
                                target_elementId=rel["target"],
                                rel_props=rel["props"] or {}
                            )
                    
                    # Redirect incoming relationships
                    for rel in incoming:
                        if rel["type"] and rel["source"]:
                            session.run(f"""
                                MATCH (source) WHERE elementId(source) = $source_elementId
                                MATCH (e1:{entity_label}) WHERE elementId(e1) = $entity1_elementId
                                MERGE (source)-[new_rel:{rel['type']}]->(e1)
                                SET new_rel = $rel_props
                                """,
                                source_elementId=rel["source"],
                                entity1_elementId=entity1_elementId,
                                rel_props=rel["props"] or {}
                            )
                
                # Step 2: Create merge record for auditing
                session.run("""
                    CREATE (mr:MergeRecord {
                        timestamp: datetime(),
                        source_entity_id: $entity2_elementId,
                        target_entity_id: $entity1_elementId,
                        entity_type: $entity_label,
                        note: 'Simple fusion - relationships redirected'
                    })
                    """,
                    entity1_elementId=entity1_elementId,
                    entity2_elementId=entity2_elementId,
                    entity_label=entity_label
                )
                
                # Step 3: Delete duplicate entity
                session.run(f"""
                    MATCH (e2:{entity_label}) WHERE elementId(e2) = $entity2_elementId
                    DETACH DELETE e2
                    """,
                    entity2_elementId=entity2_elementId
                )
                
                print(f"Successfully fused entity {entity2_elementId} into {entity1_elementId}")
                return True
                
        except Exception as e:
            print(f"Error fusing entities {entity2_elementId} into {entity1_elementId}: {e}")
            return False
    
    def fuse_all_duplicates_for_label(self, entity_label: str) -> Dict[str, Any]:
        """
        Find and fuse all duplicates for a specific entity label.
        """
        print(f"\n{'='*60}")
        print(f"Processing duplicates for: {entity_label}")
        print(f"{'='*60}")
        
        duplicates = self.find_duplicate_entities(entity_label)
        
        if not duplicates:
            return {
                "entity_label": entity_label,
                "total_duplicates_found": 0,
                "successful_fusions": 0,
                "failed_fusions": 0
            }
        
        successful = 0
        failed = 0
        fused_ids = set()
        
        for i, dup in enumerate(duplicates, 1):
            if (dup["entity1_elementId"] in fused_ids or 
                dup["entity2_elementId"] in fused_ids):
                print(f"Skipping pair {i}/{len(duplicates)} - one entity already fused")
                continue
            
            print(f"Fusing pair {i}/{len(duplicates)}: {dup['entity2_elementId']} into {dup['entity1_elementId']}")
            
            if self.fuse_duplicate_pair(
                entity_label=dup["entity_label"],
                entity1_elementId=dup["entity1_elementId"],
                entity2_elementId=dup["entity2_elementId"]
            ):
                successful += 1
                fused_ids.add(dup["entity2_elementId"])
            else:
                failed += 1
        
        stats = {
            "entity_label": entity_label,
            "total_duplicates_found": len(duplicates),
            "successful_fusions": successful,
            "failed_fusions": failed
        }
        
        print(f"Summary for {entity_label}: {successful} successful, {failed} failed")
        return stats
    
    def fuse_all_entities(self) -> Dict[str, Any]:
        """
        Fuse duplicates for all entity types in the ontology.
        """
        self.load_ontology()
        
        all_stats = {}
        total_successful = 0
        total_failed = 0
        
        entity_labels = self.get_all_entity_labels()
        
        print(f"\n{'#'*70}")
        print(f"Starting entity fusion for {len(entity_labels)} entity types")
        print(f"{'#'*70}\n")
        
        for entity_label in entity_labels:
            stats = self.fuse_all_duplicates_for_label(entity_label)
            all_stats[entity_label] = stats
            
            total_successful += stats["successful_fusions"]
            total_failed += stats["failed_fusions"]
        
        # Print summary
        print(f"\n{'#'*70}")
        print("FUSION COMPLETE")
        print(f"{'#'*70}")
        print(f"Total entity types processed: {len(entity_labels)}")
        print(f"Total successful fusions: {total_successful}")
        print(f"Total failed fusions: {total_failed}")
        print(f"{'#'*70}")
        
        return {
            "total_entity_types": len(entity_labels),
            "total_successful_fusions": total_successful,
            "total_failed_fusions": total_failed,
            "excluded_attributes": self.excluded_attributes,
            "detailed_stats": all_stats
        }
    
    def close(self):
        """Close the Neo4j driver."""
        self.driver.close()
    
    def export_fused_entities_to_csv(self, output_dir: str):
        """
        Export ALL fused entities from Neo4j to CSV files, 
        including both node entities and relationship entities.
        """
        import csv
        import os
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'='*60}")
        print(f"EXPORTING ALL FUSED ENTITIES TO CSV")
        print(f"Output directory: {output_dir}")
        print(f"{'='*60}")
        
        # Get ALL node labels from Neo4j (not just from ontology)
        # This includes both entity nodes and relationship nodes
        query = """
        CALL db.labels() YIELD label
        RETURN collect(label) as labels
        """
        
        with self.driver.session() as session:
            result = session.run(query)
            record = result.single()
            all_labels = record["labels"] if record else []
        
        print(f"Found {len(all_labels)} node labels in database:")
        
        total_exported = 0
        
        # Export node entities (Polymers, Salts, etc.)
        node_entity_labels = [
            'Polymers', 'Salts', 'Electrolyte', 'Initiators', 'Monomers', 
            'Additives', 'Ionic_Conductivity_Property', 'RESEARCH_PAPER'
        ]
        
        # Export relationship entities (CONSISTS_OF, MEASUREMENT, etc.)
        # If these are node entities in your graph
        relationship_entity_labels = [
            'CONSISTS_OF', 'MEASUREMENT', 'REPORTS', 'CONTAINS_DATA_ON'
        ]
        
        # Combine all labels to export
        labels_to_export = sorted(set(all_labels))
        
        for entity_label in labels_to_export:
            try:
                # Skip if no nodes of this label exist
                check_query = f"""
                MATCH (n:{entity_label})
                RETURN count(n) as count
                LIMIT 1
                """
                
                with self.driver.session() as session:
                    result = session.run(check_query)
                    count = result.single()["count"]
                    
                    if count == 0:
                        print(f"⏭ Skipping {entity_label}: No nodes found")
                        continue
                
                # Get all nodes of this label
                query = f"""
                MATCH (n:{entity_label})
                RETURN n.id as id, properties(n) as props
                ORDER BY n.id
                """
                
                with self.driver.session() as session:
                    result = session.run(query)
                    rows = []
                    row_count = 0
                    
                    for record in result:
                        entity_id = record["id"]
                        props = record["props"]
                        row_count += 1
                        
                        # Skip nodes without id (shouldn't happen, but just in case)
                        if not entity_id:
                            continue
                        
                        # Create a row with id as first column
                        row = {"id": str(entity_id)}
                        
                        # Add all other properties
                        for key, value in props.items():
                            if key != "id":  # Don't duplicate the id
                                # Convert None to empty string
                                if value is None:
                                    row[key] = ""
                                else:
                                    row[key] = str(value)
                        
                        rows.append(row)
                    
                    if rows:
                        # Determine all unique column names from all rows
                        all_columns = set()
                        for row in rows:
                            all_columns.update(row.keys())
                        
                        # Sort columns: id first, then alphabetical
                        sorted_columns = ["id"] + sorted([col for col in all_columns if col != "id"])
                        
                        # Write to CSV
                        csv_path = output_path / f"{entity_label}.csv"
                        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=sorted_columns)
                            writer.writeheader()
                            
                            # Write all rows
                            for row in rows:
                                # Ensure all columns exist in the row
                                for col in sorted_columns:
                                    if col not in row:
                                        row[col] = ""
                                writer.writerow(row)
                        
                        print(f"✓ Exported {len(rows):4} {entity_label} entities to {csv_path.name}")
                        total_exported += len(rows)
                        
            except Exception as e:
                print(f"✗ Error exporting {entity_label}: {e}")
        
        # Export Neo4j relationship information
        print(f"\n{'='*60}")
        print(f"EXPORTING RELATIONSHIP INFORMATION")
        print(f"{'='*60}")
        
        try:
            # Get all relationship types and their properties
            rel_query = """
            MATCH ()-[r]->()
            WITH DISTINCT type(r) as rel_type
            RETURN collect(rel_type) as rel_types
            """
            
            with self.driver.session() as session:
                result = session.run(rel_query)
                record = result.single()
                all_rel_types = record["rel_types"] if record else []
            
            if all_rel_types:
                print(f"Found {len(all_rel_types)} relationship types in database")
                
                # Create a CSV for each relationship type
                for rel_type in sorted(all_rel_types):
                    try:
                        # Get relationships with their properties
                        rel_details_query = f"""
                        MATCH (source)-[r:{rel_type}]->(target)
                        RETURN 
                            elementId(source) as source_id,
                            elementId(target) as target_id,
                            type(r) as relationship_type,
                            properties(r) as properties,
                            labels(source) as source_labels,
                            labels(target) as target_labels
                        LIMIT 1000  # Limit to avoid too much data
                        """
                        
                        with self.driver.session() as session:
                            result = session.run(rel_details_query)
                            rows = []
                            
                            for record in result:
                                row = {
                                    'source_id': record['source_id'],
                                    'target_id': record['target_id'],
                                    'relationship_type': record['relationship_type'],
                                    'source_labels': '|'.join(record['source_labels']),
                                    'target_labels': '|'.join(record['target_labels'])
                                }
                                
                                # Add relationship properties
                                props = record['properties']
                                for key, value in props.items():
                                    row[f'prop_{key}'] = str(value)
                                
                                rows.append(row)
                            
                            if rows:
                                # Write to CSV
                                safe_rel_type = rel_type.replace(':', '_').replace('/', '_')
                                rel_csv_path = output_path / f"RELATIONSHIP_{safe_rel_type}.csv"
                                
                                # Get all column names
                                all_columns = set()
                                for row in rows:
                                    all_columns.update(row.keys())
                                sorted_columns = sorted(all_columns)
                                
                                with open(rel_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                                    writer = csv.DictWriter(csvfile, fieldnames=sorted_columns)
                                    writer.writeheader()
                                    writer.writerows(rows)
                                
                                print(f"✓ Exported {len(rows):4} {rel_type} relationships to {rel_csv_path.name}")
                                
                    except Exception as e:
                        print(f"✗ Error exporting {rel_type} relationships: {e}")
                        
        except Exception as e:
            print(f"✗ Error exporting relationship information: {e}")
        
        print(f"\n{'='*60}")
        print(f"EXPORT COMPLETE")
        print(f"Total node entities exported: {total_exported}")
        print(f"Files saved to: {output_dir}")
        print(f"{'='*60}")
        
        return total_exported

def main():
    # Configuration
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "XXXXXXXXX"    ######### change to your own pwd ###########
    ONTOLOGY_PATH = "/Users/java304/Desktop/KG_builder_process_by_batch/ontology_v2.json"
    FUSED_ENTITIES_DIR = "/Users/java304/Desktop/KG_builder_process_by_batch/entities_info_fused"
    
    # Initialize and run
    fuser = Neo4jFuserSimple(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, ONTOLOGY_PATH)
    
    try:
        # Step 1: Run the fusion process
        print("\n" + "="*70)
        print("STEP 1: FUSING DUPLICATE ENTITIES")
        print("="*70)
        stats = fuser.fuse_all_entities()
        
        # Save statistics
        with open("fusion_statistics_simple.json", "w") as f:
            json.dump(stats, f, indent=2)
        print("\nStatistics saved to fusion_statistics_simple.json")
        
        # Step 2: Export fused entities to CSV
        print("\n" + "="*70)
        print("STEP 2: EXPORTING FUSED ENTITIES TO CSV")
        print("="*70)
        total_exported = fuser.export_fused_entities_to_csv(FUSED_ENTITIES_DIR)
        
        print(f"\n{'#'*70}")
        print("PROCESS COMPLETE!")
        print(f"{'#'*70}")
        print(f"Fusion statistics saved to: fusion_statistics_simple.json")
        print(f"Fused entities exported to: {FUSED_ENTITIES_DIR}")
        print(f"Total entities exported: {total_exported}")
        print(f"{'#'*70}")
        
    except Exception as e:
        print(f"Error during fusion process: {e}")
    finally:
        fuser.close()

if __name__ == "__main__":
    main()
