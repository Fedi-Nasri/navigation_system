#!/usr/bin/env python3
import sys
import numpy as np
import cv2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView, 
                            QGraphicsScene, QGraphicsPixmapItem, QVBoxLayout,
                            QWidget, QPushButton, QLabel, QHBoxLayout)
from PyQt5.QtGui import QPixmap, QImage, QPen, QColor, QWheelEvent, QPainter
from PyQt5.QtCore import Qt, QPointF

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
        if pixel_value < 205:  # Obstacle or unknown
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

class PathVisualizer:
    def __init__(self, scene, navigation_manager):
        self.scene = scene
        self.nav_manager = navigation_manager
        self.grid_items = []
        self.waypoint_items = []
        self.path_items = []
    
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
            circle = self.scene.addEllipse(point.x()-5, point.y()-5, 10, 10, 
                                           QPen(Qt.red), QColor(255, 100, 100))
            self.waypoint_items.append(circle)
            
            text = self.scene.addText(str(i+1))
            text.setPos(point.x()+10, point.y()-10)
            text.setDefaultTextColor(Qt.red)
            self.waypoint_items.append(text)
    
    def draw_path(self):
        for item in self.path_items:
            self.scene.removeItem(item)
        self.path_items.clear()
        
        if len(self.nav_manager.get_waypoints()) < 2:
            return
        
        pen = QPen(QColor(255, 0, 0))
        pen.setWidth(2)
        
        waypoints = self.nav_manager.get_waypoints()
        for i in range(len(waypoints) - 1):
            p1 = waypoints[i]
            p2 = waypoints[i+1]
            line = self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
            self.path_items.append(line)
    
    def update_display(self):
        self.draw_waypoints()
        self.draw_path()

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
        
        control_layout.addWidget(self.zoom_in_btn)
        control_layout.addWidget(self.zoom_out_btn)
        control_layout.addWidget(self.reset_zoom_btn)
        control_layout.addWidget(self.clear_btn)
        control_layout.addWidget(self.save_btn)
        
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
        
        self.path_visualizer.draw_grid()
        self.path_visualizer.update_display()
    
    def add_waypoint(self, x, y):
        if self.nav_manager.add_waypoint(x, y):
            self.path_visualizer.update_display()
            self.update_status()
        else:
            self.status_label.setText("Cannot place waypoint in obstacle/unknown area!")
    
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
    
    def update_status(self):
        self.status_label.setText(f"{len(self.nav_manager.get_waypoints())} waypoints set | "
                                f"Zoom: {self.zoom_level:.1f}x | "
                                "Click to add, Right-click to remove")
    
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