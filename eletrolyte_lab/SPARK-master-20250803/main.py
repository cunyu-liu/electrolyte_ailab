import os
import random
import re
import json
from datetime import datetime
from collections import defaultdict
from time import sleep,time
from pdfretrieve import list_files_in_directory, retrieve,retrieve_from_documents
from modelchat import ChatGPTChemicalAssistant



# deepseek
# api_key = "your-api-key"
# model = "deepseek-r1"
api_key = "sk-daud4ivzi2fdzoxq"
model = "deepseek-v3"


assistant = ChatGPTChemicalAssistant(api_key,model)


def extract_pdf_links(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return list(set(item['pdf_link'] for item in data))

def batch_process_links(pdf_links, batch_size=10):
    for i in range(0, len(pdf_links), batch_size):
        yield pdf_links[i:i + batch_size]


def merge_documents(input_data):
    merged_data = defaultdict(list)
    for entry in input_data:
        document = entry['Document']
        paragraph = entry['Paragraph'].replace('\n', ' ').strip()
        merged_data[document].append(paragraph)

    result = [{'Document': doc, 'Paragraphs': ' '.join(paras)} for doc, paras in merged_data.items()]

    return result


def find_documents(input_data, target_document):
    merged_data = defaultdict(list)
    for entry in input_data:
        document = entry['Document']
        paragraph = entry['Paragraph'].replace('\n', ' ').strip()
        merged_data[document].append(paragraph)

    if target_document in merged_data:
        result = ' '.join(merged_data[target_document])
    else:
        result = f"Document '{target_document}' not found."

    return result


def save_to_json_file(title, json_str, file_path='output_data_2009.json'):
    try:
        new_data = json.loads(json_str)

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = {}
        
        if title in existing_data:
            existing_data[title].extend(new_data)
        else:
            existing_data[title] = new_data
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)
        
        print(f"Data updated in JSON file '{file_path}'")
    except Exception as e:
        print(f"Try to save : {title}, Error : {e}")
        print("Generated data：")
        print(json_str)

def save_pdf_batch_to_txt(pdf_batch, output_file='processed_data.txt'):
    """
    Record processed files
    :param pdf_batch: list of PDF file paths to be saved
    :param output_file: output txt file path
    """
    try:
        with open(output_file, 'a', encoding='utf-8') as file:
            for pdf_path in pdf_batch:
                file.write(pdf_path + '\n') 
        print(f"PDF batch successfully saved to {output_file}")
    except Exception as e:
        print(f"Error writing to file {output_file}: {e}")


