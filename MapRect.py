from PyQt5.QtWidgets import (
    QGraphicsRectItem, QMenu,  QGraphicsSceneMouseEvent,
    QGraphicsSceneHoverEvent, QGraphicsItem, QStyle,
)
from PyQt5.QtGui import QBrush, QPixmap, QTransform, QColor, QCursor
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal, QObject
import math

from config import GRID_SIZE
from utils import snap_value

class MapRectSignals(QObject):
    rectChanged = pyqtSignal(object)


class MapRect(QGraphicsRectItem):
    EDGE_MARGIN = 8  # pixels for "hot area" to resize

    def __init__(self, rect, parent=None):
        super().__init__()

        self._rotation_center = None
        self._rotation_start_pos = None
        self.setRect(rect)
        self.signals = MapRectSignals(parent)

        self.setAcceptDrops(True)

        self.setFlags(self.ItemIsSelectable | self.ItemIsMovable | self.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.stype = "static"

        self.texture_path = None
        self.texture_pixmap: QPixmap|None = None
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
        self._is_rotating = None
        self._start_angle = None

        # Duplication-related variables
        self._is_duplicating = False
        self._ghost_item = None

        self._overlay_timer = QTimer()
        self._overlay_timer.setSingleShot(True)
        self._overlay_timer.timeout.connect(self._hide_overlays)



        self._is_resizing = False
        self.resize_edge = None
        self.mouse_press_pos = None
        self.orig_rect = None

    def _hide_overlays(self):
        self._show_texture_offset_overlay = False
        self._show_scale_overlay = False
        self._show_rotation_overlay = False
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            grid_size = GRID_SIZE

            # Find offset of rect's local (0,0) to scene
            rect = self.rect()
            # The position is where the rect's (rect.x(), rect.y()) ends up in the scene
            new_pos = value
            top_left_offset = QPointF(rect.x(), rect.y())
            scene_top_left = new_pos + top_left_offset

            # Snap the top-left to grid
            snapped_scene_top_left = QPointF(
                snap_value(scene_top_left.x(), grid_size),
                snap_value(scene_top_left.y(), grid_size)
            )

            # Find what the item's position should be to make (rect.x(), rect.y()) land at snapped_scene_top_left
            snapped_item_pos = snapped_scene_top_left - top_left_offset
            return snapped_item_pos

        if change == QGraphicsItem.ItemPositionHasChanged:
            self.signals.rectChanged.emit(self)

        return super().itemChange(change, value)

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent):
        pos = event.pos()
        rect = self.rect()
        margin = self.EDGE_MARGIN

        left = abs(pos.x() - rect.left()) < margin
        right = abs(pos.x() - rect.right()) < margin
        top = abs(pos.y() - rect.top()) < margin
        bottom = abs(pos.y() - rect.bottom()) < margin

        cursor = Qt.ArrowCursor
        edge = None
        if left and top:
            cursor = Qt.SizeFDiagCursor
            edge = "topleft"
        elif right and top:
            cursor = Qt.SizeBDiagCursor
            edge = "topright"
        elif left and bottom:
            cursor = Qt.SizeBDiagCursor
            edge = "bottomleft"
        elif right and bottom:
            cursor = Qt.SizeFDiagCursor
            edge = "bottomright"
        elif left:
            cursor = Qt.SizeHorCursor
            edge = "left"
        elif right:
            cursor = Qt.SizeHorCursor
            edge = "right"
        elif top:
            cursor = Qt.SizeVerCursor
            edge = "top"
        elif bottom:
            cursor = Qt.SizeVerCursor
            edge = "bottom"

        if edge:
            self.setCursor(QCursor(cursor))
            self.resize_edge = edge
        else:
            self.setCursor(Qt.ArrowCursor)
            self.resize_edge = None

        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):

        if event.modifiers() & Qt.ControlModifier and (event.button() == Qt.LeftButton or event.button() == Qt.RightButton):
            self.setSelected(not self.isSelected())

        if self.resize_edge:
            self._is_resizing = True
            self.mouse_press_pos = event.pos()
            self.orig_rect = self.rect()
            event.accept()
            return
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
            # Store the center of the rectangle in scene coordinates
            self._rotation_center = self.mapToScene(self.rect().center())
            self._show_rotation_overlay = True
            self._overlay_timer.start(1000)  # Show overlay for 1 second
            event.accept()
        else:
            self._is_duplicating = False
            super().mousePressEvent(event)


    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        modifiers = event.modifiers()
        if self._is_resizing:
            diff = event.pos() - self.mouse_press_pos
            r = QRectF(self.orig_rect)
            edge = self.resize_edge

            # Adjust based on which edge/corner is being resized
            if edge == "left":
                r.setLeft(r.left() + diff.x())
            elif edge == "right":
                r.setRight(r.right() + diff.x())
            elif edge == "top":
                r.setTop(r.top() + diff.y())
            elif edge == "bottom":
                r.setBottom(r.bottom() + diff.y())
            elif edge == "topleft":
                r.setLeft(r.left() + diff.x())
                r.setTop(r.top() + diff.y())
            elif edge == "topright":
                r.setRight(r.right() + diff.x())
                r.setTop(r.top() + diff.y())
            elif edge == "bottomleft":
                r.setLeft(r.left() + diff.x())
                r.setBottom(r.bottom() + diff.y())
            elif edge == "bottomright":
                r.setRight(r.right() + diff.x())
                r.setBottom(r.bottom() + diff.y())

            # Snap edges to grid
            r.setLeft(snap_value(r.left(), GRID_SIZE))
            r.setRight(snap_value(r.right(), GRID_SIZE))
            r.setTop(snap_value(r.top(), GRID_SIZE))
            r.setBottom(snap_value(r.bottom(), GRID_SIZE))

            min_size = GRID_SIZE  # Minimum size is one grid square
            if r.width() < min_size:
                r.setWidth(min_size)
            if r.height() < min_size:
                r.setHeight(min_size)
            self.setRect(r.normalized())
            event.accept()
            return
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
                        # Handle MapRect items
                        if isinstance(item, (MapRect, QGraphicsRectItem)):
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
                        
                        # Handle MapTriangle items
                        elif hasattr(item, 'polygon') and callable(getattr(item, 'polygon')):
                            from MapTriangle import MapTriangle
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

                # Add a ghost for the current item if it's not already included
                if not any(original == self for original, _ in self._ghost_items):
                    ghost = MapRect(self.rect())
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


    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self._is_resizing:
            self._is_resizing = False
            self.resize_edge = None
            self.mouse_press_pos = None
            self.orig_rect = None
            self.signals.rectChanged.emit(self)
            event.accept()
        elif self._is_duplicating:
            self._is_duplicating = False
            
            # If we have ghost items, make them permanent
            if self._ghost_items:
                # Store a reference to the scene
                scene = self.scene()

                scene.clearSelection()

                # Make all ghost items fully opaque
                for _, ghost in self._ghost_items:
                    ghost.setOpacity(1.0)
                    ghost.setSelected(True)

                # Reset the ghost items reference
                self._ghost_items = []

                # Emit signal that new items were created
                if scene:
                    try:
                        # Check if scene has isDeleted method (our MapScene)
                        if hasattr(scene, 'isDeleted') and scene.isDeleted():
                            return
                        self.signals.rectChanged.emit(self)
                    except RuntimeError:
                        # Scene was deleted
                        pass
            
            event.accept()
        elif self._is_dragging_texture:
            self._is_dragging_texture = False
            self._show_texture_offset_overlay = False
            self.signals.rectChanged.emit(self)
            event.accept()
        elif self._is_rotating:
            self._is_rotating = False
            self._start_angle = None
            self._rotation_start_pos = None
            self._rotation_center = None
            self._show_rotation_overlay = False
            self.signals.rectChanged.emit(self)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            # This check ensures only files (like dropped images) are accepted
            event.accept()
        elif event.mimeData().hasText() and event.mimeData().text().lower().endswith(
            (".png", ".jpg", ".jpeg", ".bmp", ".gif")):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

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
        self.signals.rectChanged.emit(self)
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu()
        if self.stype == "static":
            wall_act = menu.addAction("Toggle wall")
        else:
            wall_act = menu.addAction("Toggle static")
        front_act = menu.addAction("Move to Front")
        back_act = menu.addAction("Move to Back")
        del_act = menu.addAction("Delete")
        action = menu.exec_(event.screenPos())
        if action == wall_act:
            if self.stype == "static":
                self.stype = "wall"
            else:
                self.stype = "static"
            self.signals.rectChanged.emit(self)
        elif action == front_act:
            # Get all items in the scene
            all_items = self.scene().items()
            if all_items:
                # Find the highest z-value
                max_z = max(item.zValue() for item in all_items)
                # Set this item's z-value to be higher than the highest
                self.setZValue(max_z + 1)
                self.signals.rectChanged.emit(self)
        elif action == back_act:
            # Get all items in the scene
            all_items = self.scene().items()
            if all_items:
                # Find the lowest z-value
                min_z = min(item.zValue() for item in all_items)
                # Set this item's z-value to be lower than the lowest
                self.setZValue(min_z - 1)
                self.signals.rectChanged.emit(self)
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

    def wheelEvent(self, event):
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
            self.signals.rectChanged.emit(self)
        else:
            super().wheelEvent(event)

    def paint(self, painter, option, widget=None):
        # Save the original state of the option
        original_option = option
        
        # Create a copy of the option and remove the selection state
        # This prevents the default selection border from being drawn
        option.state &= ~QStyle.State_Selected
        
        if self.texture_pixmap and not self.texture_pixmap.isNull():

            t = QTransform()
            
            # Get the center of the rectangle for rotation
            rect_center_x = self.rect().center().x()
            rect_center_y = self.rect().center().y()
            
            # Apply translation to center for rotation
            t.translate(rect_center_x, rect_center_y)
            
            # Apply rotation
            t.rotate(self.texture_rotation)
            
            # Translate back
            t.translate(-rect_center_x, -rect_center_y)
            
            # Apply offset in the item's local coordinate system
            t.translate(self.texture_offset_x, self.texture_offset_y)

            # Create the brush with the texture
            brush = QBrush(self.texture_pixmap)

            # Get the top-left point of the rectangle
            top_left_point = self.rect().topLeft()

            # Create a QTransform and translate it to the top-left of your rect.
            # This aligns the texture's origin with the top-left corner of the shape you are about to draw.
            t.translate(top_left_point.x() + self.texture_offset_x, top_left_point.y() + self.texture_offset_y)

            # Apply scale last
            t.scale(self.texture_scale, self.texture_scale)

            # Apply the transform to the brush
            brush.setTransform(t)

            # Set the brush on the painter
            painter.setBrush(brush)
            painter.setPen(Qt.NoPen)  # Optional: don't draw an outline

            # Draw the shape
            painter.drawRect(self.rect())

            painter.restore()



            if getattr(self, "_show_scale_overlay", False):
                rect = self.rect()
                overlay_text = f"Scale: {self.texture_scale}x"
                painter.save()
                painter.setPen(Qt.white)
                painter.setBrush(QColor(0, 0, 0, 180))
                text_rect = QRectF(rect.left() + 10, rect.top() + 10, 100, 30)
                painter.drawRect(text_rect)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, overlay_text)
                painter.restore()
            if getattr(self, "_show_texture_offset_overlay", False):
                rect = self.rect()
                overlay_text = f"Offset: x={self.texture_offset_x:.1f}, y={self.texture_offset_y:.1f}"
                painter.save()
                painter.setPen(Qt.white)
                painter.setBrush(QColor(0, 0, 0, 180))
                # Draw the overlay below the scale overlay, or wherever you prefer
                text_rect = QRectF(rect.left() + 10, rect.top() + 10, 180, 30)
                painter.drawRect(text_rect)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, overlay_text)
                painter.restore()
                
            if getattr(self, "_show_rotation_overlay", False):
                rect = self.rect()
                overlay_text = f"Rotation: {self.texture_rotation:.1f}°"
                painter.save()
                painter.setPen(Qt.white)
                painter.setBrush(QColor(0, 0, 0, 180))
                # Draw the overlay below the other overlays
                text_rect = QRectF(rect.left() + 10, rect.top() + 10, 180, 30)
                painter.drawRect(text_rect)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, overlay_text)
                painter.restore()
        else:
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
            
            # Draw the rectangle in item coordinates
            painter.drawRect(self.rect())
            
            # Restore painter state
            painter.restore()