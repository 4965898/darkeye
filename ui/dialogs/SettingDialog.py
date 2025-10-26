from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel,QVBoxLayout,QTextEdit,QDialog,QFileDialog,QGridLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Slot
import logging
from ui.base import LazyWidget
from config import BASE_DIR,DATABASE,INI_FILE,ICONS_PATH,PRIVATE_DATABASE,DATABASE_BACKUP_PATH,PRIVATE_DATABASE_BACKUP_PATH
from controller import MessageBoxService
from pathlib import Path

class SettingDialog(QDialog):
    #软件的设置
    def __init__(self,parent=None):
        super().__init__(parent)
        logging.info("----------软件设置窗口----------")
        self.setWindowTitle("软件设置")
        self.setWindowIcon(QIcon(str(ICONS_PATH / "settings.png")))
        self.resize(400,400)
        self.msg=MessageBoxService(self)
        path_label=QLabel(f"软件的工作文件夹{str(BASE_DIR)}")
        path_label2=QLabel(f"软件的公共数据库文件位置{str(DATABASE)}")
        path_label3=QLabel(f"ini文件的位置{INI_FILE}")

        self.btn_vacuum=QPushButton("数据库清理碎片")#包括清理两个数据库
        self.btn_cover_check=QPushButton("图片数据一致性检查")

        self.btn_commit=QPushButton("保存设置")
        self.btn_commit.setVisible(False)
        
        self.btn_backupDB = QPushButton()
        self.btn_backupDB.setText("备份公共数据库")
        self.btn_backupDB.setToolTip("将现有的数据库打上时间戳备份")
        self.btn_backupDB.setIcon(QIcon(str(ICONS_PATH / "database.png")))


        self.btn_restoreDB = QPushButton()
        self.btn_restoreDB.setText("还原公共数据库")
        self.btn_restoreDB.setToolTip("在备份的数据库里选择一个数据还原，覆盖现有的数据库")
        self.btn_restoreDB.setIcon(QIcon(str(ICONS_PATH / "database.png")))


        self.btn_backupDB2 = QPushButton()
        self.btn_backupDB2.setText("备份私有数据库")
        self.btn_backupDB2.setToolTip("将现有的数据库打上时间戳备份")
        self.btn_backupDB2.setIcon(QIcon(str(ICONS_PATH / "database.png")))


        self.btn_restoreDB2 = QPushButton()
        self.btn_restoreDB2.setText("还原私有数据库")
        self.btn_restoreDB2.setToolTip("在备份的数据库里选择一个数据还原，覆盖现有的数据库")
        self.btn_restoreDB2.setIcon(QIcon(str(ICONS_PATH / "database.png")))



        layout1=QGridLayout()

        layout1.addWidget(self.btn_vacuum,0,0)
        layout1.addWidget(self.btn_cover_check,0,1)
        layout1.addWidget(self.btn_backupDB,1,0)
        layout1.addWidget(self.btn_restoreDB,1,1)
        layout1.addWidget(self.btn_backupDB2,2,0)
        layout1.addWidget(self.btn_restoreDB2,2,1)

        #总装
        layout=QVBoxLayout(self)
        layout.addLayout(layout1)
        layout.addWidget(self.btn_commit)
        layout.addWidget(path_label)
        layout.addWidget(path_label2)
        layout.addWidget(path_label3)

        self.signal_connect()


    def signal_connect(self):
        from core.database.db_utils import sqlite_vaccum
        self.btn_cover_check.clicked.connect(self.check_image_consistency)
        self.btn_vacuum.clicked.connect(sqlite_vaccum)
        self.btn_commit.clicked.connect(self.submit)

        self.btn_backupDB.clicked.connect(lambda:self.backup_db("public"))
        self.btn_restoreDB.clicked.connect(lambda:self.restoreDB("public"))
        self.btn_backupDB2.clicked.connect(lambda:self.backup_db("private"))
        self.btn_restoreDB2.clicked.connect(lambda:self.restoreDB("private"))


    @Slot()
    def check_image_consistency(self):
        '''检查数据库中的图片一致性的问题'''
        from core.database.db_utils import image_consistency
        image_consistency(True,"cover")
        image_consistency(True,"actress")
        image_consistency(True,"actor")
        self.msg.show_info("提示","处理好图片一致性问题，删除多余图片")
        
    @Slot()
    def submit(self):
        #获得基本数据
        logging.debug("保存设置")


    @Slot()
    def restoreDB(self,access_level:str):
        #选择一个备份的数据库还原
        #这个目前有，这个是直接覆盖，风险问题，数据库在写入，后面再改全局单例数据库管理器来管理所有的连接
        if access_level=="public":
            backup_path=DATABASE_BACKUP_PATH
            target_path=DATABASE
        elif access_level=="private":
            backup_path=PRIVATE_DATABASE_BACKUP_PATH
            target_path=PRIVATE_DATABASE     
        else:
            logging.info("错误，未选择等级")

        from core.database.backup_utils import restore_database,restore_backup_safely
        file_path, _ = QFileDialog.getOpenFileName(
            self,               # 父组件
            "选择一个数据库",      # 对话框标题
            str(backup_path),                 # 起始路径
            "*.db"  # 文件过滤器
        )

        if not file_path:
            return
    
        if not self.msg.ask_yes_no("确认恢复","是否用该备份覆盖现有数据库？操作不可撤销！"):
            return

        success = restore_backup_safely(Path(file_path), target_path)
        if success:
            self.msg.show_info("恢复成功", "数据库恢复完成。")
        else:
            self.msg.show_critical("恢复失败", "数据库恢复失败，请检查文件是否有效。")

    @Slot()
    def backup_db(self,access_level:str):
        '''备份数据库'''
        if access_level=="public":
            backup_path=DATABASE_BACKUP_PATH
            target_path=DATABASE
        elif access_level=="private":
            backup_path=PRIVATE_DATABASE_BACKUP_PATH
            target_path=PRIVATE_DATABASE     
        else:
            logging.info("错误，未选择等级")

        from core.database.backup_utils import backup_database
        try:
            path=backup_database(target_path,backup_path)
            self.msg.show_info("备份成功",f"备份路径{path}")
        except Exception as e:
            self.msg.show_critical(self,"备份失败",f"{str(e)}")