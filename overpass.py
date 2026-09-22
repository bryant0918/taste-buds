import overpy
from haversine import haversine, Unit

def get_overpass_places(lat, lon, radius_m=1000, top_n=10):
    """
    Get closest restaurants and fast food spots using OpenStreetMap.

    Args:
        lat (float): Latitude of center point
        lon (float): Longitude of center point
        radius_m (float): Search radius in meters
        top_n (int): Number of closest places to return

    Returns:
        List of dicts with name, distance, coordinates, and place type
    """
    api = overpy.Overpass()

    # Build Overpass query to get both restaurants and fast_food
    query = f"""
    (
      node[amenity=restaurant](around:{radius_m},{lat},{lon});
      node[amenity=fast_food](around:{radius_m},{lat},{lon});
    );
    out;
    """
    result = api.query(query)

    # Calculate distances
    places = []
    for node in result.nodes:
        distance = haversine(
            (float(lat), float(lon)),
            (float(node.lat), float(node.lon)),
            unit=Unit.METERS
        )
        places.append({
            'name': node.tags.get('name', 'N/A'),
            'distance_m': distance,
            'lat': node.lat,
            'lon': node.lon,
            'type': node.tags.get('amenity', 'N/A')
        })

    # Sort by distance and return top N
    places_sorted = sorted(places, key=lambda x: x['distance_m'])[:top_n]
    return places_sorted


if __name__ == "__main__":
    # Example: Your coordinates (appears to be Utah area)
    # center_lat = float(input("Enter latitude: "))
    # center_lon = float(input("Enter longitude: "))
    # radius = float(input("Enter radius in meters: "))
    center_lat = 40.57041
    center_lon = -111.93905
    radius = 3000

    closest_places = get_overpass_places(center_lat, center_lon, radius)

    print(f"\nClosest food places within {radius} meters:")
    for idx, place in enumerate(closest_places, 1):
        print(f"{idx}. {place['name']} ({place['type']}) - {place['distance_m']:.0f} meters away")
