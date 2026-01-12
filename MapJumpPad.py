from PyQt5.QtWidgets import QGraphicsRectItem, QMenu, QGraphicsSceneMouseEvent, QGraphicsItem, QStyle
from PyQt5.QtGui import QBrush, QPixmap, QColor
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject

from config import GRID_SIZE
from utils import snap_value

class MapJumpPadSignals(QObject):
    jumpPadChanged = pyqtSignal(object)

class MapJumpPad(QGraphicsRectItem):
    def __init__(self, pos: QPointF, velocity: float = 0.3, rotation: int = 0, parent=None):
        super().__init__(QRectF(0, 0, 96, 32), parent)
        self.signals = MapJumpPadSignals()
        self.setPos(pos)
        self.velocity: float = velocity
        # Apply initial rotation to the QGraphicsItem instead of shadowing the rotation() method
        self.setRotation(rotation)

        # Make item movable, selectable, and focusable
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        # Enable hover events
        self.setAcceptHoverEvents(True)

        # Set rotation origin to the center of the item so rotations look natural
        self.setTransformOriginPoint(self.rect().center())
        

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            # Snap to grid when moving
            new_pos = value
            grid_size = GRID_SIZE
            new_x = snap_value(new_pos.x(), grid_size)
            new_y = snap_value(new_pos.y(), grid_size)
            new_pos = QPointF(new_x, new_y)

            # Emit signal that item has changed
            self.signals.jumpPadChanged.emit(self)
            return new_pos
            
        elif change == QGraphicsItem.ItemSelectedChange:
            # Emit signal when selection changes
            if value:
                self.signals.jumpPadChanged.emit(self)
        elif change == QGraphicsItem.ItemRotationChange or change == QGraphicsItem.ItemRotationHasChanged:
            # Emit when rotation is about to change/has changed
            self.signals.jumpPadChanged.emit(self)
                
        return super().itemChange(change, value)
    
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.LeftButton:
            # Handle left-click for dragging
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.LeftButton:
            # Reset cursor after dragging
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)
    
    def contextMenuEvent(self, event):
        menu = QMenu()
        del_act = menu.addAction("Delete")
        action = menu.exec_(event.screenPos())
        if action == del_act:
            scene = self.scene()
            if self.isSelected():
                # Delete all selected items
                for item in list(scene.selectedItems()):
                    scene.removeItem(item)
                    del item
            else:
                # Delete just this item
                scene.removeItem(self)
                del self
    
    def wheelEvent(self, event):
        # Ctrl+Wheel rotates the jumppad; Shift for finer rotation
        modifiers = event.modifiers()
        if modifiers & Qt.ControlModifier:
            steps = event.delta() / 240
            if modifiers & Qt.ShiftModifier:
                step_deg = 1.0
            else:
                step_deg = 5.0
            new_rotation = self.rotation() + steps * step_deg
            # Normalize to keep value reasonable
            if new_rotation > 360 or new_rotation < -360:
                new_rotation = ((new_rotation + 360) % 720) - 360
            self.setRotation(new_rotation)
            self.update()
            self.signals.jumpPadChanged.emit(self)
            event.accept()
        else:
            super().wheelEvent(event)
    
    def paint(self, painter, option, widget=None):
        # Save the original state of the option
        original_option = option
        
        # Remove the selection state to prevent default selection border
        option.state &= ~QStyle.State_Selected

        # Draw with texture
        painter.save()
        painter.setBrush(QBrush(QPixmap("assets/jumppad.png")))
        painter.drawRect(self.rect())
        painter.restore()

        # Draw a custom selection border if selected
        if self.isSelected():
            painter.save()
            # Create a bright pink color for selection
            bright_pink = QColor(255, 20, 147)
            # Create a dashed pen
            pen = painter.pen()
            pen.setColor(bright_pink)
            pen.setStyle(Qt.DashLine)
            pen.setWidth(1)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.rect())
            painter.restore()
    
    def paintSelectionBorder(self, painter):
        """Draw the selection border on top of everything else, respecting rotation"""
        if self.isSelected():
            painter.save()
            bright_pink = QColor(255, 20, 147)
            pen = painter.pen()
            pen.setColor(bright_pink)
            pen.setStyle(Qt.DashLine)
            pen.setWidth(1)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.setTransform(self.sceneTransform(), True)
            painter.drawRect(self.rect())
            painter.restore()
