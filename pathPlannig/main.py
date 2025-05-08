#!/usr/bin/env python3
import sys
import numpy as np
import cv2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView, 
                            QGraphicsScene, QGraphicsPixmapItem, QVBoxLayout,
                            QWidget, QPushButton, QLabel, QHBoxLayout, QComboBox,
                            QMessageBox)
from PyQt5.QtGui import QPixmap, QImage, QPen, QColor, QWheelEvent, QPainter
from PyQt5.QtCore import Qt, QPointF
import math
import os
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mapGenrating.map_data import get_available_maps, get_map_coordinates
from mapGenrating.generatePGM_Map import generate_map

# Firebase configuration (commented out - to be implemented manually)

import firebase_admin
from firebase_admin import credentials, db

def initialize_firebase():
    cred = credentials.Certificate("auth.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://oceancleaner-741db-default-rtdb.firebaseio.com'
    })

def upload_waypoints_to_firebase(waypoints_data):
    ref = db.reference('navigation/coverage_path_planning')
    ref.push(waypoints_data)


class NavigationManager:
    def __init__(self, grid_size=0.5, resolution=0.05):
        self.grid_size = grid_size
        self.resolution = resolution
        self.waypoints = []
        self.map_img = None
        self.height = 0
        self.width = 0
        self.current_map_name = None
    
    def load_map(self, map_path):
        """Load a map from file"""
        self.map_img = cv2.imread(map_path, cv2.IMREAD_GRAYSCALE)
        if self.map_img is None:
            raise FileNotFoundError(f"Could not load map file: {map_path}")
        self.height, self.width = self.map_img.shape
        self.waypoints = []  # Clear waypoints when loading new map
        return True
    
    def add_waypoint(self, x, y):
        if y < 0 or y >= self.height or x < 0 or x >= self.width:
            return False
        pixel_value = self.map_img[int(y)][int(x)]
        if pixel_value != 255:  # Only white pixels (255) are navigable
            return False
        self.waypoints.append(QPointF(x, y))
        return True
    
    def remove_nearest_waypoint(self, x, y):
        if not self.waypoints:
            return
        distances = [(p.x() - x)**2 + (p.y() - y)**2 for p in self.waypoints]
        if distances:
            nearest_idx = distances.index(min(distances))
            del self.waypoints[nearest_idx]
    
    def clear_waypoints(self):
        self.waypoints = []
    
    def get_waypoints(self):
        return self.waypoints
    
    def save_waypoints(self, filename="waypoints.yaml"):
        if not self.waypoints:
            return
        waypoints_meters = []
        for p in self.waypoints:
            x = p.x() * self.resolution
            y = (self.height - p.y()) * self.resolution
            waypoints_meters.append((x, y))
        with open(filename, "w") as f:
            f.write("# Boat navigation waypoints\n")
            f.write("waypoints:\n")
            for i, (x, y) in enumerate(waypoints_meters):
                f.write(f"  - point{x:.2f}_{y:.2f}:\n")
                f.write(f"      x: {x:.2f}\n")
                f.write(f"      y: {y:.2f}\n")
                f.write(f"      name: wp{i+1}\n")
    
    def get_waypoints_data(self):
        """Get waypoints data in a format suitable for Firebase"""
        if not self.waypoints:
            return None
            
        waypoints_meters = []
        for i, p in enumerate(self.waypoints, 1):  # Start enumeration from 1
            x = p.x() * self.resolution
            y = (self.height - p.y()) * self.resolution
            waypoints_meters.append({
                "point_number": i,
                "point_name": f"point{i}",
                "x": round(x, 2),
                "y": round(y, 2)
            })
            
        return {
            "map_name": self.current_map_name,
            "timestamp": datetime.now().isoformat(),
            "waypoints": waypoints_meters,
            "resolution": self.resolution,
            "grid_size": self.grid_size
        }