def generate_initial_json(relevant_text):
    prompt = """I will provide a text. Please read it carefully and extract all the information related to the specified keywords. Ensure that you identify and include **all relevant details from the entire TEXT**, especially focusing on the substances, values, and numbers. **Complete extraction and thoroughness are crucial.** Pay attention to all parts of the document to avoid missing any relevant information.

Keywords list:
1. Electrolyte: "An electrolyte is a substance that conducts electricity through the movement of ions in batteries, but not through the movement of electrons.Usually,an electrolyte consists of additives,solvents and salts"
2. Solvent: "A solvent is a substance that dissolves a solute, resulting in a solution(For example, Ethylene carbonate (EC), Dimethyl carbonate (DMC), etc.)"
3. Salt: "Ionic salt used in electrolyte solutions (For example, lithium bis(trifluoromethanesulfonyl)imide (LiTFSI) , lithium bisfluorosulfonimide (LiFSI), etc.)"
4. Additive: "Additives are substances incorporated into electrolytes to enhance their properties, thereby improving the overall performance of batteries(For example FloroEthylene carbonate (FEC), Vinylene carbonate (VC) etc.)"
5. Anode: "A anode is the electrode where reduction occurs during discharge, with ions being intercalated into the anode material. During charging, ions are released from the anode material.(For example graphite anodes,lithium metal anodes, etc)"
6. Cathode:"A cathode is the electrode where oxidation occurs during discharge,with ions being deintercalated from the cathode material.During charging,ions are intercalated into the cathode material.(For example,Lithium iron phosphate(LFP), Li-rich Mn-based cathode materials (LRMO), Lithium Nickel Cobalt Manganese Oxide (NCM), Elemental sulfur (S8), etc. But avoid Li and avoid Cu)". To determine the anode and cathode, reference can be made to the full-cell notation, such as Li | LiNi0.8Co0.1Mn0.1O2 (NCM811) or Li | LiNi0.5Co0.2Mn0.3O2 (NCM523), where the anode is Li and the cathode is the corresponding LiNi0.8Co0.1Mn0.1O2 (NCM811) or LiNi0.5Co0.2Mn0.3O2 (NCM523).
7. System of electrolyte: "The electrolyte system includes high concentration electrolytes (HCE), localized high concentration electrolytes (LHCE),Fluorinated electrolytes, weakly solvated electrolytes (WSE), and conventional types."
8. High concentration electrolytes (HCE): "High Concentration Electrolytes (HCE) are electrolytes with salt concentrations significantly exceeding conventional levels (>3 M). "
9. Localized high concentration electrolytes (LHCE) or Diluted high concentration electrolyte (DHCE): "LHCE modifies HCE by adding chemically inert diluents, preserving localized high-ion-density solvation structures while reducing bulk viscosity and cost."
10. Fluorinated electrolytes : "Fluorinated electrolytes are functionalized electrolyte systems engineered by incorporating fluorine atoms or fluorinated groups into solvents, lithium salts, or additives to enhance oxidation resistance, thermal stability, and interfacial compatibility."
11. Weakly solvating electrolytes (WSE): "Weakly solvating electrolytes are functional electrolyte systems engineered with low-donor-number solvents or anion-dominated solvation structures to weaken Li⁺ binding energy with solvents/anions, thereby accelerating interfacial desolvation kinetics."
12. Lowest Unoccupied Molecular Orbital (LUMO) energy level: "The LUMO level refers to the energy level of the Lowest Unoccupied Molecular Orbital in molecular orbital theory. "
13. Highest Occupied Molecular Orbital (HOMO) energy level: "The HOMO level refers to the energy level of the Highest Occupied Molecular Orbital in molecular orbital theory."
14. Viscosity (η): "Viscosity is a measure of the internal resistance of a fluid to flow. "
15. Dielelectric constant (ε): "The dielectric constant, namely relative permittivity, reflects the response of a matter toward an external electric field and has become one of the most important topics in physical science."
16. Melting point: "The melting point is the temperature at which a solid substance transitions to a liquid state under a given pressure."
17. Boiling point: "The boiling point is the temperature at which the saturated vapor pressure of a liquid equals the external pressure."
18. Flash Point: "The flash point is the lowest temperature at which a combustible liquid can evaporate to produce a sufficient amount of vapor to ignite briefly when exposed to a flame under specified conditions."
19. Performance: "The performance of an electrolyte involves the energy density, initial coulombic efficiency and cycling lifespan/cycle number of **the pouch cell or soft-packed batteries it constitutes**."
20. Energy density: "Energy density is the amount of energy stored per unit mass of a storage medium."
21. Coulombic Efficiency (CE): "Coulombic efficiency is the percentage ratio of the charge output during discharge to the charge input during charging."
22. Cycling lifespan: "Cycling lifespan is the number of charge-discharge cycles a battery can endure under specified operating conditions before its capacity decays to a threshold percentage (typically 80%) of its initial rated capacity."
23. Rate performance:  "A battery's ability to deliver or accept charge at various current densities, typically normalized as a C-rate. The C-rate is defined as the rate at which a battery is charged or discharged relative to its nominal capacity. For example, a 1C rate means the battery is fully charged or discharged in one hour, while a 2C rate corresponds to a 30-minute charge or discharge."

Please ensure to comprehensively extract all information related to each keyword. **All of them are important, so you avoid missing one.** Your JSON should include all details aside by the EXAMPLE, especially those regarding different conditions, values.

Now you know what these keywords' basic meanings and their difference, based on the provided text, ensure you have extracted all information from the entire document and carefully generate the JSON format data.
The output of the substance should be like **fill name (abbreviation)**.
Ensure that the content is original to the TEXT and AVOID COPYING the provided Example JSON content.
**Only generate the key showed in the JSON example.** 
If the key is a list type, it means there could be multiple values, so ensure to extract ALL of them. If the key is a single dictionary, it means there should be only one value, so provide the most relevant one.
If you find there is irrelevant data after carefully reading the text and you avoid inferring its value,you must output "N/A" for the key in the JSON example data, avoid deleting the key from the JSON data.
To determine the anode and cathode, reference can be made to the full-cell notation, such as Li | LiNi0.8Co0.1Mn0.1O2 (NCM811) or Li | LiNi0.5Co0.2Mn0.3O2 (NCM523), where the anode is Li and the cathode is the corresponding LiNi0.8Co0.1Mn0.1O2 (NCM811) or LiNi0.5Co0.2Mn0.3O2 (NCM523). Avoid symmetric cells (e.g., Li | Li), where Li avoid to be identified as the cathode, and avoid half cells (e.g., Li | Cu), where Cu avoid to be identified as the cathode. Note that in configurations like Li | Li and Li | Cu, while the anode can be inferred as Li, the cathode material avoid to be determined.
The performance refers specifically to that of pouch full cells, excluding coin cells, excluding symmetric cells, and excluding half cells.

TEXT:
{relevant_text}


Example JSON structure:
```json
[
  {{
    "Electrolytes": {{
      "Salts":{{"Name":"Li bis(fluorosulfonyl)imide (LiFSI)"}}, 
      "Solvents":{{"Name":"1,2-dimethoxyethane (DME)"}},
      "Additives":{{"Name":" 1,1,2,2-tetrafluoroethyl-2,2,3,3 tetrafluoropropylether (HFE)"}}
    }},
        
    "Anode":{{"Name":"Li metal"}},

    "Cathode":{{"Name":"NCM523 cathode"}},

    "System of electrolyte":{{
      "Type":  ,(choose from "Conventional" or "High concentration electrolytes (HCE)" or "Localized high concentration electrolytes (LHCE)" or "Fluorinated electrolytes" or "Weakly solvating electrolytes (WSE)")
    }},
    
    "Properties of electrolyte":{{
      "LUMO energy level":{{"Value": , 
                     "Unit": "eV"}},
      "HOMO energy level":{{"Value": , 
                     "Unit": "eV"}},
      "Viscosity (η)":{{"Value": , 
                    "Unit": "Pa s",
                    "Temperature": {{
                        "Value": ,
                        "Unit": "°C"}}
                  }},
      "Dielectric constant (ε)":{{"Value":  ,}},
      "Melting point":{{"Value": , 
                       "Unit": "°C"}},
      "Boiling point":{{"Value": , 
                       "Unit": "°C"}},
      "Flash Point":{{"Value": , 
                       "Unit": "°C"}}
    }},

    "Performance":{{
      "Energy density":{{"Value": , 
                       "Unit": "Wh/kg"}},
      "Coulombic efficiency":{{"Value": , 
                             "Unit": "%"}},
      "Cycle lifespan":{{"Value": ,
                        "Unit": "cycles"}},
      "Rate performance":{{"Value": ,
                        "Unit": "C"}}
    }}
  }}

  {{...
  }}
]
```
"""
  
    response = assistant.generate_answer(prompt.format(relevant_text=relevant_text))
    try:
        json_str = re.search(r'```json(.*?)```', response, re.DOTALL).group(1).strip() #LLM生成的json数据
    except Exception as e:
        print(e)
        json_str = [ ]

    return json_str


