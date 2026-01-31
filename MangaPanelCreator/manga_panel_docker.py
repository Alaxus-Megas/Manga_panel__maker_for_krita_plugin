from krita import DockWidget, Krita, DockWidgetFactory, DockWidgetFactoryBase
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout,
                             QPushButton, QSpinBox, QDoubleSpinBox,
                             QLabel, QGroupBox, QColorDialog, QMessageBox,
                             QSlider, QHBoxLayout, QCheckBox, QDialog, QScrollArea,
                             QGraphicsView, QGraphicsScene, QGraphicsRectItem,
                             QGraphicsPolygonItem, QGraphicsItem, QGraphicsLineItem,
                             QSizePolicy, QSplitter)
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QColor, QPen, QBrush, QPolygonF, QPainter, QCursor

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
class DraggableGuide(QGraphicsLineItem):
    def __init__(self, is_horizontal, index, parent_view, min_val, max_val):
        super().__init__()
        self.is_horizontal = is_horizontal
        self.guide_index = index
        self.view = parent_view
        self.min_val = min_val
        self.max_val = max_val

        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)

        pen = QPen(QColor("red") if is_horizontal else QColor("#00AAFF"))
        pen.setWidth(4 if is_horizontal else 2)
        if not is_horizontal:
            pen.setStyle(Qt.DashLine)
        self.setPen(pen)

        if is_horizontal:
            self.setCursor(QCursor(Qt.SplitVCursor))
        else:
            self.setCursor(QCursor(Qt.SplitHCursor))

    def mouseMoveEvent(self, event):

        new_pos = self.mapToParent(event.pos())

        if self.is_horizontal:

            y = new_pos.y()

            y = max(self.min_val, min(y, self.max_val))
            self.setPos(0, y)


            self.view.update_row_heights()
        else:

            x = new_pos.x()
            x = max(self.min_val, min(x, self.max_val))
            self.setPos(x, 0)



    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.view.recalculate_ratios()

