#!/usr/bin/env python3
import sys
import numpy as np
import cv2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView, 
                            QGraphicsScene, QGraphicsPixmapItem, QVBoxLayout,
                            QWidget, QPushButton, QLabel, QHBoxLayout)
from PyQt5.QtGui import QPixmap, QImage, QPen, QColor, QWheelEvent, QPainter
from PyQt5.QtCore import Qt, QPointF
import math

class NavigationManager:
    def __init__(self, map_path, grid_size=0.5, resolution=0.05):
        self.map_img = cv2.imread(map_path, cv2.IMREAD_GRAYSCALE)
        if self.map_img is None:
            raise FileNotFoundError(f"Could not load map file: {map_path}")
        self.height, self.width = self.map_img.shape
        self.grid_size = grid_size
        self.resolution = resolution
        self.waypoints = []
    
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

class MapNavigator(QMainWindow):
    def __init__(self, map_path="map.pgm"):
        super().__init__()
        self.setWindowTitle("Boat Navigation Waypoint Planner (with Zoom)")
        self.setGeometry(100, 100, 1000, 800)
        
        self.nav_manager = NavigationManager(map_path, grid_size=0.5, resolution=0.05)
        
        self.zoom_level = 1.0
        self.zoom_factor = 1.25
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        
        self.init_ui()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        control_layout = QHBoxLayout()
        
        self.scene = QGraphicsScene()
        self.view = CustomGraphicsView(self.scene)
        self.view.setMouseTracking(True)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        
        self.path_visualizer = PathVisualizer(self.scene, self.nav_manager)
        
        self.setup_scene()
        
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
        
        control_layout.addWidget(self.zoom_in_btn)
        control_layout.addWidget(self.zoom_out_btn)
        control_layout.addWidget(self.reset_zoom_btn)
        control_layout.addWidget(self.clear_btn)
        control_layout.addWidget(self.save_btn)
        control_layout.addWidget(self.create_path_btn)
        
        self.status_label = QLabel("Click on the map to add waypoints | "
                                 "Mouse wheel to zoom | Right-click drag to pan")
        
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.view)
        main_layout.addWidget(self.status_label)
        
        self.view.centerOn(self.scene.sceneRect().center())
    
    def setup_scene(self):
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
        
        self.path_visualizer.draw_grid()
        self.path_visualizer.update_display()
    
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

class CustomGraphicsView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setMouseTracking(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
    
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    map_path = sys.argv[1] if len(sys.argv) > 1 else "map.pgm"
    window = MapNavigator(map_path)
    window.show()
    sys.exit(app.exec_())