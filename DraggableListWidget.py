import os
import shutil
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QMenu, QAbstractItemView, QMessageBox
from PyQt5.QtGui import QDrag, QPixmap, QIcon
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QUrl

class DraggableListWidget(QListWidget):
    setSkyRequested = pyqtSignal(str)
    setOverlayRequested = pyqtSignal(str)
    textureAdded = pyqtSignal()
    textureRemoveRequested = pyqtSignal(str)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragEnabled(True)  # Enable dragging from this widget
        self.setAcceptDrops(True)  # Enable dropping onto this widget
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self._textures_folder = None  # Will be set by TexturesPanel
        
    # Property for textures_folder
    @property
    def textures_folder(self):
        return self._textures_folder
        
    @textures_folder.setter
    def textures_folder(self, value):
        self._textures_folder = value

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item:
            mime = QMimeData()
            mime.setText(item.data(Qt.UserRole))
            drag = QDrag(self)
            drag.setMimeData(mime)
            drag.exec_(Qt.CopyAction)
    
    def _get_textures_folder(self):
        """Helper method to get the textures folder from parent or self"""
        from TexturesPanel import TexturesPanel
        parent = self.parent()
        textures_folder = None
        
        # Try to get textures_folder from parent
        if isinstance(parent, TexturesPanel):
            textures_folder = parent.textures_folder
        else:
            # Fallback to our own textures_folder
            textures_folder = self._textures_folder
            
        return textures_folder
    
    def dragEnterEvent(self, event):
        # Accept drag events that contain URLs (files) and we have a valid textures_folder
        textures_folder = self._get_textures_folder()
        if event.mimeData().hasUrls() and textures_folder:
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
    
    def dragMoveEvent(self, event):
        textures_folder = self._get_textures_folder()
        if event.mimeData().hasUrls() and textures_folder:
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)
    
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            # Get the textures folder using our helper method
            textures_folder = self._get_textures_folder()
                
            # Check if we have a valid textures folder
            if not textures_folder:
                event.ignore()
                return
                
            # Always accept drops as we now have a temporary folder if no project is saved
            event.setDropAction(Qt.CopyAction)
            event.accept()
            
            # Create textures folder if it doesn't exist
            os.makedirs(textures_folder, exist_ok=True)
            
            # Process the dropped files
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path) and file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                    # Copy the file to the textures folder
                    dest_path = os.path.join(textures_folder, os.path.basename(file_path))
                    shutil.copy2(file_path, dest_path)
                    
                    # Add the new texture to the list
                    pixmap = QPixmap(dest_path)
                    if not pixmap.isNull():
                        thumb = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        item = QListWidgetItem(QIcon(thumb), os.path.basename(dest_path))
                        item.setData(Qt.UserRole, dest_path)
                        self.addItem(item)
            
            # Signal that textures have been added
            self.textureAdded.emit()
        else:
            super().dropEvent(event)
            
    def showContextMenu(self, position):
        item = self.itemAt(position)
        if item:
            menu = QMenu()
            set_sky_action = menu.addAction("Use as Sky")
            set_overlay_action = menu.addAction("Use as Overlay")
            remove_texture_action = menu.addAction("Delete Texture")
            action = menu.exec_(self.mapToGlobal(position))
            
            texture_path = item.data(Qt.UserRole)
            
            if action == set_sky_action:
                self.setSkyRequested.emit(texture_path)
            elif action == set_overlay_action:
                self.setOverlayRequested.emit(texture_path)
            elif action == remove_texture_action:
                self.textureRemoveRequested.emit(texture_path)