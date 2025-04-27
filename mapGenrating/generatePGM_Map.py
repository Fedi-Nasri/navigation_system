import cv2
from pyproj import Proj
import numpy as np

# Your polygon coordinates (Paris, France example)
polygon = [
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
]

# UTM Zone for Paris (zone 31N)
utm_proj = Proj(proj="utm", zone=31, ellps="WGS84")

# Convert to UTM (meters)
utm_points = [utm_proj(point["lng"], point["lat"]) for point in polygon]
utm_points = np.array(utm_points)

# Calculate map bounds
min_x, min_y = np.min(utm_points, axis=0)
max_x, max_y = np.max(utm_points, axis=0)
print("Min", min_x, min_y)
print("Max", max_x, max_y)

# Map parameters
resolution = 0.05  # 5cm/pixel (adjustable)
width_m = max_x - min_x
height_m = max_y - min_y
width_px = int(width_m / resolution)
height_px = int(height_m / resolution)

# Create map layers
free_space_layer = np.zeros((height_px, width_px), dtype=np.uint8)  # Interior=255
border_layer = np.zeros((height_px, width_px), dtype=np.uint8)      # Border=255 (temporary)

# Convert UTM to pixel coordinates
pixel_points = [(
    int((x - min_x) / resolution),
    height_px - int((y - min_y) / resolution)  # Flip Y-axis
) for (x, y) in utm_points]
pixel_points = np.array([pixel_points], dtype=np.int32)

# Draw filled polygon (interior, 255=free)
cv2.fillPoly(free_space_layer, pixel_points, color=255)

# Draw border (temporary 255, thickness=50cm)
border_thickness = int(0.5 / resolution)  # 50cm thick border
cv2.polylines(border_layer, pixel_points, isClosed=True, 
              color=255, thickness=border_thickness)

# Create final map (default=unknown, 205)
grid = np.full((height_px, width_px), 205, dtype=np.uint8)
grid[free_space_layer == 255] = 255  # Interior=free (255)
grid[border_layer == 255] = 0        # Border=occupied (0)

# Save PGM
cv2.imwrite("map.pgm", grid)