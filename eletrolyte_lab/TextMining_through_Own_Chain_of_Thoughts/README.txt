Text mining, KG building, visualisation, user_query_answering
ALL in ONE:
Developed by Jiahua Xiao and Xiongfei Du on 06/02/2026

----------------
Prerequisites:
----------------
	1. You MUST "pip install" all required packages ONE by ONE
	2. You MUST pre-defined ontology and stored as name "ontology_v2.json"
	3. You MUST make sure the format of new ontology is EXACTLY as same as ontology_v2.json

-----------------
Function 1: text mining
-----------------
PLEASE follow step by step:

1. Store original research paper in pdf format in "research"_paper_store_here
2. Run "pdf_to_cleaned_text.py"
	- change "INPUT_DIRECTORY" in main()
	- change "OUTPUT_DIRECTORY" in main()
3. Run "process_miner_by_patch.py"
	- change "input_directory" in main()
	- change "output_directory" in main()
	- CHANGE dictionaries of "entity_relationships", "relationship_attributes", "entity_schemas" from predefined ontology_v2.json in "KG_info_miner.py" (MAKE SURE format correct!!!)
	- CHANGE all "DEEPSEEK API CONFIGURATION" section in "KG_info_miner.py"

-----------------
Function 2: KG building and visualisation
-----------------

4. Run "assign_id_to_entities.py"
	- change "input_dir" in main()
	- change "output_dir" in main()
	- change "relationship_attributes" dictionary by copying and pasting from "ontology_v2.json" (NOTE: make sure format consistent)
5. Run "ontology_csv_container.py"
	- change "ontology_path" in main()
	- change "output_dir" in main()
6. Run "sort_KG_miner_output.py"
	- change "input_dir" in main()
	- change "csv_path" and "ontology_path" in sort_entities_relations_to_csv function(...)
	- change "ontology_path" and "entities_dir" in sort_entities_to_csv function(...)
7. Run "neo4j_KG_importer.py"
	- change the "CONFIG" inside "if __name__ == "__main__:"

	NOW: You can visualise the KG by logging in on neo4j web

8. Run "neo4j_fuser.py"
	- change the "NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD", "ONTOLOGY_PATH", "FUSED_ENTITIES_DIR" in main()

	NOW: You can visualise fused version of KG by logging in on neo4j web

-----------------
Function 3: user_query_answering system
-----------------

9. Run "entities_embedder"
	- change "entities_dir" in main()
10. Run "main_GUI.py"
	- change all "CONFIGURATION" section in "query_search_entities.py"

	NOW: You can type your query and waiting for 1 min to return the answer based on KG searching.

NOTE: You can change the prompt in "retrieve_and_analyze_summaries" function in "query_search_entities.py" to enable the chatbot answer any type queried NOT JUST recommendation of electrolytes which based on user query.














































































To someone who finds this very last 彩蛋：
	I wish you all the best and succeed in whatever future/path you choose to take!




