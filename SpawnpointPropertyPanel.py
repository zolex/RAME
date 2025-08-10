from PyQt5.QtWidgets import QWidget, QFormLayout, QLabel, QDoubleSpinBox, QVBoxLayout
from PyQt5.QtCore import QPointF

class SpawnpointPropertyPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Use a QVBoxLayout as the main layout to match EmptyPropertiesPanel
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        
        # Add the form layout to the main layout
        self.layout = QFormLayout()
        self.main_layout.addLayout(self.layout)
        
        # Add stretch at the bottom to match EmptyPropertiesPanel
        self.main_layout.addStretch()

        self._spawnpoint = None  # Track the current edited item
        self._disable_update = False  # Prevent recursion

        # Create position spinboxes
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-1000000000, 1000000000)
        self.x_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("X:", self.x_spin)

        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-1000000000, 1000000000)
        self.y_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("Y:", self.y_spin)

        # Add a label with information about the spawnpoint
        self.info_label = QLabel("Player spawnpoint position")
        self.layout.addRow("Info:", self.info_label)

    def _on_edit(self, value):
        if self._disable_update or self._spawnpoint is None:
            return

        # Get current position values
        new_x = self.x_spin.value()
        new_y = self.y_spin.value()
        
        # Update the spawnpoint position
        self._spawnpoint.setPos(QPointF(new_x, new_y))
        
        # Emit the spawnpoint changed signal
        self._spawnpoint.signals.spawnpointChanged.emit(self._spawnpoint)

    def set_spawnpoint(self, spawnpoint):
        # Disconnect previous signal if needed
        if hasattr(self, "_spawnpoint") and self._spawnpoint is not None and self._spawnpoint != spawnpoint:
            try:
                self._spawnpoint.signals.spawnpointChanged.disconnect(self.set_spawnpoint)
            except Exception:
                pass

        # Even if it's the same item, disconnect before reconnecting to avoid stacking connections
        try:
            spawnpoint.signals.spawnpointChanged.disconnect(self.set_spawnpoint)
        except Exception:
            pass

        self._spawnpoint = spawnpoint
        spawnpoint.signals.spawnpointChanged.connect(self.set_spawnpoint)

        self._disable_update = True
        
        # Set the position values in the spinboxes
        self.x_spin.setValue(spawnpoint.pos().x())
        self.y_spin.setValue(spawnpoint.pos().y())
        
        self._disable_update = False