from krita import DockWidget, Krita, DockWidgetFactory, DockWidgetFactoryBase
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, 
                             QPushButton, QSpinBox, QDoubleSpinBox, 
                             QLabel, QGroupBox, QColorDialog, QMessageBox,
                             QSlider, QHBoxLayout, QCheckBox, QDialog, 
                             QGraphicsView, QGraphicsScene, QGraphicsRectItem, 
                             QGraphicsPolygonItem, QGraphicsItem)
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QPen, QBrush, QPolygonF, QPainter

class DesignCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.setBackgroundBrush(QBrush(QColor("#202020")))
        self.setRenderHint(QPainter.Antialiasing)
        self.setAlignment(Qt.AlignCenter)
        
        self.current_tool = "select"
        self.temp_item = None
        self.poly_points = []
        
        self.history = []
        self.redo_stack = []
        
        self.page_width = 2480
        self.page_height = 3508
        self.margin_size = 100
        
        self.sheet_rect = None
        self.margin_rect = None

        self.refresh_guides()

    def refresh_guides(self):
        self.scene.clear()
        self.temp_item = None
        self.poly_points = []
        self.history = []
        self.redo_stack = []
        
        self.sheet_rect = self.scene.addRect(0, 0, self.page_width, self.page_height, QPen(Qt.NoPen), QBrush(QColor("white")))
        self.sheet_rect.setZValue(-10)
        
        m = self.margin_size
        if m < self.page_width/2 and m < self.page_height/2:
            self.margin_rect = self.scene.addRect(m, m, self.page_width - (m*2), self.page_height - (m*2), QPen(QColor("#00FF00"), 4, Qt.DashLine))
            self.margin_rect.setZValue(-5)

        self.scene.setSceneRect(-100, -100, self.page_width + 200, self.page_height + 200)
        self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def set_tool(self, tool_name):
        self.current_tool = tool_name
        self.poly_points = []
        if self.temp_item:
            self.scene.removeItem(self.temp_item)
            self.temp_item = None
            
        if tool_name == "select":
            self.setDragMode(QGraphicsView.RubberBandDrag)
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(Qt.CrossCursor)

    def undo_action(self):
        if not self.history:
            return
        item = self.history.pop()
        self.scene.removeItem(item)
        self.redo_stack.append(item)

    def redo_action(self):
        if not self.redo_stack:
            return
        item = self.redo_stack.pop()
        self.scene.addItem(item)
        self.history.append(item)

    def push_to_history(self, item):
        self.history.append(item)
        self.redo_stack.clear()

    def mousePressEvent(self, event):
        if self.current_tool == "select":
            super().mousePressEvent(event)
            return
            
        scene_pos = self.mapToScene(event.pos())
        
        if self.current_tool in ["rect", "square"]:
            self.start_pos = scene_pos
            self.temp_item = QGraphicsRectItem(QRectF(scene_pos, scene_pos))
            self.temp_item.setPen(QPen(QColor("blue"), 4))
            self.temp_item.setBrush(QBrush(QColor(0, 0, 255, 50)))
            self.scene.addItem(self.temp_item)
            
        elif self.current_tool == "poly":
            self.poly_points.append(scene_pos)
            if not self.temp_item:
                self.temp_item = QGraphicsPolygonItem(QPolygonF(self.poly_points))
                self.temp_item.setPen(QPen(QColor("red"), 4))
                self.temp_item.setBrush(QBrush(QColor(255, 0, 0, 50)))
                self.scene.addItem(self.temp_item)
            else:
                self.temp_item.setPolygon(QPolygonF(self.poly_points))

    def mouseMoveEvent(self, event):
        if self.current_tool == "select":
            super().mouseMoveEvent(event)
            return

        current_pos = self.mapToScene(event.pos())

        if self.current_tool == "rect" and self.temp_item:
            rect = QRectF(self.start_pos, current_pos).normalized()
            self.temp_item.setRect(rect)
            
        elif self.current_tool == "square" and self.temp_item:
            dx = current_pos.x() - self.start_pos.x()
            dy = current_pos.y() - self.start_pos.y()
            size = max(abs(dx), abs(dy))
            
            sx = 1 if dx >= 0 else -1
            sy = 1 if dy >= 0 else -1
            
            new_pos = QPointF(self.start_pos.x() + (size * sx), self.start_pos.y() + (size * sy))
            rect = QRectF(self.start_pos, new_pos).normalized()
            self.temp_item.setRect(rect)
            
        elif self.current_tool == "poly" and self.temp_item:
            temp_points = self.poly_points[:]
            temp_points.append(current_pos)
            self.temp_item.setPolygon(QPolygonF(temp_points))

    def mouseReleaseEvent(self, event):
        if self.current_tool == "select":
            super().mouseReleaseEvent(event)
            return

        if self.current_tool in ["rect", "square"] and self.temp_item:
            final_rect = self.temp_item.rect()
            self.scene.removeItem(self.temp_item)
            self.temp_item = None
            
            if final_rect.width() > 10 and final_rect.height() > 10:
                item = self.scene.addRect(final_rect, QPen(QColor("black"), 5), QBrush(QColor(255, 255, 255, 200)))
                item.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
                self.push_to_history(item)
            
    def mouseDoubleClickEvent(self, event):
        if self.current_tool == "poly" and len(self.poly_points) > 2:
            self.scene.removeItem(self.temp_item)
            self.temp_item = None
            
            final_poly = QPolygonF(self.poly_points)
            item = self.scene.addPolygon(final_poly, QPen(QColor("black"), 5), QBrush(QColor(255, 255, 255, 200)))
            item.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
            self.push_to_history(item)
            
            self.poly_points = []

    def resizeEvent(self, event):
        if self.scene:
            self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        super().resizeEvent(event)

