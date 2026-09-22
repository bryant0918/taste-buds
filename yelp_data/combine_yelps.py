import json
import os
import glob
from datetime import datetime
from haversine import haversine, Unit

def load_all_yelp_files(directory="."):
    """Load all yelp_data_*.json files from the directory."""
    all_places = []
    file_pattern = os.path.join(directory, "yelp_data_home*.json")
    json_files = glob.glob(file_pattern)
    
    print(f"Found {len(json_files)} Yelp data files to process:")
    
    for file_path in sorted(json_files):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            places = data.get("data", [])
            timestamp = data.get("timestamp", "Unknown")
            filename = os.path.basename(file_path)
            
            print(f"  - {filename}: {len(places)} places (saved: {timestamp})")
            all_places.extend(places)
            
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            print(f"Error loading {file_path}: {e}")
    
    print(f"\nTotal places loaded: {len(all_places)}")
    return all_places

def deduplicate_places(places, distance_threshold_m=50):
    """
    Remove duplicate places based on name similarity and proximity.
    Places with the same name within distance_threshold_m are considered duplicates.
    """
    unique_places = []
    duplicates_removed = 0
    
    print(f"\nDeduplicating places (threshold: {distance_threshold_m}m)...")
    
    for place in places:
        is_duplicate = False
        
        # Convert coordinates to float to ensure compatibility with haversine
        place_lat = float(place['lat'])
        place_lon = float(place['lon'])
        
        for existing in unique_places:
            # Check if names match (case insensitive)
            if place['name'].lower() == existing['name'].lower():
                # Convert existing coordinates to float as well
                existing_lat = float(existing['lat'])
                existing_lon = float(existing['lon'])
                
                # Calculate distance between coordinates
                distance = haversine(
                    (place_lat, place_lon), 
                    (existing_lat, existing_lon), 
                    unit=Unit.METERS
                )
                
                # If same name and within threshold distance, it's a duplicate
                if distance <= distance_threshold_m:
                    is_duplicate = True
                    duplicates_removed += 1
                    
                    # Keep the one with shorter distance from center (better data)
                    if place['distance_m'] < existing['distance_m']:
                        # Replace existing with this better one
                        unique_places.remove(existing)
                        unique_places.append(place)
                        print(f"  Replaced duplicate: {place['name']} (better distance: {place['distance_m']:.0f}m vs {existing['distance_m']:.0f}m)")
                    else:
                        print(f"  Skipped duplicate: {place['name']} (distance: {place['distance_m']:.0f}m)")
                    break
        
        if not is_duplicate:
            unique_places.append(place)
    
    print(f"Removed {duplicates_removed} duplicates")
    print(f"Final unique places: {len(unique_places)}")
    
    return unique_places

def save_combined_data(places, filename="yelp_data.json"):
    """Save the combined and deduplicated data to a JSON file."""
    # Sort by distance for consistency
    sorted_places = sorted(places, key=lambda x: x['distance_m'])
    
    save_data = {
        "timestamp": datetime.now().isoformat(),
        "data": sorted_places,
        "count": len(sorted_places),
        "source": "Combined from multiple Yelp data files"
    }
    
    with open(filename, 'w') as f:
        json.dump(save_data, f, indent=2)
    
    print(f"\nSaved {len(sorted_places)} unique places to {filename}")
    return sorted_places

def main():
    """Main function to combine and deduplicate all Yelp data files."""
    print("=== Yelp Data Combiner ===")
    
    # Load all data from JSON files
    all_places = load_all_yelp_files()
    
    if not all_places:
        print("No data found to process!")
        return
    
    # Deduplicate the places
    unique_places = deduplicate_places(all_places, distance_threshold_m=50)
    
    # Save the combined data
    output_file = "../yelp_data_home.json"  # Save to parent directory
    final_places = save_combined_data(unique_places, output_file)
    
    # Show some statistics
    print(f"\n=== Summary ===")
    print(f"Original total places: {len(all_places)}")
    print(f"Unique places after deduplication: {len(final_places)}")
    print(f"Duplicates removed: {len(all_places) - len(final_places)}")
    print(f"Deduplication rate: {((len(all_places) - len(final_places)) / len(all_places) * 100):.1f}%")
    
    # Show closest 10 places
    print(f"\nClosest 10 unique places:")
    for idx, place in enumerate(final_places[:10], 1):
        print(f"{idx:2d}. {place['name']} - {place['distance_m']:.0f}m - {place['address']}")

if __name__ == "__main__":
    main()
