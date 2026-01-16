import networkx as nx
import re
import networkx.algorithms.isomorphism as isom
import argparse
import os
from rdkit import Chem
from rdkit.Chem import rdchem
import pickle
import csv
from rdkit.Chem import AllChem
from rdkit.Chem import Draw
# from rdkit.Chem.Draw import IPythonConsole #Needed to show molecules
# 移除了旧的导入库，使用新版本的库
# from rdkit.Chem.Draw.MolDrawing import MolDrawing, DrawingOptions #Only needed if modifying defaults
from rdkit.Chem.Draw import rdMolDraw2D #For modern drawing options
import matplotlib.pyplot as plt
from collections import deque
import time

def degree_count(G, n):
    i = 0
    for adj_node in G[n]:
        i += G[n][adj_node]["bond"]
    return i

def has_cycle(graph):
    try:
        nx.find_cycle(graph)
        return True
    except nx.exception.NetworkXNoCycle:
        return False

def shortest_path_node_count(graph, node1, node2):
    # 使用NetworkX计算两个节点之间的最短路径长度
    length = nx.shortest_path_length(graph, node1, node2)
    # 路径长度加上起点节点，得到总节点数
    node_count = length + 1
    return node_count

def just_num_rings(graph, node1, node2):
    if (shortest_path_node_count(graph, node1, node2) == 5) or (shortest_path_node_count(graph, node1, node2) == 6):
        return True
    else:
        return False
    
def file_2_list(n):
    """ Extract Graphs with n-1 nodes and n-2 edges.
        Convert files to lists. 

    Args:
        n (int): The current number of nodes in the graph to be generated.

    Returns:
        list: A list of graph with n-1 nodes and n-2 edges.
    """
    graph_list_last = []
    newfile = f"./tmp/ether_isomers_{n}.gra"
    with open(newfile, 'rb') as file:
        while True:
            try:
                graph_list_last.append(pickle.load(file))
            except EOFError:
                break
    return graph_list_last

def list_2_files(graph_dict, n):
    next_file = f"./tmp/ether_isomers_{n}.gra"
    with open(next_file, 'ab') as file:
        for graph in graph_dict:
            pickle.dump(graph, file)

def graph_draw(G):
    pos = nx.spring_layout(G)
    node_labels_tmp = nx.get_node_attributes(G, 'atom')  # 获取节点的desc属性
    node_labels = dict()
    for key, value in node_labels_tmp.items():
        node_labels[key] = f"{key}-{value}"
    edge_labels = nx.get_edge_attributes(G, 'bond') # 获取边的name属性
    nx.draw(G, pos,edge_color="grey", node_size=500)
    nx.draw_networkx_labels(G,pos,labels=node_labels)
    nx.draw_networkx_edge_labels(G, pos)
    
def graph_2_smiles(graph_dict, index, ids, smiles, graph_smiles, cycles):
    bond_list = [Chem.rdchem.BondType.UNSPECIFIED, Chem.rdchem.BondType.SINGLE, Chem.rdchem.BondType.DOUBLE,
             Chem.rdchem.BondType.TRIPLE]
    file = f'./{index}_{ids}/1_{cycles}_results/{index}_{ids}_{smiles}_{cycles}.smi'
    with open(file, 'a') as f:
        for graph in graph_dict:
            # print(graph)
            atoms = [graph.nodes[node_every_graph]["atom"] for node_every_graph in range(0, len(graph.nodes()))]
            adjacency_matrix = nx.to_numpy_array(graph, dtype = int, weight = "bond")
            molecule = Chem.RWMol()
            #往RWMOL注入原子信息
            atom_index = []
            for atom_number in range(len(atoms)):
                atom = Chem.Atom(atoms[atom_number])
                molecular_index = molecule.AddAtom(atom)
                atom_index.append(molecular_index)
            #在原子和原子直接加入指定种类的键
            for index_x, row_vector in enumerate(adjacency_matrix):
                for index_y, bond in enumerate(row_vector):
                    if index_y <= index_x:
                        continue
                    if bond == 0:
                        continue
                    else:
                        molecule.AddBond(atom_index[index_x], atom_index[index_y], bond_list[bond])
            
            molecule = molecule.GetMol()
            temp_smiles = Chem.MolToSmiles(molecule)
            temp_mol = Chem.MolFromSmiles(temp_smiles)
            f.write(Chem.MolToSmiles(temp_mol))
            graph_smiles.append(Chem.MolToSmiles(temp_mol))
            f.write('\n')

