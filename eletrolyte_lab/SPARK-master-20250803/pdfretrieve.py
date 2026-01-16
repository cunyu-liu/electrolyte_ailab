import json
import os
import re
import requests
import fitz
import nltk
import fitz  # PyMuPDF
from collections import defaultdict
from semanticsearch import SemanticSearch
from textindex import TextIndexer
import concurrent.futures

# nltk.download('punkt')
# nltk.download('punkt_tab')

query_keywords = [
    "Electrolyte",
    "Solvent",
    "Salt",
    "Additive",
    "Anode",
    "Graphite anodes",
    "Lithium metal anodes",
    "Cathode",
    "Lithium iron phosphate(LFP)",
    "Li-rich Mn-based cathode materials (LRMO)",
    "Lithium Nickel Cobalt Manganese Oxide (NCM)",
    "Elemental sulfur (S8)",
    "Li | LiNi0.8Co0.1Mn0.1O2(NCM811)",
    "Li | LiNi0.5Co0.2Mn0.3O2 (NCM523)",
    "Li | NCM811",
    "Li | NCM523",
    "System of electrolyte",
    "High concentration electrolytes (HCE)",
    "Localized high concentration electrolytes (LHCE)",
    "Diluted high concentration electrolyte (DHCE)",
    "Fluorinated electrolytes",
    "Weakly solvating electrolytes (WSE)",
    "Lowest Unoccupied Molecular Orbital energy level",
    "LUMO level",
    "Highest Occupied Molecular Orbital energy level",
    "HOMO level",
    "Viscosity (η)",
    "Dielelectric constant (ɛ)",
    "Relative permittivity (ɛ)",
    "Melting point (MP)",
    "Boiling point (BP)",
    "Flash Point (FP)",
    "Performance",
    "Energy density",
    "Coulombic Efficiency (CE)",
    "Cycle life",
    "Cycling lifespan",
    "Rate performance"
    ]