class VisualGridPreview(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setBackgroundBrush(QBrush(QColor("#303030")))
        self.setAlignment(Qt.AlignCenter)

        self.page_w = 1000
        self.page_h = 1414
        self.margin = 50


        self.num_rows = 2
        self.cols_per_row = [1, 1]


        self.row_separators = [0.5]
        self.col_separators = [[0.5]]

        self.guide_items_rows = []
        self.guide_items_cols = []

    def initialize(self, rows, cols_config, aspect_ratio):
        self.num_rows = rows
        self.cols_per_row = cols_config


        self.page_h = self.page_w / aspect_ratio


        if len(self.row_separators) != rows - 1:
            self.row_separators = [i/rows for i in range(1, rows)]


        self.col_separators = []
        for r in range(rows):
            count = cols_config[r]
            separators = [i/count for i in range(1, count)]
            self.col_separators.append(separators)

        self.draw_grid()

    def update_col_count(self, row_idx, new_count):

        self.cols_per_row[row_idx] = new_count
        separators = [i/new_count for i in range(1, new_count)]


        if row_idx < len(self.col_separators):
            self.col_separators[row_idx] = separators
        else:
            self.col_separators.append(separators)

        self.draw_grid()

    def draw_grid(self):
        self.scene.clear()
        self.guide_items_rows = []
        self.guide_items_cols = []


        sheet = self.scene.addRect(0, 0, self.page_w, self.page_h, QPen(Qt.NoPen), QBrush(QColor("white")))
        sheet.setZValue(-10)


        safe_w = self.page_w - (self.margin * 2)
        safe_h = self.page_h - (self.margin * 2)
        safe_rect = self.scene.addRect(self.margin, self.margin, safe_w, safe_h, QPen(QColor("#DDDDDD"), 2, Qt.DashLine))
        safe_rect.setZValue(-5)



        min_y = self.margin + 20
        max_y = self.page_h - self.margin - 20


        row_y_positions = [self.margin]

        for i, ratio in enumerate(self.row_separators):
            y_pos = self.margin + (safe_h * ratio)

            line = DraggableGuide(True, i, self, min_y, max_y)
            line.setLine(0, 0, self.page_w, 0)
            line.setPos(0, y_pos)
            self.scene.addItem(line)
            self.guide_items_rows.append(line)
            row_y_positions.append(y_pos)

        row_y_positions.append(self.page_h - self.margin)


        for r in range(self.num_rows):

            top_y = row_y_positions[r]
            bot_y = row_y_positions[r+1]
            row_height = bot_y - top_y


            min_x = self.margin + 20
            max_x = self.page_w - self.margin - 20


            separators = self.col_separators[r]

            for k, ratio in enumerate(separators):
                x_pos = self.margin + (safe_w * ratio)

                col_line = DraggableGuide(False, k, self, min_x, max_x)

                col_line.setLine(0, 0, 0, row_height)

                col_line.setPos(x_pos, top_y)


                col_line.row_owner_index = r
                col_line.ratio_index = k

                self.scene.addItem(col_line)
                self.guide_items_cols.append(col_line)

        self.scene.setSceneRect(-50, -50, self.page_w + 100, self.page_h + 100)
        self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def update_row_heights(self):

        safe_h = self.page_h - (self.margin * 2)


        current_y_positions = [self.margin]
        for line in self.guide_items_rows:

            current_y_positions.append(line.pos().y())
        current_y_positions.append(self.page_h - self.margin)


        for col_line in self.guide_items_cols:
            r = col_line.row_owner_index
            top_y = current_y_positions[r]
            bot_y = current_y_positions[r+1]


            current_x = col_line.pos().x()
            col_line.setPos(current_x, top_y)
            col_line.setLine(0, 0, 0, bot_y - top_y)

    def recalculate_ratios(self):

        safe_w = self.page_w - (self.margin * 2)
        safe_h = self.page_h - (self.margin * 2)


        new_row_ratios = []
        for line in self.guide_items_rows:

            rel_y = line.pos().y() - self.margin
            ratio = rel_y / safe_h
            new_row_ratios.append(ratio)
        new_row_ratios.sort()
        self.row_separators = new_row_ratios



        new_col_separators = [[] for _ in range(self.num_rows)]

        for col_line in self.guide_items_cols:
            r = col_line.row_owner_index
            rel_x = col_line.pos().x() - self.margin
            ratio = rel_x / safe_w
            new_col_separators[r].append(ratio)

        for r in range(self.num_rows):
            new_col_separators[r].sort()

        self.col_separators = new_col_separators

    def get_final_geometry(self):


        self.recalculate_ratios()
        return {
            'rows': self.row_separators,
            'cols': self.col_separators
        }

class CustomGridDialog(QDialog):
    def __init__(self, parent=None, total_rows=2, current_config=None, aspect_ratio=0.7):
        super().__init__(parent)
        self.setWindowTitle("Custom Visual Grid Layout")
        self.resize(1100, 700)
        self.result_data = None
        self.total_rows = total_rows


        main_layout = QHBoxLayout(self)


        left_panel = QWidget()
        left_panel.setFixedWidth(250)
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel(f"<b>Config Columns ({total_rows} Rows)</b>"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)

        self.row_spinboxes = []


        if not current_config:
            current_config = [1] * total_rows

        for i in range(total_rows):
            row_box = QGroupBox(f"Row {i+1}")
            row_box_layout = QHBoxLayout()

            lbl = QLabel("Cols:")
            spin = QSpinBox()
            spin.setRange(1, 10)


            val = current_config[i] if i < len(current_config) else 1
            spin.setValue(val)

            spin.valueChanged.connect(lambda val, idx=i: self.update_preview_cols(idx, val))

            self.row_spinboxes.append(spin)
            row_box_layout.addWidget(lbl)
            row_box_layout.addWidget(spin)
            row_box.setLayout(row_box_layout)
            self.scroll_layout.addWidget(row_box)

        self.scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll)


        info_lbl = QLabel("💡 <b>Instructions:</b>\n\n🔴 <b>Red Lines:</b> Drag vertically to change Row Height.\n\n🔵 <b>Blue Lines:</b> Drag horizontally to change Column Width.")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #888; font-size: 11px;")
        left_layout.addWidget(info_lbl)

        btn_box = QHBoxLayout()
        btn_ok = QPushButton("Create Layout")
        btn_ok.setStyleSheet("background-color: #00FF00; color: black; font-weight: bold; height: 40px;")
        btn_ok.clicked.connect(self.save_and_close)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_ok)
        left_layout.addLayout(btn_box)


        self.preview = VisualGridPreview()

        initial_counts = [s.value() for s in self.row_spinboxes]
        self.preview.initialize(total_rows, initial_counts, aspect_ratio)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.preview)

    def update_preview_cols(self, row_idx, count):
        self.preview.update_col_count(row_idx, count)

    def save_and_close(self):

        self.result_data = self.preview.get_final_geometry()

        self.counts = [s.value() for s in self.row_spinboxes]
        self.accept()

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


        self.custom_row_config = []
        self.custom_layout_data = None
        self.use_custom_grid = False

        grid_group = QGroupBox("1. Grid Structure")
        grid_layout = QVBoxLayout()


        row_container = QHBoxLayout()
        self.slider_rows, self.spin_rows = self.create_slider_spin_pair(1, 10, 2)


        lbl_rows = QLabel("Rows:")
        lbl_rows.setFixedWidth(80)
        row_container.addWidget(lbl_rows)
        row_container.addWidget(self.slider_rows)
        row_container.addWidget(self.spin_rows)

        self.btn_custom_rows = QPushButton("Custom")
        self.btn_custom_rows.setFixedWidth(60)
        self.btn_custom_rows.setStyleSheet("font-size: 10px; padding: 2px;")
        self.btn_custom_rows.clicked.connect(self.open_custom_grid_dialog)
        row_container.addWidget(self.btn_custom_rows)

        grid_layout.addLayout(row_container)


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

    def open_custom_grid_dialog(self):
        rows = self.spin_rows.value()


        doc = Krita.instance().activeDocument()
        ratio = doc.width() / doc.height() if doc else 0.707


        dialog = CustomGridDialog(self, total_rows=rows, current_config=self.custom_row_config, aspect_ratio=ratio)

        if dialog.exec_():

            self.custom_layout_data = dialog.result_data
            self.custom_row_config = dialog.counts
            self.use_custom_grid = True
            self.btn_custom_rows.setStyleSheet("background-color: #00FF00; color: black; font-size: 10px;")
            QMessageBox.information(self, "Custom Mode", "Visual layout saved!")
        else:


            self.use_custom_grid = False
            self.custom_row_config = []
            self.custom_layout_data = None
            self.btn_custom_rows.setStyleSheet("")

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


        is_custom = self.use_custom_grid and self.custom_layout_data is not None and len(self.custom_layout_data['rows']) == rows - 1

        margin = self.spin_margin.value()
        gutter = self.spin_gutter.value()
        stroke_w = self.spin_thickness.value()

        available_w = doc_w - (margin * 2)
        available_h = doc_h - (margin * 2)


        row_heights = []
        if is_custom:

            ratios = [0.0] + self.custom_layout_data['rows'] + [1.0]



            total_gutter_h = (rows - 1) * gutter



            pixel_cuts = [r * available_h for r in ratios]






            raw_heights = []
            for i in range(len(pixel_cuts)-1):
                raw_h = pixel_cuts[i+1] - pixel_cuts[i]
                raw_heights.append(raw_h)


            sum_raw = sum(raw_heights)
            scale_factor = (available_h - total_gutter_h) / sum_raw

            row_heights = [h * scale_factor for h in raw_heights]

        else:

            total_gutter_h = (rows - 1) * gutter
            if available_h <= total_gutter_h:
                QMessageBox.critical(self, "Error", "Margins/Gutters too big (Height)!")
                return
            h_per_row = (available_h - total_gutter_h) / rows
            row_heights = [h_per_row] * rows

        current_y = margin
        panel_counter = 1

        for r in range(rows):
            this_row_h = row_heights[r]


            col_widths = []

            if is_custom:
                col_ratios = self.custom_layout_data['cols'][r]
                cols_count = len(col_ratios) + 1


                full_ratios = [0.0] + col_ratios + [1.0]

                raw_widths = []
                for k in range(len(full_ratios)-1):
                    w = (full_ratios[k+1] - full_ratios[k]) * available_w
                    raw_widths.append(w)

                total_gutter_w = (cols_count - 1) * gutter
                sum_raw_w = sum(raw_widths)

                if sum_raw_w > 0:
                    scale_w = (available_w - total_gutter_w) / sum_raw_w
                    col_widths = [w * scale_w for w in raw_widths]
                else:
                    col_widths = [available_w]
            else:
                cols_count = self.spin_cols.value()
                total_gutter_w = (cols_count - 1) * gutter
                w_per_col = (available_w - total_gutter_w) / cols_count
                col_widths = [w_per_col] * cols_count

            current_x = margin
            for c_w in col_widths:

                x1, y1 = current_x, current_y
                x2, y2 = x1 + c_w, y1 + this_row_h

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

                current_x += c_w + gutter
                panel_counter += 1

            current_y += this_row_h + gutter

        doc.refreshProjection()
        QMessageBox.information(self, "Success", "Panels created successfully!")

        if self.use_custom_grid and len(self.custom_row_config) != self.spin_rows.value():
             self.btn_custom_rows.setStyleSheet("")
             self.use_custom_grid = False

Krita.instance().addDockWidgetFactory(DockWidgetFactory("Manga Panel Creator Pro", DockWidgetFactoryBase.DockRight, MangaPanelDocker))