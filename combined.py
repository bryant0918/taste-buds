from overpass import get_overpass_places
from yelp import load_yelp_data_from_json
from foursquare import get_foursquare_places
from google_maps import load_google_data_from_json
from haversine import haversine, Unit
from visited import office_visited, office_doesnt_exist, office_skip, home_visited, home_doesnt_exist, home_skip

def normalize_place_name(name):
    """
    Normalize place names for robust matching across data sources.
    """
    if not name:
        return ""
    return " ".join(str(name).split()).casefold()

def deduplicate_places(places, distance_threshold_m=50):
    """
    Remove duplicate places based on name similarity and proximity.
    Places with the same name within distance_threshold_m are considered duplicates.
    """
    unique_places = []

    for place in places:
        is_duplicate = False

        # Convert coordinates to float to ensure compatibility with haversine
        place_lat = float(place['lat'])
        place_lon = float(place['lon'])

        # print(f"Checking place: {place['name']} at ({place_lat}, {place_lon})")

        for existing in unique_places:
            # Check if names match (case insensitive)
            if normalize_place_name(place['name']) == normalize_place_name(existing['name']):
                # print(f"\nFound potential duplicate: {existing['name']} at ({existing['lat']}, {existing['lon']})")

                # Convert existing coordinates to float as well
                existing_lat = float(existing['lat'])
                existing_lon = float(existing['lon'])

                # Calculate distance between coordinates
                distance = haversine(
                    (place_lat, place_lon),
                    (existing_lat, existing_lon),
                    unit=Unit.METERS
                )
                # print(f"Distance to existing: {distance:.3f} m")

                # If same name and within threshold distance, it's a duplicate
                if distance <= distance_threshold_m:
                    is_duplicate = True
                    # Keep the one with shorter distance from center
                    if place['distance_m'] < existing['distance_m']:
                        # Replace existing with this better one
                        unique_places.remove(existing)
                        unique_places.append(place)
                    break

        if not is_duplicate:
            unique_places.append(place)

    return unique_places

def filter_unvisited_places(places, visited_places, distance_threshold_m=50):
    """
    Remove places that have been visited before.
    Places with the same name and similar distance are considered visited.
    """
    unvisited_places = []

    for place in places:
        is_visited = False
        place_name = normalize_place_name(place.get('name'))

        for visited in visited_places:
            # Check if names match (case insensitive)
            if place_name == normalize_place_name(visited.get('name')):
                # Check if the distance is within threshold (same place, roughly same distance from center)
                distance_diff = abs(place['distance_m'] - visited['distance_m'])

                if distance_diff <= distance_threshold_m:
                    is_visited = True
                    break

        if not is_visited:
            unvisited_places.append(place)

    return unvisited_places

def main(start_location="office"):
    if start_location == "office":
        center_lat = 40.57041
        center_lon = -111.93905
        yelp_json = "yelp_data.json"
        google_json = "google_data/google_office.json"
    elif start_location == "home":
        center_lat = 40.368675
        center_lon = -111.824788
        yelp_json = "yelp_data_home.json"
        google_json = "google_data/google_home.json"
    elif start_location == "wework":
        center_lat = 40.43064
        center_lon = 111.87575

    radius = 3000

    # Get closest places from OpenStreetMap
    try:
        closest_overpass = get_overpass_places(center_lat, center_lon, radius)
    except Exception as e:
        print(f"Error fetching Overpass data: {e}")
        closest_overpass = []
    # Get closest places from Yelp (load from saved JSON file)
    closest_yelp = load_yelp_data_from_json(yelp_json)

    # Get closest places from Foursquare
    closest_fsq = get_foursquare_places(center_lat, center_lon, radius)

    # Get closest places from Google Maps (load from saved JSON file)
    closest_google = load_google_data_from_json(google_json)

    # Assuming closest_osm, closest_yelp, closest_fsq are lists of dicts
    combined = closest_overpass + closest_yelp + closest_fsq + closest_google

    # Deduplicate by name and proximity (smart deduplication)
    unique_places = deduplicate_places(combined, distance_threshold_m=150)


    if start_location == "office":
        visited = office_visited
        doesnt_exist = office_doesnt_exist
        skip = office_skip
    elif start_location == "home":
        visited = home_visited
        doesnt_exist = home_doesnt_exist
        skip = home_skip

    # Filter out visited places
    unvisited_places = filter_unvisited_places(unique_places, visited, distance_threshold_m=100)

    # Filter out places that don't exist
    unvisited_places = filter_unvisited_places(unvisited_places, doesnt_exist, distance_threshold_m=100)

    # Filter places to skip (like drink places and grocery stores)
    unvisited_places = filter_unvisited_places(unvisited_places, skip, distance_threshold_m=100)

    final_sorted = sorted(unvisited_places, key=lambda x: x['distance_m'])

    # Show visited places for reference
    print(f"\nVisited places ({len(visited)}):")
    for visited_place in visited:
        print(f"- {visited_place['name']} ({visited_place['distance_m']} m)")

    # Show top 10 closest unvisited places
    print(f"\nTop 10 closest unvisited places:")
    for idx, place in enumerate(final_sorted[:10], 1):
        name = place.get("name", "N/A")
        dist = place.get("distance_m", 0)
        print(f"{idx}. {name} - {dist:.0f} m")

if __name__ == "__main__":
    main("home")