class FreeModeDialog(QDialog):
    def __init__(self, parent=None, thickness=8, border_col="#000000", fill_col="#ffffff", bg_col="#ffffff"):
        super().__init__(parent)
        self.setWindowTitle("Free Mode Editor")
        self.resize(1200, 800)
        
        self.line_thickness = thickness
        self.border_color = border_col
        self.panel_fill_color = fill_col
        self.page_bg_color = bg_col
        
        layout = QHBoxLayout(self)
        
        controls_layout = QVBoxLayout()
        controls_widget = QWidget()
        controls_widget.setFixedWidth(280)
        controls_widget.setLayout(controls_layout)
        
        config_group = QGroupBox("Canvas Settings")
        config_form = QFormLayout()
        
        doc = Krita.instance().activeDocument()
        w_val = doc.width() if doc else 2480
        h_val = doc.height() if doc else 3508
        res_val = doc.resolution() if doc else 300
        
        self.spin_width = QSpinBox()
        self.spin_width.setRange(100, 20000); self.spin_width.setValue(w_val)
        self.spin_height = QSpinBox()
        self.spin_height.setRange(100, 20000); self.spin_height.setValue(h_val)
        self.spin_dpi = QSpinBox()
        self.spin_dpi.setRange(72, 1200); self.spin_dpi.setValue(res_val)
        
        self.spin_margin = QSpinBox()
        self.spin_margin.setRange(0, 2000); self.spin_margin.setValue(100)
        
        btn_update_canvas = QPushButton("Update Canvas Size")
        btn_update_canvas.clicked.connect(self.update_canvas_guide)
        
        config_form.addRow("Width (px):", self.spin_width)
        config_form.addRow("Height (px):", self.spin_height)
        config_form.addRow("DPI:", self.spin_dpi)
        config_form.addRow("Margin (px):", self.spin_margin)
        config_group.setLayout(config_form)
        
        controls_layout.addWidget(config_group)
        controls_layout.addWidget(btn_update_canvas)
        
        tools_group = QGroupBox("Tools")
        tools_layout = QVBoxLayout()
        
        self.btn_select = QPushButton("👆 Select / Move")
        self.btn_select.setCheckable(True)
        self.btn_select.clicked.connect(lambda: self.change_tool("select"))
        
        self.btn_rect = QPushButton("▭ Rectangle (Free)")
        self.btn_rect.setCheckable(True)
        self.btn_rect.clicked.connect(lambda: self.change_tool("rect"))
        
        self.btn_square = QPushButton("⬜ Square (Locked)")
        self.btn_square.setCheckable(True)
        self.btn_square.clicked.connect(lambda: self.change_tool("square"))
        
        self.btn_poly = QPushButton("📐 Polygon (Free)")
        self.btn_poly.setCheckable(True)
        self.btn_poly.clicked.connect(lambda: self.change_tool("poly"))
        
        self.btn_panel_color = QPushButton("Set Panel Interior Color")
        self.btn_panel_color.setStyleSheet(f"background-color: {self.panel_fill_color}; color: black; border: 1px solid gray;")
        self.btn_panel_color.clicked.connect(self.change_panel_color)

        self.btn_bg_color = QPushButton("Set Page Background Color")
        self.btn_bg_color.setStyleSheet(f"background-color: {self.page_bg_color}; color: black; border: 1px solid gray;")
        self.btn_bg_color.clicked.connect(self.change_bg_color)

        undo_layout = QHBoxLayout()
        self.btn_undo = QPushButton("↶ Back")
        self.btn_undo.clicked.connect(self.undo_click)
        self.btn_redo = QPushButton("↷ Front")
        self.btn_redo.clicked.connect(self.redo_click)
        undo_layout.addWidget(self.btn_undo)
        undo_layout.addWidget(self.btn_redo)
        
        self.btn_clear = QPushButton("🗑 Clear All Panels")
        self.btn_clear.clicked.connect(self.clear_items)

        tools_layout.addWidget(self.btn_select)
        tools_layout.addWidget(self.btn_rect)
        tools_layout.addWidget(self.btn_square)
        tools_layout.addWidget(self.btn_poly)
        tools_layout.addSpacing(10)
        tools_layout.addWidget(self.btn_panel_color)
        tools_layout.addWidget(self.btn_bg_color)
        tools_layout.addLayout(undo_layout)
        tools_layout.addSpacing(10)
        tools_layout.addWidget(self.btn_clear)
        tools_group.setLayout(tools_layout)
        
        controls_layout.addWidget(tools_group)
        controls_layout.addStretch()
        
        self.btn_create = QPushButton("GENERATE PANELS")
        self.btn_create.setFixedHeight(60)
        self.btn_create.setStyleSheet("background-color: #3daee9; color: white; font-weight: bold; font-size: 16px;")
        self.btn_create.clicked.connect(self.generate_and_close)
        controls_layout.addWidget(self.btn_create)
        
        self.canvas = DesignCanvas()
        
        layout.addWidget(controls_widget)
        layout.addWidget(self.canvas)
        
        self.tool_buttons = [self.btn_select, self.btn_rect, self.btn_square, self.btn_poly]
        self.change_tool("select")
        self.update_canvas_guide()

    def update_canvas_guide(self):
        self.canvas.page_width = self.spin_width.value()
        self.canvas.page_height = self.spin_height.value()
        self.canvas.margin_size = self.spin_margin.value()
        self.canvas.refresh_guides()

    def change_tool(self, mode):
        for btn in self.tool_buttons:
            btn.setChecked(False)
            
        if mode == "select": self.btn_select.setChecked(True)
        elif mode == "rect": self.btn_rect.setChecked(True)
        elif mode == "square": self.btn_square.setChecked(True)
        elif mode == "poly": self.btn_poly.setChecked(True)
        
        self.canvas.set_tool(mode)

    def change_panel_color(self):
        color = QColorDialog.getColor(QColor(self.panel_fill_color))
        if color.isValid():
            self.panel_fill_color = color.name()
            self.btn_panel_color.setStyleSheet(f"background-color: {self.panel_fill_color}; color: black; border: 1px solid gray;")

    def change_bg_color(self):
        color = QColorDialog.getColor(QColor(self.page_bg_color))
        if color.isValid():
            self.page_bg_color = color.name()
            self.btn_bg_color.setStyleSheet(f"background-color: {self.page_bg_color}; color: black; border: 1px solid gray;")

    def undo_click(self):
        self.canvas.undo_action()

    def redo_click(self):
        self.canvas.redo_action()

    def clear_items(self):
        for item in self.canvas.scene.items():
            if item != self.canvas.sheet_rect and item != self.canvas.margin_rect:
                self.canvas.scene.removeItem(item)
        self.canvas.history = []
        self.canvas.redo_stack = []

    def generate_and_close(self):
        valid_items = []
        for item in self.canvas.scene.items():
            if item != self.canvas.sheet_rect and item != self.canvas.margin_rect and item != self.canvas.temp_item:
                valid_items.append(item)
        
        if not valid_items:
            QMessageBox.warning(self, "Empty", "Draw some panels first!")
            return

        doc = Krita.instance().activeDocument()
        target_w = self.spin_width.value()
        target_h = self.spin_height.value()
        margin = self.spin_margin.value()
        
        if not doc:
            doc = Krita.instance().createDocument(target_w, target_h, "Comic Page", "RGBA", "U8", "", float(self.spin_dpi.value()))
            Krita.instance().activeWindow().addView(doc)
        
        root = doc.rootNode()
        main_group = doc.createGroupLayer("FreeForm Panels")
        root.addChildNode(main_group, None)
        
        bg_vector = doc.createVectorLayer("Page Background")
        rect_svg = f'<svg width="{target_w}" height="{target_h}"><rect x="0" y="0" width="{target_w}" height="{target_h}" fill="{self.page_bg_color}" /></svg>'
        bg_vector.addShapesFromSvg(rect_svg)
        main_group.addChildNode(bg_vector, None)
        
        safe_rect = QRectF(margin, margin, target_w - (margin * 2), target_h - (margin * 2))
        safe_poly = QPolygonF(safe_rect)

        count = 1
        for item in reversed(valid_items):
            svg_path = ""
            
            if isinstance(item, QGraphicsRectItem):
                item_rect = item.sceneBoundingRect()
                clipped_rect = item_rect.intersected(safe_rect)
                
                if clipped_rect.width() > 1 and clipped_rect.height() > 1:
                    x, y, w, h = clipped_rect.x(), clipped_rect.y(), clipped_rect.width(), clipped_rect.height()
                    svg_path = f"M {x},{y} L {x+w},{y} L {x+w},{y+h} L {x},{y+h} Z"
                
            elif isinstance(item, QGraphicsPolygonItem):
                poly = item.polygon()
                scene_poly = item.mapToScene(poly)
                clipped_poly = scene_poly.intersected(safe_poly)
                
                if not clipped_poly.isEmpty():
                    points_str = ""
                    first = True
                    for pt in clipped_poly:
                        if first:
                            points_str += f"M {pt.x()},{pt.y()}"
                            first = False
                        else:
                            points_str += f" L {pt.x()},{pt.y()}"
                    svg_path = points_str + " Z"
            
            if svg_path:
                self.create_panel_structure(doc, main_group, count, svg_path)
                count += 1
        
        doc.refreshProjection()
        self.accept()

    def create_panel_structure(self, doc, parent, index, path_d):
        p_group = doc.createGroupLayer(f"Panel {index}")
        parent.addChildNode(p_group, None)
        
        svg_xml = f"""
        <svg xmlns="http://www.w3.org/2000/svg" width="{doc.width()}" height="{doc.height()}">
            <path d="{path_d}" fill="{self.panel_fill_color}" stroke="{self.border_color}" stroke-width="{self.line_thickness}" stroke-linejoin="round" />
        </svg>
        """
        v_layer = doc.createVectorLayer(f"Shape {index}")
        v_layer.addShapesFromSvg(svg_xml)
        p_group.addChildNode(v_layer, None)
        
        paint_layer = doc.createNode(f"Draw {index}", "paintlayer")
        paint_layer.setInheritAlpha(True)
        p_group.addChildNode(paint_layer, v_layer)

class MangaPanelDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manga Panel Creator Pro")
        
        main_widget = QWidget(self)
        layout = QVBoxLayout(main_widget)
        
        btn_free_mode = QPushButton("✨ OPEN FREE MODE EDITOR ✨")
        btn_free_mode.setFixedHeight(50)
        btn_free_mode.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold; font-size: 14px; border-radius: 5px;")
        btn_free_mode.clicked.connect(self.open_free_mode_window)
        layout.addWidget(btn_free_mode)
        
        layout.addWidget(QLabel("--- OR USE GRID GENERATOR ---"))

        grid_group = QGroupBox("1. Grid Structure")
        grid_layout = QVBoxLayout()
        self.slider_rows, self.spin_rows = self.create_slider_spin_pair(1, 10, 2)
        grid_layout.addLayout(self.create_labeled_row("Rows:", self.slider_rows, self.spin_rows))
        self.slider_cols, self.spin_cols = self.create_slider_spin_pair(1, 10, 2)
        grid_layout.addLayout(self.create_labeled_row("Columns:", self.slider_cols, self.spin_cols))
        grid_group.setLayout(grid_layout)
        layout.addWidget(grid_group)
        
        space_group = QGroupBox("2. Spacing (px)")
        space_layout = QVBoxLayout()
        self.slider_margin, self.spin_margin = self.create_slider_spin_pair(0, 1000, 50)
        space_layout.addLayout(self.create_labeled_row("Page Margin:", self.slider_margin, self.spin_margin))
        self.slider_gutter, self.spin_gutter = self.create_slider_spin_pair(0, 500, 20)
        space_layout.addLayout(self.create_labeled_row("Gap (Gutter):", self.slider_gutter, self.spin_gutter))
        space_group.setLayout(space_layout)
        layout.addWidget(space_group)

        style_group = QGroupBox("3. Panel Style")
        style_layout = QFormLayout()
        
        self.spin_thickness = QDoubleSpinBox()
        self.spin_thickness.setRange(0.0, 100.0)
        self.spin_thickness.setValue(8.0)
        
        self.btn_border_color = QPushButton()
        self.btn_border_color.setStyleSheet("background-color: black;")
        self.border_color = "#000000"
        self.btn_border_color.clicked.connect(lambda: self.select_color("border"))
        
        self.btn_panel_fill = QPushButton()
        self.btn_panel_fill.setStyleSheet("background-color: white;")
        self.panel_fill_color = "#ffffff"
        self.btn_panel_fill.clicked.connect(lambda: self.select_color("panel_fill"))
        
        style_layout.addRow("Line Thickness:", self.spin_thickness)
        style_layout.addRow("Line Color:", self.btn_border_color)
        style_layout.addRow("Panel Interior (Draw Area):", self.btn_panel_fill)
        style_group.setLayout(style_layout)
        layout.addWidget(style_group)
        
        layer_group = QGroupBox("4. Layer Options")
        layer_layout = QVBoxLayout()
        frame_fill_layout = QHBoxLayout()
        self.chk_frame_fill = QCheckBox("Create Page Background Layer")
        self.chk_frame_fill.setChecked(True)
        self.btn_frame_color = QPushButton()
        self.btn_frame_color.setStyleSheet("background-color: white;")
        self.frame_color = "#ffffff"
        self.btn_frame_color.clicked.connect(lambda: self.select_color("frame_bg"))
        frame_fill_layout.addWidget(self.chk_frame_fill)
        frame_fill_layout.addWidget(self.btn_frame_color)
        
        label_bg = QLabel("Page Background (Frame/Gutters)")
        layer_layout.addWidget(label_bg)
        layer_layout.addLayout(frame_fill_layout)
        layer_group.setLayout(layer_layout)
        layout.addWidget(layer_group)

        self.btn_create = QPushButton("GENERATE GRID PAGE")
        self.btn_create.setFixedHeight(50)
        self.btn_create.setStyleSheet("background-color: #3daee9; color: white; font-weight: bold; font-size: 14px;")
        self.btn_create.clicked.connect(self.create_grid_panels)
        layout.addWidget(self.btn_create)
        
        layout.addStretch()
        self.setWidget(main_widget)

    def open_free_mode_window(self):
        dialog = FreeModeDialog(self, 
                                thickness=self.spin_thickness.value(), 
                                border_col=self.border_color, 
                                fill_col=self.panel_fill_color,
                                bg_col=self.frame_color)
        dialog.exec_()

    def create_slider_spin_pair(self, min_val, max_val, default_val):
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default_val)
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        return slider, spin

    def create_labeled_row(self, text, slider, spin):
        layout = QHBoxLayout()
        lbl = QLabel(text)
        lbl.setFixedWidth(80)
        layout.addWidget(lbl)
        layout.addWidget(slider)
        layout.addWidget(spin)
        return layout

    def select_color(self, target):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            if target == "border":
                self.border_color = hex_color
                self.btn_border_color.setStyleSheet(f"background-color: {hex_color};")
            elif target == "panel_fill":
                self.panel_fill_color = hex_color
                self.btn_panel_fill.setStyleSheet(f"background-color: {hex_color};")
            elif target == "frame_bg":
                self.frame_color = hex_color
                self.btn_frame_color.setStyleSheet(f"background-color: {hex_color};")

    def canvasChanged(self, canvas):
        pass

    def create_grid_panels(self):
        doc = Krita.instance().activeDocument()
        if not doc:
            QMessageBox.warning(self, "Error", "Please open a document first.")
            return

        root = doc.rootNode()
        main_group = doc.createGroupLayer("Comic Page System")
        root.addChildNode(main_group, None)
        
        if self.chk_frame_fill.isChecked():
            bg_vector = doc.createVectorLayer("Page Background")
            rect_svg = f'<svg width="{doc.width()}" height="{doc.height()}"><rect x="0" y="0" width="{doc.width()}" height="{doc.height()}" fill="{self.frame_color}" /></svg>'
            bg_vector.addShapesFromSvg(rect_svg)
            main_group.addChildNode(bg_vector, None)

        doc_w = doc.width()
        doc_h = doc.height()
        rows = self.spin_rows.value()
        cols = self.spin_cols.value()
        margin = self.spin_margin.value()
        gutter = self.spin_gutter.value()
        stroke_w = self.spin_thickness.value()
        
        available_w = doc_w - (margin * 2)
        available_h = doc_h - (margin * 2)
        total_gutter_w = (cols - 1) * gutter
        total_gutter_h = (rows - 1) * gutter
        
        if available_w <= total_gutter_w or available_h <= total_gutter_h:
            QMessageBox.critical(self, "Error", "Margins are too big!")
            return

        panel_w = (available_w - total_gutter_w) / cols
        panel_h = (available_h - total_gutter_h) / rows
        
        current_y = margin
        panel_counter = 1

        for r in range(rows):
            current_x = margin
            for c in range(cols):
                x1, y1 = current_x, current_y
                x2, y2 = x1 + panel_w, y1 + panel_h
                
                d_path = f"M {x1},{y1} L {x2},{y1} L {x2},{y2} L {x1},{y2} Z"
                
                panel_svg = f"""
                <svg xmlns="http://www.w3.org/2000/svg" width="{doc_w}" height="{doc_h}">
                    <path d="{d_path}" fill="{self.panel_fill_color}" stroke="{self.border_color}" stroke-width="{stroke_w}" stroke-linejoin="round" />
                </svg>
                """

                panel_group = doc.createGroupLayer(f"Panel {panel_counter}")
                main_group.addChildNode(panel_group, None)
                
                vector_layer = doc.createVectorLayer(f"Shape {panel_counter}")
                vector_layer.addShapesFromSvg(panel_svg)
                panel_group.addChildNode(vector_layer, None)
                
                paint_layer = doc.createNode(f"Draw {panel_counter}", "paintlayer")
                paint_layer.setInheritAlpha(True)
                panel_group.addChildNode(paint_layer, vector_layer) 
                
                current_x += panel_w + gutter
                panel_counter += 1
            current_y += panel_h + gutter

        doc.refreshProjection()
        QMessageBox.information(self, "Success", "Panels created successfully!")

Krita.instance().addDockWidgetFactory(DockWidgetFactory("Manga Panel Creator Pro", DockWidgetFactoryBase.DockRight, MangaPanelDocker))