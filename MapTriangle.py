from PyQt5.QtWidgets import QMenu, QGraphicsItem, QStyle
from PyQt5.QtGui import QPolygonF, QTransform, QColor, QPixmap, QBrush, QPainterPath
from PyQt5.QtCore import Qt, QPointF, QObject, pyqtSignal, QRectF, QTimer
from PyQt5.QtWidgets import QGraphicsPolygonItem
import math
from config import GRID_SIZE

class MapTriangleSignals(QObject):
    triChanged = pyqtSignal(object)

class MapTriangle(QGraphicsPolygonItem):
    POINT_RADIUS = 8  # radius for point hitbox in pixels

    def __init__(self, p1=None, p2=None, p3=None, parent=None):
        if p1 is None or p2 is None or p3 is None:
            size = 64  # default size of triangle
            p1 = QPointF(size, size)   # bottom right (right angle)
            p2 = QPointF(0, size)      # bottom left
            p3 = QPointF(size, 0)      # top right
        super().__init__(QPolygonF([p1, p2, p3]))
        self.signals = MapTriangleSignals(parent)
        self.setFlags(self.ItemIsSelectable | self.ItemIsMovable | self.ItemSendsGeometryChanges)
        self.stype = "ramp"

        self.texture_path = None
        self.texture_pixmap = None
        self.texture_scale = 1.0
        self.texture_offset_x = 0
        self.texture_offset_y = 0
        self.texture_rotation = 0.0
        self._is_dragging_texture = False
        self._drag_start_pos = None
        self._start_offset_x = 0
        self._start_offset_y = 0
        self._show_texture_offset_overlay = False
        self._show_scale_overlay = False
        self._show_rotation_overlay = False
        self._is_rotating = False
        self._start_angle = None
        self._rotation_start_pos = None
        self._rotation_center = None

        # Duplication-related variables
        self._is_duplicating = False
        self._ghost_item = None

        self._overlay_timer = QTimer()
        self._overlay_timer.setSingleShot(True)
        self._overlay_timer.timeout.connect(self._hide_overlays)


        self.setBrush(QColor("#E20074"))
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        self.dragging_point = None  # which point index, if any, is being dragged

    def _hide_overlays(self):
        self._show_scale_overlay = False
        self._show_texture_offset_overlay = False
        self._show_rotation_overlay = False
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # Snap the new top-left position to the grid
            snapped_pos = QPointF(
                round(value.x() / GRID_SIZE) * GRID_SIZE,
                round(value.y() / GRID_SIZE) * GRID_SIZE
            )
            return snapped_pos

        if change == QGraphicsItem.ItemPositionHasChanged:
            self.signals.triChanged.emit(self)

        return super().itemChange(change, value)

    def snap(self, value):
        return round(value / GRID_SIZE) * GRID_SIZE

    def dropEvent(self, event):
        self.scene().clearSelection()
        self.setSelected(True)
        if event.mimeData().hasUrls():
            image_path = event.mimeData().urls()[0].toLocalFile()
        elif event.mimeData().hasText():
            image_path = event.mimeData().text()
        else:
            event.ignore()
            return

        self.texture_path = image_path
        self.texture_rotation = 0.0
        self.texture_scale = 1.0
        self.texture_offset_x = 0.0
        self.texture_offset_y = 0.0
        self.texture_pixmap = QPixmap(image_path)
        self.update()  # This triggers paint
        self.signals.triChanged.emit(self)
        event.accept()

    def hoverMoveEvent(self, event):
        idx = self._point_at(event.pos())
        if idx is not None:
            self.setCursor(Qt.SizeAllCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier and (event.button() == Qt.LeftButton or event.button() == Qt.RightButton):
            self.setSelected(not self.isSelected())
            
        idx = self._point_at(event.pos())
        if idx is not None:
            self.dragging_point = idx
            event.accept()
        elif event.modifiers() & Qt.ControlModifier and event.button() == Qt.LeftButton:
            # Ctrl+Left click for texture dragging
            self._is_dragging_texture = True
            self._show_texture_offset_overlay = True
            self._drag_start_pos = event.scenePos()
            self._start_offset_x = self.texture_offset_x
            self._start_offset_y = self.texture_offset_y
            event.accept()
        elif event.modifiers() & Qt.ShiftModifier and event.button() == Qt.LeftButton:
            # Shift+Left click for duplication
            self._is_duplicating = True
            self._drag_start_pos = event.scenePos()
            self._ghost_items = []  # Store multiple ghost items for all selected shapes
            event.accept()
        elif event.modifiers() & Qt.AltModifier and event.button() == Qt.LeftButton:
            # Alt+Left click for rotation
            self._is_rotating = True
            self._start_angle = self.texture_rotation
            # Store the initial mouse position for angle calculation
            self._rotation_start_pos = event.scenePos()
            # Calculate and store the center of the triangle in scene coordinates
            points = self.polygon()
            center_x = (points[0].x() + points[1].x() + points[2].x()) / 3
            center_y = (points[0].y() + points[1].y() + points[2].y()) / 3
            self._rotation_center = self.mapToScene(QPointF(center_x, center_y))
            self._show_rotation_overlay = True
            self._overlay_timer.start(1000)  # Show overlay for 1 second
            event.accept()
        else:
            self._is_duplicating = False
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        modifiers = event.modifiers()
        if self.dragging_point is not None:
            points = list(self.polygon())
            pos = event.pos()
            # Snap to grid in item coordinates
            snapped = QPointF(self.snap(pos.x()), self.snap(pos.y()))
            points[self.dragging_point] = snapped
            self.setPolygon(QPolygonF(points))
            event.accept()
        elif self._is_duplicating:
            # Calculate the delta from the start position
            delta = event.scenePos() - self._drag_start_pos
            
            # Snap to grid
            snapped_dx = round(delta.x() / GRID_SIZE) * GRID_SIZE
            snapped_dy = round(delta.y() / GRID_SIZE) * GRID_SIZE
            
            # Get all selected items
            selected_items = self.scene().selectedItems()
            
            # Create or update ghost items for all selected items
            if not self._ghost_items:
                # First time - create ghost items for all selected shapes
                for item in selected_items:
                    # Create ghosts for all selected items except self
                    if item != self:
                        # Handle different types of items
                        if isinstance(item, MapTriangle):
                            # Create a new ghost triangle with the same points
                            points = [pt for pt in item.polygon()]
                            ghost = MapTriangle(points[0], points[1], points[2])
                            ghost.setPos(item.pos())
                            if hasattr(item, 'texture_path'):
                                ghost.texture_path = item.texture_path
                                ghost.texture_pixmap = item.texture_pixmap
                                ghost.texture_scale = item.texture_scale
                                ghost.texture_offset_x = item.texture_offset_x
                                ghost.texture_offset_y = item.texture_offset_y
                                ghost.texture_rotation = item.texture_rotation
                                ghost.stype = item.stype
                            
                            # Make it semi-transparent
                            ghost.setOpacity(0.5)
                            
                            # Add it to the scene and our list
                            self.scene().addItem(ghost)
                            self._ghost_items.append((item, ghost))
                        
                        # Handle MapRect items
                        elif hasattr(item, 'rect') and callable(getattr(item, 'rect')):
                            from MapRect import MapRect
                            # Create a new ghost rect
                            ghost = MapRect(item.rect())
                            ghost.setPos(item.pos())
                            if hasattr(item, 'texture_path'):
                                ghost.texture_path = item.texture_path
                                ghost.texture_pixmap = item.texture_pixmap
                                ghost.texture_scale = item.texture_scale
                                ghost.texture_offset_x = item.texture_offset_x
                                ghost.texture_offset_y = item.texture_offset_y
                                ghost.texture_rotation = item.texture_rotation
                                ghost.stype = item.stype
                            
                            # Make it semi-transparent
                            ghost.setOpacity(0.5)
                            
                            # Add it to the scene and our list
                            self.scene().addItem(ghost)
                            self._ghost_items.append((item, ghost))
                
                # Add a ghost for the current item if it's not already included
                if not any(original == self for original, _ in self._ghost_items):
                    points = [pt for pt in self.polygon()]
                    ghost = MapTriangle(points[0], points[1], points[2])
                    ghost.setPos(self.pos())
                    ghost.texture_path = self.texture_path
                    ghost.texture_pixmap = self.texture_pixmap
                    ghost.texture_scale = self.texture_scale
                    ghost.texture_offset_x = self.texture_offset_x
                    ghost.texture_offset_y = self.texture_offset_y
                    ghost.texture_rotation = self.texture_rotation
                    ghost.stype = self.stype
                    
                    # Make it semi-transparent
                    ghost.setOpacity(0.5)
                    
                    # Add it to the scene and our list
                    self.scene().addItem(ghost)
                    self._ghost_items.append((self, ghost))
            
            # Update all ghost items' positions
            for original, ghost in self._ghost_items:
                ghost_pos = original.pos() + QPointF(snapped_dx, snapped_dy)
                ghost.setPos(ghost_pos)
            
            event.accept()
        elif self._is_dragging_texture:
            delta = event.scenePos() - self._drag_start_pos
            if modifiers & Qt.ShiftModifier:
                # Free movement without scaling the delta
                self.texture_offset_x = self._start_offset_x + delta.x()
                self.texture_offset_y = self._start_offset_y + delta.y()
            else:
                # Snap to grid
                snapped_dx = round(delta.x() / GRID_SIZE) * GRID_SIZE
                snapped_dy = round(delta.y() / GRID_SIZE) * GRID_SIZE
                self.texture_offset_x = self._start_offset_x + snapped_dx
                self.texture_offset_y = self._start_offset_y + snapped_dy
            self.update()
            event.accept()
        elif self._is_rotating:
            # Get the current cursor position in scene coordinates
            current_pos = event.scenePos()
            
            # Calculate the initial angle from center to start position
            start_vector_x = self._rotation_start_pos.x() - self._rotation_center.x()
            start_vector_y = self._rotation_start_pos.y() - self._rotation_center.y()
            initial_angle = math.degrees(math.atan2(start_vector_y, start_vector_x))
            
            # Calculate the current angle from center to current position
            current_vector_x = current_pos.x() - self._rotation_center.x()
            current_vector_y = current_pos.y() - self._rotation_center.y()
            current_angle = math.degrees(math.atan2(current_vector_y, current_vector_x))
            
            # Calculate the angle change
            angle_change = current_angle - initial_angle
            
            # Apply the angle change to the starting rotation
            new_rotation = self._start_angle + angle_change
            
            if modifiers & Qt.ShiftModifier:
                # Free rotation
                self.texture_rotation = new_rotation
            else:
                # Snap rotation to 15-degree increments
                self.texture_rotation = round(new_rotation / 15) * 15
            
            self._show_rotation_overlay = True
            self._overlay_timer.start(1000)  # Show overlay for 1 second
            self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging_point is not None:
            # Snap all vertices to grid on release
            snapped_points = []
            for pt in self.polygon():
                snapped_pt = QPointF(self.snap(pt.x()), self.snap(pt.y()))
                snapped_points.append(snapped_pt)
            self.setPolygon(QPolygonF(snapped_points))
            self.dragging_point = None
            self.signals.triChanged.emit(self)
            event.accept()
        elif self._is_duplicating:
            self._is_duplicating = False
            
            # If we have ghost items, make them permanent
            if self._ghost_items:
                # Store a reference to the scene
                scene = self.scene()
                
                # Make all ghost items fully opaque
                for _, ghost in self._ghost_items:
                    ghost.setOpacity(1.0)
                
                # Reset the ghost items reference
                self._ghost_items = []
                
                # Emit signal that new items were created
                if scene:
                    try:
                        # Check if scene has isDeleted method (our MapScene)
                        if hasattr(scene, 'isDeleted') and scene.isDeleted():
                            return
                        self.signals.triChanged.emit(self)
                    except RuntimeError:
                        # Scene was deleted
                        pass
            
            event.accept()
        elif self._is_dragging_texture:
            self._is_dragging_texture = False
            self._show_texture_offset_overlay = False
            self.signals.triChanged.emit(self)
            event.accept()
        elif self._is_rotating:
            self._is_rotating = False
            self._start_angle = None
            self._rotation_start_pos = None
            self._rotation_center = None
            self._show_rotation_overlay = False
            self.signals.triChanged.emit(self)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        # Only clear selection if Ctrl is not pressed (to allow multi-selection)
        if not (event.modifiers() & Qt.ControlModifier):
            self.scene().clearSelection()
            self.setSelected(True)
        modifiers = event.modifiers()
        if modifiers & Qt.ControlModifier:
            steps = event.delta() / 240

            if modifiers & Qt.ShiftModifier:
                scale_change = self.texture_scale * 0.01 * steps
            else:
                scale_change = self.texture_scale * 0.1 * steps

            new_scale = self.texture_scale + scale_change
            new_scale = min(max(new_scale, 0.01), 10)
            new_scale = round(new_scale, 4)
            self.texture_scale = new_scale
            self._show_scale_overlay = True
            self.update()
            # Restart timer for overlay (e.g. show for 1 second after each scale)
            self._overlay_timer.start(1000)
            event.accept()
            self.signals.triChanged.emit(self)
        else:
            super().wheelEvent(event)

    def _point_at(self, pos):
        # Checks which point the mouse is near
        for i, pt in enumerate(self.polygon()):
            if (pt - pos).manhattanLength() < self.POINT_RADIUS:
                return i
        return None


    @staticmethod
    def default_right_angle(size=64, origin=QPointF(0, 0)):
        x, y = origin.x(), origin.y()
        points = [
            QPointF(x, y + size),  # Bottom Left
            QPointF(x + size, y + size),  # Bottom Right (right angle)
            QPointF(x + size, y),  # Top Right
        ]
        return MapTriangle(*points)

    def contextMenuEvent(self, event):
        menu = QMenu()
        front_act = menu.addAction("Move to Front")
        back_act = menu.addAction("Move to Back")
        del_act = menu.addAction("Delete")
        action = menu.exec_(event.screenPos())
        if action == front_act:
            # Get all items in the scene
            all_items = self.scene().items()
            if all_items:
                # Find the highest z-value
                max_z = max(item.zValue() for item in all_items)
                # Set this item's z-value to be higher than the highest
                self.setZValue(max_z + 1)
                self.signals.triChanged.emit(self)
        elif action == back_act:
            # Get all items in the scene
            all_items = self.scene().items()
            if all_items:
                # Find the lowest z-value
                min_z = min(item.zValue() for item in all_items)
                # Set this item's z-value to be lower than the lowest
                self.setZValue(min_z - 1)
                self.signals.triChanged.emit(self)
        elif action == del_act:
            scene = self.scene()
            if self.isSelected():
                # Delete all selected items (copy the list to avoid modification during iteration)
                for item in list(scene.selectedItems()):
                    scene.removeItem(item)
                    del item
            else:
                # Select only this item, then delete it
                self.setSelected(True)
                scene.removeItem(self)
                del self

    def paint(self, painter, option, widget):
        # Save the original state of the option
        original_option = option
        
        # Create a copy of the option and remove the selection state
        # This prevents the default selection border from being drawn
        option.state &= ~QStyle.State_Selected
        
        if self.texture_pixmap:
            # Create triangle clipping path
            path = QPainterPath()
            path.addPolygon(self.polygon())
            painter.setClipPath(path)

            # Create a texture brush with the pixmap directly
            brush = QBrush(self.texture_pixmap)

            # Apply optional scaling, offset, and rotation using transform
            transform = QTransform()
            
            # Calculate the center of the triangle for rotation
            points = self.polygon()
            center_x = (points[0].x() + points[1].x() + points[2].x()) / 3
            center_y = (points[0].y() + points[1].y() + points[2].y()) / 3
            
            # Get the bounding rectangle of the triangle
            bounding_rect = self.boundingRect()
            top_left = bounding_rect.topLeft()
            
            # Apply translation to center for rotation
            transform.translate(center_x, center_y)
            
            # Apply rotation
            transform.rotate(self.texture_rotation)
            
            # Translate back
            transform.translate(-center_x, -center_y)
            
            # Apply translation to the top-left corner of the bounding rectangle
            transform.translate(top_left.x() + self.texture_offset_x, top_left.y() + self.texture_offset_y)
            
            # Apply scale last
            transform.scale(self.texture_scale, self.texture_scale)
            
            brush.setTransform(transform)

            # Set brush and draw the triangle
            painter.setBrush(brush)
            painter.setPen(Qt.black)  # Optional: triangle border
            painter.drawPolygon(self.polygon())

            # Reset clip after drawing
            painter.setClipping(False)
            
            # Draw scale overlay if needed
            if getattr(self, "_show_scale_overlay", False):
                rect = self.boundingRect()
                overlay_text = f"Scale: {self.texture_scale}x"
                painter.save()
                painter.setPen(Qt.white)
                painter.setBrush(QColor(0, 0, 0, 180))
                text_rect = QRectF(rect.left() + 10, rect.top() + 10, 100, 30)
                painter.drawRect(text_rect)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, overlay_text)
                painter.restore()
                
            # Draw texture offset overlay if needed
            if getattr(self, "_show_texture_offset_overlay", False):
                rect = self.boundingRect()
                overlay_text = f"Offset: x={self.texture_offset_x:.1f}, y={self.texture_offset_y:.1f}"
                painter.save()
                painter.setPen(Qt.white)
                painter.setBrush(QColor(0, 0, 0, 180))
                text_rect = QRectF(rect.left() + 10, rect.top() + 45, 180, 30)
                painter.drawRect(text_rect)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, overlay_text)
                painter.restore()
                
            # Draw rotation overlay if needed
            if getattr(self, "_show_rotation_overlay", False):
                rect = self.boundingRect()
                overlay_text = f"Rotation: {self.texture_rotation:.1f}°"
                painter.save()
                painter.setPen(Qt.white)
                painter.setBrush(QColor(0, 0, 0, 180))
                text_rect = QRectF(rect.left() + 10, rect.top() + 80, 180, 30)
                painter.drawRect(text_rect)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, overlay_text)
                painter.restore()
        else:
            # Default fallback (e.g., solid color brush)
            super().paint(painter, option, widget)
        
        # We don't draw the selection border here anymore, it will be drawn in paintSelectionBorder
        
    def paintSelectionBorder(self, painter):
        """Draw the selection border on top of everything else"""
        if self.isSelected():
            # Save current painter state
            painter.save()
            
            # Create a bright pink color
            bright_pink = QColor(255, 20, 147)
            
            # Create a dashed pen
            pen = painter.pen()
            pen.setColor(bright_pink)
            pen.setStyle(Qt.DashLine)
            pen.setWidth(1)
            
            # Set the pen and draw the selection border
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            
            # Apply the item's transformation to the painter
            painter.setTransform(self.sceneTransform(), True)
            
            # Draw the polygon in item coordinates
            painter.drawPolygon(self.polygon())
            
            # Restore painter state
            painter.restore()