def isomorphism(G, graph_dict):
    flag = False
    nm = isom.categorical_node_match("atom","C")
    em = isom.numerical_edge_match("bond", 1)
    for graph in graph_dict:
        if nx.is_isomorphic(G, graph, node_match = nm, edge_match = em):
            flag = True
            break
    return flag
def generate_new_node_without_f(graph, n, graph_dict, max_per_node=15):
    """生成新节点
    
    Args:
        graph: 输入图
        n: 节点数
        graph_dict: 存储生成图的字典
        max_per_node: 每个节点最多生成的新分子数量，默认为3
    """
    # print("generate_new_ node")
    count = 0
    added_structures = set()#用于记录已添加结构，便于计数，修改量
    for node in graph:
        # 限制每个节点生成的分子数量
        if count >= max_per_node:
            break
        #修改量
        if(graph.nodes[node]["atom"] == 'O') and (degree_count(graph, node) < 2):
            temp_graph = graph.copy()
            temp_graph.add_node(n, atom = 'C')
            temp_graph.add_edge(node, n, bond = 1)
            if not isomorphism(temp_graph, graph_dict):
                graph_dict.append(temp_graph)
                count += 1
        #修改量   
        if (graph.nodes[node]["atom"] == 'C') and (degree_count(graph, node) < 4):
            temp_graph = graph.copy()
            temp_graph.add_node(n, atom = 'C')
            temp_graph.add_edge(node, n, bond = 1)
            if not isomorphism(temp_graph, graph_dict):
                graph_dict.append(temp_graph)
                count += 1
        #修改量
         # 尝试添加氧原子（单键）
        if (graph.nodes[node]["atom"] == 'C') and (degree_count(graph, node) < 4):
            # 情况2：添加氧原子（单键）
            temp_graph_o_single = graph.copy()
            temp_graph_o_single.add_node(n, atom='O')
            temp_graph_o_single.add_edge(node, n, bond=1)
            
            graph_key = get_graph_signature(temp_graph_o_single)
            if not isomorphism(temp_graph_o_single, graph_dict) and graph_key not in added_structures:
                graph_dict.append(temp_graph_o_single)
                added_structures.add(graph_key)
                count += 1
                if count >= max_per_node:
                    break
        # 尝试添加氧原子（双键）- 只有当当前节点可以形成双键时
        if (graph.nodes[node]["atom"] == 'C') and (degree_count(graph, node) < 3):  # 双键需要更多空间
            # 情况3：添加氧原子（双键）
            temp_graph_o_double = graph.copy()
            temp_graph_o_double.add_node(n, atom='O')
            temp_graph_o_double.add_edge(node, n, bond=2)
            
            graph_key = get_graph_signature(temp_graph_o_double)
            if not isomorphism(temp_graph_o_double, graph_dict) and graph_key not in added_structures:
                graph_dict.append(temp_graph_o_double)
                added_structures.add(graph_key)
                count += 1
                if count >= max_per_node:
                    break
    for node in graph:
        # 限制每个节点生成的分子数量
        if count >= max_per_node:
            break
        #修改量
        if(graph.nodes[node]["atom"] == 'O') and (degree_count(graph, node) < 2) :
            temp_graph = graph.copy()
            temp_graph.add_node(n, atom = 'C')
            temp_graph.add_edge(node, n, bond = 1)
            if not isomorphism(temp_graph, graph_dict):
                graph_dict.append(temp_graph)
                count += 1
