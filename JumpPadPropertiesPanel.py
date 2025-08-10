from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QWidget, QFormLayout, QDoubleSpinBox, QComboBox, QVBoxLayout, QSpinBox

import MapJumpPad


class JumpPadPropertiesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Use a QVBoxLayout as the main layout to match other property panels
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        
        # Add the form layout to the main layout
        self.layout = QFormLayout()
        self.main_layout.addLayout(self.layout)
        
        # Add stretch at the bottom to match other property panels
        self.main_layout.addStretch()

        self._jump_pad: MapJumpPad|None = None  # Track the current edited item
        self._disable_update = False  # Prevent recursion

        # Velocity X
        self.vel_x_spin = QDoubleSpinBox()
        self.vel_x_spin.setRange(0, 10)
        self.vel_x_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("Velocity X:", self.vel_x_spin)

        # Velocity Y
        self.vel_y_spin = QDoubleSpinBox()
        self.vel_y_spin.setRange(0, 10)
        self.vel_y_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("Velocity Y:", self.vel_y_spin)

        # Position controls
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-1000000000, 1000000000)
        self.x_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("X:", self.x_spin)

        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-1000000000, 1000000000)
        self.y_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("Y:", self.y_spin)

    def _on_edit(self, value):
        """Handle property value changes"""
        if self._disable_update or self._jump_pad is None:
            return

        # Update position
        rect = self._jump_pad.rect()
        old_scene_x = self._jump_pad.pos().x() + rect.x()
        old_scene_y = self._jump_pad.pos().y() + rect.y()
        new_scene_x = self.x_spin.value()
        new_scene_y = self.y_spin.value()

        # If the top-left coordinate changes, move object or rect accordingly
        delta_x = new_scene_x - old_scene_x
        delta_y = new_scene_y - old_scene_y
        if delta_x != 0 or delta_y != 0:
            self._jump_pad.setPos(self._jump_pad.pos() + QPointF(delta_x, delta_y))

        # Update velocity
        self._jump_pad.vel.setX(self.vel_x_spin.value())
        self._jump_pad.vel.setY(self.vel_y_spin.value())

        # Update item appearance
        self._jump_pad.update()

    def set_jump_pad(self, jump_pad: MapJumpPad):
        """Set the item to be edited"""
        # Disconnect previous signal if needed
        if hasattr(self, "_jump_pad") and self._jump_pad is not None and self._jump_pad != jump_pad:
            try:
                self._jump_pad.signals.jumpPadChanged.disconnect(self.set_jump_pad)
            except Exception:
                pass

        # Even if it's the same item, disconnect before reconnecting to avoid stacking connections
        try:
            jump_pad.signals.jumpPadChanged.disconnect(self.set_jump_pad)
        except Exception:
            pass

        self._jump_pad = jump_pad
        jump_pad.signals.jumpPadChanged.connect(self.set_jump_pad)

        self._disable_update = True
        rect = jump_pad.rect()

        # Set velocity
        self.vel_x_spin.setValue(jump_pad.vel.x())
        self.vel_y_spin.setValue(jump_pad.vel.y())

        # Set position and size
        scene_x = jump_pad.pos().x() + rect.x()
        scene_y = jump_pad.pos().y() + rect.y()
        self.x_spin.setValue(scene_x)
        self.y_spin.setValue(scene_y)

        self._disable_update = False