from PyQt5.QtWidgets import QWidget, QFormLayout, QLabel, QDoubleSpinBox, QHBoxLayout, QLineEdit, QPushButton, QFileDialog, QComboBox, QVBoxLayout
from PyQt5.QtGui import QPixmap, QColor, QPolygonF
from PyQt5.QtCore import QPointF

class TrianglePropertiesPanel(QWidget):
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

        self._tri_item = None
        self._disable_update = False

        self.stype_combo = QComboBox()
        self.stype_combo.addItems(["ramp"])
        self.stype_combo.currentTextChanged.connect(self._on_stype_changed)
        self.layout.addRow("Type:", self.stype_combo)

        # Point spinboxes
        self.p1_x = QDoubleSpinBox(); self.p1_y = QDoubleSpinBox()
        self.p2_x = QDoubleSpinBox(); self.p2_y = QDoubleSpinBox()
        self.p3_x = QDoubleSpinBox(); self.p3_y = QDoubleSpinBox()
        for spin in [self.p1_x, self.p1_y, self.p2_x, self.p2_y, self.p3_x, self.p3_y]:
            spin.setRange(-100000, 100000)
            spin.valueChanged.connect(self._on_edit)

        self.layout.addRow("P1 X:", self.p1_x)
        self.layout.addRow("P1 Y:", self.p1_y)
        self.layout.addRow("P2 X:", self.p2_x)
        self.layout.addRow("P2 Y:", self.p2_y)
        self.layout.addRow("P3 X:", self.p3_x)
        self.layout.addRow("P3 Y:", self.p3_y)

        # Texture
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
        if not self._tri_item:
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Select Texture", "", "Image Files (*.png *.jpg *.bmp)")
        if filename:
            self._tri_item.texture_path = filename
            self._tri_item.texture_pixmap = QPixmap(filename)
            self.texture_edit.setText(filename)
            self._tri_item.update()

    def _on_stype_changed(self, new_stype):
        if self._tri_item is not None and hasattr(self._tri_item, 'stype'):
            self._tri_item.stype = new_stype
            color_map = {
                "ramp": QColor("#ADD8E6"),
            }
            brush_color = color_map.get(new_stype)
            self._tri_item.setBrush(brush_color)
            self._tri_item.update()

    def _on_edit(self, value):
        if self._disable_update or self._tri_item is None:
            return

        item_pos = self._tri_item.pos()

        # Convert scene coords from spinboxes to local coords relative to item's position
        p1 = QPointF(self.p1_x.value(), self.p1_y.value()) - item_pos
        p2 = QPointF(self.p2_x.value(), self.p2_y.value()) - item_pos
        p3 = QPointF(self.p3_x.value(), self.p3_y.value()) - item_pos

        self._tri_item.setPolygon(QPolygonF([p1, p2, p3]))
        self._tri_item.texture_scale = self.scale_spin.value()
        self._tri_item.texture_rotation = self.rotation_spin.value()
        self._tri_item.texture_offset_x = self.offset_x_spin.value()
        self._tri_item.texture_offset_y = self.offset_y_spin.value()
        self._on_stype_changed(self.stype_combo.currentText())
        self._tri_item.update()

    def set_triangle(self, tri_item):
        if self._tri_item and self._tri_item != tri_item:
            try:
                self._tri_item.signals.triChanged.disconnect(self.set_triangle)
            except Exception:
                pass

        try:
            tri_item.signals.triChanged.disconnect(self.set_triangle)
        except Exception:
            pass

        self._tri_item = tri_item
        tri_item.signals.triChanged.connect(self.set_triangle)

        self._disable_update = True

        polygon = tri_item.polygon()
        self.p1_x.setValue(polygon[0].x() + tri_item.pos().x())
        self.p1_y.setValue(polygon[0].y() + tri_item.pos().y())
        self.p2_x.setValue(polygon[1].x() + tri_item.pos().x())
        self.p2_y.setValue(polygon[1].y() + tri_item.pos().y())
        self.p3_x.setValue(polygon[2].x() + tri_item.pos().x())
        self.p3_y.setValue(polygon[2].y() + tri_item.pos().y())

        self.scale_spin.setValue(getattr(tri_item, 'texture_scale', 1.0))
        self.rotation_spin.setValue(getattr(tri_item, 'texture_rotation', 0.0))
        self.offset_x_spin.setValue(getattr(tri_item, 'texture_offset_x', 0.0))
        self.offset_y_spin.setValue(getattr(tri_item, 'texture_offset_y', 0.0))
        self.texture_edit.setText(getattr(tri_item, "texture_path", "") or "")

        idx = self.stype_combo.findText(getattr(tri_item, "stype", "static"))
        self.stype_combo.setCurrentIndex(idx if idx >= 0 else 0)

        self._on_stype_changed(self.stype_combo.currentText())
        self._disable_update = False
