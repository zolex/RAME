from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QWidget, QFormLayout, QDoubleSpinBox, QComboBox, QVBoxLayout, QSpinBox, QCheckBox


class ItemPropertyPanel(QWidget):
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

        self._item = None  # Track the current edited item
        self._disable_update = False  # Prevent recursion

        # Item type selection
        self.type_combo = QComboBox()
        self.type_combo.addItems(["plasma", "rocket"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.layout.addRow("Type:", self.type_combo)

        # Ammo count
        self.ammo_spin = QSpinBox()
        self.ammo_spin.setRange(0, 1000)
        self.ammo_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("Ammo:", self.ammo_spin)

        # Stay
        self.stay_spin = QCheckBox()
        self.stay_spin.toggled.connect(self._on_edit)
        self.layout.addRow("Stay:", self.stay_spin)

        # Position controls
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-1000000000, 1000000000)
        self.x_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("X:", self.x_spin)

        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-1000000000, 1000000000)
        self.y_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("Y:", self.y_spin)

    def _on_type_changed(self, new_type):
        """Handle item type changes"""
        if self._item is not None and hasattr(self._item, 'item_type'):
            self._item.item_type = new_type
            self._item.update()

    def _on_edit(self, value):
        """Handle property value changes"""
        if self._disable_update or self._item is None:
            return

        # Update position
        rect = self._item.rect()
        old_scene_x = self._item.pos().x() + rect.x()
        old_scene_y = self._item.pos().y() + rect.y()
        new_scene_x = self.x_spin.value()
        new_scene_y = self.y_spin.value()

        # If the top-left coordinate changes, move object or rect accordingly
        delta_x = new_scene_x - old_scene_x
        delta_y = new_scene_y - old_scene_y
        if delta_x != 0 or delta_y != 0:
            self._item.setPos(self._item.pos() + QPointF(delta_x, delta_y))

        # Update ammo count
        self._item.ammo = self.ammo_spin.value()
        self._item.stay = self.stay_spin.isChecked()

        # Update item appearance
        self._item.update()

    def set_item(self, item):
        """Set the item to be edited"""
        # Disconnect previous signal if needed
        if hasattr(self, "_item") and self._item is not None and self._item != item:
            try:
                self._item.signals.itemChanged.disconnect(self.set_item)
            except Exception:
                pass

        # Even if it's the same item, disconnect before reconnecting to avoid stacking connections
        try:
            item.signals.itemChanged.disconnect(self.set_item)
        except Exception:
            pass

        self._item = item
        item.signals.itemChanged.connect(self.set_item)

        self._disable_update = True
        rect = item.rect()

        # Set type
        idx = self.type_combo.findText(getattr(item, "item_type", "plasma"))
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        else:
            self.type_combo.setCurrentIndex(0)

        # Set ammo
        self.ammo_spin.setValue(getattr(item, "ammo", 10))

        # Set stay flag
        self.stay_spin.setChecked(getattr(item, "stay", False))

        # Set position and size
        scene_x = item.pos().x() + rect.x()
        scene_y = item.pos().y() + rect.y()
        self.x_spin.setValue(scene_x)
        self.y_spin.setValue(scene_y)

        self._disable_update = False