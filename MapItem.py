from PyQt5.QtWidgets import (
    QGraphicsRectItem, QMenu, QGraphicsSceneMouseEvent,
    QGraphicsSceneHoverEvent, QGraphicsItem, QStyle,
)
from PyQt5.QtGui import QBrush, QPixmap, QTransform, QColor, QCursor
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal, QObject

from config import GRID_SIZE
from utils import snap_value

class MapItemSignals(QObject):
    itemChanged = pyqtSignal(object)

class MapItem(QGraphicsRectItem):
    def __init__(self, rect: QRectF = QRectF(0, 0, 32, 32), stay: bool = False, parent=None):
        super().__init__(rect, parent)
        self.signals = MapItemSignals()
        
        # Make item movable, selectable, and focusable
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        # Enable hover events
        self.setAcceptHoverEvents(True)
        
        # Set default properties
        self.item_type: str = "plasma"  # Can be "plasma" or "rocket"
        self.ammo: int = 10  # Default ammo count
        self.stay: bool = stay

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            # Snap to grid when moving
            new_pos = value
            grid_size = GRID_SIZE
            new_x = snap_value(new_pos.x(), grid_size)
            new_y = snap_value(new_pos.y(), grid_size)
            new_pos = QPointF(new_x, new_y)
            
            # Emit signal that item has changed
            self.signals.itemChanged.emit(self)
            return new_pos
            
        elif change == QGraphicsItem.ItemSelectedChange:
            # Emit signal when selection changes
            if value:
                self.signals.itemChanged.emit(self)
                
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

        if self.item_type == "plasma":
            texture_path = "assets/plasma.png"
        else:
            texture_path = "assets/rocket.png"
        texture_pixmap = QPixmap(texture_path)
        
        # Draw with texture
        painter.save()

        # Create a transform for the texture
        transform = QTransform()
        transform.scale(0.25, 0.25)

        # Create a brush with the texture
        brush = QBrush(texture_pixmap)
        brush.setTransform(transform)

        painter.setBrush(brush)
        painter.drawRect(self.rect())

        painter.restore()

        if self.stay:
            painter.save()
            pen = painter.pen()
            pen.setColor(Qt.darkBlue)
            pen.setStyle(Qt.SolidLine)
            pen.setWidth(3)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
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

        painter.setPen(Qt.black)
        # Draw ammo count
        painter.save()
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        text_rect = self.rect()
        painter.drawText(text_rect, Qt.AlignHCenter, str(self.ammo))
        painter.restore()