# # for complete
# def complete_json_data(relevant_text, json_str):
#     prompt_for_complete = """I will provide a text and a JSON data. Please read TEXT carefully and complte  the JSON data.
# Ensure that you identify and include all relevant details from the entire TEXT. Complete extraction and thoroughness are crucial. 
# Pay attention to all parts of the document to avoid missing any relevant information.
# Your work is to do finish the below tasks perfectly:
# Add 'CAS','SMILES' for key 'Monomers','Salts','Initiators',please pay attention to complete them with your own knowledge and the given TEXT.If you dont know it,please infer it by its 'Name'.
# Complete the data of 'Polymer.Name','Monomers.Name','Salts.Name'(usually Li salts like LiTFSI, LiFSI) and 'Initiators.Name' according to the TEXT . The 'N/A' data you should dig them in the given TEXT,such as Polymer's"Weight_Ratio" or "Molar_Ratio".
# If there are some 'Name' are just abbreviate,please change it to the full name of chemical standard.

# For the json data ,If the key is a list type, it means there could be multiple values,you could to extract **ALL** of them. If the key is a single dictionary, it means there should be only one value, so provide the most relevant one. 
# Your output must be the correct json format and dont write comments.
# Your json format must strictly follow the same as the json data,dont change or add,delete keys. But 'CAS','SMILES',more list values are allowed.  

# TEXT:
# {relevant_text}

# JSON data:
# ```json
# {json_data}
# ```"""
    
#     response = assistant.generate_answer(prompt_for_complete.format(relevant_text=relevant_text, json_data=json_str))
#     json_str = re.search(r'```json(.*?)```', response, re.DOTALL).group(1).strip() #LLM生成的json数据
#     return json_str

# def complete_json_data_specical(relevant_text, json_str):
#     prompt_for_complete = """I will provide a text and a JSON data. Please read TEXT carefully and complte  the JSON data.
# Ensure that you identify and include all relevant details from the entire TEXT. Complete extraction and thoroughness are crucial. 
# Pay attention to all parts of the document to avoid missing any relevant information.
# Your work is to do finish the below tasks perfectly:
# Pay special attention to ** Find all relevant data about "Polymers","Monomer(usually can be deduced from the polymer name,such as delete 'poly' and keep only the part in brackets,e.g.PEO's monomer is EO,poly(AB) C is AB)" , "Salts", "Initiators","Conductivity", add them as the same format data on the old JSON data ** All relevant results must be given, and your output is a complete JSON data with everything.

