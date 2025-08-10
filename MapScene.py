from PyQt5.QtWidgets import QGraphicsScene
from PyQt5.QtGui import QPen, QColor
from PyQt5.QtCore import Qt
from config import GRID_SIZE

class MapScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.setSceneRect(0, 0, 1024, 768)
        self._is_deleted = False
        
    def isDeleted(self):
        return self._is_deleted
        
    def deleteLater(self):
        self._is_deleted = True
        super().deleteLater()

    def drawBackground(self, painter, rect):
        pen = QPen(QColor(200, 200, 200), 1, Qt.DashLine)  # Light gray, dashed
        painter.setPen(pen)

        left = int(rect.left()) - (int(rect.left()) % GRID_SIZE)
        top = int(rect.top()) - (int(rect.top()) % GRID_SIZE)
        right = int(rect.right())
        bottom = int(rect.bottom())

        # Draw vertical lines
        x = left
        while x <= right:
            painter.drawLine(x, top, x, bottom)
            x += GRID_SIZE

        # Draw horizontal lines
        y = top
        while y <= bottom:
            painter.drawLine(left, y, right, y)
            y += GRID_SIZE
            
    def drawForeground(self, painter, rect):
        """Draw selection borders on top of everything else"""
        super().drawForeground(painter, rect)
        
        # Draw selection borders for all selected items
        for item in self.selectedItems():
            # Check if the item has a paintSelectionBorder method
            if hasattr(item, 'paintSelectionBorder'):
                item.paintSelectionBorder(painter)