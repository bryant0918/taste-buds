import os
import requests
from haversine import haversine, Unit
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FOURSQUARE_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "X-Places-Api-Version": "2025-06-17",
    "accept": "application/json"
}

def get_foursquare_places(lat, lon, radius_m=1000, limit=10):
    url = "https://places-api.foursquare.com/places/search"
    params = {
        "ll": f"{lat},{lon}",
        "radius": radius_m,
        "query": "restaurant",  # Using text query for restaurants instead of category IDs
        "limit": 50
    }

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        
        if response.status_code == 401:
            print("Foursquare API Key appears to be invalid or expired")
            return []
        
        response.raise_for_status()
        data = response.json()
        places = data.get("results", [])

        results = []
        for p in places:
            # Handle the new geocodes structure
            # geocodes = p.get("geocodes", {})
            # main_geocode = geocodes.get("main", {})
            b_lat = p.get("latitude")
            b_lon = p.get("longitude")
            
            if b_lat is None or b_lon is None:
                continue  # Skip places without valid coordinates
                
            distance = haversine((lat, lon), (b_lat, b_lon), unit=Unit.METERS)
            results.append({
                "name": p.get("name", "N/A"),
                "distance_m": distance,
                "lat": b_lat,
                "lon": b_lon
            })

        return sorted(results, key=lambda x: x["distance_m"])[:limit]
    
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return []


if __name__ == "__main__":
    # center_lat = float(input("Enter latitude: "))
    # center_lon = float(input("Enter longitude: "))
    # radius = float(input("Enter radius in meters: "))

    center_lat = 40.57041
    center_lon = -111.93905
    radius = 3000

    closest_fsq = get_foursquare_places(center_lat, center_lon, radius)
    print("\nClosest Foursquare places:")
    for idx, place in enumerate(closest_fsq, 1):
        print(f"{idx}. {place['name']} - {place['distance_m']:.0f} m")
