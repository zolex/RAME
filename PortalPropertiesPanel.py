from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QWidget, QFormLayout, QDoubleSpinBox, QComboBox, QVBoxLayout, QSpinBox

class PortalPropertiesPanel(QWidget):
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

        self._portal = None  # Track the current edited item
        self._disable_update = False  # Prevent recursion

        # Item type selection
        self.type_combo = QComboBox()
        self.type_combo.addItems(["entry", "exit"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.layout.addRow("Type:", self.type_combo)

        # Ammo count
        self.id_spin = QSpinBox()
        self.id_spin.setRange(0, 1000)
        self.id_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("ID:", self.id_spin)

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
        if self._portal is not None and hasattr(self._portal, 'item_type'):
            self._portal.item_type = new_type
            self._portal.update()

    def _on_edit(self, value):
        """Handle property value changes"""
        if self._disable_update or self._portal is None:
            return

        # Update position
        rect = self._portal.rect()
        old_scene_x = self._portal.pos().x() + rect.x()
        old_scene_y = self._portal.pos().y() + rect.y()
        new_scene_x = self.x_spin.value()
        new_scene_y = self.y_spin.value()

        # If the top-left coordinate changes, move object or rect accordingly
        delta_x = new_scene_x - old_scene_x
        delta_y = new_scene_y - old_scene_y
        if delta_x != 0 or delta_y != 0:
            self._portal.setPos(self._portal.pos() + QPointF(delta_x, delta_y))

        # Update ammo count
        self._portal.ID = self.id_spin.value()

        # Update item appearance
        self._portal.update()

    def set_portal(self, portal):
        """Set the item to be edited"""
        # Disconnect previous signal if needed
        if hasattr(self, "_portal") and self._portal is not None and self._portal != portal:
            try:
                self._portal.signals.portalChanged.disconnect(self.set_portal)
            except Exception:
                pass

        # Even if it's the same item, disconnect before reconnecting to avoid stacking connections
        try:
            portal.signals.portalChanged.disconnect(self.set_portal)
        except Exception:
            pass

        self._portal = portal
        portal.signals.portalChanged.connect(self.set_portal)

        self._disable_update = True
        rect = portal.rect()

        # Set type
        idx = self.type_combo.findText(getattr(portal, "item_type", "entry"))
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        else:
            self.type_combo.setCurrentIndex(0)

        # Set ammo
        self.id_spin.setValue(getattr(portal, "ID", 0))

        # Set position and size
        scene_x = portal.pos().x() + rect.x()
        scene_y = portal.pos().y() + rect.y()
        self.x_spin.setValue(scene_x)
        self.y_spin.setValue(scene_y)

        self._disable_update = False