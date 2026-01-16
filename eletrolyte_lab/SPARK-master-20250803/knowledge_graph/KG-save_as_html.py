import pandas as pd
import networkx as nx
from pyvis.network import Network


node_df = pd.read_csv("data/nodes.csv", encoding='utf-8')
edge_df = pd.read_csv("data/edges.csv", encoding='utf-8')



G = nx.DiGraph()


for _, row in node_df.iterrows():
    node = row["Node"]
    node_attrs = row.drop("Node").to_dict()
    G.add_node(node, **node_attrs)


for _, row in edge_df.iterrows():
    G.add_edge(row["Source"], row["Target"], **row.drop(["Source", "Target"]).to_dict())


net = Network(notebook=False, directed=True, cdn_resources='in_line')

# define color maps for different node types
color_map = {
    "Monomers.Abbr": "#99DDCC",
    "Initiators":'#99DDCC',
    "Salts.Abbr": "#99DDCC",
    "Polymer.Abbr": "#99DDCC",

    "dummy_SPE":"#CABBE9",
    "Conductivity_Label": '#EF7B7B',

}

label_color_map = {
    "high":'#EF7B7B',
    "medium":'#FEE4A6',
    "low":'#A6E3E9',

    "Unknown":'#DDDEDE',
    'nan':'#DDDEDE'
}




for node, data in G.nodes(data=True):
    node_type = data.get('label', 'Unknown')
    title = ", ".join([f"{k}: {v}" for k, v in data.items()])

    rounded_value = data.get('rounded_value', None)

    if rounded_value is not None and pd.notna(rounded_value):
        label = str(rounded_value)
    else:
        label = str(node)

    if node_type == 'Conductivity.Value':
        key = data.get('label1', 'Unknown')
        if pd.isna(key):
            key = 'Unknown'
        color = label_color_map.get(key, '#DDDEDE')
    elif node_type == 'Conductivity_Label':
        color = label_color_map[str(node)]
    else:
        color = color_map.get(node_type, '#DDDEDE')
    

    net.add_node(node, label=label, title=title, color=color)

default_edge_color = '#B0DEDB'


edge_label_color_map = {
    "high":'#EF7B7B',
    "medium":'#FEE4A6',
    "low":'#A6E3E9'
}


default_edge_color = '#D3D4D8'

for edge in G.edges():

    node1, node2 = edge[0], edge[1]
    
    color = default_edge_color
    width = 2
    
    if 'high' in node1 or 'high' in node2:
        color = edge_label_color_map['high']
        width = 4
    elif 'medium' in node1 or 'medium' in node2:
        color = edge_label_color_map['medium']
        width = 3
    elif 'low' in node1 or 'low' in node2:
        color = edge_label_color_map['low']
        width = 2.5
    

    if color != default_edge_color:
        net.add_edge(node1, node2, color=color, width=width)
    else:
        net.add_edge(node1, node2, color=color,width=width)


net.toggle_physics(True)

net.show_buttons(filter_=['physics'])


html_content = net.generate_html()

with open('data/all_nodes_knowledge_graph_0416.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Graph saved as UTF-8. You can open it in a browser.")


print("Graph saved. You can open it in a browser.")