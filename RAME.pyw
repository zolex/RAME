import sys, os, yaml, shutil, tempfile
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QFileDialog, QToolBar,
    QAction,  QSplitter, QDockWidget, QMessageBox
)
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QColor, QBrush
from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF, QSettings, QSize

import utils
from FinishLine import FinishLine
from GraphicsView import GraphicsView
from LayersPanel import LayersPanel

from MapScene import MapScene
from MapTriangle import MapTriangle
from PortalPropertiesPanel import PortalPropertiesPanel
from JumpPadPropertiesPanel import JumpPadPropertiesPanel
from RectPropertiesPanel import RectPropertiesPanel
from StartLine import StartLine
from TexturesPanel import TexturesPanel
from TrianglePropertiesPanel import TrianglePropertiesPanel
from EmptyPropertiesPanel import EmptyPropertiesPanel
from SpawnpointPropertyPanel import SpawnpointPropertyPanel
from ItemPropertyPanel import ItemPropertyPanel
from utils import snap, resolve_texture_path
from MapRect import MapRect
from MapItem import MapItem
from MapPortal import MapPortal
from MapJumpPad import MapJumpPad
from PlayerSpawnpoint import PlayerSpawnpoint

class MapDesigner(QMainWindow):

    SPAWN_OFFSET_X = 32

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Map Designer")
        self.filename = None
        self.settings = QSettings("Racesow", "MapDesigner/App")

        # Create a temporary directory for textures when no project is saved
        self.temp_textures_dir = tempfile.mkdtemp(prefix="mapdesigner_textures_")

        self.scene = MapScene()

        # --- VIEW (grid editor window) ---
        self.view = GraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.RubberBandDrag)

        # --- Textures Panel ---
        self.textures_panel = TexturesPanel()
        self.textures_panel.setSkyRequested.connect(self.set_sky)
        self.textures_panel.setOverlayRequested.connect(self.set_overlay)
        self.textures_panel.textureRemoveRequested.connect(self.remove_texture)
        self.textures_panel.set_textures_folder(self.temp_textures_dir, True)

        # --- MAIN LAYOUT ---
        self.layout = QSplitter(Qt.Horizontal)
        self.layout.addWidget(self.textures_panel)
        self.layout.addWidget(self.view)
        self.layout.setStretchFactor(1, 1)
        self.setCentralWidget(self.layout)

        # --- RIGHT DOCK ---
        self.right_dock_splitter = QSplitter(Qt.Vertical)
        self.layout.addWidget(self.right_dock_splitter)

        # --- RIGHT TOP DOCK ---
        self.right_top_dock = QDockWidget("Selection Properties", self)
        self.right_top_dock.setObjectName("right_dock")
        self.right_top_dock.setFeatures(self.right_top_dock.features() & ~QDockWidget.DockWidgetClosable & ~QDockWidget.DockWidgetFloatable)
        self.right_dock_splitter.addWidget(self.right_top_dock)

        # --- RIGHT BOTTOM DOCK ---
        self.layers_panel = LayersPanel(self.scene)
        self.right_bottom_dock = QDockWidget("Layers", self)
        self.right_bottom_dock.setFeatures(self.right_bottom_dock.features() & ~QDockWidget.DockWidgetClosable & ~QDockWidget.DockWidgetFloatable)
        self.right_bottom_dock.setWidget(self.layers_panel)
        self.right_dock_splitter.addWidget(self.right_bottom_dock)

        # --- Property Panels ---
        self.rect_properties_panel = RectPropertiesPanel()
        self.triangle_properties_panel = TrianglePropertiesPanel()
        self.spawnpoint_properties_panel = SpawnpointPropertyPanel()
        self.empty_properties_panel = EmptyPropertiesPanel()
        self.item_properties_panel = ItemPropertyPanel()
        self.portal_properties_panel = PortalPropertiesPanel()
        self.jump_pad_properties_panel = JumpPadPropertiesPanel()

        self.right_top_dock.setWidget(self.empty_properties_panel)
        self.scene.selectionChanged.connect(self.on_selection_changed)

        self.create_actions()
        self.create_toolbar()
        self.statusBar()
        self._init_ui()

    def properties_panel_for(self, item):
        if isinstance(item, MapRect):
            self.rect_properties_panel.set_rect(item)
            self.right_top_dock.setWindowTitle("Rectangle Properties")
            self.right_top_dock.setWidget(self.rect_properties_panel)
        elif isinstance(item, MapTriangle):
            self.triangle_properties_panel.set_triangle(item)
            self.right_top_dock.setWindowTitle("Triangle Properties")
            self.right_top_dock.setWidget(self.triangle_properties_panel)
        elif isinstance(item, PlayerSpawnpoint):
            self.spawnpoint_properties_panel.set_spawnpoint(item)
            self.right_top_dock.setWindowTitle("Player Spawnpoint Properties")
            self.right_top_dock.setWidget(self.spawnpoint_properties_panel)
        elif isinstance(item, MapItem):
            self.item_properties_panel.set_item(item)
            self.right_top_dock.setWindowTitle("Item Properties")
            self.right_top_dock.setWidget(self.item_properties_panel)
        elif isinstance(item, MapPortal):
            self.portal_properties_panel.set_portal(item)
            self.right_top_dock.setWindowTitle("Portal Properties")
            self.right_top_dock.setWidget(self.portal_properties_panel)
        elif isinstance(item, MapJumpPad):
            self.jump_pad_properties_panel.set_jump_pad(item)
            self.right_top_dock.setWindowTitle("Jump Pad Properties")
            self.right_top_dock.setWidget(self.jump_pad_properties_panel)
        else:
            self.right_top_dock.setWindowTitle("Selection Properties")
            self.right_top_dock.setWidget(self.empty_properties_panel)

    def _init_ui(self):
        # Restore window size from settings or use default
        size = self.settings.value("window/size", QSize(1200, 900))
        self.resize(size)
        
    def closeEvent(self, event):
        # Save window size
        self.settings.setValue("window/size", self.size())

        # Sync settings to ensure they're written to disk
        self.settings.sync()
        
        # Clean up temporary textures directory
        if hasattr(self, 'temp_textures_dir') and os.path.exists(self.temp_textures_dir):
            try:
                shutil.rmtree(self.temp_textures_dir)
            except Exception as e:
                print(f"Error removing temporary directory: {e}")
        
        # Accept the close event
        event.accept()
        
    def _migrate_textures_from_temp(self, project_textures_dir):
        """
        Migrate textures from temporary folder to project folder
        
        Args:
            project_textures_dir: Path to the textures directory in the project folder
        """
        if not hasattr(self, 'temp_textures_dir') or not os.path.exists(self.temp_textures_dir):
            return
            
        print(f"Migrating textures from {self.temp_textures_dir} to {project_textures_dir}")
            
        # Ensure project textures directory exists
        os.makedirs(project_textures_dir, exist_ok=True)
        
        # Get list of texture files in temporary directory
        temp_files = []
        if os.path.exists(self.temp_textures_dir):
            temp_files = [f for f in os.listdir(self.temp_textures_dir) 
                         if os.path.isfile(os.path.join(self.temp_textures_dir, f)) and 
                         f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))]
        
        # Copy files from temporary directory to project directory
        texture_map = {}  # Maps old paths to new paths
        for filename in temp_files:
            src_path = os.path.join(self.temp_textures_dir, filename)
            dst_path = os.path.join(project_textures_dir, filename)
            
            # Handle filename conflicts by adding a suffix if needed
            if os.path.exists(dst_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dst_path):
                    new_filename = f"{base}_{counter}{ext}"
                    dst_path = os.path.join(project_textures_dir, new_filename)
                    counter += 1
            
            # Copy the file
            shutil.copy2(src_path, dst_path)
            texture_map[src_path] = dst_path
            
        # Update texture paths in scene items
        for item in self.scene.items():
            texture_path = getattr(item, "texture_path", None)
            if texture_path and texture_path in texture_map:
                item.texture_path = texture_map[texture_path]
                
        # Update sky if it's from the temporary folder
        if hasattr(self.view, '_background_image_path') and self.view._has_sky:
            sky_path = self.view._sky_image_path
            if sky_path in texture_map:
                self.view._sky_image_path = texture_map[sky_path]

    def _show_panel(self, panel):
        panel.show()

    def create_rectangle_icon(self, size=32):
        """Create a custom icon showing a rectangle shape"""
        # Create a pixmap with transparent background
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        # Create a painter to draw on the pixmap
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw a rectangle with a border
        painter.setPen(QColor(0, 0, 0))  # Black border
        painter.setBrush(QBrush(QColor(200, 200, 255, 180)))  # Light blue fill with transparency
        
        # Draw rectangle with some padding from the edges
        padding = 4
        painter.drawRect(padding, padding, size - 2*padding, size - 2*padding)
        
        # End painting
        painter.end()
        
        # Create and return an icon from the pixmap
        return QIcon(pixmap)

    def create_toolbar(self):
        toolbar = QToolBar("Tools", self)
        self.addToolBar(toolbar)

        # Add rectangle button with custom rectangle icon
        rect_action = QAction(QIcon.fromTheme("draw-rectangle", QIcon.fromTheme("insert-object")), "New Rectangle", self)
        rect_action.setToolTip("Add a new rectangle")
        rect_action.triggered.connect(self.add_rectangle)
        toolbar.addAction(rect_action)

        # Add triangle button with icon
        tri_action = QAction(QIcon.fromTheme("draw-triangle", QIcon.fromTheme("insert-object")), "New Triangle", self)
        tri_action.setToolTip("Add a new triangle")
        tri_action.triggered.connect(self.add_triangle)
        toolbar.addAction(tri_action)
        
        # Add player spawnpoint button with icon
        player_icon = QIcon("assets/player.png")
        player_action = QAction(player_icon, "Player Spawnpoint", self)
        player_action.setToolTip("Add a Player Spawnpoint (only one allowed)")
        player_action.triggered.connect(self.add_player_spawnpoint)
        toolbar.addAction(player_action)

        # Add start line button with icon
        player_icon = QIcon("assets/start.png")
        player_action = QAction(player_icon, "Start Line", self)
        player_action.setToolTip("Add a Start Line (only one allowed)")
        player_action.triggered.connect(self.add_start_line)
        toolbar.addAction(player_action)

        # Add finish line button with icon
        player_icon = QIcon("assets/finish.png")
        player_action = QAction(player_icon, "Finish Line", self)
        player_action.setToolTip("Add a Finish Line (only one allowed)")
        player_action.triggered.connect(self.add_finish_line)
        toolbar.addAction(player_action)

        # Add item button with icon
        item_icon = QIcon("assets/plasma.png")  # Default to plasma icon
        item_action = QAction(item_icon, "Add Item", self)
        item_action.setToolTip("Add a new item (plasma or rocket)")
        item_action.triggered.connect(self.add_item)
        toolbar.addAction(item_action)

        # Add portal button with icon
        portal_icon = QIcon("assets/portal_entry.png")
        portal_action = QAction(portal_icon, "Portal", self)
        portal_action.setToolTip("Add a Portal")
        portal_action.triggered.connect(self.add_portal)
        toolbar.addAction(portal_action)

        # Add jump pad button with icon
        jump_pad_icon = QIcon("assets/jumppad.png")
        jump_pad_action = QAction(jump_pad_icon, "Jump Pad", self)
        jump_pad_action.setToolTip("Add a Jump Pad")
        jump_pad_action.triggered.connect(self.add_jump_pad)
        toolbar.addAction(jump_pad_action)
        
        # Add separator before zoom controls
        toolbar.addSeparator()
        
        # Add zoom in button with icon
        zoom_in_action = QAction(QIcon.fromTheme("zoom-in"), "Zoom In", self)
        zoom_in_action.setToolTip("Zoom in")
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)
        
        # Add zoom out button with icon
        zoom_out_action = QAction(QIcon.fromTheme("zoom-out"), "Zoom Out", self)
        zoom_out_action.setToolTip("Zoom out")
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)
        
        # Add reset zoom button with icon
        reset_zoom_action = QAction(QIcon.fromTheme("zoom-original", QIcon.fromTheme("zoom-fit-best")), "Reset Zoom", self)
        reset_zoom_action.setToolTip("Reset zoom to default")
        reset_zoom_action.triggered.connect(self.reset_zoom)
        toolbar.addAction(reset_zoom_action)
        
        # Add separator before sky controls
        toolbar.addSeparator()
        
        # Add remove sky button with icon
        remove_sky_action = QAction(QIcon.fromTheme("edit-clear", QIcon.fromTheme("edit-delete")), "Remove Sky", self)
        remove_sky_action.setToolTip("Remove the current sky image")
        remove_sky_action.triggered.connect(self.remove_sky)
        toolbar.addAction(remove_sky_action)

    def add_rectangle(self):
        # Get the center of the visible area
        center = self.get_view_center()
        # Calculate top-left point by offsetting from center
        top_left = QPointF(center.x() - 64, center.y() - 32)  # Half of width (128) and height (64)
        rect = MapRect(QRectF(top_left, QSizeF(128, 64)))
        self.scene.addItem(rect)
        self.properties_panel_for(rect)

    def add_triangle(self):
        # Get the center of the visible area
        center = self.get_view_center()
        # Create triangle centered at the visible area center
        triangle = MapTriangle.default_right_angle(size=64, origin=QPointF(center.x() - 32, center.y() - 32))
        self.scene.addItem(triangle)
        self.properties_panel_for(triangle)

    def add_player_spawnpoint(self):
        # Check if there's already a spawnpoint in the scene
        for item in self.scene.items():
            if isinstance(item, PlayerSpawnpoint):
                # Remove the existing spawnpoint
                self.scene.removeItem(item)
                break

        # Get the center of the visible area
        center = self.get_view_center()
        # Create a new spawnpoint at the center
        spawnpoint = PlayerSpawnpoint(center)
        self.scene.addItem(spawnpoint)
        self.statusBar().showMessage("Player spawnpoint added", 3000)
        self.properties_panel_for(spawnpoint)

    def add_start_line(self):
        # Check if there's already a spawnpoint in the scene
        for item in self.scene.items():
            if isinstance(item, StartLine):
                # Remove the existing spawnpoint
                self.scene.removeItem(item)
                break

        # Get the center of the visible area
        center = self.get_view_center()
        # Create a new spawnpoint at the center
        start_line = StartLine(center)
        self.scene.addItem(start_line)
        self.properties_panel_for(start_line)

    def add_finish_line(self):
        # Check if there's already a spawnpoint in the scene
        for item in self.scene.items():
            if isinstance(item, FinishLine):
                # Remove the existing spawnpoint
                self.scene.removeItem(item)
                break

        # Get the center of the visible area
        center = self.get_view_center()
        # Create a new spawnpoint at the center
        finish_line = FinishLine(center)
        self.scene.addItem(finish_line)
        self.properties_panel_for(finish_line)

    def add_portal(self):
        # Get the center of the visible area
        center = self.get_view_center()
        # Create a new portal at the center
        portal = MapPortal(center)
        self.scene.addItem(portal)
        self.statusBar().showMessage("Portal added", 3000)
        self.properties_panel_for(portal)

    def add_jump_pad(self):
        # Get the center of the visible area
        center = self.get_view_center()
        # Create a new portal at the center
        jump_pad = MapJumpPad(center)
        self.scene.addItem(jump_pad)
        self.statusBar().showMessage("Jump Pad added", 3000)
        self.properties_panel_for(jump_pad)
        
    def add_item(self):
        try:
            # Get the center of the visible area
            center = self.get_view_center()
            # Calculate top-left point by offsetting from center
            top_left = QPointF(center.x(), center.y())  # Half of width (64) and height (64)
            # Create a new MapItem at the center
            item = MapItem(QRectF(top_left, QSizeF(32, 32)))
            self.scene.addItem(item)
            self.statusBar().showMessage("Item added", 3000)
            self.properties_panel_for(item)
            return item
        except Exception as e:
            self.statusBar().showMessage(f"Error adding item: {str(e)}", 3000)
            return None
        
    def zoom_in(self):
        """Zoom in the view by a factor of 1.15"""
        self.view.scale(1.15, 1.15)
        # Force viewport update to keep sky fixed
        self.view.viewport().update()
        
    def zoom_out(self):
        """Zoom out the view by a factor of 1/1.15"""
        self.view.scale(1/1.15, 1/1.15)
        # Force viewport update to keep sky fixed
        self.view.viewport().update()
        
    def reset_zoom(self):
        """Reset the view to the default zoom level"""
        # Reset the transformation matrix to identity
        self.view.resetTransform()
        # Force viewport update to keep sky fixed
        self.view.viewport().update()
        
    def get_view_center(self):
        """Get the center point of the current visible area in scene coordinates"""
        # Get the visible rectangle in viewport coordinates
        visible_rect = self.view.viewport().rect()
        # Convert the center point to scene coordinates
        center_point = self.view.mapToScene(visible_rect.center())
        # Snap to grid
        return snap(center_point)

    def set_sky(self, texture_path):
        """Set the selected texture as a fixed sky behind the grid"""
        if texture_path and os.path.exists(texture_path):
            self.view.set_sky_image(texture_path)
            self.statusBar().showMessage(f"Sky set to: {os.path.basename(texture_path)}", 3000)

    def set_overlay(self, texture_path):
        """Set the selected texture as a fixed sky behind the grid"""
        if texture_path and os.path.exists(texture_path):
            self.view.set_overlay_image(texture_path)
            self.statusBar().showMessage(f"Overlay set to: {os.path.basename(texture_path)}", 3000)
            
    def remove_sky(self):
        """Remove the current sky image"""
        self.view.set_sky_image(None)
        self.statusBar().showMessage("Sky removed", 3000)

    def remove_overlay(self):
        """Remove the current overlay image"""
        self.view.set_overlay_image(None)
        self.statusBar().showMessage("Overlay removed", 3000)
        
    def remove_texture(self, texture_path):
        """Remove a texture from the project and update all items that use it"""
        # Check if the texture is in use as a sky
        sky_in_use = False
        overlay_in_use = False
        if self.view._has_sky:
            if self.view._sky_image_path == texture_path:
                sky_in_use = True

        if self.view._has_overlay:
            if self.view._overlay_image_path == texture_path:
                overlay_in_use = True

        # Check if the texture is in use by any map items
        items_using_texture = []
        for item in self.scene.items():
            if hasattr(item, "texture_path") and item.texture_path is not None:
                abs_path = os.path.join(os.path.dirname(self.filename), item.texture_path)
                if abs_path == texture_path:
                    items_using_texture.append(item)

        print(len(items_using_texture))

        # If texture is in use, show confirmation dialog
        if sky_in_use or overlay_in_use or items_using_texture:
            message = "This texture is currently in use by "
            usedBy = []
            if sky_in_use:
                usedBy.append("the sky")
            if overlay_in_use:
                usedBy.append("the overlay")
            if items_using_texture:
                usedBy.append(f"{len(items_using_texture)} map item(s)")

            message += " and ".join(usedBy) + "."

            message += ".\nAre you sure you want to remove it?"
            
            reply = QMessageBox.question(
                self, 
                "Confirm Texture Removal", 
                message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
                
        # Delete the texture file
        try:
            if os.path.exists(texture_path):
                os.remove(texture_path)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error Removing Texture",
                f"Could not delete the texture file: {str(e)}"
            )
            return
            
        # Remove texture from sky if it's in use
        if sky_in_use:
            self.remove_sky()

        # Remove texture from overlay if it's in use
        if overlay_in_use:
            self.remove_overlay()
            
        # Remove texture from all items that use it
        for item in items_using_texture:
            item.texture_path = None
            item.texture_pixmap = None
            item.update()
            
        # Reload textures panel to reflect the changes
        self.textures_panel.load_textures_folder()
        
        self.statusBar().showMessage(f"Texture removed: {os.path.basename(texture_path)}", 3000)

    def create_actions(self):
        self.menuBar().clear()
        if self.filename is not None:
            save_act = QAction("Save", self, triggered=self.save)
            self.menuBar().addAction(save_act)
            save_as_act = QAction("Save As", self, triggered=self.save_as)
            self.menuBar().addAction(save_as_act)
        else:
            save_act = QAction("Save", self, triggered=self.save_as)
            self.menuBar().addAction(save_act)

        load_act = QAction("Load", self, triggered=self.load)
        self.menuBar().addAction(load_act)

    def on_selection_changed(self):
        items = self.scene.selectedItems()
        if items:
            self.properties_panel_for(items[0])
        else:
            self.properties_panel_for(None)

    def save_textures(scene, filename):
        base_dir = os.path.dirname(filename)
        textures_dir = os.path.join(base_dir, "textures")
        os.makedirs(textures_dir, exist_ok=True)

        texture_map = {}  # original_path -> new_relative_path

        for item in scene.items():
            # Adjust this for your actual item types that use textures
            if hasattr(item, "texture_path") and item.texture_path:
                src_path = item.texture_path
                if os.path.exists(src_path):
                    texture_name = os.path.basename(src_path)
                    dst_path = os.path.join(textures_dir, texture_name)
                    # Avoid duplicate copy
                    if not os.path.exists(dst_path):
                        shutil.copy(src_path, dst_path)
                    # Store the new relative path for YAML
                    texture_map[src_path] = os.path.relpath(dst_path, base_dir)

        # When building YAML data, for each texture path, use texture_map to substitute paths
        yaml_data = []
        for item in scene.items():
            # Collect and update texture references for YAML export
            entry = ...  # your export logic for item
            if hasattr(item, "texture_path") and item.texture_path:
                entry["texture"] = texture_map.get(item.texture_path, "")
            yaml_data.append(entry)

        with open(filename, "w") as f:
            yaml.dump(yaml_data, f)

    def save_as(self):
        last_folder = self.settings.value("map/last_folder", "")
        self.filename, _ = QFileDialog.getSaveFileName(self, "Save Map", last_folder, "YAML Files (*.yaml)")
        self.save()

    def show_error(self, title: str, message: str):
        QMessageBox.critical(
            self,
            title,
            message,
            QMessageBox.StandardButton.Ok
        )

    def save(self):
        if self.filename:
            self.setWindowTitle(f"Map Designer: {self.filename}")
            base_dir = os.path.dirname(self.filename)
            self.settings.setValue("map/last_folder", base_dir)
            textures_dir = os.path.join(base_dir, "textures")
            os.makedirs(textures_dir, exist_ok=True)
            
            # Migrate textures from temporary folder to project folder
            self._migrate_textures_from_temp(textures_dir)
            
            # Update textures panel with the new textures folder
            self.textures_panel.set_textures_folder(textures_dir, True)
            
            texture_map = {}  # original_path -> relative path in textures/
            
            # Get sky image path if it exists
            sky_path = None
            if self.view._has_sky:
                sky_path = self.view._sky_image_path

            # Step 1: Collect textures and copy them if needed

            # Add sky to texture_map if it exists
            if sky_path and os.path.exists(sky_path):
                sky_basename = os.path.basename(sky_path)
                sky_dst = os.path.join(textures_dir, sky_basename)
                if not os.path.exists(sky_dst):
                    shutil.copy(sky_path, sky_dst)
                texture_map[sky_path] = os.path.relpath(sky_dst, base_dir)

            # Get overlay image path if it exists
            overlay_path = None
            if self.view._has_overlay:
                overlay_path = self.view._overlay_image_path

            # Add overlay to texture_map if it exists
            if overlay_path and os.path.exists(overlay_path):
                overlay_basename = os.path.basename(overlay_path)
                overlay_dst = os.path.join(textures_dir, overlay_basename)
                if not os.path.exists(overlay_dst):
                    shutil.copy(overlay_path, overlay_dst)
                texture_map[overlay_path] = os.path.relpath(overlay_dst, base_dir)
                
            for item in self.scene.items():
                texture_path = getattr(item, "texture_path", None)
                if texture_path:
                    texture_basename = os.path.basename(texture_path)
                    texture_dst = os.path.join(textures_dir, texture_basename)
                    if not os.path.exists(texture_dst) and os.path.exists(texture_path):
                        shutil.copy(texture_path, texture_dst)
                    texture_map[texture_path] = os.path.relpath(texture_dst, base_dir)

            # Step 2: Save items with relative texture paths
            data = {}
            rectangles = []
            triangles = []
            items = []
            portals = []
            jump_pads = []

            for item in self.scene.items():
                if isinstance(item, PlayerSpawnpoint):
                    # Save player spawnpoint position at the root level
                    data["player_spawnpoint"] = {
                        "x": item.pos().x() + MapDesigner.SPAWN_OFFSET_X,
                        "y": item.pos().y()
                    }
                elif isinstance(item, StartLine):
                    data["start_line"] = {
                        "x": item.pos().x(),
                        "y": item.pos().y()
                    }
                elif isinstance(item, FinishLine):
                    data["finish_line"] = {
                        "x": item.pos().x(),
                        "y": item.pos().y()
                    }
                elif isinstance(item, MapRect):
                    texture = getattr(item, "texture_path", None)
                    d = {
                        "x": item.pos().x() + item.rect().x(),
                        "y": item.pos().y() + item.rect().y(),
                        "w": item.rect().width(),
                        "h": item.rect().height(),
                        "wall_type": getattr(item, "stype", "static"),
                        "texture": texture_map.get(texture, None) if texture else None,
                        "texture_scale": getattr(item, "texture_scale", 1.0),
                        "texture_rotation": getattr(item, "texture_rotation", 0.0),
                        "texture_offset_x": getattr(item, "texture_offset_x", 0.0),
                        "texture_offset_y": getattr(item, "texture_offset_y", 0.0),
                        "z_index": item.zValue(),
                    }
                    rectangles.append(d)
                elif isinstance(item, MapTriangle):
                    texture = getattr(item, "texture_path", None)
                    item_pos = item.pos()
                    d = {
                         "points": [{'x': (p + item_pos).x(), 'y': (p + item_pos).y()} for p in item.polygon()],
                        "wall_type": getattr(item, "stype", "ramp"),
                        "texture": texture_map.get(texture, None) if texture else None,
                        "texture_scale": getattr(item, "texture_scale", 1.0),
                        "texture_rotation": getattr(item, "texture_rotation", 0.0),
                        "texture_offset_x": getattr(item, "texture_offset_x", 0.0),
                        "texture_offset_y": getattr(item, "texture_offset_y", 0.0),
                        "z_index": item.zValue(),
                    }
                    triangles.append(d)
                elif isinstance(item, MapItem):
                    d = {
                        "x": item.pos().x() + item.rect().x(),
                        "y": item.pos().y() + item.rect().y(),
                        "type": getattr(item, "item_type", "plasma"),
                        "ammo": getattr(item, "ammo", 10),
                        "stay": getattr(item, "stay", False),
                    }
                    items.append(d)
                elif isinstance(item, MapJumpPad):
                    d = {
                        "x": item.pos().x() + item.rect().x(),
                        "y": item.pos().y() + item.rect().y(),
                        "vel": getattr(item, 'velocity', 0.3),
                        "rotation": item.rotation(),
                    }
                    jump_pads.append(d)
                elif isinstance(item, MapPortal) and item.item_type == "entry":

                    exit = None
                    num = 0
                    for portal in self.scene.items():
                        if isinstance(portal, MapPortal) and portal.item_type == "exit" and item.ID == portal.ID:
                            num += 1
                            exit = portal

                    if exit is None:
                        self.show_error("Missing Portal", f"The Portal Entry with ID {item.ID} has no Portal Exit.")
                        return

                    if num > 1:
                        self.show_error("Wrong Portal", f"The Portal Entry with ID {item.ID} has more than one Exit.")
                        return

                    d = {
                        "entry_x": item.pos().x() + item.rect().x(),
                        "entry_y": item.pos().y() + item.rect().y(),
                        "entry_flipped": item.flipped,
                        "exit_x": exit.pos().x() + exit.rect().x(),
                        "exit_y": exit.pos().y() + exit.rect().y(),
                        "exit_flipped": exit.flipped,
                    }
                    portals.append(d)

                elif isinstance(item, MapPortal) and item.item_type == "exit":
                    entry = None
                    num = 0
                    for portal in self.scene.items():
                        if isinstance(portal, MapPortal) and portal.item_type == "entry" and item.ID == portal.ID:
                            num += 1
                            entry = portal

                    if entry is None:
                        self.show_error("Missing Portal", f"The Portal Exit with ID {item.ID} has no Portal Entry.")
                        return

                    if num > 1:
                        self.show_error("Wrong Portal", f"The Portal Exit with ID {item.ID} has more than one Entry.")
                        return
            
            # Sort rectangles and triangles by z-index in ascending order
            rectangles.sort(key=lambda x: x["z_index"])
            triangles.sort(key=lambda x: x["z_index"])
            
            # Add rectangles, triangles, and items to data if they exist
            if rectangles:
                data["rectangles"] = rectangles
            if triangles:
                data["triangles"] = triangles
            if items:
                data["items"] = items
            if portals:
                data["portals"] = portals
            if jump_pads:
                data["jump_pads"] = jump_pads

            # Add sky to data if it exists
            if sky_path and sky_path in texture_map:
                data["sky"] = texture_map[sky_path]

            # Add sky to data if it exists
            if overlay_path and overlay_path in texture_map:
                data["parallax_1"] = texture_map[overlay_path]

            with open(self.filename, "w") as f:
                yaml.dump(data, f)

    def load(self):
        last_folder = self.settings.value("map/last_folder", "")
        self.filename, _ = QFileDialog.getOpenFileName(self, "Load Map", last_folder, "YAML Files (*.yaml)")
        self.setWindowTitle(f"Map Designer: {self.filename}")
        if self.filename:
            folder = os.path.dirname(self.filename)
            self.settings.setValue("map/last_folder", folder)
            self.scene.clear()
            with open(self.filename) as f:
                data = yaml.safe_load(f)
                
                # Handle sky entry
                if "sky" in data:
                    sky_path = resolve_texture_path(data["sky"], self.filename)
                    if os.path.exists(sky_path):
                        self.set_sky(sky_path)

                # Handle overlay entry
                if "parallax_1" in data:
                    overlay_path = resolve_texture_path(data["parallax_1"], self.filename)
                    if os.path.exists(overlay_path):
                        self.set_overlay(overlay_path)

                # Handle player spawnpoint
                if "player_spawnpoint" in data:
                    spawnpoint_data = data["player_spawnpoint"]
                    position = QPointF(spawnpoint_data["x"] - MapDesigner.SPAWN_OFFSET_X, spawnpoint_data["y"])
                    spawnpoint = PlayerSpawnpoint(position)
                    self.scene.addItem(spawnpoint)

                # Handle start line
                if "start_line" in data:
                    start_line_data = data["start_line"]
                    position = QPointF(start_line_data["x"], start_line_data["y"])
                    start_line = StartLine(position)
                    self.scene.addItem(start_line)

                # Handle finish line
                if "finish_line" in data:
                    finish_line_data = data["finish_line"]
                    position = QPointF(finish_line_data["x"], finish_line_data["y"])
                    finish_line = FinishLine(position)
                    self.scene.addItem(finish_line)

                # Handle rectangles
                if "rectangles" in data:
                    for it in data["rectangles"]:
                        rect = MapRect(QRectF(it["x"], it["y"], it["w"], it["h"]))
                        # Load position separately
                        rect.setPos(it.get("pos_x", 0.0), it.get("pos_y", 0.0))
                        rect.stype = it.get("wall_type", "static")
                        rect.texture_scale = it.get("texture_scale", 1.0)
                        rect.texture_rotation = it.get("texture_rotation", 0.0)
                        rect.texture_offset_x = it.get("texture_offset_x", 0.0)
                        rect.texture_offset_y = it.get("texture_offset_y", 0.0)
                        # Set z-index if available
                        if "z_index" in it:
                            rect.setZValue(it["z_index"])
                        tex = it.get("texture")
                        if tex:
                            rect.texture_path = tex
                            rect.texture_pixmap = QPixmap(resolve_texture_path(tex, self.filename))
                        self.scene.addItem(rect)
                
                # Handle triangles
                if "triangles" in data:
                    for it in data["triangles"]:
                        pts = [QPointF(xy["x"], xy["y"]) for xy in it["points"]]
                        if len(pts) == 3:
                            triangle = MapTriangle(*pts)
                            triangle.stype = it.get("wall_type", False)
                            triangle.texture_scale = it.get("texture_scale", 1.0)
                            triangle.texture_rotation = it.get("texture_rotation", 0.0)
                            triangle.texture_offset_x = it.get("texture_offset_x", 0.0)
                            triangle.texture_offset_y = it.get("texture_offset_y", 0.0)
                            # Set z-index if available
                            if "z_index" in it:
                                triangle.setZValue(it["z_index"])
                            tex = it.get("texture")
                            if tex:
                                triangle.texture_path = tex
                                triangle.texture_pixmap = QPixmap(resolve_texture_path(tex, self.filename))
                            self.scene.addItem(triangle)

                # Handle items
                if "items" in data:
                    for it in data["items"]:
                        #try:
                        # Create item with proper error checking
                        if "x" not in it or "y" not in it:
                            self.statusBar().showMessage(f"Warning: Skipping item with missing position/size data",3000)
                            continue

                        # Create item at origin first, then we'll set position
                        item = MapItem()
                        item.stay = it.get("stay", False)

                        # Set position separately to match how rectangles are handled
                        item.setPos(it["x"], it["y"])

                        # Set item properties with defaults if missing
                        item.item_type = it.get("type", "plasma")
                        if item.item_type not in ["plasma", "rocket"]:
                            self.statusBar().showMessage(f"Warning: Unknown item type '{item.item_type}', defaulting to 'plasma'", 3000)
                            item.item_type = "plasma"

                        item.ammo = int(it.get("ammo", 10))

                        self.scene.addItem(item)
                        #except Exception as e:
                        #    self.statusBar().showMessage(f"Error loading item: {str(e)}", 3000)

                # Handle portals
                if "portals" in data:
                    for index, pt in enumerate(data["portals"]):
                        try:
                            # Create item with proper error checking
                            if "entry_x" not in pt or "entry_y" not in pt or "exit_x" not in pt or "exit_y" not in pt:
                                self.statusBar().showMessage(f"Warning: Skipping item with missing portal data",3000)
                                continue

                            # Create entry portal
                            entry_portal = MapPortal(QPointF(pt["entry_x"], pt["entry_y"]), "entry", pt.get("entry_flipped", False))
                            entry_portal.ID = index
                            self.scene.addItem(entry_portal)

                            exit_portal  = MapPortal(QPointF(pt["exit_x"], pt["exit_y"]), "exit", pt.get("exit_flipped", False))
                            exit_portal.ID = index
                            self.scene.addItem(exit_portal)
                        except Exception as e:
                            self.statusBar().showMessage(f"Error loading Portal: {str(e)}", 3000)

                # Handle Jump Pads
                if "jump_pads" in data:
                    for jp in data["jump_pads"]:
                        try:
                            if "x" not in jp or "y" not in jp:
                                self.statusBar().showMessage(
                                    f"Warning: Skipping Jump Pad with missing position", 3000)
                                continue

                            pos = QPointF(jp["x"], jp["y"])

                            # New format: single velocity and rotation
                            if "vel" in jp:
                                item = MapJumpPad(pos, jp.get("vel", 0.3))
                                if "rotation" in jp:
                                    try:
                                        item.setRotation(float(jp["rotation"]))
                                    except Exception:
                                        pass
                            # Legacy format: vel_x, vel_y → compute magnitude and rotation
                            elif "vel_x" in jp and "vel_y" in jp:
                                vx = float(jp.get("vel_x", 0.0))
                                vy = float(jp.get("vel_y", 0.0))
                                # Compute speed magnitude
                                speed = (vx ** 2 + vy ** 2) ** 0.5
                                item = MapJumpPad(pos, speed)
                                # Compute rotation in degrees from vector, atan2 returns radians
                                import math
                                angle_rad = math.atan2(vy, vx)
                                angle_deg = math.degrees(angle_rad)
                                item.setRotation(angle_deg)
                            else:
                                self.statusBar().showMessage(
                                    f"Warning: Skipping Jump Pad with missing velocity", 3000)
                                continue

                            self.scene.addItem(item)
                        except Exception as e:
                            self.statusBar().showMessage(f"Error loading Jump Pad: {str(e)}", 3000)

            # Set the textures folder to be next to the YAML file
            textures_path = os.path.join(os.path.dirname(self.filename), 'textures')
            self.textures_panel.set_textures_folder(textures_path, True)

            self.create_actions()


# Only include QApplication/main loop if running as main script
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapDesigner()
    window.show()
    sys.exit(app.exec_())