def generate_new_node(graph, n, graph_dict, max_per_node=30):
    """生成新节点
    
    Args:
        graph: 输入图
        n: 节点数
        graph_dict: 存储生成图的字典
        max_per_node: 每个节点最多生成的新分子数量，默认为3
    """
    # print("generate_new_ node")
    count = 0
    added_structures = set()#用于记录已添加结构，便于计数，修改量
    for node in graph:
        # 限制每个节点生成的分子数量
        if count >= max_per_node:
            break
        #修改量
        if(graph.nodes[node]["atom"] == 'O') and (degree_count(graph, node) < 2):
            temp_graph = graph.copy()
            temp_graph.add_node(n, atom = 'C')
            temp_graph.add_edge(node, n, bond = 1)
            if not isomorphism(temp_graph, graph_dict):
                graph_dict.append(temp_graph)
                count += 1
        #修改量   
        if (graph.nodes[node]["atom"] == 'C') and (degree_count(graph, node) < 4):
            temp_graph = graph.copy()
            temp_graph.add_node(n, atom = 'C')
            temp_graph.add_edge(node, n, bond = 1)
            if not isomorphism(temp_graph, graph_dict):
                graph_dict.append(temp_graph)
                count += 1
        #修改量
         # 尝试添加氧原子（单键）
        if (graph.nodes[node]["atom"] == 'C') and (degree_count(graph, node) < 4):
            # 情况2：添加氧原子（单键）
            temp_graph_o_single = graph.copy()
            temp_graph_o_single.add_node(n, atom='O')
            temp_graph_o_single.add_edge(node, n, bond=1)
            
            graph_key = get_graph_signature(temp_graph_o_single)
            if not isomorphism(temp_graph_o_single, graph_dict) and graph_key not in added_structures:
                graph_dict.append(temp_graph_o_single)
                added_structures.add(graph_key)
                count += 1
                if count >= max_per_node:
                    break
        if (graph.nodes[node]["atom"] == 'C') and (degree_count(graph, node) < 4):
            # 情况2：添加氟原子（单键）
            temp_graph_f_single = graph.copy()
            temp_graph_f_single.add_node(n, atom='F')
            temp_graph_f_single.add_edge(node, n, bond=1)
            
            graph_key = get_graph_signature(temp_graph_f_single)
            if not isomorphism(temp_graph_f_single, graph_dict) and graph_key not in added_structures:
                graph_dict.append(temp_graph_f_single)
                added_structures.add(graph_key)
                count += 1
                if count >= max_per_node:
                    break
        if (graph.nodes[node]["atom"] == 'C') and (degree_count(graph, node) < 4):
            # 情况2：添加氨基
            temp_graph_n_single = graph.copy()
            temp_graph_n_single.add_node(n, atom='N')
            temp_graph_n_single.add_edge(node, n, bond=1)
            
            graph_key = get_graph_signature(temp_graph_n_single)
            if not isomorphism(temp_graph_n_single, graph_dict) and graph_key not in added_structures:
                graph_dict.append(temp_graph_n_single)
                added_structures.add(graph_key)
                count += 1
                if count >= max_per_node:
                    break
        # 尝试添加氧原子（双键）- 只有当当前节点可以形成双键时
        if (graph.nodes[node]["atom"] == 'C') and (degree_count(graph, node) < 3):  # 双键需要更多空间
            # 情况3：添加氧原子（双键）
            temp_graph_o_double = graph.copy()
            temp_graph_o_double.add_node(n, atom='O')
            temp_graph_o_double.add_edge(node, n, bond=2)
            
            graph_key = get_graph_signature(temp_graph_o_double)
            if not isomorphism(temp_graph_o_double, graph_dict) and graph_key not in added_structures:
                graph_dict.append(temp_graph_o_double)
                added_structures.add(graph_key)
                count += 1
                if count >= max_per_node:
                    break
        if (graph.nodes[node]["atom"] == 'C') and (degree_count(graph, node) < 2):  # 双键需要更多空间
            # 情况3：添加氧原子（双键）
            temp_graph_n_triple = graph.copy()
            temp_graph_n_triple.add_node(n, atom='N')
            temp_graph_n_triple.add_edge(node, n, bond=3)
            
            graph_key = get_graph_signature(temp_graph_n_triple)
            if not isomorphism(temp_graph_n_triple, graph_dict) and graph_key not in added_structures:
                graph_dict.append(temp_graph_n_triple)
                added_structures.add(graph_key)
                count += 1
                if count >= max_per_node:
                    break
    for node in graph:
        # 限制每个节点生成的分子数量
        if count >= max_per_node:
            break
        #修改量
        if(graph.nodes[node]["atom"] == 'O') and (degree_count(graph, node) < 2) :
            temp_graph = graph.copy()
            temp_graph.add_node(n, atom = 'C')
            temp_graph.add_edge(node, n, bond = 1)
            if not isomorphism(temp_graph, graph_dict):
                graph_dict.append(temp_graph)
                count += 1
