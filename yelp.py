import requests
import json
import os
from datetime import datetime
from haversine import haversine, Unit
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YELP_API_KEY")
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def save_yelp_data_to_json(data, filename="yelp_data.json"):
    """Save Yelp data to a JSON file with metadata."""
    save_data = {
        "timestamp": datetime.now().isoformat(),
        "data": data,
        "count": len(data)
    }
    
    with open(filename, 'w') as f:
        json.dump(save_data, f, indent=2)
    
    print(f"Saved {len(data)} Yelp places to {filename}")

def load_yelp_data_from_json(filename="yelp_data.json"):
    """Load Yelp data from a JSON file."""
    if not os.path.exists(filename):
        print(f"No saved Yelp data found at {filename}")
        return []
    
    try:
        with open(filename, 'r') as f:
            saved_data = json.load(f)
        
        data = saved_data.get("data", [])
        timestamp = saved_data.get("timestamp", "Unknown")
        print(f"Loaded {len(data)} Yelp places from {filename} (saved: {timestamp})")
        return data
    
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error loading Yelp data from {filename}: {e}")
        return []

def get_yelp_places(lat, lon, radius_m=1000, term="food", limit=10):
    url = "https://api.yelp.com/v3/businesses/search"
    params = {
        "latitude": lat,
        "longitude": lon,
        "radius": radius_m,
        "term": term,
        "categories": "restaurants,food",
        "limit": limit  # Max per request
    }

    response = requests.get(url, headers=HEADERS, params=params)
    
    if response.status_code != 200:
        print(f"Yelp API Error: {response.status_code} - {response.text}")
        return []
    
    response.raise_for_status()
    businesses = response.json().get("businesses", [])

    # Compute distance manually to ensure exact haversine distance
    results = []
    for b in businesses:
        b_lat = b["coordinates"]["latitude"]
        b_lon = b["coordinates"]["longitude"]
        distance = haversine((lat, lon), (b_lat, b_lon), unit=Unit.METERS)
        results.append({
            "name": b["name"],
            "distance_m": distance,
            "address": ", ".join(b["location"]["display_address"]),
            "lat": b_lat,
            "lon": b_lon
        })

    # Sort and return top N
    return sorted(results, key=lambda x: x["distance_m"])[:limit]


if __name__ == "__main__":
    # center_lat = float(input("Enter latitude: "))
    # center_lon = float(input("Enter longitude: "))
    # radius = float(input("Enter radius in meters: "))
    # Office
    # center_lat = 40.57041
    # center_lon = -111.93905
    # Home
    center_lat = 40.368675
    center_lon = -111.824788
    radius = 1500
    limit = 50

    radii = [i * 500 for i in range(20)]
    for radius in radii:
        output_path = f"yelp_data/yelp_data_home_{radius}.json"
        closest_yelp = get_yelp_places(center_lat, center_lon, radius, limit=limit)
        
        # Save the data to JSON file
        save_yelp_data_to_json(closest_yelp, output_path)

    print("\nClosest Yelp places:")
    for idx, place in enumerate(closest_yelp, 1):
        print(f"{idx}. {place['name']} - {place['distance_m']:.0f} m - {place['address']}")
