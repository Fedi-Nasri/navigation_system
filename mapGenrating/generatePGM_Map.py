import cv2
from pyproj import Proj, Transformer
import numpy as np

def get_utm_zone(lon, lat):
    """
    Determine the UTM zone number for given longitude and latitude
    """
    # UTM zones are 6 degrees wide, starting at -180
    zone_number = int((lon + 180) / 6) + 1
    
    # Handle special cases for Norway and Svalbard
    if lat >= 56.0 and lat < 64.0 and lon >= 3.0 and lon < 12.0:
        zone_number = 32
    elif lat >= 72.0 and lat < 84.0:
        if lon >= 0.0 and lon < 9.0:
            zone_number = 31
        elif lon >= 9.0 and lon < 21.0:
            zone_number = 33
        elif lon >= 21.0 and lon < 33.0:
            zone_number = 35
        elif lon >= 33.0 and lon < 42.0:
            zone_number = 37
    
    # Determine if we're in the northern or southern hemisphere
    zone_letter = 'N' if lat >= 0 else 'S'
    
    return zone_number, zone_letter

def generate_map(coordinates, output_path="map.pgm", resolution=0.05):
    """
    Generate a PGM map from a list of coordinates
    coordinates: list of dicts with 'lat' and 'lng' keys
    output_path: path to save the generated map
    resolution: map resolution in meters per pixel
    """
    # Calculate the center point of the coordinates
    center_lon = sum(point["lng"] for point in coordinates) / len(coordinates)
    center_lat = sum(point["lat"] for point in coordinates) / len(coordinates)
    
    # Get the appropriate UTM zone
    zone_number, zone_letter = get_utm_zone(center_lon, center_lat)
    print(f"Using UTM Zone {zone_number}{zone_letter}")
    
    # Create UTM projection for the detected zone
    utm_proj = Proj(proj="utm", zone=zone_number, ellps="WGS84", south=(zone_letter == 'S'))
    
    # Convert to UTM (meters)
    utm_points = [utm_proj(point["lng"], point["lat"]) for point in coordinates]
    utm_points = np.array(utm_points)

    # Calculate map bounds
    min_x, min_y = np.min(utm_points, axis=0)
    max_x, max_y = np.max(utm_points, axis=0)
    print("Min", min_x, min_y)
    print("Max", max_x, max_y)

    # Map parameters
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
    cv2.imwrite(output_path, grid)
    # Also save to the Gazebo maps directory
    gazebo_map_path = "/home/fedi/asv_ws/src/asv_wave_sim/asv_wave_sim_gazebo/maps/map.pgm"
    cv2.imwrite(gazebo_map_path, grid)
    return output_path

if __name__ == "__main__":
    # Example usage
    from map_data import MAPS_DATA
    coordinates = MAPS_DATA["Paris Area 1"]
    generate_map(coordinates)