#修改量，检测函数
def get_graph_signature(graph):
    """生成图的唯一签名，用于去重"""
    # 将图转换为规范化的SMILES字符串作为签名
    try:
        from rdkit import Chem
        from rdkit.Chem import rdchem
        
        bond_list = [
            Chem.rdchem.BondType.UNSPECIFIED,
            Chem.rdchem.BondType.SINGLE, 
            Chem.rdchem.BondType.DOUBLE,
            Chem.rdchem.BondType.TRIPLE
        ]
        
        atoms = [graph.nodes[node]["atom"] for node in graph.nodes()]
        adjacency_matrix = nx.to_numpy_array(graph, dtype=int, weight="bond")
        
        molecule = Chem.RWMol()
        atom_index = []
        
        # 添加原子
        for atom_symbol in atoms:
            atom = Chem.Atom(atom_symbol)
            molecular_index = molecule.AddAtom(atom)
            atom_index.append(molecular_index)
        
        # 添加键
        for index_x, row_vector in enumerate(adjacency_matrix):
            for index_y, bond in enumerate(row_vector):
                if index_y <= index_x or bond == 0:
                    continue
                molecule.AddBond(atom_index[index_x], atom_index[index_y], bond_list[bond])
        
        molecule = molecule.GetMol()
        return Chem.MolToSmiles(molecule, canonical=True)
        
    except Exception:
        # 如果RDKit不可用，使用简单的字符串表示
        nodes = sorted(graph.nodes(data=True))
        edges = sorted(graph.edges(data=True))
        return f"{nodes}_{edges}"


def isomorphism(G, graph_dict):
    """检查图是否已存在"""
    flag = False
    nm = isom.categorical_node_match("atom", "C")
    em = isom.numerical_edge_match("bond", 1)
    for graph in graph_dict:
        if nx.is_isomorphic(G, graph, node_match=nm, edge_match=em):
            flag = True
            break
    return flag
#以上为修改量
def generate_new_edge(temp_que_graph, n, graph_dict, max_edges=3):
    """生成新边
    
    Args:
        temp_que_graph: 输入图
        n: 节点数
        graph_dict: 存储生成图的字典
        max_edges: 最多生成的新边数量，默认为3
    """
    edge_count = 0
    for i in range(0, n):
        if edge_count >= max_edges:
            break
            
        if degree_count(temp_que_graph, i) < 4:
            for j in range(i + 1, n):
                if edge_count >= max_edges:
                    break
                    
                if (degree_count(temp_que_graph, j) < 4) and ((i, j) not in temp_que_graph.edges) and (i != j) and (not has_cycle(temp_que_graph)) and just_num_rings(temp_que_graph, i, j):
                    if temp_que_graph.nodes[i]["atom"] == 'C' and temp_que_graph.nodes[j]["atom"] == 'C':
                        temp_bfs_graph = temp_que_graph.copy()
                        temp_bfs_graph.add_edge(i, j, bond = 1)
                        if not isomorphism(temp_bfs_graph, graph_dict):
                            graph_dict.append(temp_bfs_graph)
                            edge_count += 1
                    
def count_atom(smiles):
    cou = 0
    for i in smiles:
        if i.isalpha():
            cou += 1
    return cou

def file_2_list(index, ep_ids, n):
    """ Extract Graphs with n-1 nodes and n-2 edges.
        Convert files to lists. 

    Args:
        n (int): The current number of nodes in the graph to be generated.

    Returns:
        list: A list of graph with n-1 nodes and n-2 edges.
    """
    graph_list_last = []
    newfile = f"{index}_{ep_ids}/tmp/isomers_{n}.gra"
    with open(newfile, 'rb') as file:
        while True:
            try:
                graph_list_last.append(pickle.load(file))
            except EOFError:
                break
    return graph_list_last

def list_2_files(index, ep_ids, graph_dict, n):
    next_file = f"{index}_{ep_ids}/tmp/isomers_{n}.gra"
    with open(next_file, 'ab') as file:
        for graph in graph_dict:
            pickle.dump(graph, file)

