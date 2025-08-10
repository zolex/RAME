import os
import shutil
from PyQt5.QtWidgets import QFileDialog, QWidget, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem, QMessageBox
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize, QSettings, pyqtSignal
from DraggableListWidget import DraggableListWidget


class TexturesPanel(QWidget):
    setSkyRequested = pyqtSignal(str)
    setOverlayRequested = pyqtSignal(str)
    textureRemoveRequested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("Racesow", "MapDesigner/TexturesPanel")
        layout = QVBoxLayout(self)

        self.add_texture_btn = QPushButton("Add")

        self.list_widget = DraggableListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(64, 64))
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setDragEnabled(True)  # Enable dragging
        
        # Connect the setSkyRequested signal from the list widget to our own signal
        self.list_widget.setSkyRequested.connect(self.setSkyRequested.emit)

        # Connect the setOverlayRequested signal from the list widget to our own signal
        self.list_widget.setOverlayRequested.connect(self.setOverlayRequested.emit)
        
        # Connect the textureRemoveRequested signal from the list widget to our own signal
        self.list_widget.textureRemoveRequested.connect(self.textureRemoveRequested.emit)
        
        # Connect the textureAdded signal to reload the textures folder
        self.list_widget.textureAdded.connect(self.load_textures_folder)
        
        layout.addWidget(self.list_widget)
        layout.addWidget(self.add_texture_btn)
        self.add_texture_btn.clicked.connect(self.add_texture)
        
        # Default textures folder (will be updated when project is loaded/saved)
        self.textures_folder = None
        self.project_saved = False
        
        # Disable add button initially since no project is saved
        self.add_texture_btn.setEnabled(False)

    def set_textures_folder(self, folder_path, project_saved=True):
        """Set the textures folder path and update UI state"""
        self.textures_folder = folder_path
        self.project_saved = project_saved
        
        # Always enable the Add Texture button if we have a valid folder
        # (either temporary or project folder)
        self.add_texture_btn.setEnabled(folder_path is not None)
        
        # Update the textures folder in the list widget
        if self.list_widget:
            # Update the textures_folder property
            self.list_widget.textures_folder = folder_path
            
            # Always enable drag and drop
            self.list_widget.setAcceptDrops(True)
        
        # Load textures from the folder
        self.load_textures_folder()
    
    def load_textures_folder(self):
        """Load all textures from the textures folder"""
        self.list_widget.clear()
        
        if not self.textures_folder or not os.path.isdir(self.textures_folder):
            return
            
        for file in os.listdir(self.textures_folder):
            if file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                path = os.path.join(self.textures_folder, file)
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    thumb = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    item = QListWidgetItem(QIcon(thumb), os.path.basename(path))
                    item.setData(Qt.UserRole, path)
                    self.list_widget.addItem(item)
    
    def add_texture(self):
        """Open file dialog to select and add textures to the textures folder"""
        # Only allow adding textures if textures folder exists
        if not self.textures_folder:
            return
            
        last_folder = self.settings.value("textures/last_folder", "")
        files, _ = QFileDialog.getOpenFileNames(
            self, 
            "Select Texture Files", 
            last_folder, 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if files:
            # Save the last folder used
            self.settings.setValue("textures/last_folder", os.path.dirname(files[0]))
            
            # Create textures folder if it doesn't exist
            os.makedirs(self.textures_folder, exist_ok=True)
            
            # Copy selected files to textures folder
            for file_path in files:
                if os.path.exists(file_path):
                    dest_path = os.path.join(self.textures_folder, os.path.basename(file_path))
                    shutil.copy2(file_path, dest_path)
            
            # Reload the textures folder to show the new files
            self.load_textures_folder()

