import firebase_admin
from firebase_admin import credentials, db

# Firebase configuration (commented out - to be implemented manually)

cred = credentials.Certificate("/home/fedi/Desktop/navigation_system-main/navigation_system/pathPlannig/auth.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://oceancleaner-741db-default-rtdb.firebaseio.com/'
})

def get_maps_from_firebase():
    ref = db.reference('navigation/Maps')
    return ref.get()
def fetch_and_format_maps_from_firebase():
    """
    Fetch maps from Firebase and format them to match MAPS_DATA structure:
    """
    raw_maps = get_maps_from_firebase()
    formatted_maps = {}
    if not raw_maps:
        return formatted_maps

    for map_id, map_obj in raw_maps.items():
        name = map_obj.get("name", f"Map_{map_id}")
        coords = []
        for coord in map_obj.get("coordinates", []):
            if isinstance(coord, dict):
                coords.append({
                    "lat": coord.get("lat"),
                    "lng": coord.get("long") if "long" in coord else coord.get("lng")
                })
            else:
                # Skip or handle non-dict coordinate entries
                continue
        formatted_maps[name] = coords
    return formatted_maps

# Temporary map data for testing
MAPS_DATA = {
    "Paris Area 1": [
        {
            "lat": 48.83982259868138,
            "lng": 2.2680751075932153
        },
        {
            "lat": 48.8392718096646,
            "lng": 2.269190611027758
        },
        {
            "lat": 48.84002031633827,
            "lng": 2.26983417070155
        },
        {
            "lat": 48.84024627841906,
            "lng": 2.2697269107559053
        },
        {
            "lat": 48.84126309516769,
            "lng": 2.270692250266593
        },
        {
            "lat": 48.84177149580109,
            "lng": 2.27135726192949
        },
        {
            "lat": 48.84225164721632,
            "lng": 2.2701344985493015
        },
        {
            "lat": 48.84072644445604,
            "lng": 2.2687830232343624
        }
    ],
    "Area1": [
        {
            "lat": 48.83982259868138,
            "lng": 2.2680751075932153
        },
        {
            "lat": 48.8392718096646,
            "lng": 2.269190611027758
        },
        {
            "lat": 48.84002031633827,
            "lng": 2.26983417070155
        },
        {
            "lat": 48.84024627841906,
            "lng": 2.2697269107559053
        }
    ]
}
# Update MAPS_DATA with maps from Firebase if available
MAPS_DATA.update(fetch_and_format_maps_from_firebase())
# Uncomment the line below to fetch maps from Firebase only
# MAPS_DATA = fetch_and_format_maps_from_firebase()
def get_available_maps():
    """Get list of available map names"""
    return list(MAPS_DATA.keys())

def get_map_coordinates(map_name):
    """Get coordinates for a specific map"""
    return MAPS_DATA.get(map_name, [])

