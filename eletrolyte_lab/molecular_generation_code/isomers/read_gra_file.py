import pickle
import networkx as nx
import matplotlib.pyplot as plt

def read_gra_file(file_path):
    """读取.gra文件并返回其中的图结构列表"""
    graph_list = []
    with open(file_path, 'rb') as file:
        while True:
            try:
                graph = pickle.load(file)
                graph_list.append(graph)
            except EOFError:
                break
    return graph_list

def display_graph_info(graph):
    """显示图结构的基本信息"""
    print(f"节点数量: {graph.number_of_nodes()}")
    print(f"边数量: {graph.number_of_edges()}")
    print("\n节点属性:")
    for node in graph.nodes():
        print(f"  节点 {node}: {graph.nodes[node]}")
    print("\n边属性:")
    for edge in graph.edges():
        print(f"  边 {edge}: {graph.edges[edge]}")

def draw_graph(graph, title="分子图结构"):
    """绘制图结构"""
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(graph)
    
    # 获取节点标签
    node_labels = {}
    for node in graph.nodes():
        atom_type = graph.nodes[node].get("atom", "")
        node_labels[node] = f"{node}-{atom_type}"
    
    # 获取边标签
    edge_labels = {}
    for u, v in graph.edges():
        bond_type = graph.edges[u, v].get("bond", "")
        edge_labels[(u, v)] = bond_type
    
    # 绘制图
    nx.draw(graph, pos, with_labels=False, node_size=500, node_color="skyblue")
    nx.draw_networkx_labels(graph, pos, labels=node_labels)
    nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels)
    
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(f"{title}.png")
    print(f"图像已保存为 {title}.png")
    plt.show()

def main():
    # 文件路径
    file_path = r"D:\1_CO\tmp\isomers_2.gra"
    
    # 读取图结构
    graph_list = read_gra_file(file_path)
    
    print(f"共读取了 {len(graph_list)} 个图结构")
    
    # 显示每个图的信息并绘制
    for i, graph in enumerate(graph_list):
        print(f"\n=== 图 {i+1} ===")
        display_graph_info(graph)
        draw_graph(graph, f"graph_{i+1}")
        
        # 如果图太多，只显示前5个
        if i >= 4:
            print(f"\n还有 {len(graph_list) - 5} 个图未显示...")
            break

if __name__ == "__main__":
    main()
