import firebase_admin
from firebase_admin import credentials, db

# Firebase configuration (commented out - to be implemented manually)
"""
cred = credentials.Certificate("path/to/your/serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'your-database-url'
})

def get_maps_from_firebase():
    ref = db.reference('/maps')
    return ref.get()
"""

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
    "Paris Area 2": [
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

def get_available_maps():
    """Get list of available map names"""
    return list(MAPS_DATA.keys())

def get_map_coordinates(map_name):
    """Get coordinates for a specific map"""
    return MAPS_DATA.get(map_name, []) 