# For the json data ,If the key is a list type, it means there could be multiple values,you could to extract **ALL** of them. If the key is a single dictionary, it means there should be only one value, so provide the most relevant one. 
# Your output must be the correct json format and dont write comments.
# Your json format must strictly follow the same as the json data,dont change or add,delete keys. But 'CAS','SMILES',more list values are allowed.  

# TEXT:
# {relevant_text}

# JSON data:
# ```json
# {json_data}
# ```"""
    
#     response = assistant.generate_answer(prompt_for_complete.format(relevant_text=relevant_text, json_data=json_str))
#     json_str = re.search(r'```json(.*?)```', response, re.DOTALL).group(1).strip() #LLM生成的json数据
#     return json_str



# conductivity_queries = [
#     "The ion conductivity value measured for the polymer electrolyte in the study, including specific experimental conditions and results",
#     "Detailed measurement results of ionic conductivity in the electrolyte solution, covering various experimental setups and findings",
#     "Comprehensive data on the ionic conductivity of the polymer electrolyte, including measurement techniques and values",
#     "The ionic conductivity value of the electrolyte at various temperatures as reported in the research, along with experimental conditions",
#     "Measured conductivity values for the polymer in the study, including specific conditions and contexts in which measurements were taken",
#     "Results of conductivity measurements in the polymer electrolyte, with a focus on different temperatures and experimental conditions",
#     "Ionic conductivity values reported at different temperatures, including experimental setups and specific findings",
#     "Electrolyte solution conductivity value and detailed measurement data from the study, covering various experimental conditions",
#     "Experimental results of measured ionic conductivity, including specific methodologies and conditions used in the study",
#     "Ion conductivity of the polymer electrolyte and its value as detailed in the study, including specific experimental setups and results"
# ]

# conductivity_keywords =[
#     "conductivity",
#     "ion conductivity value",
#     "ionic conductivity measurement",
#     "ionic conductivity data",
#     "ionic conductivity of the electrolyte",
#     "conductivity value in polymer",
#     "conductivity measurement result",
#     "electrolyte conductivity value",
#     "measured ionic conductivity",
#     "polymer electrolyte ion conductivity"
# ]
    


if __name__ == "__main__":

    print("Starting...")

    batch_size = 1
    max_total = 150 # set max processed files

    total_processed = 1
    batch_counter = 0  # just for counter

    pdf_paths = list_files_in_directory("/Users/liucunyu/Downloads/SPARK-master-20250803/SicPDF")
    print(len(pdf_paths))

    for pdf_batch in batch_process_links(pdf_paths, batch_size):
        if total_processed >= max_total:
            break
        print(pdf_batch)

        start_time = time()

        save_pdf_batch_to_txt(pdf_batch)

        print(f"Batch {batch_counter} processing")
        batch_counter += 1 


        current_batch_size = min(batch_size, max_total - total_processed)
        re_start_time = time()
        retrieved_index_data = retrieve_from_documents(pdf_batch[:current_batch_size])
        re_end_time = time()
        retrieve_time = re_end_time - re_start_time
        print(f"Retrieve processed in {retrieve_time:.2f} seconds.")
        
        paragraphs_data = merge_documents(retrieved_index_data)
     

        for entry in paragraphs_data:
            if total_processed >= max_total:
                break
            title = entry['Document']
            relevant_text = entry['Paragraphs']

            ge_start_time = time()
            try:
              json_str = generate_initial_json(relevant_text)
              

              # json_str = complete_json_data(relevant_text,json_str)

              # when necessary
              # json_str = complete_json_data_specical(relevant_text,json_str)
              ge_end_time = time()
              generate_time = ge_end_time - ge_start_time
              print(f"Generation processed in {generate_time:.2f} seconds.")
              print(f"Document: {entry['Document']} has been processed")

              save_to_json_file(title,json_str)
              total_processed += 1

              print(f"{total_processed}") 
            except Exception as e:
              with open("errors.txt", "a",encoding='utf-8') as file:
                file.write(f"\nbatch_counter {batch_counter} escaped\n")
                file.write("__________________________________________________________\n")
                file.flush()
                print(e)


        end_time = time()
        batch_time = end_time - start_time
        print(f"Batch processed in {batch_time:.2f} seconds.")
        print(datetime.now())