import uuid
import numpy as np
import pandas as pd
import networkx as nx

# Read Excel
# raw_data_df = pd.read_excel('file_path')

# Read CSV data(mined data)
raw_data_df = pd.read_csv('Mined_data_file_path')


G = nx.DiGraph()

# Add Nodes
# Add 'Polymer'
for node_id in raw_data_df['Polymer.Abbr.Standard'].unique():
    if pd.notna(node_id):
        if node_id =="FALSE":
            continue
        G.add_node(node_id,label='Polymer.Abbr')


# Add 'Monomer'
all_monomers = pd.concat([raw_data_df['Monomers1.Abbr.Standard']])
unique_monomers = all_monomers.dropna().unique()
for node_id in unique_monomers:
    if pd.notna(node_id):
        if node_id =="FALSE":
            continue
        G.add_node(node_id, label='Monomers.Abbr')



# Add 'Salt'
all_salts = pd.concat([raw_data_df['Salts1.Abbr.Standard']])
unique_salts = all_salts.dropna().unique()
for node_id in unique_salts:
    if pd.notna(node_id):
        if node_id =="FALSE":
                continue
        G.add_node(node_id, label='Salts.Abbr')

# Add 'Initiators' 
for node_id in raw_data_df['Initiators1.Abbr.Standard'].unique():
    if pd.notna(node_id):
        if node_id =="FALSE":
            continue
        G.add_node(node_id,label='Initiators')


# Add SPE
for node_id in raw_data_df['Transference_Number.Value'].unique():
    if pd.notna(node_id):
        G.add_node(node_id,label='Transference_Number')

for node_id in raw_data_df['Glass_transition_temperature1.Name'].unique():
    if pd.notna(node_id):
        G.add_node(node_id,label='Glass_transition_temperature.Name')

for index, row in raw_data_df.iterrows():
    if pd.notna(row['Glass_transition_temperature1.Name']):
        if pd.notna(row['Glass_transition_temperature1.Value']):
            G.add_node(row['Glass_transition_temperature1.Value'], 
                       label='Glass_transition_temperature.Value', 
                       unit=str(row['Glass_transition_temperature1.Unit']) if pd.notna(row['Glass_transition_temperature1.Unit']) else None,
                       conditon=f'{row["Glass_transition_temperature1.Name"]}')
        else:
            G.add_node(row['Glass_transition_temperature1.Name'],
                       label='Glass_transition_temperature.Name')


    if pd.notna(row['Tensile_Strength.Value']):
        G.add_node(row['Tensile_Strength.Value'], label='Tensile_Strength.Value', unit=str(row['Tensile_Strength.Unit']) if pd.notna(row['Tensile_Strength.Unit']) else None)

    if pd.notna(row['Critical_Current_Density.Value']):
        G.add_node(row['Critical_Current_Density.Value'], label='Critical_Current_Density.Value', unit=str(row['Critical_Current_Density.Unit']) if pd.notna(row['Critical_Current_Density.Unit']) else None)

    if pd.notna(row['Electrochemical_Window.Value']):
        G.add_node(row['Electrochemical_Window.Value'], 
                   label='Electrochemical_Window.Value',
                   unit=str(row['Tensile_Strength.Unit']) if pd.notna(row['Tensile_Strength.Unit']) else None)
    if pd.notna(row['Transference_Number.Value']):
        G.add_node(row['Transference_Number.Value'], 
                   label='Transference_Number.Value', 
                   unit=str(row['Transference_Number.Unit']) if pd.notna(row['Transference_Number.Unit']) else None)
    if pd.notna(row['Initiators1.Concentration.Value']):
        G.add_node(row['Initiators1.Concentration.Value'], label='Initiators.Concentration.Value', unit=str(row['Initiators1.Concentration.Unit']) if pd.notna(row['Initiators1.Concentration.Unit']) else None)

    if pd.notna(row['Polymer.Molecular_weight.Value']):
        G.add_node(row['Polymer.Molecular_weight.Value'], label='Polymer.Molecular_weight.Value', unit=str(row['Polymer.Molecular_weight.Unit']) if pd.notna(row['Polymer.Molecular_weight.Unit']) else None)

    if pd.notna(row['Polymerization1.Temperature.Value']):
        G.add_node(row['Polymerization1.Temperature.Value'], label='Polymerization1.Temperature.Value', unit=str(row['Polymerization1.Temperature.Unit']) if pd.notna(row['Polymerization1.Temperature.Unit']) else None)

    if pd.notna(row['Polymerization1.Time.Value']):
        G.add_node(row['Polymerization1.Time.Value'], label='Polymerization1.Time.Value', unit=str(row['Polymerization1.Time.Unit']) if pd.notna(row['Polymerization1.Time.Unit']) else None)
    
    if pd.notna(row['Conductivity Label']):
        G.add_node(row['Conductivity Label'],label='Conductivity_Label')


