"""软件设置窗口
包含多个设置页面，通过左侧树形菜单切换"""

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel,QVBoxLayout,QTextEdit,QDialog,QFileDialog,QGridLayout,QWidget ,QTreeWidget, QTreeWidgetItem,QStackedWidget
from PySide6.QtGui import QIcon
from PySide6.QtCore import Slot
import logging
from config import ICONS_PATH
from controller import MessageBoxService
from pathlib import Path

from .VideoSettingPage import VideoSettingPage
from .ClawerSettingPage import ClawerSettingPage
from .DBSettingPage import DBSettingPage
from .FirstPage import FirstPage


class SettingDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        logging.info("----------软件设置窗口----------")
        self.setWindowTitle("软件设置")
        self.setWindowIcon(QIcon(str(ICONS_PATH / "settings.png")))
        self.resize(600,600)
        self.setMinimumSize(600,600)


        # 主分割器（左右布局）
        layout=QVBoxLayout(self)#整体是上下布局
        
        btn_layout=QHBoxLayout()#按钮行是横着的
        mainlayout=QHBoxLayout()

        layout.addLayout(mainlayout)
        layout.addLayout(btn_layout)

        # 按钮行
        self.btn_default=QPushButton("恢复默认设置")
        self.btn_ok=QPushButton("确定")
        self.btn_cancal=QPushButton("取消")
        btn_layout.addWidget(self.btn_default)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancal)

        # === 左侧：树形列表 ===
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)  # 隐藏表头
        self.tree.setFixedWidth(150)

        # 添加树节点
        root1 = QTreeWidgetItem(self.tree, ["软件信息"])
        root2 = QTreeWidgetItem(self.tree, ["视频相关"])
        root4 = QTreeWidgetItem(self.tree, ["爬虫相关"])

        root3 = QTreeWidgetItem(self.tree, ["数据库"])
        child1 = QTreeWidgetItem(root3, ["公共数据库"])
        child2 = QTreeWidgetItem(root3, ["私有数据库"])

        # 展开系统管理节点（可选）
        self.tree.expandItem(root3)


        # === 右侧：堆叠页面 ===
        self.stacked = QStackedWidget()

        # 创建各个页面
        self.page1 = FirstPage()
        self.page2 = VideoSettingPage()
        self.page3 = DBSettingPage()
        self.page4 = ClawerSettingPage()

        # 添加到 stacked
        self.stacked.addWidget(self.page1)  # index 0
        self.stacked.addWidget(self.page2)  # index 1
        self.stacked.addWidget(self.page3)  # index 2
        self.stacked.addWidget(self.page4)  # index 3

        mainlayout.addWidget(self.tree)
        mainlayout.addWidget(self.stacked)

        # === 信号连接：点击树节点切换页面 ===
        self.tree.itemClicked.connect(self.on_tree_item_clicked)

        # 默认选中第一个项
        self.tree.setCurrentItem(root1)
        
        self.btn_default.clicked.connect(self.restore_default_settings)
        self.btn_ok.clicked.connect(self.btn_accept)
        self.btn_cancal.clicked.connect(self.btn_reject)

    def on_tree_item_clicked(self, item, column):
        """根据点击的树节点切换右侧页面"""
        # 通过 item 的文本或自定义数据判断
        text = item.text(0)

        if text == "软件信息":
            self.stacked.setCurrentIndex(0)
        elif text == "视频相关":
            self.stacked.setCurrentIndex(1)
        elif text == "爬虫相关":
            self.stacked.setCurrentIndex(3)
        elif text == "数据库":
            self.stacked.setCurrentIndex(2)
        # 可以继续添加更多项...

        # 更通用方式：用 setData 存储页面索引（推荐扩展时用）
        # index = item.data(0, Qt.UserRole)
        # if index is not None:
        #     self.stacked.setCurrentIndex(index)

    @Slot()
    def restore_default_settings(self):
        """恢复默认设置"""
        self.accept()


    @Slot()
    def btn_accept(self):
        """点击确定按钮时调用，保存设置"""
        self.page2.accept()
        self.accept()  # 关闭对话框

    @Slot()
    def btn_reject(self):
        """点击取消按钮时调用，放弃更改"""
        self.reject()  # 关闭对话框


