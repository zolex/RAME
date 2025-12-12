from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsItem, QMenu
from PyQt5.QtGui import QPixmap, QCursor
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, QObject
from PyQt5.QtGui import QTransform
from PyQt6.QtCore import QRect

from config import GRID_SIZE
from utils import snap_value

class PlayerSpawnpointSignals(QObject):
    spawnpointChanged = pyqtSignal(object)

class PlayerSpawnpoint(QGraphicsPixmapItem):
    def __init__(self, position, parent=None):
        # Load the player texture
        pixmap = QPixmap("assets/player.png")

        t = QTransform()
        t.scale(0.75, 0.75)
        pixmap = pixmap.transformed(t)

        pixmap = pixmap.copy(16, 32, 64, 96)

        super().__init__(pixmap)




        # Set position
        self.setPos(position)
        
        # Create signals
        self.signals = PlayerSpawnpointSignals(parent)
        
        # Set flags
        self.setFlags(self.ItemIsSelectable | self.ItemIsMovable | self.ItemSendsGeometryChanges)
        
        # Center the pixmap at the position
        #self.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)
        
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            grid_size = GRID_SIZE
            
            # Get new position
            new_pos = value
            
            # Snap to grid
            snapped_pos = QPointF(
                snap_value(new_pos.x(), grid_size),
                snap_value(new_pos.y(), grid_size)
            )
            
            return snapped_pos
            
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.signals.spawnpointChanged.emit(self)
            
        return super().itemChange(change, value)
    
    def contextMenuEvent(self, event):
        menu = QMenu()
        delete_action = menu.addAction("Delete")
        action = menu.exec_(QCursor.pos())
        
        if action == delete_action:
            scene = self.scene()
            if scene:
                scene.removeItem(self)
                del self