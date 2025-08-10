from PyQt5.QtCore import Qt, QPoint, QRectF, QEvent
from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtGui import QPixmap, QBrush

class GraphicsView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._panning = False
        self._pan_start_pos = QPoint()

        self._sky_image_path = None
        self._sky_pixmap = None
        self._has_sky = False

        self._overlay_image_path = None
        self._overlay_pixmap = None
        self._has_overlay = False
        
        # Install event filter on scrollbars to handle sky updates
        self.horizontalScrollBar().installEventFilter(self)
        self.verticalScrollBar().installEventFilter(self)
        
        # Connect directly to scrollbar valueChanged signals
        self.horizontalScrollBar().valueChanged.connect(self._on_scrollbar_value_changed)
        self.verticalScrollBar().valueChanged.connect(self._on_scrollbar_value_changed)
        
    def keyPressEvent(self, event):
        # Check for Ctrl+A
        if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_A:
            if self.scene():
                for item in self.scene().items():
                    item.setSelected(True)
            event.accept()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.AltModifier:
            delta = event.angleDelta().x()
            factor = 1.15
            if delta > 0:
                self.scale(factor, factor)
            elif delta < 0:
                self.scale(1 / factor, 1 / factor)
            # Force viewport update to refresh the fixed background after zooming
            if self._has_sky:
                self.viewport().update()
            event.accept()
        else:
            super().wheelEvent(event)
            # Also update after standard wheel events (scrolling)
            if self._has_sky:
                self.viewport().update()
            
    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event):
        if self._panning:
            # Calculate how far to scroll based on mouse movement
            delta = event.pos() - self._pan_start_pos
            self._pan_start_pos = event.pos()
            
            # Scroll the view
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
                
            # Check if we need to extend the scene rect
            self._extend_scene_if_needed()
            
            # Force viewport update to refresh the fixed background
            self.viewport().update()
            
            event.accept()
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            # Check if we can reduce the scene size when panning stops
            self._reduce_scene_if_possible()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
            
    def _extend_scene_if_needed(self):
        """Extend the scene rect if the view is near the edge"""
        if not self.scene():
            return
            
        # Get current scene rect
        scene_rect = self.scene().sceneRect()
        
        # Get the visible area in scene coordinates
        visible_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        
        # Calculate margin (10% of the visible area)
        margin_x = visible_rect.width() * 0.1
        margin_y = visible_rect.height() * 0.1
        
        # Check if we need to extend in any direction
        new_rect = QRectF(scene_rect)
        
        # Check left edge
        if visible_rect.left() < scene_rect.left() + margin_x:
            new_rect.setLeft(visible_rect.left() - margin_x)
            
        # Check right edge
        if visible_rect.right() > scene_rect.right() - margin_x:
            new_rect.setRight(visible_rect.right() + margin_x)
            
        # Check top edge
        if visible_rect.top() < scene_rect.top() + margin_y:
            new_rect.setTop(visible_rect.top() - margin_y)
            
        # Check bottom edge
        if visible_rect.bottom() > scene_rect.bottom() - margin_y:
            new_rect.setBottom(visible_rect.bottom() + margin_y)
            
        # Update scene rect if it changed
        if new_rect != scene_rect:
            self.scene().setSceneRect(new_rect)
            
    def _reduce_scene_if_possible(self):
        """Reduce the scene rect if there are empty areas with no items"""
        if not self.scene():
            return
            
        # Get current scene rect
        scene_rect = self.scene().sceneRect()
        
        # Get the visible area in scene coordinates
        visible_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        
        # Get the bounding rect of all items in the scene
        items_rect = self._get_items_bounding_rect()
        
        # If there are no items, use a default minimum size
        if items_rect.isEmpty():
            # Use the initial scene size (1024x768) as the minimum
            min_rect = QRectF(0, 0, 1024, 768)
            
            # Make sure the visible area is included
            min_rect = min_rect.united(visible_rect)
            
            # Update scene rect if it's different
            if min_rect != scene_rect:
                self.scene().setSceneRect(min_rect)
            return
            
        # Add some margin around the items (same as in extend)
        margin_x = visible_rect.width() * 0.1
        margin_y = visible_rect.height() * 0.1
        
        # Create a rect that includes all items plus margin
        items_rect.adjust(-margin_x, -margin_y, margin_x, margin_y)
        
        # Make sure the visible area is included
        new_rect = items_rect.united(visible_rect)
        
        # Ensure we don't go smaller than the initial scene size (1024x768)
        min_rect = QRectF(0, 0, 1024, 768)
        new_rect = new_rect.united(min_rect)
        
        # Update scene rect if it's different
        if new_rect != scene_rect:
            self.scene().setSceneRect(new_rect)
            
    def _get_items_bounding_rect(self):
        """Get the bounding rectangle of all items in the scene"""
        if not self.scene() or not self.scene().items():
            return QRectF()
            
        # Start with the first item's bounding rect
        result = self.scene().items()[0].sceneBoundingRect()
        
        # Union with all other items
        for item in self.scene().items()[1:]:
            result = result.united(item.sceneBoundingRect())
            
        return result
        
    def set_sky_image(self, image_path=None):
        """Set a fixed sky image that doesn't move when scrolling or zooming"""
        if image_path:
            self._sky_pixmap = QPixmap(image_path)
            self._sky_image_path = image_path  # Store the original file path
            self._has_sky = True
        else:
            self._sky_pixmap = None
            self._sky_image_path = None
            self._has_sky = False
        self.viewport().update()

    def set_overlay_image(self, image_path=None):
        """Set a fixed background image that doesn't move when scrolling or zooming"""
        if image_path:
            self._overlay_pixmap = QPixmap(image_path)
            self._overlay_image_path = image_path  # Store the original file path
            self._has_overlay = True
        else:
            self._overlay_pixmap = None
            self._overlay_image_path = None
            self._has_overlay = False
        self.viewport().update()
        
    def resizeEvent(self, event):
        """Handle resize events to ensure the sky stays fixed"""
        super().resizeEvent(event)
        # Force viewport update when the view is resized
        if self._has_sky:
            self.viewport().update()
            
    def eventFilter(self, obj, event):
        """Filter events for scrollbars to update the sky when scrolling"""
        if (obj == self.horizontalScrollBar() or obj == self.verticalScrollBar()):
            # Capture all relevant scrollbar events
            if event.type() in (QEvent.Scroll, QEvent.Move, QEvent.Resize, QEvent.UpdateRequest, QEvent.Show, QEvent.Paint):
                # Force viewport update when scrollbar values change
                if self._has_sky:
                    self.viewport().update()
        return super().eventFilter(obj, event)
        
    def _on_scrollbar_value_changed(self, value):
        """Handle scrollbar value changes directly from the valueChanged signal"""
        if self._has_sky:
            # Force a complete viewport update to redraw the fixed background
            self.viewport().update()
        
    def drawBackground(self, painter, rect):
        """Override to draw the fixed background image"""
        # If we have a sky image, draw it first (behind everything)
        if self._has_sky and self._sky_pixmap and not self._sky_pixmap.isNull():
            # Draw the image as a fixed background that doesn't move with scrolling
            painter.save()
            # Reset the transformation to draw in viewport coordinates
            painter.resetTransform()

            # Get viewport dimensions
            viewport_rect = self.viewport().rect()

            # Calculate scaled size that fits width while maintaining aspect ratio
            pixmap_size = self._sky_pixmap.size()
            scaled_width = viewport_rect.width()
            scaled_height = (pixmap_size.height() * scaled_width) / pixmap_size.width()

            # Calculate position to center vertically
            x = 0
            y = (viewport_rect.height() - scaled_height) / 2 if scaled_height < viewport_rect.height() else 0

            # Draw the scaled pixmap
            painter.drawPixmap(int(x), int(y), int(scaled_width), int(scaled_height), self._sky_pixmap)
            painter.restore()

            # If we have an overlay image, draw it over the sky
            if self._has_overlay and self._overlay_pixmap and not self._overlay_pixmap.isNull():
                painter.save()
                painter.drawPixmap(0, 0, self._overlay_pixmap)
                painter.restore()
            
        # Then call the parent implementation to draw the default background (grid)
        super().drawBackground(painter, rect)


