from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QFormLayout, QLabel, QDoubleSpinBox, QHBoxLayout, QLineEdit, QPushButton, \
    QFileDialog, QComboBox, QVBoxLayout


class RectPropertiesPanel(QWidget):
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

        self._rect_item = None  # Track the current edited item
        self._disable_update = False  # Prevent recursion

        #self.type_label = QLabel("")
        #self.layout.addRow("Type:", self.type_label)

        self.stype_combo = QComboBox()
        self.stype_combo.addItems(["static", "wall", "deco", "death"])
        self.stype_combo.currentTextChanged.connect(self._on_stype_changed)
        self.layout.addRow("Type:", self.stype_combo)


        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-1000000000, 1000000000)
        self.x_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("X:", self.x_spin)

        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-1000000000, 1000000000)
        self.y_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("Y:", self.y_spin)

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0, 1000000000)
        self.width_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("Width:", self.width_spin)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(0, 100000000)
        self.height_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("Height:", self.height_spin)

        # --- Texture file row ---
        texture_row_layout = QHBoxLayout()
        self.texture_edit = QLineEdit()
        self.texture_edit.setReadOnly(True)
        texture_row_layout.addWidget(self.texture_edit)
        self.texture_button = QPushButton("...")
        self.texture_button.setFixedWidth(30)
        self.texture_button.clicked.connect(self._choose_texture)
        texture_row_layout.addWidget(self.texture_button)
        self.layout.addRow("Texture:", texture_row_layout)


        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setDecimals(4)
        self.scale_spin.setRange(0.01, 10)
        self.scale_spin.setSingleStep(0.1)
        self.scale_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("Texture Scale:", self.scale_spin)

        self.rotation_spin = QDoubleSpinBox()
        self.rotation_spin.setDecimals(4)
        self.rotation_spin.setRange(-360, 360)
        self.rotation_spin.setSingleStep(0.1)
        self.rotation_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("Texture Rotation:", self.rotation_spin)

        self.offset_x_spin = QDoubleSpinBox()
        self.offset_x_spin.setRange(-10000, 10000)
        self.offset_x_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("Texture X Offset:", self.offset_x_spin)

        self.offset_y_spin = QDoubleSpinBox()
        self.offset_y_spin.setRange(-10000, 10000)
        self.offset_y_spin.valueChanged.connect(self._on_edit)
        self.layout.addRow("Texture Y Offset:", self.offset_y_spin)

    def _choose_texture(self):
        if not self._rect_item:
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Select Texture", "", "Image Files (*.png *.jpg *.bmp)")
        if filename:
            self._rect_item.texture_path = filename
            from PyQt5.QtGui import QPixmap
            self._rect_item.texture_pixmap = QPixmap(filename)
            self.texture_edit.setText(filename)
            self._rect_item.update()

    def _on_edit(self, value):
        if self._disable_update or self._rect_item is None:
            return

        rect = self._rect_item.rect()
        old_scene_x = self._rect_item.pos().x() + rect.x()
        old_scene_y = self._rect_item.pos().y() + rect.y()
        new_scene_x = self.x_spin.value()
        new_scene_y = self.y_spin.value()
        new_w = self.width_spin.value()
        new_h = self.height_spin.value()

        # If the top-left coordinate changes, move object or rect accordingly
        delta_x = new_scene_x - old_scene_x
        delta_y = new_scene_y - old_scene_y
        if delta_x != 0 or delta_y != 0:
            self._rect_item.setPos(self._rect_item.pos() + QPointF(delta_x, delta_y))

        # Update rect size if needed (anchor stays at top-left in scene coords)
        if (rect.width(), rect.height()) != (new_w, new_h):
            self._rect_item.setRect(rect.x(), rect.y(), new_w, new_h)

        self._rect_item.texture_scale = self.scale_spin.value()
        self._rect_item.texture_rotation = self.rotation_spin.value()
        self._rect_item.texture_offset_x = self.offset_x_spin.value()
        self._rect_item.texture_offset_y = self.offset_y_spin.value()

        self._on_stype_changed(self.stype_combo.currentText())

        self._rect_item.update()

    def _on_stype_changed(self, new_stype):
        if self._rect_item is not None and hasattr(self._rect_item, 'stype'):
            self._rect_item.stype = new_stype
            color_map = {
                "static": QColor("#ADD8E6"),
                "wall": QColor("#E20074"),
                "deco": QColor("#00ff00"),
                "death": QColor("#FF0000"),
            }
            brush_color = color_map.get(new_stype)
            self._rect_item.setBrush(brush_color)
            self._rect_item.update()

    def set_rect(self, rect_item):
        # Disconnect previous signal if needed
        if hasattr(self, "_rect_item") and self._rect_item is not None and self._rect_item != rect_item:
            try:
                self._rect_item.signals.rectChanged.disconnect(self.set_rect)
            except Exception:
                pass

        # Even if it's the same item, disconnect before reconnecting to avoid stacking connections
        try:
            rect_item.signals.rectChanged.disconnect(self.set_rect)
        except Exception:
            pass

        self._rect_item = rect_item
        rect_item.signals.rectChanged.connect(self.set_rect)

        self._disable_update = True
        rect = rect_item.rect()

        idx = self.stype_combo.findText(getattr(rect_item, "stype", "static"))
        if idx >= 0:
            self.stype_combo.setCurrentIndex(idx)
        else:
            self.stype_combo.setCurrentIndex(0)

        # Calculate the visible top-left corner position in the scene
        scene_x = rect_item.pos().x() + rect.x()
        scene_y = rect_item.pos().y() + rect.y()
        self.x_spin.setValue(scene_x)
        self.y_spin.setValue(scene_y)
        self.width_spin.setValue(rect.width())
        self.height_spin.setValue(rect.height())
        self.scale_spin.setValue(getattr(rect_item, 'texture_scale', 1.0))
        self.rotation_spin.setValue(getattr(rect_item, 'texture_rotation', 0.0))
        self.offset_x_spin.setValue(getattr(rect_item, 'texture_offset_x', 0.0))
        self.offset_y_spin.setValue(getattr(rect_item, 'texture_offset_y', 0.0))
        # Set texture field
        self.texture_edit.setText(getattr(rect_item, "texture_path", "") or "")

        self._on_stype_changed(self.stype_combo.currentText())


        self._disable_update = False



