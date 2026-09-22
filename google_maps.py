import requests
import json
import os
import time
from datetime import datetime
from haversine import haversine, Unit
from dotenv import load_dotenv
import math

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")


def save_google_data_to_json(data, filename="google_maps_data.json"):
    """Save Google Maps data to a JSON file with metadata."""
    save_data = {
        "timestamp": datetime.now().isoformat(),
        "data": data,
        "count": len(data)
    }

    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, 'w') as f:
        json.dump(save_data, f, indent=2)

    print(f"Saved {len(data)} Google places to {filename}")


def load_google_data_from_json(filename="google_maps_data.json"):
    """Load Google Maps data from a JSON file."""
    if not os.path.exists(filename):
        print(f"No saved Google data found at {filename}")
        return []

    try:
        with open(filename, 'r') as f:
            saved_data = json.load(f)

        data = saved_data.get("data", [])
        timestamp = saved_data.get("timestamp", "Unknown")
        print(f"Loaded {len(data)} Google places from {filename} (saved: {timestamp})")
        return data

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error loading Google data: {e}")
        return []
    
def generate_grid(lat, lon, step_m=1000):
    """
    Generate grid points around center.
    step_m = spacing between points
    """
    offsets = [-1, 0, 1]
    points = []

    for dx in offsets:
        for dy in offsets:
            new_lat = lat + (dx * step_m / 111_000)
            new_lon = lon + (dy * step_m / (111_000 * abs(math.cos(math.radians(lat)))))

            points.append((new_lat, new_lon))

    return points


def dedup_google_results(places):
    seen = {}
    
    for place in places:
        place_id = place.get("place_id")

        if place_id:
            # keep closest version if duplicates exist
            if place_id not in seen or place["distance_m"] < seen[place_id]["distance_m"]:
                seen[place_id] = place
        else:
            key = (place["name"].lower(), round(place["distance_m"], -1))
            if key not in seen:
                seen[key] = place

    return list(seen.values())


def get_google_places(center_lat, center_lon, radius_m=1200):
    """
    Advanced Google Places fetch:
    - Uses grid search to bypass 60-result cap
    - Uses multiple keywords to diversify results
    - Calculates distance from ORIGINAL center point
    - Returns a combined list ready for deduplication
    """

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    # Place type (Google's category taxonomy, not free-text keyword search).
    # Tested against the live API: type=restaurant already catches fast-food
    # chains (e.g. In-N-Out) since Google tags them "restaurant" too — the
    # old keyword="restaurant" text search missed them because it matched on
    # name/description text, not category. type=food and type=meal_takeaway
    # were tested and dropped: "food" returns unrelated POIs (Target, hotels,
    # the city itself — Google doesn't actually filter on it), and
    # "meal_takeaway" only ever returned places already tagged "restaurant".
    place_types = [
        "restaurant",
    ]

    # 🔥 Generate grid points (you already implemented this)
    grid_points = generate_grid(center_lat, center_lon, step_m=radius_m)

    all_results = []

    for grid_lat, grid_lon in grid_points:
        for place_type in place_types:

            next_page_token = None

            while True:
                params = {
                    "location": f"{grid_lat},{grid_lon}",
                    "radius": radius_m,
                    "type": place_type,
                    "key": API_KEY
                }

                if next_page_token:
                    params["pagetoken"] = next_page_token

                response = requests.get(url, params=params)

                if response.status_code != 200:
                    print(f"❌ HTTP Error: {response.text}")
                    break

                data = response.json()

                status = data.get("status")

                if status not in ["OK", "ZERO_RESULTS"]:
                    print(f"❌ Google API Error: {status}")
                    print(data)
                    break

                results = data.get("results", [])

                for place in results:
                    g_lat = place["geometry"]["location"]["lat"]
                    g_lon = place["geometry"]["location"]["lng"]

                    # 🔥 IMPORTANT: distance from ORIGINAL center
                    distance = haversine(
                        (center_lat, center_lon),
                        (g_lat, g_lon),
                        unit=Unit.METERS
                    )

                    all_results.append({
                        "name": place.get("name", "N/A"),
                        "distance_m": distance,
                        "address": place.get("vicinity", "N/A"),
                        "lat": g_lat,
                        "lon": g_lon,
                        "rating": place.get("rating"),
                        "user_ratings_total": place.get("user_ratings_total"),
                        "place_id": place.get("place_id"),  # 🔥 useful later
                        "source": "google"
                    })

                next_page_token = data.get("next_page_token")

                if next_page_token:
                    time.sleep(2)  # required by Google
                else:
                    break

    # Final sort by distance from center
    deduped = dedup_google_results(all_results)
    return sorted(deduped, key=lambda x: x["distance_m"])


def dedup_google_json(input_file, output_file=None):
    """
    Deduplicate saved Google Maps JSON using place_id (primary) and fallback to name+distance.
    """

    import json
    import os

    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        return []

    with open(input_file, "r") as f:
        saved = json.load(f)

    data = saved.get("data", [])

    seen_place_ids = set()
    unique = []

    for place in data:
        place_id = place.get("place_id")

        # 🔥 Primary dedup: place_id
        if place_id:
            if place_id in seen_place_ids:
                continue
            seen_place_ids.add(place_id)
            unique.append(place)
        else:
            # fallback (rare): name + rounded distance
            key = (place["name"].lower(), round(place["distance_m"], -1))
            if key not in seen_place_ids:
                seen_place_ids.add(key)
                unique.append(place)

    # Sort again (clean output)
    unique_sorted = sorted(unique, key=lambda x: x["distance_m"])

    output_path = output_file or input_file.replace(".json", "_deduped.json")

    with open(output_path, "w") as f:
        json.dump({
            "timestamp": saved.get("timestamp"),
            "count": len(unique_sorted),
            "data": unique_sorted
        }, f, indent=2)

    print(f"Deduped {len(data)} → {len(unique_sorted)} places")
    print(f"Saved to {output_path}")

    return unique_sorted


if __name__ == "__main__":
    # Office
    center_lat = 40.57041
    center_lon = -111.93905

    # Home example:
    # center_lat = 40.368675
    # center_lon = -111.824788

    # radii = [i * 500 for i in range(1, 10)]
    # for radius in radii:
    #     output_path = f"google_data/google_data_home_{radius}.json"
    #     results = get_google_places(center_lat, center_lon, radius)
    #     save_google_data_to_json(results, output_path)

    # Just using grid to accumulate
    # radius = 1600
    # output_path = f"google_data/google_data_office_{radius}.json"
    # results = get_google_places(center_lat, center_lon, radius)
    # save_google_data_to_json(results, output_path)

    # print("\nSample output:")
    # for r in results[:10]:
    #     print(f"{r['name']} - {r['distance_m']:.0f} m")

    dedup_google_json("google_data/google_data_office_1600.json")
    dedup_google_json("google_data/google_data_home_1600.json")