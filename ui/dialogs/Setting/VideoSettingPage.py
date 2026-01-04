from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel,QVBoxLayout,QTextEdit,QDialog,QFileDialog,QGridLayout,QWidget
from PySide6.QtGui import QIcon
from PySide6.QtCore import Slot
import logging
from pathlib import Path
from ui.basic import MultiplePathManagement
from config import get_video_path

class VideoSettingPage(QWidget):
    '''这个是视频相关设置页面'''
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.pathManagement=MultiplePathManagement(label_text="视频文件夹路径管理：")
        layout.addWidget(self.pathManagement)
        
        self.pathManagement.load_paths(get_video_path())

    def accept(self):
        # 保存路径设置
        paths=self.pathManagement.get_paths()
        # 这里可以添加代码将paths保存到配置文件或应用设置中
        from config import update_video_path
        update_video_path(paths)
        logging.info(f"保存的视频路径设置写入.ini: {paths}")