# Add 'Conductivity'
for index, row in raw_data_df.iterrows():
    if pd.notna(row['Conductivity.Temperature.Value']):
        unique_temp_id = f"{row['Conductivity.Temperature.Value']}"  
        G.add_node(unique_temp_id, 
                   label='Polymer.Concentration.Value', 
                   unit=str(row['Conductivity.Temperature.Unit']) if pd.notna(row['Conductivity.Temperature.Unit']) else None)


# 'SPE'
i = 0
for url, group in raw_data_df.groupby('Title'):
    i += 1
    for index, row in group.iterrows():

        if row['Salts1.Abbr.Standard'] !='FALSE' and row['Polymer.Abbr.Standard'] !='FALSE': 
            dummy_node_id = f"{row['Polymer.Abbr.Standard']}@{row['Salts1.Abbr.Standard']}"
        elif row['Salts1.Abbr'] and row['Polymer.Abbr.Standard']:
            dummy_node_id = f"{row['Polymer.Abbr']}@{row['Salts1.Abbr']}"
        
        G.add_node(dummy_node_id, label='dummy_SPE')
    
        rounded_value = round(row['log(Conductivity.Value)'], 2) 
        unique_value_id = f'{rounded_value}_({index})'


        unique_node_id = uuid.uuid4()

        G.add_node(unique_node_id, 
                   label='Conductivity.Value',
                   rounded_value=rounded_value,
                   label1=str(row['Conductivity Label']) if pd.notna(row['Conductivity Label']) else None,
                   unit=str(row['Conductivity.Unit']) if pd.notna(row['Conductivity.Unit']) else None,
                   )  


        if row['Salts1.Abbr.Standard'] !='FALSE': 
            if not G.has_edge(row['Salts1.Abbr.Standard'], dummy_node_id):
                G.add_edge(row['Salts1.Abbr.Standard'], dummy_node_id,
                        label='Basis')
            
        if row['Polymer.Abbr.Standard'] !='FALSE': 
            if not G.has_edge(row['Polymer.Abbr.Standard'], dummy_node_id):
                G.add_edge(row['Polymer.Abbr.Standard'], dummy_node_id,
                        label='Basis',
                        condition=f'Concentration:{row["Polymer.Concentration.Value"]}{row["Polymer.Concentration.Unit"]},Weight_Ratio:{row["Polymer.Component.Weight_Ratio"]},Molar_Ratio:{row["Polymer.Component.Molar_Ratio"]}')
            
        if not G.has_edge(dummy_node_id, unique_node_id):
            G.add_edge(dummy_node_id,unique_node_id,
                    label='Property',
                    condition=f'{row["Conductivity.Temperature.Value"]}{row["Conductivity.Temperature.Unit"]}')

        if pd.notnull(row['Salts1.Abbr.Standard']) and pd.notnull(rounded_value) and row['Salts1.Abbr.Standard']!='FALSE':  # 只在 salt 和 Conductivity 都非空时添加边
            G.add_edge(row['Salts1.Abbr.Standard'], unique_node_id, label='Property', condition=f'{row["Conductivity.Ion"]}')
        
        if not G.has_edge(dummy_node_id, row['Electrochemical_Window.Value']):
            G.add_edge(dummy_node_id, row['Electrochemical_Window.Value'],
                       label='Property',
                       condition=f"{row['Electrochemical_Window.Temperature.Value']}{str(row['Electrochemical_Window.Temperature.Unit']) if pd.notna(row['Electrochemical_Window.Temperature.Unit']) else None}")
        if not G.has_edge(dummy_node_id, row['Transference_Number.Value']):
            G.add_edge(dummy_node_id, row['Transference_Number.Value'],
                       label='Property',
                       condition=f"{row['Transference_Number.Temperature.Value']} {str(row['Transference_Number.Temperature.Unit']) if pd.notna(row['Transference_Number.Temperature.Unit']) else None}")
        if not G.has_edge(dummy_node_id, row['Critical_Current_Density.Value']):
            G.add_edge(dummy_node_id, row['Critical_Current_Density.Value'],label='Property')
        
            # Conductivity Label
        if pd.notnull(row['Conductivity Label']): 
            G.add_edge(row['Conductivity Label'],unique_node_id,label ='Property')



