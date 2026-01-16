import json
import pandas as pd

# JSON data
files = "output_data_2008"
file_path = files + ".json"
with open(file_path, 'r', encoding='utf-8') as file:
    json_data = file.read()

data = json.loads(json_data)

def process_conductivity_data(data):
    new_data = {}

    for url, entries in data.items():
        new_entries = []
        for entry in entries:
            if isinstance(entry, dict):
                # Extract all key-value pairs except for "Conductivity"
                base_record = {k: v for k, v in entry.items() if k != "Conductivity"}

                if "Conductivity" in entry and entry["Conductivity"]:
                    for conductivity in entry["Conductivity"]:
                        # Create a new record for each conductivity value
                        new_record = base_record.copy()
                        new_record["Conductivity"] = conductivity
                        new_entries.append(new_record)
                else:
                    new_entries.append(base_record)
            else:
                # If the entry is not a dict, just append it as is
                new_entries.append(entry)
        
        new_data[url] = new_entries
    
    return new_data


def json_to_csv_recursive(data):
    rows = []
    columns = set()

    def flatten_dict(d, parent_key='', sep='.'):
        if not isinstance(d, dict):
            return {parent_key: d}
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                for i, item in enumerate(v, start=1):
                    if isinstance(item, dict):
                        items.extend(flatten_dict(item, f"{new_key}{i}", sep=sep).items())
                    else:
                        items.append((f"{new_key}{i}", item))
            else:
                items.append((new_key, v))
        return dict(items)

    ordered_columns = ["url"]

    for url, entries in data.items():
        for entry in entries:
            row = {"url": url}
            flat_entry = flatten_dict(entry)

            for k, v in flat_entry.items():
                if k not in columns:
                    columns.add(k)
                    ordered_columns.append(k)
                row[k] = v

            rows.append(row)

    df = pd.DataFrame(rows)
    df = df.reindex(columns=ordered_columns)
    
    return df


processed_data = process_conductivity_data(data)
df = json_to_csv_recursive(processed_data)
csv_file_path = files + ".csv"
df.to_csv(csv_file_path, index=False,encoding='utf-8')

# csv_file_path