query_statements = [
        "We were the first to propose a sparingly solvating electrolyte for Li2Sx in Li−S cells and to use HFE as a diluent inHCEs tocreateLHCEs.",
        "The strategy of enhancing electrolyte concentrations to improve battery performance originated from LIB research.",
        "Electrode and Electrolyte Preparation.",
        "S Cathode Preparation.",
        "Adopting a high-concentration electrolyte (HCE) is a promising strategy to solve the problem due to its unique solvation structure with fewer roaming solvents.",
        "PerformanceofLi||NCM90Batteries.",
        "Fabrication of Sulfur Cathodes.",
        "With in 50 cycles,the E-control group’s capacity “dives” significantly, while the introduction of FEC prolongs the battery cycle life to 600 cycles , with a capacity retention of 60.4%.",
        "Electrolyte solutions with specific molar ratios of Li[TFSA], Li[FSA], and solvents were prepared by dissolving the required amounts of salts into SL.",
        "However, Li−S cells with a 70 μm thick Li anode exhibited a gradual capacity decline after 60 cycles, retaining only 43 percents of the initial capacity after 80 cycles, with an average capacity decay rate of 0.71% per cycle.",
        "The coordination with lithium-ions lowers the electrolyte LUMO and HOMO levels: the higher is the number of interactions with lithium-ions, the more likely the solvent molecule, FSI−anion , or diluent molecule is to be reduced and the less likely it is to be come oxidized.",
        "This high interfacial reactivity makes the dilute electrolyte formulations, dominant inconventional lithium-ionbatteries,inadequate to resist uncontrolled electrolyte decomposition , which triggers",
        "By optimizing the salt concentration, the CE is further promoted to 99.4%",
        "The Li||LFP) battery with developed electrolyte maintains >90% Of the original capacity over 400 cycles",
        "Besides, the “weakly solvating power” solvent is a relative definition, which is compared with DME in our work.",
        "By eliminating one O atom and increasing steric hinderance, the solvating power of resulting cyclopentylmethyl ether (CPME) is significantly weakened.",
        "Meanwhile, CPME exhibits a lower melting point and higher boiling point around 140°C and 106°C, respectively, showing a great prospect for wide temperature application.",
        "Even lithium bis(fluorosulfonyl)imide (LiFSI):CPME with a molar ratio of 1:10, the CPME-based electrolyte exhibits a controlled solvation structure, in which CIPs and AGGs prevail, leading to an anion-derived, inorganic-rich SEI and allowing for excellent compatibility with LMA (CE: 99%).",
        "Theoretically, the solvating power decreased in the following order: DME (ɛ=7.2)>CPME (ɛ=4.7)>DEE (ɛ=4.3)>MTBE (ɛ=2.6) in Table S2, and MTBE should show weakest solvating power than DME, CPME, and DEE.",
        "A bilayer structure of SEI is tailored through trioxane-modulated electrolytes: the inner layer is dominated by LiF to improve  homogeneity while the outer layer contains Lipolyoxymethylene to improve  mechanical stability, synergistically leading to mitigated reconstruction of SEI and reversible Li plating/stripping.",
        "A prototype 440 Wh kg−1 pouch cell (5.3 Ah), with a low negative/positive capacity ratio of 1.8 and lean electrolytes of 2.1 g Ah−1, achieves 130 cycles.",
        "In particular, the anion-derived and LiF-rich SEI, widely found in localized high-concentration electrolytes (LHCE), emerges as an effective route to improve the uniformity of SEI",
        "in situ constructed in trioxane (TO)-modulated electrolyte",
        "A conventional LHCE constituting LiFSI:DME:HFE (1.00:1.80:2.00 by mol, denoted as DME-based electrolyte), which generates single/F SEI, is considered for comparison.",
        "Li | LiNi0.8Co0.1Mn0.1O2(NCM811) pouch cells (5.3 Ah; Fig. 6a and Supplementary Fig. 29) with lean electrolytes (2.1 g Ah−1) and an ultra-low N/P ratio (the capacity ratio of negative electrode to positive electrode) of 1.8 were assembled and evaluated to demonstrate the effectiveness of bilayer/P–F SEI.",
        "The Li | NCM811 pouch cell achieves a specific energy of 440 Wh kg−1 at the cell level and maintains a capacity retention of 91.7% after 130 cycles at 0.1 C charge/0.2 C discharge.",
        "Another pouch cell with an initial energy density of 435 Wh kg−1 also achieves a capacity retention of 85.2% after 110 cycles at 0.1 C charge/discharge, demonstrating the reliability of bilayer/P–F SEI design at different cycling conditions",
        "The specific energy achieved in this work (440 Wh kg−1) is much higher than the state-of-the-art Li-ion batteries (250–270 Wh kg−1).",
        "In particular, a Li metal pouch cell of 440 Wh kg−1 achieves a lifespan of 130 cycles.",
        "To construct the bilayer/P–F SEI, the electrolyte composed of Li bis(fluorosulfonyl)imide (LiFSI):TO:1,2-dimethoxyethane (DME):1,1,2,2-tetrafluoroethyl-2,2,3,3 tetrafluoropropylether (HFE) = 1.00:0.16:1.80:2.00 (by mol, denoted as TO-based electrolyte) is proposed, in which the molar ratio of TO is 3.2%.",
        "TO was dissolved in DME-based electrolyte to prepare the TO-based electrolyte. The molar ratio of LiFSI, DME and HFE in DME-based electrolyte is 1.00:1.80:2.00. The molar ratio of LiFSI, TO, DME and HFE in the TO-based electrolyte is 1.00:0.16:1.80:2.00,",
        "Li | NCM811 pouch cells (7.0 × 4.0 cm2) were assembled in a dry room at a dew point of −60 °C.",
        "Consequently, for coin cells of practical merits, such as high-loading LiNi0.5Co0.2Mn0.3O2 (NCM523) cathode (3.0 mAh cm−2) and ultrathin Li anode (50 μm), the lifespan is extended to 430 cycles tested at 1.2 mA cm−2, significantly outperforming 200 cycles with routine anion-derived SEI.",
        "Towards graphite (Gr) anode and high oxidation  stability towards high-nickel cathode LiNi0.8Co0.1Mn0.1O2-NCM811), as well as the formationof inorganic rich electrode/electrolyte interphase.",
        "The capacity retention of Grj jNCM811 Ah-class pouch cell can reach 70.85% for 1000 cycles at room-temperature and 75.86% for 400 cycles at 20°C.",
        "For instance, the oxidation stability follows the order of tetraethylene glycol dimethyl ether (TEGDME)>diethyleneglycol dimethyl ether>1,2-dimethoxyethane (DME).",
        "AWSEs has been operated for longest cycle life (400 cycles) with excellent capacity retention at 20°C",
        "We designed an electrolyte with high salt concentration (LiFSI), and a weakly solvating solvent (DEE) that can generate solvation structures dominated by associated species, such as CIPs and AGGs at a relatively lower concentration, compared to common superconcentrated electrolytes.",
        "The cell with 2 M LiFSI-DME exhibited massive fluctuations and an average CE of only 98.2% within 450 cycles owing to the unstable SEI and dead Li formation.",
        "Node-free pouch cells after 80 cycles at 0.2 C charge and 0.3 C discharge, fully charged to the upper cut-off voltage, were chosen for SEM examination due to Li deposition under realistic full-cell conditions."
    ]


def get_pdf_text_from_url(pdf_url):
    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
        pdf_data = response.content
        doc = fitz.open(stream=pdf_data, filetype='pdf')
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
        return text
    except requests.exceptions.RequestException as e:
        print(f"Request failed for URL {pdf_url}: {e}")
    except Exception as e:
        print(f"Error processing PDF from URL {pdf_url}: {e}")
    return None  # Return None if there is an error

def process_pdf(pdf_link):
    text = get_pdf_text_from_url(pdf_link)
    title = pdf_link
    text = remove_footer(text)
    text = remove_ref(text)
    return (title, text)

def process_pdf_file(file_path):
    """Process a PDF file to extract its title and text."""
    try:
        doc = fitz.open(file_path)
        text = ""
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text += page.get_text()
        doc.close()
        title = file_path.split("/")[-1].replace(".pdf", "")
        return (title, text)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None, None

