import pandas as pd
from rdkit import Chem
from rdkit.Chem import Draw
import os

def generate_molecule_images(mol_info_df, output_dir='D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\molecule_picture', img_size=(400, 400)):
    """
    Generate molecule images from SMILES and save them with formula as filename
    
    Parameters:
    mol_info_df (pd.DataFrame): DataFrame containing 'smiles' and 'formula' columns
    output_dir (str): Directory to save the images (default: current directory)
    img_size (tuple): Size of the output images in pixels (width, height)
    
    Returns:
    list: List of successfully generated image paths
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    generated_images = []
    
    for idx, row in mol_info_df.iterrows():
        try:
            # Get SMILES and formula
            smiles = row['smiles']
            test = row['test']
            
            # Convert SMILES to RDKit molecule
            mol = Chem.MolFromSmiles(smiles)
            
            if mol is None:
                print(f"Failed to parse SMILES for formula: {test}")
                continue
                
            # Generate 2D depiction
            img = Draw.MolToImage(mol, size=img_size)
            
            # Create filename
            filename = f"{test}.png"
            filepath = os.path.join(output_dir, filename)
            
            # Save image
            img.save(filepath)
            generated_images.append(filepath)
            print(f"Successfully generated image for {test}")
            
        except Exception as e:
            print(f"Error processing {test}: {str(e)}")
    
    return generated_images

mol_info=pd.read_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\electrolyte_1\\4mol_info_1_remove.xlsx')
# print(mol_info)
# generate_molecule_images(mol_info)