for index, row in raw_data_df.iterrows():
    rounded_value = round(row['log(Conductivity.Value)'], 2) 
    # Monomer edge
    monomers = [row['Monomers1.Abbr.Standard']]
    for monomer in monomers:
        if pd.notnull(monomer) and row['Monomers1.Abbr.Standard']!='FALSE':  # 只在 monomer 非空时添加边
            G.add_edge(monomer, row['Polymer.Abbr.Standard'],
                       label="Polymerzation",
                       condition=f"{row['Initiators1.Name.Standard']} {row['Initiators1.Concentration.Value']}{row['Initiators1.Concentration.Unit']}, {row['Polymerization.Temperature.Value']}{row['Polymerization.Temperature.Unit']}, {row['Polymerization.Time.Value']}{row['Polymerization.Time.Unit']}")
            


    # Polymer edge
    if pd.notnull(row['Polymer.Abbr.Standard']) and pd.notnull(row['Tensile_Strength.Value']) and row['Polymer.Abbr.Standard']!='FALSE': 
        G.add_edge(row['Polymer.Abbr.Standard'], row['Tensile_Strength.Value'], label='Property')
    if pd.notnull(row['Polymer.Abbr.Standard']) and pd.notnull(row['Initiators1.Name.Standard']) and row['Polymer.Abbr.Standard']!='FALSE' and row['Initiators1.Name.Standard']!='FALSE': 
        G.add_edge(row['Initiators1.Name.Standard'], row['Polymer.Abbr.Standard'],
                       label="Polymerzation")




nodes_to_remove = [node for node, data in G.nodes(data=True) if (not node or pd.isna(node)) and all(pd.isna(v) or v == "" for v in data.values())]
G.remove_nodes_from(nodes_to_remove)


print("\nNumber of nodes:", G.number_of_nodes())
print("Number of edges:", G.number_of_edges())


node_data = []
for node, data in G.nodes(data=True):
     if node == 'FALSE':
         continue
     node_data.append({"Node": node, **data})


edge_data = []
for u, v, data in G.edges(data=True):
    if u == 'FALSE' or v == 'FALSE':
         continue
    edge_data.append({"Source": u, "Target": v, **data})

# Save to CSV
node_df = pd.DataFrame(node_data)
edge_df = pd.DataFrame(edge_data)

edge_nodes = set(edge_df['Source']).union(set(edge_df['Target']))
node_nodes = set(node_df['Node'])
missing_nodes = edge_nodes - node_nodes

if missing_nodes:
    print(f"Adding {len(missing_nodes)} missing nodes to node data.")
    for node in missing_nodes:
        node_data.append({"Node": node})
    node_df = pd.DataFrame(node_data)

node_df.to_csv("data/nodes.csv", index=False)
edge_df.to_csv("data/edges.csv", index=False)



print("Node and edge data saved to CSV.")
print(f"Total nodes in node_df: {len(node_df)}")
print(f"Total edges in edge_df: {len(edge_df)}")