class CoveragePathPlanner:
    def __init__(self, map_img):
        self.map_img = map_img
        self.height, self.width = map_img.shape
    
    def get_navigable_range(self, y):
        y_int = int(round(y))
        if y_int < 0 or y_int >= self.height:
            return None, None
        x_min = None
        x_max = None
        for x in range(self.width):
            if self.map_img[y_int, x] == 255:
                if x_min is None:
                    x_min = x
                x_max = x
        return x_min, x_max
    
    def generate_path(self, x0, y0):
        points = [(float(x0), float(y0))]
        x_current = float(x0)
        y_current = float(y0)
        direction = 1.0  # 1.0 for right, -1.0 for left
        min_step = 10.0  # Minimum 0.5m (10 pixels)
        vertical_step = 60.0  # 60 pixels = 3m
        while True:
            # Get navigable range for current y
            y_int = int(round(y_current))
            if y_int < 0 or y_int >= self.height:
                break
            x_min, x_max = self.get_navigable_range(y_current)
            if x_min is None or x_max is None:
                break
            # Calculate dynamic spacing based on navigable width
            if direction > 0:
                x_start = max(x_current, x_min + 20)  # Start at least 1m from left border
                x_end = x_max - 10  # Stop 0.5m from right border
                if x_end <= x_start:
                    break
                available_width = x_end - x_start
                num_points = min(4, int(available_width // min_step) + 1)  # Up to 4 points
                if num_points > 1:
                    step = available_width / (num_points - 1)
                    for i in range(num_points):
                        x_candidate = x_start + i * step
                        x_int = int(round(x_candidate))
                        y_int = int(round(y_current))
                        if 0 <= x_int < self.width and self.map_img[y_int, x_int] == 255:
                            points.append((x_candidate, y_current))
                        else:
                            break
                    if len(points) > len(points) - num_points:
                        x_current = points[-1][0]
                elif num_points == 1:
                    x_candidate = x_start
                    x_int = int(round(x_candidate))
                    y_int = int(round(y_current))
                    if 0 <= x_int < self.width and self.map_img[y_int, x_int] == 255:
                        points.append((x_candidate, y_current))
                        x_current = x_candidate
            else:
                x_start = min(x_current, x_max - 20)  # Start at least 1m from right border
                x_end = x_min + 10  # Stop 0.5m from left border
                if x_end >= x_start:
                    break
                available_width = x_start - x_end
                num_points = min(4, int(available_width // min_step) + 1)  # Up to 4 points
                if num_points > 1:
                    step = available_width / (num_points - 1)
                    for i in range(num_points):
                        x_candidate = x_start - i * step
                        x_int = int(round(x_candidate))
                        y_int = int(round(y_current))
                        if 0 <= x_int < self.width and self.map_img[y_int, x_int] == 255:
                            points.append((x_candidate, y_current))
                        else:
                            break
                    if len(points) > len(points) - num_points:
                        x_current = points[-1][0]
                elif num_points == 1:
                    x_candidate = x_start
                    x_int = int(round(x_candidate))
                    y_int = int(round(y_current))
                    if 0 <= x_int < self.width and self.map_img[y_int, x_int] == 255:
                        points.append((x_candidate, y_current))
                        x_current = x_candidate
            # Move up
            y_next = y_current - vertical_step
            if y_next < 0:
                break
            # Check if there's navigable area at y_next
            x_min_next, x_max_next = self.get_navigable_range(y_next)
            if x_min_next is None or x_max_next is None:
                break
            points.append((x_current, y_next))
            y_current = y_next
            direction = -direction
        return points

class PathVisualizer:
    def __init__(self, scene, navigation_manager):
        self.scene = scene
        self.nav_manager = navigation_manager
        self.grid_items = []
        self.waypoint_items = []
        self.path_items = []
        self.arrow_items = []
    
    def clear_all(self):
        """Clear all visual elements from the scene"""
        try:
            # Clear grid items
            for item in self.grid_items:
                if item and item.scene():
                    self.scene.removeItem(item)
            self.grid_items.clear()
            
            # Clear waypoint items
            for item in self.waypoint_items:
                if item and item.scene():
                    self.scene.removeItem(item)
            self.waypoint_items.clear()
            
            # Clear path items
            for item in self.path_items:
                if item and item.scene():
                    self.scene.removeItem(item)
            self.path_items.clear()
            
            # Clear arrow items
            for item in self.arrow_items:
                if item and item.scene():
                    self.scene.removeItem(item)
            self.arrow_items.clear()
        except Exception as e:
            print(f"Error clearing items: {str(e)}")
    
    def draw_grid(self):
        for item in self.grid_items:
            self.scene.removeItem(item)
        self.grid_items.clear()
        
        pen = QPen(QColor(100, 100, 255, 100))
        pen.setWidth(1)
        
        grid_spacing_px = int(self.nav_manager.grid_size / self.nav_manager.resolution)
        
        for x in range(0, self.nav_manager.width, grid_spacing_px):
            line = self.scene.addLine(x, 0, x, self.nav_manager.height, pen)
            self.grid_items.append(line)
        
        for y in range(0, self.nav_manager.height, grid_spacing_px):
            line = self.scene.addLine(0, y, self.nav_manager.width, y, pen)
            self.grid_items.append(line)
    
    def draw_waypoints(self):
        for item in self.waypoint_items:
            self.scene.removeItem(item)
        self.waypoint_items.clear()
        
        for i, point in enumerate(self.nav_manager.get_waypoints()):
            # Starting point (first waypoint) in blue
            if i == 0:
                circle = self.scene.addEllipse(point.x()-5, point.y()-5, 10, 10, 
                                             QPen(Qt.blue), QColor(0, 0, 255))
            else:
                # Other waypoints in darker green
                circle = self.scene.addEllipse(point.x()-5, point.y()-5, 10, 10, 
                                             QPen(QColor(0, 100, 0)), QColor(0, 100, 0))
            self.waypoint_items.append(circle)
            
            text = self.scene.addText(str(i+1))
            text.setPos(point.x()+10, point.y()-10)
            text.setDefaultTextColor(Qt.red)
            self.waypoint_items.append(text)
    
    def draw_path(self):
        for item in self.path_items:
            self.scene.removeItem(item)
        self.path_items.clear()
        
        waypoints = self.nav_manager.get_waypoints()
        if len(waypoints) < 2:
            return
        
        pen = QPen(QColor(0, 255, 0))  # Green lines for path
        pen.setWidth(2)
        
        for i in range(len(waypoints) - 1):
            p1 = waypoints[i]
            p2 = waypoints[i+1]
            line = self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
            self.path_items.append(line)
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            dist_px = math.sqrt(dx**2 + dy**2)
            dist_m = dist_px * self.nav_manager.resolution
            mid_x = (p1.x() + p2.x()) / 2
            mid_y = (p1.y() + p2.y()) / 2
            text = self.scene.addText(f"{dist_m:.2f} m")
            text.setPos(mid_x, mid_y - 10)
            text.setDefaultTextColor(Qt.black)
            self.path_items.append(text)
    
    def draw_arrows(self):
        for item in self.arrow_items:
            self.scene.removeItem(item)
        self.arrow_items.clear()
        waypoints = self.nav_manager.get_waypoints()
        if len(waypoints) < 2:
            return
        for i in range(len(waypoints) - 1):
            p1 = waypoints[i]
            p2 = waypoints[i+1]
            mid_x = (p1.x() + p2.x()) / 2
            mid_y = (p1.y() + p2.y()) / 2
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            length = math.sqrt(dx**2 + dy**2)
            if length == 0:
                continue
            dx /= length
            dy /= length
            arrow_length = 10
            arrow_start_x = mid_x - arrow_length / 2 * dx
            arrow_start_y = mid_y - arrow_length / 2 * dy
            arrow_end_x = mid_x + arrow_length / 2 * dx
            arrow_end_y = mid_y + arrow_length / 2 * dy
            shaft = self.scene.addLine(arrow_start_x, arrow_start_y,
                                      arrow_end_x, arrow_end_y,
                                      QPen(Qt.black))
            self.arrow_items.append(shaft)
            arrow_size = 5
            angle = math.atan2(dy, dx)
            head1_x = arrow_end_x - arrow_size * math.cos(angle + math.pi / 6)
            head1_y = arrow_end_y - arrow_size * math.sin(angle + math.pi / 6)
            head2_x = arrow_end_x - arrow_size * math.cos(angle - math.pi / 6)
            head2_y = arrow_end_y - arrow_size * math.sin(angle - math.pi / 6)
            head1 = self.scene.addLine(arrow_end_x, arrow_end_y,
                                      head1_x, head1_y,
                                      QPen(Qt.black))
            head2 = self.scene.addLine(arrow_end_x, arrow_end_y,
                                      head2_x, head2_y,
                                      QPen(Qt.black))
            self.arrow_items.append(head1)
            self.arrow_items.append(head2)
    
    def update_display(self):
        self.draw_waypoints()
        self.draw_path()
        self.draw_arrows()

class CustomGraphicsView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setMouseTracking(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.nav_manager = None  # Will be set by MapNavigator
    
    def set_nav_manager(self, nav_manager):
        """Set the navigation manager for coordinate conversion"""
        self.nav_manager = nav_manager
    
    def mouseMoveEvent(self, event):
        """Handle mouse movement and update coordinate display"""
        super().mouseMoveEvent(event)
        if self.nav_manager and self.nav_manager.map_img is not None:
            # Get mouse position in scene coordinates
            pos = self.mapToScene(event.pos())
            x, y = pos.x(), pos.y()
            
            # Convert to real-world coordinates (meters)
            if 0 <= x < self.nav_manager.width and 0 <= y < self.nav_manager.height:
                real_x = x * self.nav_manager.resolution
                real_y = (self.nav_manager.height - y) * self.nav_manager.resolution
                
                # Update status label with coordinates
                navigator = self.parent().parent()
                navigator.update_coordinate_status(real_x, real_y)
    
    def wheelEvent(self, event: QWheelEvent):
        navigator = self.parent().parent()
        if event.angleDelta().y() > 0:
            navigator.zoom_in()
        else:
            navigator.zoom_out()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton or event.button() == Qt.RightButton:
            navigator = self.parent().parent()
            pos = self.mapToScene(event.pos())
            x, y = pos.x(), pos.y()
            if event.button() == Qt.RightButton:
                navigator.remove_nearest_waypoint(x, y)
            else:
                navigator.add_waypoint(x, y)
        else:
            super().mousePressEvent(event)

class MapNavigator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Boat Navigation Waypoint Planner")
        self.setGeometry(100, 100, 1000, 800)
        
        # Create maps directory if it doesn't exist
        self.maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
        os.makedirs(self.maps_dir, exist_ok=True)
        
        self.nav_manager = NavigationManager(grid_size=0.5, resolution=0.05)
        self.current_map_name = None
        self.current_map_path = None
        
        self.zoom_level = 1.0
        self.zoom_factor = 1.25
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        
        self.init_ui()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create two control layouts for better organization
        top_control_layout = QHBoxLayout()
        bottom_control_layout = QHBoxLayout()
        
        # Add map selection dropdown
        self.map_selector = QComboBox()
        self.map_selector.addItems(get_available_maps())
        self.map_selector.currentIndexChanged.connect(self.on_map_selected)
        
        # Add generate map button
        self.generate_map_btn = QPushButton("Generate Map")
        self.generate_map_btn.clicked.connect(self.generate_selected_map)
        
        # Add upload waypoints button (next to generate map)
        self.upload_btn = QPushButton("Upload Waypoints")
        self.upload_btn.clicked.connect(self.upload_waypoints)
        self.upload_btn.setEnabled(False)  # Initially disabled
        
        # Add buttons to top control layout
        top_control_layout.addWidget(self.map_selector)
        top_control_layout.addWidget(self.generate_map_btn)
        top_control_layout.addWidget(self.upload_btn)
        
        self.scene = QGraphicsScene()
        self.view = CustomGraphicsView(self.scene)
        self.view.setMouseTracking(True)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.set_nav_manager(self.nav_manager)  # Set nav_manager for coordinate conversion
        
        self.path_visualizer = PathVisualizer(self.scene, self.nav_manager)
        
        # Initialize empty scene
        self.setup_empty_scene()
        
        self.zoom_in_btn = QPushButton("Zoom In (+)")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        
        self.zoom_out_btn = QPushButton("Zoom Out (-)")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        
        self.reset_zoom_btn = QPushButton("Reset Zoom")
        self.reset_zoom_btn.clicked.connect(self.reset_zoom)
        
        self.clear_btn = QPushButton("Clear Waypoints")
        self.clear_btn.clicked.connect(self.clear_waypoints)
        
        self.save_btn = QPushButton("Save Waypoints")
        self.save_btn.clicked.connect(self.save_waypoints)
        
        self.create_path_btn = QPushButton("Create Path Planning")
        self.create_path_btn.clicked.connect(self.create_coverage_path)
        
        # Add buttons to bottom control layout
        bottom_control_layout.addWidget(self.zoom_in_btn)
        bottom_control_layout.addWidget(self.zoom_out_btn)
        bottom_control_layout.addWidget(self.reset_zoom_btn)
        bottom_control_layout.addWidget(self.clear_btn)
        bottom_control_layout.addWidget(self.save_btn)
        bottom_control_layout.addWidget(self.create_path_btn)
        
        # Disable buttons until map is loaded
        self.set_buttons_enabled(False)
        
        # Add both control layouts to main layout
        main_layout.addLayout(top_control_layout)
        main_layout.addLayout(bottom_control_layout)
        
        self.status_label = QLabel("Please select a map and click 'Generate Map' to begin")
        
        main_layout.addWidget(self.view)
        main_layout.addWidget(self.status_label)
        
        self.view.centerOn(self.scene.sceneRect().center())
    
    def setup_empty_scene(self):
        """Setup an empty scene with a message"""
        try:
            self.scene.clear()
            self.path_visualizer.clear_all()
            # Add a text item to indicate no map is loaded
            text = self.scene.addText("No map loaded.\nPlease select a map and click 'Generate Map'")
            text.setDefaultTextColor(Qt.gray)
            # Center the text
            text.setPos(self.view.width()/2 - text.boundingRect().width()/2,
                       self.view.height()/2 - text.boundingRect().height()/2)
        except Exception as e:
            print(f"Error setting up empty scene: {str(e)}")
            self.status_label.setText(f"Error setting up empty scene: {str(e)}")
    
    def set_buttons_enabled(self, enabled):
        """Enable or disable buttons based on map loading state"""
        try:
            self.zoom_in_btn.setEnabled(enabled)
            self.zoom_out_btn.setEnabled(enabled)
            self.reset_zoom_btn.setEnabled(enabled)
            self.clear_btn.setEnabled(enabled)
            self.save_btn.setEnabled(enabled)
            self.create_path_btn.setEnabled(enabled)
            self.upload_btn.setEnabled(enabled)
        except Exception as e:
            print(f"Error setting button states: {str(e)}")
    
    def on_map_selected(self, index):
        """Handle map selection from dropdown"""
        self.current_map_name = self.map_selector.currentText()
        self.status_label.setText(f"Selected map: {self.current_map_name}. Click 'Generate Map' to create it.")
    
    def upload_waypoints(self):
        """Upload waypoints to Firebase"""
        try:
            # Get waypoints data
            waypoints_data = self.nav_manager.get_waypoints_data()
            
            if not waypoints_data:
                QMessageBox.warning(self, "No Waypoints", 
                                  "Please add some waypoints before uploading.")
                return
            
            # Print data that would be uploaded (for testing)
            print("Preparing to upload waypoints data:")
            print(json.dumps(waypoints_data, indent=2))
            
            # Show confirmation dialog
            reply = QMessageBox.question(self, 'Confirm Upload',
                                       f'Upload {len(waypoints_data["waypoints"])} waypoints to Firebase?',
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # Firebase upload code (commented out - to be implemented manually)
                
                try:
                    initialize_firebase()
                    upload_waypoints_to_firebase(waypoints_data)
                    QMessageBox.information(self, "Success", 
                                          "Waypoints uploaded successfully!")
                except Exception as e:
                    QMessageBox.critical(self, "Upload Error", 
                                       f"Failed to upload waypoints: {str(e)}")
                
                
                # For testing, just print success message
                print("Waypoints would be uploaded to Firebase here")
                QMessageBox.information(self, "Test Mode", 
                                      "In test mode: Waypoints would be uploaded to Firebase.\n" +
                                      "Check console for data that would be uploaded.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                               f"An error occurred while preparing waypoints: {str(e)}")
    
    def generate_selected_map(self):
        """Generate map for the selected area"""
        if not hasattr(self, 'current_map_name'):
            self.status_label.setText("Please select a map first")
            return
        
        coordinates = get_map_coordinates(self.current_map_name)
        if not coordinates:
            self.status_label.setText("No coordinates found for selected map")
            return
        
        try:
            # Disable all buttons during map generation
            self.set_buttons_enabled(False)
            
            # Clear existing scene and items
            self.scene.clear()
            self.path_visualizer.clear_all()
            self.nav_manager.waypoints = []
            
            # Generate map filename based on map name
            map_filename = f"{self.current_map_name.replace(' ', '_')}.pgm"
            self.current_map_path = os.path.join(self.maps_dir, map_filename)
            
            # Generate the map
            generate_map(coordinates, output_path=self.current_map_path)
            
            # Load the generated map
            if self.nav_manager.load_map(self.current_map_path):
                self.nav_manager.current_map_name = self.current_map_name
                # Create a new scene
                self.scene = QGraphicsScene()
                self.view.setScene(self.scene)
                self.path_visualizer = PathVisualizer(self.scene, self.nav_manager)
                self.view.set_nav_manager(self.nav_manager)  # Update nav_manager reference
                self.setup_scene()
                self.set_buttons_enabled(True)
                self.status_label.setText(f"Generated and loaded map: {self.current_map_name}")
            else:
                self.status_label.setText("Error loading generated map")
        except Exception as e:
            self.status_label.setText(f"Error generating map: {str(e)}")
            self.set_buttons_enabled(False)
    
    def setup_scene(self):
        """Setup the scene with the current map"""
        try:
            if self.nav_manager.map_img is None:
                self.setup_empty_scene()
                return
            
            # Create new map display
            map_display = cv2.cvtColor(self.nav_manager.map_img, cv2.COLOR_GRAY2RGB)
            bytes_per_line = 3 * self.nav_manager.width
            qimg = QImage(map_display.data, self.nav_manager.width, self.nav_manager.height, 
                         bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            self.scene.addPixmap(pixmap)
            
            # Add border visualization
            border_mask = (self.nav_manager.map_img == 0).astype(np.uint8) * 255
            border_image = np.zeros((self.nav_manager.height, self.nav_manager.width, 4), dtype=np.uint8)
            border_image[:, :, 2] = border_mask  # Red channel
            border_image[:, :, 3] = border_mask  # Alpha channel
            bytes_per_line = 4 * self.nav_manager.width
            qimg_border = QImage(border_image.tobytes(), self.nav_manager.width, self.nav_manager.height, 
                                bytes_per_line, QImage.Format_ARGB32)
            pixmap_border = QPixmap.fromImage(qimg_border)
            self.scene.addPixmap(pixmap_border)
            
            # Draw new grid and update display
            self.path_visualizer.draw_grid()
            self.path_visualizer.update_display()
            
            # Reset zoom and center view
            self.zoom_level = 1.0
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        except Exception as e:
            print(f"Error setting up scene: {str(e)}")
            self.status_label.setText(f"Error setting up scene: {str(e)}")
    
    def add_waypoint(self, x, y):
        if self.nav_manager.add_waypoint(x, y):
            self.path_visualizer.update_display()
            self.update_status()
        else:
            self.status_label.setText("Cannot place waypoint on border or non-navigable area!")
    
    def remove_nearest_waypoint(self, x, y):
        self.nav_manager.remove_nearest_waypoint(x, y)
        self.path_visualizer.update_display()
        self.update_status()
    
    def clear_waypoints(self):
        self.nav_manager.clear_waypoints()
        self.path_visualizer.update_display()
        self.update_status()
    
    def save_waypoints(self):
        self.nav_manager.save_waypoints()
        self.status_label.setText(f"Saved {len(self.nav_manager.get_waypoints())} waypoints to waypoints.yaml")
    
    def create_coverage_path(self):
        if not self.nav_manager.get_waypoints():
            self.status_label.setText("Please add at least one waypoint as starting point")
            return
        start_point = self.nav_manager.get_waypoints()[0]
        x0, y0 = start_point.x(), start_point.y()
        planner = CoveragePathPlanner(self.nav_manager.map_img)
        coverage_points = planner.generate_path(x0, y0)
        for p in coverage_points:
            self.nav_manager.add_waypoint(p[0], p[1])
        self.path_visualizer.update_display()
        self.update_status()
    
    def update_status(self):
        wp_count = len(self.nav_manager.get_waypoints())
        self.status_label.setText(f"{wp_count} waypoints | "
                                f"Zoom: {self.zoom_level:.1f}x | "
                                "Click to add waypoint, Right-click to remove")
    
    def zoom_in(self):
        self.zoom_level = min(self.zoom_level * self.zoom_factor, self.max_zoom)
        self.apply_zoom()
    
    def zoom_out(self):
        self.zoom_level = max(self.zoom_level / self.zoom_factor, self.min_zoom)
        self.apply_zoom()
    
    def reset_zoom(self):
        self.zoom_level = 1.0
        self.apply_zoom()
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
    
    def apply_zoom(self):
        transform = self.view.transform()
        transform.reset()
        transform.scale(self.zoom_level, self.zoom_level)
        self.view.setTransform(transform)
    
    def update_coordinate_status(self, x, y):
        """Update the status label with current cursor coordinates"""
        wp_count = len(self.nav_manager.get_waypoints())
        # Convert to real-world coordinates
        real_x = x * self.nav_manager.resolution
        real_y = (self.nav_manager.height - y) * self.nav_manager.resolution
        
        self.status_label.setText(
            f"Pixel Coordinates: X: {int(x)}, Y: {int(y)} | "
            f"Real-world: X: {real_x:.2f}m, Y: {real_y:.2f}m | "
            f"{wp_count} waypoints | "
            f"Zoom: {self.zoom_level:.1f}x | "
            "Click to add waypoint, Right-click to remove"
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapNavigator()
    window.show()
    sys.exit(app.exec_())