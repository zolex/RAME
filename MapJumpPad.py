from PyQt5.QtWidgets import QGraphicsRectItem, QMenu, QGraphicsSceneMouseEvent, QGraphicsItem, QStyle
from PyQt5.QtGui import QBrush, QPixmap, QColor, QVector2D
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject

from config import GRID_SIZE
from utils import snap_value

class MapJumpPadSignals(QObject):
    jumpPadChanged = pyqtSignal(object)

class MapJumpPad(QGraphicsRectItem):
    def __init__(self, pos: QPointF, vel: QVector2D = QVector2D(0, 0.3), parent=None):
        super().__init__(QRectF(0, 0, 128, 42), parent)
        self.signals = MapJumpPadSignals()
        self.setPos(pos)
        self.vel: QVector2D = vel

        # Make item movable, selectable, and focusable
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        # Enable hover events
        self.setAcceptHoverEvents(True)
        

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
