"""
Force-directed view settings panel: UI and signals/slots only.
Parent connects panel signals to view/session.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QCheckBox, QLabel,
    QFormLayout, QRadioButton,QSlider
)
from PySide6.QtCore import Qt, Signal


from ui.basic import ToggleSwitch
from ui.basic.Collapse import CollapsibleSection


class ClickableSlider(QSlider):
    def __init__(self, orientation=Qt.Horizontal, parent=None):  # type: ignore[arg-type]
        super().__init__(orientation, parent)
        style = """
    QSlider::groove:horizontal {
        height: 4px;
        background: #d0d0d0;
        margin: 0px;
        border-radius: 2px;
    }
    QSlider::handle:horizontal {
        background: #5c6bc0;
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }
    QSlider::groove:vertical {
        width: 4px;
        background: #d0d0d0;
        margin: 0px;
        border-radius: 2px;
    }
    QSlider::handle:vertical {
        background: #5c6bc0;
        width: 14px;
        height: 14px;
        margin: 0 -5px;
        border-radius: 7px;
    }
    """
        self.setStyleSheet(style)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:  # type: ignore[arg-type]
            if self.orientation() == Qt.Horizontal:  # type: ignore[arg-type]
                ratio = event.position().x() / max(1, self.width())
            else:
                ratio = 1.0 - event.position().y() / max(1, self.height())
            ratio = float(max(0.0, min(1.0, ratio)))
            value = self.minimum() + int(round(ratio * (self.maximum() - self.minimum())))
            self.setValue(value)
        super().mousePressEvent(event)


class ForceViewSettingsPanel(QWidget):
    """Settings panel for force-directed view. Emits signals for parent to connect to view/session."""

    # --- Outgoing signals (parent connects to view/session) ---
    fitInViewRequested = Signal()
    manyBodyStrengthChanged = Signal(float)
    centerStrengthChanged = Signal(float)
    linkStrengthChanged = Signal(float)
    linkDistanceChanged = Signal(float)
    radiusFactorChanged = Signal(float)
    textThresholdFactorChanged = Signal(float)
    linkwidthFactorChanged = Signal(float)

    restartRequested = Signal()
    pauseRequested = Signal()
    resumeRequested = Signal()
    addNodeRequested = Signal()

    removeNodeRequested = Signal()
    addEdgeRequested = Signal()
    removeEdgeRequested = Signal()
    graphModeChanged = Signal(str)
    contentSizeChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("my_panel")
        self.setStyleSheet(
            "#my_panel {"
            "    background-color: #fdfdfd; "
            "    border: 1px solid #cccccc; "
            "    border-radius: 6px;"
            "}"
        )
        self.setVisible(False)
        self._build_ui()
        self._connect_internal()

    def _build_ui(self):
        panel_layout = QVBoxLayout(self)

        self.label_cal = QLabel()
        self.label_paint = QLabel()

        effect_section = CollapsibleSection("效果", self)
        effect_form = QFormLayout()

        self.manybodyfstrength = ClickableSlider(Qt.Horizontal)  # type: ignore[arg-type]
        self.manybodyfstrength.setMinimum(1000)
        self.manybodyfstrength.setMaximum(50000)
        self.manybodyfstrength.setValue(10000)

        self.centerfstrength = ClickableSlider(Qt.Horizontal)  # type: ignore[arg-type]
        self.centerfstrength.setMinimum(1)#范围0.005-0.05
        self.centerfstrength.setMaximum(50)
        self.centerfstrength.setValue(10)

        self.linkfstrength = ClickableSlider(Qt.Horizontal)  # type: ignore[arg-type]
        self.linkfstrength.setMinimum(1)#范围0.01-1
        self.linkfstrength.setMaximum(100)
        self.linkfstrength.setValue(30)

        self.linklength = ClickableSlider(Qt.Horizontal)  # type: ignore[arg-type]
        self.linklength.setMinimum(10)
        self.linklength.setMaximum(80)
        self.linklength.setValue(40)

        effect_form.addRow("斥力强度", self.manybodyfstrength)
        effect_form.addRow("中心力强度", self.centerfstrength)
        effect_form.addRow("连接力强度", self.linkfstrength)
        effect_form.addRow("连接距离", self.linklength)
        effect_section.addLayout(effect_form)

        display_section = CollapsibleSection("显示", self)
        display_form = QFormLayout()
        self.show_image = ToggleSwitch(width=48, height=24)
        self.show_image.setChecked(True)

        self.textfadeshreshold = ClickableSlider(Qt.Horizontal)  # type: ignore[arg-type]
        self.textfadeshreshold.setMinimum(10)
        self.textfadeshreshold.setMaximum(1000)
        self.textfadeshreshold.setValue(100)

        self.nodesize = ClickableSlider(Qt.Horizontal)  # type: ignore[arg-type]
        self.nodesize.setMinimum(10)
        self.nodesize.setMaximum(300)
        self.nodesize.setValue(100)

        self.linkwidth = ClickableSlider(Qt.Horizontal)  # type: ignore[arg-type]
        self.linkwidth.setMinimum(10)
        self.linkwidth.setMaximum(300)
        self.linkwidth.setValue(60)

        self.show_coordinate_sys = QCheckBox("显示坐标轴", self)
        self.show_coordinate_sys.setChecked(False)

        display_form.addRow("显示图片", self.show_image)
        display_form.addRow("文字渐隐", self.textfadeshreshold)
        display_form.addRow("节点大小", self.nodesize)
        display_form.addRow("连线宽度", self.linkwidth)
        display_section.addLayout(display_form)

        self.btn_restart = QPushButton("Restart", self)
        self.btn_pause = QPushButton("Pause", self)
        self.btn_resume = QPushButton("Resume", self)
        self.btn_fitinview = QPushButton("适配视图", self)
        self.btn_add_node = QPushButton("加点", self)
        self.btn_remove_node = QPushButton("减点", self)
        self.btn_add_edge = QPushButton("加边", self)
        self.btn_remove_edge = QPushButton("减边", self)

        self.radio_graph_all = QRadioButton("总图", self)
        self.radio_graph_favorite = QRadioButton("片关系图", self)
        self.radio_graph_test = QRadioButton("2000点图", self)
        self.radio_graph_all.setChecked(True)
        graph_type_layout = QHBoxLayout()
        graph_type_layout.addWidget(self.radio_graph_all)
        graph_type_layout.addWidget(self.radio_graph_favorite)
        graph_type_layout.addWidget(self.radio_graph_test)
        effect_form.addRow("图类型", graph_type_layout)

        test_section = CollapsibleSection("测试", self)
        self.label_scale = QLabel()
        self.label_fps = QLabel()
        self.lable_alpha=QLabel()

        test_section.addWidget(self.btn_fitinview)
        test_section.addWidget(self.btn_restart)
        test_section.addWidget(self.btn_pause)
        test_section.addWidget(self.btn_resume)
        test_section.addWidget(self.show_coordinate_sys)
        test_section.addWidget(self.btn_add_node)
        test_section.addWidget(self.btn_remove_node)
        test_section.addWidget(self.btn_add_edge)
        test_section.addWidget(self.btn_remove_edge)

        fromlayout = QFormLayout()
        fromlayout.addRow("tick消耗", self.label_cal)
        fromlayout.addRow("paint消耗", self.label_paint)
        fromlayout.addRow("当前缩放", self.label_scale)
        fromlayout.addRow("当前帧率", self.label_fps)
        fromlayout.addRow("当前模拟热度", self.lable_alpha)
        test_section.addLayout(fromlayout)

        run_layout = QHBoxLayout()
        panel_layout.addLayout(run_layout)
        panel_layout.addWidget(effect_section)
        panel_layout.addWidget(display_section)
        panel_layout.addWidget(test_section)

        self._effect_section = effect_section
        self._display_section = display_section
        self._test_section = test_section

    def _connect_internal(self):
        """Wire internal controls to our signals."""
        self.btn_fitinview.clicked.connect(self.fitInViewRequested.emit)
        self.manybodyfstrength.valueChanged.connect(self.manyBodyStrengthChanged.emit)
        self.centerfstrength.valueChanged.connect(lambda x: self.centerStrengthChanged.emit(float(x) / 1000.0))
        self.linkfstrength.valueChanged.connect(lambda x: self.linkStrengthChanged.emit(float(x) / 100.0))

        self.linklength.valueChanged.connect(self.linkDistanceChanged.emit)
        self.nodesize.valueChanged.connect(lambda x: self.radiusFactorChanged.emit(float(x) / 100.0))
        self.textfadeshreshold.valueChanged.connect(
            lambda x: self.textThresholdFactorChanged.emit(float(x) / 100.0)
        )
        self.linkwidth.valueChanged.connect(lambda x: self.linkwidthFactorChanged.emit(float(x) / 100.0))

        self.btn_restart.clicked.connect(self.restartRequested.emit)
        self.btn_pause.clicked.connect(self.pauseRequested.emit)
        self.btn_resume.clicked.connect(self.resumeRequested.emit)
        self.btn_add_node.clicked.connect(self.addNodeRequested.emit)
        self.btn_remove_node.clicked.connect(self.removeNodeRequested.emit)
        self.btn_add_edge.clicked.connect(self.addEdgeRequested.emit)
        self.btn_remove_edge.clicked.connect(self.removeEdgeRequested.emit)

        self.radio_graph_all.toggled.connect(
            lambda checked: self.graphModeChanged.emit("all") if checked else None
        )
        self.radio_graph_favorite.toggled.connect(
            lambda checked: self.graphModeChanged.emit("favorite") if checked else None
        )
        self.radio_graph_test.toggled.connect(
            lambda checked: self.graphModeChanged.emit("test") if checked else None
        )

        def on_section_toggled():
            self.adjustSize()
            self.contentSizeChanged.emit()

        self._effect_section.toggled.connect(lambda _: on_section_toggled())
        self._display_section.toggled.connect(lambda _: on_section_toggled())
        self._test_section.toggled.connect(lambda _: on_section_toggled())

    # --- Slots for parent to push view state into labels ---
    def setFps(self, value: float):
        self.label_fps.setText(f"{value:.2f}")

    def setTickTime(self, ms: float):
        self.label_cal.setText(f"{ms:.3f}ms")

    def setPaintTime(self, ms: float):
        self.label_paint.setText(f"{ms:.3f}ms")
    
    def setscale(self,value:float):
        self.label_scale.setText(f"{value:.2f}")

    def setalpha(self,value:float):
        self.lable_alpha.setText(f"{value:.2f}")
