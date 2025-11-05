"""Interactive image measurement tool with scaling and path tracing."""

import math
from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import QEvent, QPointF, Qt
from PyQt5.QtGui import QBrush, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QFileDialog,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QInputDialog,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ZoomableGraphicsView(QGraphicsView):
    """Graphics view with zoom and pan controls similar to image editors."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 0
        self._space_pressed = False
        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHint(QPainter.Antialiasing, True)

    def wheelEvent(self, event):
        if event.angleDelta().y() == 0:
            return
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
            self._zoom += 1
        else:
            zoom_factor = zoom_out_factor
            self._zoom -= 1
        if self._zoom < -20:
            self._zoom = -20
            return
        if self._zoom > 50:
            self._zoom = 50
            return
        self.scale(zoom_factor, zoom_factor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not self._space_pressed:
            self._space_pressed = True
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space:
            self._space_pressed = False
            self.setDragMode(QGraphicsView.NoDrag)
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        if self._space_pressed and event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._space_pressed and event.button() == Qt.LeftButton:
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def is_panning_active(self) -> bool:
        """Return True while the user holds space to pan the view."""
        return self._space_pressed


class MeasurementScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.background_item = None

    def load_image(self, image_path: Path):
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            raise ValueError("Failed to load image.")
        if self.background_item:
            self.removeItem(self.background_item)
        self.clear()
        self.background_item = self.addPixmap(pixmap)
        self.setSceneRect(self.background_item.boundingRect())


class MeasurementWindow(QMainWindow):
    SCALE_POINT_COLOR = Qt.red
    PATH_COLOR = Qt.green

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Distance Measurement Tool")
        self.resize(1200, 800)

        self.scene = MeasurementScene(self)
        self.view = ZoomableGraphicsView(self)
        self.view.setScene(self.scene)
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        self.status_label = QLabel("Load an image to get started.")
        self.total_label = QLabel("Distance: 0")

        self.scale_button = QPushButton("Set Scale")
        self.scale_button.clicked.connect(self.start_scale_selection)
        self.trace_button = QPushButton("Trace Path")
        self.trace_button.clicked.connect(self.start_path_tracing)
        self.clear_button = QPushButton("Clear Path")
        self.clear_button.clicked.connect(self.clear_path)
        self.unit_button = QPushButton("Set Units")
        self.unit_button.clicked.connect(self.set_units)

        controls_text = (
            "Controls:\n"
            "- Mouse Wheel: Zoom\n"
            "- Space + Drag: Pan\n"
            "- Left Click: Select points (depends on active mode)\n"
            "- Right Click: Remove a traced point\n"
            "- Esc: Cancel current mode\n"
            "- 'Set Units' button: Choose the unit label for measurements\n"
        )
        self.control_overview = QTextEdit()
        self.control_overview.setReadOnly(True)
        self.control_overview.setText(controls_text)
        self.control_overview.setMaximumHeight(120)

        button_row = QHBoxLayout()
        button_row.addWidget(self.scale_button)
        button_row.addWidget(self.trace_button)
        button_row.addWidget(self.clear_button)
        button_row.addWidget(self.unit_button)
        button_row.addStretch()
        button_row.addWidget(self.total_label)

        layout = QVBoxLayout()
        layout.addLayout(button_row)
        layout.addWidget(self.view)
        layout.addWidget(self.control_overview)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.statusBar().addWidget(self.status_label, 1)

        open_action = QAction("Open Image", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_image)
        self.menuBar().addMenu("File").addAction(open_action)

        self.mode = "idle"
        self.scale_points: List[QPointF] = []
        self.scale_markers: List[QGraphicsEllipseItem] = []
        self.scale_line: Optional[QGraphicsLineItem] = None
        self.path_points: List[QPointF] = []
        self.path_markers: List[QGraphicsEllipseItem] = []
        self.path_item: Optional[QGraphicsPathItem] = None
        self.units_per_pixel: Optional[float] = None
        self.unit_name: str = "units"

        self.view.viewport().installEventFilter(self)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.mode != "idle":
            self.cancel_mode()
            event.accept()
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        if obj is self.view.viewport():
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                if self.view.is_panning_active():
                    return False
                scene_pos = self.view.mapToScene(event.pos())
                if self.mode == "scale_first":
                    self.handle_scale_first_click(scene_pos)
                    return True
                elif self.mode == "scale_second":
                    self.handle_scale_second_click(scene_pos)
                    return True
                elif self.mode == "trace":
                    self.handle_trace_click(scene_pos)
                    return True
            elif event.type() == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
                scene_pos = self.view.mapToScene(event.pos())
                if self.mode in {"scale_first", "scale_second"}:
                    self.cancel_mode()
                    return True
                if self.remove_path_point_at(scene_pos):
                    return True
            elif event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
                if self.mode != "idle":
                    self.cancel_mode()
                    return True
        return super().eventFilter(obj, event)

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select image", str(Path.home()), "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            try:
                self.scene.load_image(Path(path))
            except ValueError as exc:
                QMessageBox.critical(self, "Error", str(exc))
                return
            self.reset_measurements()
            self.status_label.setText("Image loaded. Set the scale to begin measuring.")

    def start_scale_selection(self):
        if not self.scene.background_item:
            QMessageBox.information(self, "No image", "Load an image before setting the scale.")
            return
        self.reset_scale_items()
        self.mode = "scale_first"
        self.status_label.setText("Click the first point for the scale reference.")

    def handle_scale_first_click(self, point: QPointF):
        marker = self.add_marker(point)
        self.scale_markers.append(marker)
        self.scale_points = [point]
        self.mode = "scale_second"
        self.status_label.setText("Click the second point for the scale reference.")

    def handle_scale_second_click(self, point: QPointF):
        marker = self.add_marker(point)
        self.scale_markers.append(marker)
        self.scale_points.append(point)
        if len(self.scale_points) == 2:
            distance_pixels = self.distance(self.scale_points[0], self.scale_points[1])
            if distance_pixels == 0:
                QMessageBox.warning(self, "Invalid scale", "Selected points are identical. Try again.")
                self.reset_scale_items()
                self.mode = "scale_first"
                return
            value, ok = QInputDialog.getDouble(
                self,
                "Scale distance",
                "Enter the real-world distance between the two points (in your chosen units):",
                decimals=4,
                min=0.0001,
            )
            if ok and value > 0:
                self.units_per_pixel = value / distance_pixels
                self.draw_scale_line()
                self.mode = "idle"
                self.status_label.setText(
                    f"Scale set: {value:.4f} {self.unit_name} over {distance_pixels:.2f} pixels. Trace a path to measure."
                )
                self.update_distance_label()
            else:
                QMessageBox.information(self, "Scale cancelled", "Scale input was cancelled.")
                self.reset_scale_items()
                self.mode = "idle"

    def draw_scale_line(self):
        if self.scale_line:
            self.scene.removeItem(self.scale_line)
            self.scale_line = None
        if len(self.scale_points) == 2:
            line = QGraphicsLineItem(
                self.scale_points[0].x(),
                self.scale_points[0].y(),
                self.scale_points[1].x(),
                self.scale_points[1].y(),
            )
            pen = QPen(self.SCALE_POINT_COLOR, 2)
            line.setPen(pen)
            self.scale_line = line
            self.scene.addItem(line)

    def start_path_tracing(self):
        if not self.scene.background_item:
            QMessageBox.information(self, "No image", "Load an image before tracing a path.")
            return
        if self.units_per_pixel is None:
            reply = QMessageBox.question(
                self,
                "No scale set",
                "No scale has been defined. Distances will be in pixels. Continue?",
            )
            if reply != QMessageBox.Yes:
                return
        self.mode = "trace"
        self.path_points = []
        self.remove_path_markers()
        self.remove_path_item()
        self.status_label.setText("Click to add points. Right-click a marker to remove it, or press Esc to cancel.")

    def handle_trace_click(self, point: QPointF):
        self.path_points.append(point)
        marker = self.add_path_marker(point)
        self.path_markers.append(marker)
        self.update_path_item()
        self.update_distance_label()

    def update_path_item(self):
        self.remove_path_item()
        if len(self.path_points) >= 2:
            path = QPainterPath(self.path_points[0])
            for pt in self.path_points[1:]:
                path.lineTo(pt)
            item = QGraphicsPathItem(path)
            pen = QPen(self.PATH_COLOR, 2)
            item.setPen(pen)
            item.setZValue(0)
            self.path_item = item
            self.scene.addItem(item)

    def update_distance_label(self):
        if len(self.path_points) < 2:
            if self.units_per_pixel is not None:
                self.total_label.setText(f"Distance: 0 {self.unit_name}")
            else:
                self.total_label.setText("Distance: 0 (pixels)")
            return
        total_pixels = 0.0
        for start, end in zip(self.path_points[:-1], self.path_points[1:]):
            total_pixels += self.distance(start, end)
        if self.units_per_pixel is not None:
            total_units = total_pixels * self.units_per_pixel
            self.total_label.setText(f"Distance: {total_units:.4f} {self.unit_name}")
        else:
            self.total_label.setText(f"Distance: {total_pixels:.2f} (pixels)")

    def clear_path(self):
        self.path_points = []
        self.remove_path_markers()
        self.remove_path_item()
        self.update_distance_label()
        self.status_label.setText("Path cleared. Trace again or set a new scale if desired.")

    def cancel_mode(self):
        if self.mode == "trace":
            self.mode = "idle"
            self.status_label.setText("Tracing cancelled.")
        elif self.mode in {"scale_first", "scale_second"}:
            self.reset_scale_items()
            self.mode = "idle"
            self.status_label.setText("Scale selection cancelled.")

    def reset_measurements(self):
        self.units_per_pixel = None
        self.reset_scale_items()
        self.clear_path()

    def reset_scale_items(self):
        for marker in self.scale_markers:
            self.scene.removeItem(marker)
        self.scale_markers = []
        if self.scale_line:
            self.scene.removeItem(self.scale_line)
            self.scale_line = None
        self.scale_points = []

    def remove_path_item(self):
        if self.path_item:
            self.scene.removeItem(self.path_item)
            self.path_item = None

    def remove_path_markers(self):
        for marker in self.path_markers:
            self.scene.removeItem(marker)
        self.path_markers = []

    def add_marker(self, point: QPointF) -> QGraphicsEllipseItem:
        radius = 5
        ellipse = QGraphicsEllipseItem(point.x() - radius, point.y() - radius, radius * 2, radius * 2)
        ellipse.setBrush(QBrush(self.SCALE_POINT_COLOR))
        ellipse.setPen(QPen(Qt.black))
        ellipse.setZValue(2)
        self.scene.addItem(ellipse)
        return ellipse

    def add_path_marker(self, point: QPointF) -> QGraphicsEllipseItem:
        radius = 4
        ellipse = QGraphicsEllipseItem(point.x() - radius, point.y() - radius, radius * 2, radius * 2)
        ellipse.setBrush(QBrush(self.PATH_COLOR))
        ellipse.setPen(QPen(Qt.black))
        ellipse.setZValue(1)
        self.scene.addItem(ellipse)
        return ellipse

    def remove_path_point_at(self, scene_pos: QPointF) -> bool:
        index = self.find_path_point_index(scene_pos)
        if index is None:
            return False
        marker = self.path_markers.pop(index)
        self.scene.removeItem(marker)
        self.path_points.pop(index)
        self.update_path_item()
        self.update_distance_label()
        self.status_label.setText("Trace point removed.")
        return True

    def find_path_point_index(self, scene_pos: QPointF) -> Optional[int]:
        for idx, marker in enumerate(self.path_markers):
            local_pos = marker.mapFromScene(scene_pos)
            if marker.contains(local_pos):
                return idx
        return None

    def set_units(self):
        text, ok = QInputDialog.getText(
            self,
            "Set measurement units",
            "Enter the unit label for measurements (e.g., meters, inches):",
            text=self.unit_name,
        )
        if not ok:
            return
        unit = text.strip() or "units"
        self.unit_name = unit
        self.status_label.setText(f"Measurement units set to '{self.unit_name}'.")
        self.update_distance_label()

    @staticmethod
    def distance(start: QPointF, end: QPointF) -> float:
        return math.hypot(start.x() - end.x(), start.y() - end.y())


def main():
    import sys

    app = QApplication(sys.argv)
    window = MeasurementWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