def remove_footer(text):
    if text is None:
        return ''
    patterns = [
        r'Article\nhttps:\/\/doi\.org\/10\.\d{4}\/[a-z0-9\-]+',  # match DOI
        r'https:\/\/doi\.org\/10\.\d{4}\/[a-z0-9\-]+'
        r'www\.nature\.com'
        r'Nature Communications\| *\(\d{4}\) \d{2}:\d{4}',        # match some journal name
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text)
    return text

def remove_ref(text):
    if text is None:
        return ''
    ref_positions = [m.start() for m in re.finditer(r'\breference', text, re.IGNORECASE)]
    
    for ref_start in ref_positions:
        snippet = text[ref_start:min(ref_start + 5000, len(text)-1)]

        if all(tag in snippet for tag in ['1.', '2.', '3.']):
            return text[:ref_start]
    
    return text

def process_all_pdfs(pdf_links):
    documents = []
    for pdf_link in pdf_links:
        title, text = process_pdf(pdf_link)
        if text:
            if text=='':
                print(print(f"PDF from URL got None."))
            documents.append((title, text))
            print(f"PDF from URL {pdf_link} has been added.")
        else:
            print(f"Skipping PDF from URL {pdf_link} due to previous error.")
    return documents

def process_all_pdfs_file(pdf_paths):
    documents = []
    for pdf_path in pdf_paths:
        title, text = process_pdf_file(pdf_path)
        if text:
            if text == '':
                print(f"PDF {pdf_path} got empty content.")
            documents.append((title, text))
            print(f"PDF {pdf_path} has been added.")
        else:
            print(f"Skipping PDF {pdf_path} due to previous error.")
    return documents

def extract_paragraphs(json_file, output_txt):
    with open(json_file, 'r', encoding='utf-8') as f:
        search_results = json.load(f)
    
    with open(output_txt, 'w', encoding='utf-8') as f:
        for result in search_results:
            paragraph = result['Paragraph']
            f.write(paragraph + '\n\n')


def list_files_in_directory(directory_path):
    file_list = []
    try:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_list.append(file_path)
        return file_list
    except Exception as e:
        print(f"Error reading files in directory {directory_path}: {e}")
        return []

# retrieve from url
def retrieve(pdf_links,keywords = query_keywords,keystatements = query_statements):

    documents = process_all_pdfs(pdf_links)

    indexer = TextIndexer("indexdir")
    indexer.create_index(documents)

    indexed_documents = indexer.get_documents()

    grouped_documents = defaultdict(list)
    for doc in indexed_documents:
        grouped_documents[doc['title']].append(doc)

    search_results = []
    seen_paragraphs = set()

    searcher = SemanticSearch()

    for title, documents in grouped_documents.items():
        try:
            searcher.add_documents(documents)
        except ValueError as e:
            print(f"Error processing documents for {title}: {e}")
            continue

        for query_str in keywords:
            result_set0 = searcher.search(query_str, method='bm25')
            for result in result_set0:
                paragraph = result['paragraph']
                if paragraph not in seen_paragraphs:
                    seen_paragraphs.add(paragraph)
                    search_results.append({
                        "Document": result['title'],
                        "Paragraph": paragraph
                    })

        for query_str in keystatements:
            result_set0 = searcher.search(query_str, method='semantic')
            for result in result_set0:
                paragraph = result['paragraph']
                if paragraph not in seen_paragraphs:
                    seen_paragraphs.add(paragraph)
                    search_results.append({
                        "Document": result['title'],
                        "Paragraph": paragraph
                    })

    return search_results

def retrieve_from_documents(pdf_paths,keywords = query_keywords,keystatements = query_statements):

    documents = process_all_pdfs_file(pdf_paths)

    indexer = TextIndexer("indexdir")
    indexer.create_index(documents)

    indexed_documents = indexer.get_documents()

    grouped_documents = defaultdict(list)
    for doc in indexed_documents:
        grouped_documents[doc['title']].append(doc)

    search_results = []
    seen_paragraphs = set()

    searcher = SemanticSearch()

    for title, documents in grouped_documents.items():
        try:
            searcher.add_documents(documents)
        except ValueError as e:
            print(f"Error processing documents for {title}: {e}")
            continue

    
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_bm25 = [executor.submit(lambda query: searcher.search(query, method='bm25'), query_str) for query_str in keywords]
            future_semantic = [executor.submit(lambda query: searcher.search(query, method='semantic'), query_str) for query_str in keystatements]
            
            for future in concurrent.futures.as_completed(future_bm25):
                result_set0 = future.result()
                for result in result_set0:
                    paragraph = result['paragraph']
                    if paragraph not in seen_paragraphs:
                        seen_paragraphs.add(paragraph)
                        search_results.append({
                            "Document": result['title'],
                            "Paragraph": paragraph
                        })
            
            for future in concurrent.futures.as_completed(future_semantic):
                result_set0 = future.result()
                for result in result_set0:
                    paragraph = result['paragraph']
                    if paragraph not in seen_paragraphs:
                        seen_paragraphs.add(paragraph)
                        search_results.append({
                            "Document": result['title'],
                            "Paragraph": paragraph
                        })
    return search_results