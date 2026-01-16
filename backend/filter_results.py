import json

def count_triplets_and_results():
    # Load the extraction results
    with open('extraction_results.json', 'r') as f:
        data = json.load(f)
    
    total_results = len(data)
    total_triplets = sum(len(item['triplets']) for item in data)
    
    print(f"Total results: {total_results}")
    print(f"Total triplets: {total_triplets}")
    return total_results, total_triplets

def filter_extraction_results():
    # Load the extraction results
    with open('extraction_results.json', 'r') as f:
        data = json.load(f)
    
    # Filter out entries with 0 triplets
    filtered_data = [item for item in data if len(item['triplets']) > 0]
    
    # Write back the filtered data
    with open('extraction_results.json', 'w') as f:
        json.dump(filtered_data, f, indent=2)
    
    print(f"Original entries: {len(data)}")
    print(f"Filtered entries: {len(filtered_data)}")
    print(f"Removed {len(data) - len(filtered_data)} entries with 0 triplets.")

if __name__ == "__main__":
    count_triplets_and_results()
    # filter_extraction_results()  # Uncomment if you want to filter after counting