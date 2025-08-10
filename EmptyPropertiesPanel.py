from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class EmptyPropertiesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Create a label with instructions
        self.info_label = QLabel("Select an object to edit its properties.")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.info_label)
        
        # Add some spacing to make it look better
        self.layout.addStretch()