def count_mol(index, ep_ids, cycles):
    cou_all = 0
    for i in range(1, cycles + 1):
        cou = 0
        with open(f'./{index}_{ep_ids}/1_{i}_results/{index}_{ep_ids}_{smiles}_{i}.smi', 'r') as f1:
            with open(f'./{index}_{ep_ids}/{index}_{ep_ids}.smi', 'a') as f2:
                for lines in f1.readlines():
                    cou += 1
                    f2.write(lines)
        with open(f"{index}_{ep_ids}/{index}_{ep_ids}_log.csv", 'a') as f2:
            writer = csv.writer(f2)
            writer.writerow([i, cou])
        cou_all += cou
    with open(f"{index}_{ep_ids}/{index}_{ep_ids}_log.csv", 'a') as f2:
        writer = csv.writer(f2)
        writer.writerow(["Total", cou_all])
    

# "CC#N", "N#Cc1ccccc1", "N#CCC#N", "N#CCCC#N", "COC(C)C#N", "CCOCCC#N", "CN(C)C(=O)N(C)C", "CC(=O)N(C)C", "CN(C)C=O", "CCOP1(=O)OCCO1", "O=P1(OCC(F)(F)F)OCCO1", "COP(C)(=O)OC", "COP(=O)(OC)OC", "CCOP(=O)(OCC)OCC", "CS(=O)C", "COS(=O)OC", "CCOS(=O)OCC", "C1COS(=O)O1", "CC1COS(=O)O1", "CS(=O)(=O)c1ccccc1F", "CCS(=O)(=O)C", "CC(C)S(=O)(=O)C", "CS(=O)(=O)F", "CS(=O)(=O)CCC(F)(F)F", "COCCS(=O)(=O)C", "CCS(=O)(=O)CCOC", "CCS(=O)(=O)CCOCCOC", "CCS(=O)(=O)C(C)C", "CCS(=O)(=O)CC(C)C", "CCC(C)S(=O)(=O)CC", "CCS(=O)(=O)C=C", "CCS(=O)(=O)C1CCCC1", "CCCS(=O)(=O)CCC", "CC1CCS1(=O)=O", "C1CCS(=O)(=O)C1", "CC1CCS(=O)(=O)C1", "C[Si](C)(C)OB(O[Si](C)(C)C)O[Si](C)(C)C", "CO[Si](C)(C)OC", "CCO[Si](OCC)(OCC)OCC", "CCO[Si](C)(OCC)OCC", "CCO[Si](C)(C)OCC", "CO[Si](C)(C)C", "C[Si](C)(C)C(F)(F)F"
def smiles_2_graph(smiles):
    """
    Document: https://www.rdkit.org/docs/source/rdkit.Chem.rdmolfiles.html#rdkit.Chem.rdmolfiles.MolFromSmiles
    Func: MolFromSmiles 从 SMILES 字符串构建分子
    Args:
        - smiles (str): SMILES 字符串
        - sanitize (optional[bool]): 是否进行分子的 sanitization, 默认为 True
        - replacements (optional[dict]): 替换字符串的字典, 默认为 {}
    Returns:
        - a Mol object, None on failure
    Examples of replacements:
        - CC{Q}C with {'{Q}': 'OCCO'} -> CCOCCOC
        - C{A}C{Q}C with {'{Q}': 'OCCO', '{A}': 'C1(CC1)'} -> CC1(CC1)COCCOC
        - C{A}C{Q}C with {'{Q}': '{X}CC{X}', '{A}': 'C1CC1', '{X}': 'N'} -> CC1CC1CNCCNC
    """
    mol = Chem.MolFromSmiles(smiles)
    # TODO: 对 mol 返回为 None 情况进行处理
    graph = nx.Graph()

    # 添加节点
    for atom in mol.GetAtoms():
        graph.add_node(atom.GetIdx(), atom=atom.GetSymbol())

    # 添加边
    for bond in mol.GetBonds():
        atom1 = bond.GetBeginAtomIdx()
        atom2 = bond.GetEndAtomIdx()
        bond_type = bond.GetBondType()

        if bond_type == rdchem.BondType.SINGLE:
            bond_info = 1
        elif bond_type == rdchem.BondType.DOUBLE:
            bond_info = 2
        elif bond_type == rdchem.BondType.TRIPLE:
            bond_info = 3
        else:
            bond_info = 0

        graph.add_edge(atom1, atom2, bond=bond_info)

    return graph

