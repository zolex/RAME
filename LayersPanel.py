from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from DraggableListWidget import DraggableListWidget
from MapScene import MapScene


class LayersPanel(QWidget):

    def __init__(self, scene: MapScene, parent=None):
        super().__init__(parent)
        self.scene = scene

        self.list_widget = DraggableListWidget()
        self.list_widget.setViewMode(QListWidget.ListMode)
        self.list_widget.setDragEnabled(True)  # Enable dragging

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)

    def update(self):
        self.list_widget.clear()
        for item in self.scene.items():
            layer = QListWidgetItem(f"layer {item.type()}")
            self.list_widget.addItem(layer)