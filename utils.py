from PyQt5.QtCore import QPointF
from config import GRID_SIZE
import os

def snap_value(value, grid_size):
    return round(value / grid_size) * grid_size


# Helper to snap a point to grid
def snap(pt):
    return QPointF(
        round(pt.x() / GRID_SIZE) * GRID_SIZE,
        round(pt.y() / GRID_SIZE) * GRID_SIZE
    )

def resolve_texture_path(texture, map_file_path):
    # map_file_path: full path to YAML file being loaded
    if not texture:
        return None
    # Absolute path? Keep as is
    if os.path.isabs(texture):
        return texture
    # Otherwise, relative path: join with yaml directory
    return os.path.normpath(os.path.join(os.path.dirname(map_file_path), texture))