def main(index, ep_ids, smiles, cycles, max_molecules=None):
    """主函数，控制分子生成过程
    
    Args:
        index: 索引标识
        ep_ids: ID标识
        smiles: 起始分子的SMILES字符串
        cycles: 循环次数
        max_molecules: 每个循环中最多生成的分子数量，默认为None表示生成所有可能的分子
    """
    # parser = argparse.ArgumentParser()
    # parser.add_argument('--n', help="Number of nodes")
    # args = parser.parse_args()
    # n = int(args.n)
    
    cycles = int(cycles)
    
    graph_dict = {}
    
    for i in range(cycles + 1):
        if not os.path.exists(f"{index}_{ep_ids}/1_{i}_results"):
            os.makedirs(f"{index}_{ep_ids}/1_{i}_results")
        
        if not os.path.exists(f"{index}_{ep_ids}/2_{i}_pictures"):
            os.makedirs(f"{index}_{ep_ids}/2_{i}_pictures")
    
    if not os.path.exists(f"{index}_{ep_ids}/tmp"):
        os.makedirs(f"{index}_{ep_ids}/tmp")
    
    graph_smiles = {}
    
    for i in range(cycles + 1):
        graph_dict[i] = []
        graph_smiles[i] = []
        
    G0 = smiles_2_graph(smiles)
    graph_dict[0].append(G0)
    
    first_file = f"{index}_{ep_ids}/tmp/isomers_0.gra"
    with open(first_file, 'ab') as file:
        pickle.dump(G0, file)
    
    for i in range(cycles):
        graph_list_last = file_2_list(index, ep_ids, i)
        for G in graph_list_last:
            # 只有当指定了max_molecules且已达到限制时才跳过生成
            if max_molecules is not None and len(graph_dict[i+1]) >= max_molecules:
                break
            generate_new_node(G, G.number_of_nodes(), graph_dict[i+1])
        list_2_files(index, ep_ids, graph_dict[i+1], i+1)
    
        for G in graph_dict[i+1]:
            # 只有当指定了max_molecules且已达到限制时才跳过生成
            if max_molecules is not None and len(graph_dict[i+1]) >= max_molecules:
                break
            generate_new_edge(G, G.number_of_nodes(), graph_dict[i+1])
        
    
    
    for i in range(cycles + 1):
        graph_2_smiles(graph_dict[i], index, ids, smiles, graph_smiles[i], i)
    
    print(f"The number of ether isomers: {len(graph_smiles)}")
    
    for i in range(cycles + 1):
        with open(f'./{index}_{ids}/1_{i}_results/{index}_{ids}_{smiles}_{i}.smi', 'r') as f1:
            for line in f1.readlines():
                """
                Use Draw.rdMolDraw2D.MolDrawOptions instead of DrawingOptions
                """
                # opts = DrawingOptions()
                m = Chem.MolFromSmiles(line.strip())
                # opts.includeAtomNumbers=True
                # opts.bondLineWidth=2.8
                # draw=Draw.MolToImage(m, options=opts)
                drawer = rdMolDraw2D.MolDraw2DCairo(400, 300)
                drawer_opts = drawer.drawOptions()
                drawer_opts.addAtomIndices = True
                drawer_opts.bondLineWidth = 2.8
                drawer.DrawMolecule(m)
                drawer.FinishDrawing()
                draw = Draw.MolToImage(m, size=(400, 300), kekulize=True)
                draw.save(f'./{index}_{ids}/2_{i}_pictures/{line.strip()}.jpg')
    
    count_mol(index, ep_ids, cycles)
    
if __name__ == "__main__":
    # 检查是否有足够的参数
    import sys
    if len(sys.argv) < 5:
        print("错误：至少需要4个参数")
        sys.exit(1)

    # 从命令行参数获取值
    index = sys.argv[1]
    ids = sys.argv[2]
    smiles = sys.argv[3]
    cycles = sys.argv[4]
    # 可选参数：限制生成的分子数量
    max_molecules = 5
    if len(sys.argv) >= 6:
        max_molecules = int(sys.argv[5])

    if max_molecules is not None:
        print(f"开始生成分子，每个循环最多生成{max_molecules}个分子")
    else:
        print("开始生成分子，将生成所有可能的分子")
    main(index, ids, smiles, cycles, max_molecules)
