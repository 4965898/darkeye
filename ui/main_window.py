from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QToolButton, QFrame, QStyle,QStatusBar,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QSize, Signal, QEasingCurve

import os,psutil,logging
from PySide6.QtWidgets import QWidget,QStackedWidget,QPushButton,QHBoxLayout, QVBoxLayout,QLineEdit,QLabel,QStatusBar,QMainWindow
from PySide6.QtCore import Qt,Signal,QTimer,Slot,QSize,QThreadPool,QObject,QEvent,QRect
from PySide6.QtGui import QIcon,QKeySequence,QShortcut,QPainter,QColor,QAction
from config import ICONS_PATH,APP_VERSION,set_max_window
from ui.pages import WorkPage,ManagementPage,StatisticsPage,ActressPage,AvPage,SingleActressPage,SingleWorkPage,ModifyActressPage,ActorPage,ModifyActorPage,SettingPage
from ui.pages import CoverBrowser
from core.recommendation.Recommend import recommendStart,randomRec
from ui.basic import IconPushButton,ToggleSwitch,StatusBarNotification,StateToggleButton
from controller.GlobalSignalBus import global_signals
from core.database.query import get_serial_number
from ui.widgets.text.CompleterLineEdit import CompleterLineEdit
from ui.widgets.StatusBarNotification import TaskListWindow
from controller import StatusManager,TaskManager,ShortcutRegistry
from utils.utils import capture_full





class MenuButton(QWidget):
    '''左侧抽屉里的按钮'''
    clicked = Signal()
    
    def __init__(self, text, icon_name, expanded_width=240, collapsed_width=60):
        super().__init__()
        self.setFixedHeight(50)
        self.setFixedWidth(expanded_width)  # 锁死宽度，关键！
        
        # 关键设置：允许 QWidget 渲染 QSS 背景
        self.setAttribute(Qt.WA_StyledBackground)
        
        # 初始化状态
        self._is_selected = False
        
        # 1. 容器布局：不使用自动间距
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # 2. 图标层：位置完全固定
        self.icon_label = IconPushButton(str(ICONS_PATH / icon_name), color="#8a8e99")
        self.icon_label.setFixedSize(collapsed_width, 50)  # 宽度等于折叠宽度
        
        # 3. 文字层：起始位置在 60px 之后
        self.text_label = QLabel(text)
        self.text_label.setStyleSheet("color: #8a8e99; font-size: 13px; border: none;")
        
        # 关键：让子控件不处理鼠标事件，防止它们"遮挡"父级的悬停状态
        self.icon_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.text_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.layout.addWidget(self.icon_label)
        self.layout.addWidget(self.text_label)
        self.layout.addStretch()  # 把剩下的空间填满
        
        # 4. 初始样式 - 添加选中状态的竖线效果
        self._update_style()
    
    def _update_style(self):
        """更新样式表，根据选中状态显示不同的左侧竖线"""
        if self._is_selected:
            style = """
                MenuButton {
                    background-color: #F7E6B0;
                    border-left: 3px solid #DBCA97;
                }
                MenuButton:hover {
                    background-color: #F7E6B0;
                }
                QLabel {
                    color: white;
                    font-size: 13px;
                    background: transparent;
                }
                MenuButton:hover QLabel {
                    color: white;
                }
            """
        else:
            style = """
                MenuButton {
                    background-color: transparent;
                    border-left: 3px solid transparent;
                }
                MenuButton:hover {
                    background-color: #F7E6B0;
                }
                QLabel {
                    color: #8a8e99;
                    font-size: 13px;
                    background: transparent;
                }
                MenuButton:hover QLabel {
                    color: white;
                }
            """
        
        self.setStyleSheet(style)
        
        # 同时更新图标颜色
        #if self._is_selected:
        #    self.icon_label.setIconColor("#BD93F9")  # 使用紫色图标表示选中
        #else:
        #    self.icon_label.setIconColor("#8a8e99")
    
    def set_selected(self, selected: bool):
        """设置选中状态"""
        if self._is_selected != selected:
            self._is_selected = selected
            self._update_style()
    
    def is_selected(self):
        """获取选中状态"""
        return self._is_selected
    
    def mousePressEvent(self, event):
        self.clicked.emit()

class Sidebar(QWidget):
    '''左侧抽屉栏'''
    def __init__(self, parent=None):
        super().__init__(parent)
        self.expanded_width = 240
        self.collapsed_width = 60
        
        # 初始状态
        self.setMinimumWidth(self.collapsed_width)
        self.setMaximumWidth(self.collapsed_width)
        self._is_expanded = False
        
        # 背景色
        #self.setStyleSheet("background-color: #282c34;")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 1. 顶部切换按钮
        self.toggle_btn = self._create_menu_btn("隐藏菜单", "menu.svg")
        self.toggle_btn.clicked.connect(self.toggle_menu)
        self.main_layout.addWidget(self.toggle_btn)
        
        # 2. 菜单项容器
        self.menu_container = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_container)
        self.menu_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_layout.setSpacing(0)
        
        # 添加几个按钮
        self.btn_home = self._create_menu_btn("首页", "house.svg")
        self.btn_database = self._create_menu_btn("管理", "database.svg")
        self.btn_chart = self._create_menu_btn("统计", "chart-line.svg")
        self.btn_work = self._create_menu_btn("作品", "film.svg")
        self.btn_actress = self._create_menu_btn("女优","venus.svg")
        self.btn_actor = self._create_menu_btn("男优","mars.svg")
        self.btn_av = self._create_menu_btn("暗黑界","scroll-text.svg")
        self.btn_settings = self._create_menu_btn("软件设置", "settings.svg")

        
        # 连接点击信号
        self.btn_home.clicked.connect(lambda: self._on_menu_item_clicked(self.btn_home))
        self.btn_chart.clicked.connect(lambda: self._on_menu_item_clicked(self.btn_chart))
        #self.btn_settings.clicked.connect(lambda: self._on_menu_item_clicked(self.btn_settings))
        self.btn_actress.clicked.connect(lambda: self._on_menu_item_clicked(self.btn_actress))
        self.btn_actor.clicked.connect(lambda: self._on_menu_item_clicked(self.btn_actor))
        self.btn_database.clicked.connect(lambda: self._on_menu_item_clicked(self.btn_database))
        self.btn_work.clicked.connect(lambda: self._on_menu_item_clicked(self.btn_work))
        self.btn_av.clicked.connect(lambda: self._on_menu_item_clicked(self.btn_av))
        
        self.menu_layout.addWidget(self.btn_home)
        self.menu_layout.addWidget(self.btn_database)
        self.menu_layout.addWidget(self.btn_work)
        self.menu_layout.addWidget(self.btn_chart)
        self.menu_layout.addWidget(self.btn_actress)
        self.menu_layout.addWidget(self.btn_actor)
        self.menu_layout.addWidget(self.btn_av)
        self.menu_layout.addStretch()
        self.menu_layout.addWidget(self.btn_settings)
        
        
        self.main_layout.addWidget(self.menu_container)
        
        # 初始化选中第一个菜单项
        self._current_selected = self.btn_home
        self.btn_home.set_selected(True)
        
        # 动画组
        self.anim = QPropertyAnimation(self, b"minimumWidth")
        self.anim.setDuration(500)
        self.anim.setEasingCurve(QEasingCurve.InOutQuint)
        
        # 实时同步 maximumWidth，确保动画顺滑
        self.anim.valueChanged.connect(lambda v: self.setMaximumWidth(v))
        
        # 设置动画的总区间
        self.anim.setStartValue(self.collapsed_width)
        self.anim.setEndValue(self.expanded_width)
    
    def _create_menu_btn(self, text, icon_type):
        # 使用我们自定义的分层按钮
        btn = MenuButton(text, icon_type, self.expanded_width, self.collapsed_width)
        return btn
    
    def _on_menu_item_clicked(self, clicked_button):
        """处理菜单项点击事件"""
        if self._current_selected != clicked_button:
            # 取消之前选中的按钮
            if self._current_selected:
                self._current_selected.set_selected(False)
            
            # 设置新的选中按钮
            clicked_button.set_selected(True)
            self._current_selected = clicked_button
        
        # 发出信号（如果需要）
        # 这里可以根据具体需求添加业务逻辑
    
    def get_selected_menu(self):
        """获取当前选中的菜单项"""
        return self._current_selected
    
    def toggle_menu(self):
        # 动画逻辑保持不变
        if self._is_expanded:
            # 当前是展开状态，想要收起
            self.anim.setDirection(QPropertyAnimation.Direction.Backward)
        else:
            # 当前是收起状态，想要展开
            self.anim.setDirection(QPropertyAnimation.Direction.Forward)
        
        target_width = self.expanded_width if not self._is_expanded else self.collapsed_width
        self.anim.start()
        self._is_expanded = not self._is_expanded

class TopBar(QWidget):
    '''顶栏'''
    def __init__(self, parent=None):
        super().__init__(parent)

        self.main_layout=QHBoxLayout(self)

        self.QLE=CompleterLineEdit(get_serial_number)
        #self.QLE.setClearButtonEnabled(True)
        self.QLE.setMaximumWidth(200)
        self.QLE.setFixedHeight(32)
        self.QLE.setStyleSheet("""
            QLineEdit {
                color: black;  
                background-color: transparent;  /* 可选：背景透明或其他颜色 */
                border: 2px solid black;        /* 白色边框 */ 
            }
        """)
        self.btn_help=IconPushButton("circle-question-mark.svg",iconsize=24,outsize=24,color="#000000")
        self.main_layout.addWidget(self.QLE)
        self.main_layout.addStretch()
        self.main_layout.addWidget(self.btn_help)
        

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("暗之眼 "+"V"+APP_VERSION)
        self.setWindowIcon(QIcon(str(ICONS_PATH / "logo.svg"))) 
        self.resize(1000, 700)

        # ==================== 状态栏设置 ====================
        self.myStatusBar = QStatusBar()
        self.statusmanager=StatusManager(self.myStatusBar)#初始化消息管理
        #self.setStatusBar(self.myStatusBar)
        self.memlabel = QLabel("内存占用:0 MB")
        self.myStatusBar.addPermanentWidget(self.memlabel)

        self.thread_count_label = QLabel("后台线程: 0")
        self.myStatusBar.addPermanentWidget(self.thread_count_label)
        self.greenbutton=StateToggleButton("sprout.svg","#5E5E5E","sprout.svg","#00FF40",16,16)
        self.greenbutton.stateChanged.connect(global_signals.green_mode_changed.emit)#转发信号

        self.myStatusBar.addPermanentWidget(self.greenbutton)

        self.taskwindow=TaskListWindow(self)
        self.notifier = StatusBarNotification(self.taskwindow)
        self.taskmanager=TaskManager.instance(self.taskwindow,self.notifier)#初始化后台任务管理

        self.myStatusBar.addPermanentWidget(self.notifier)

        #内存显示每秒刷新
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_memory)
        self.timer.timeout.connect(self.update_thread_count)
        self.timer.start(500)  # 每秒更新

        #======================整体布局设置==========================
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.sidebar = Sidebar()
        self.right_widget=QWidget()
        self.right_layout=QVBoxLayout(self.right_widget)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)

        self.topbar=TopBar()
        self.stack = QStackedWidget()
        self.right_layout.addWidget(self.topbar)
        self.right_layout.addWidget(self.stack)
        self.right_layout.addWidget(self.myStatusBar)
        

        #左右两栏布局
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.right_widget)


        self.stackPageConnectMenu()

        # A. 初始化配置中心
        self.registry = ShortcutRegistry()
        self.init_actions()
        self.jump_connect()
        self.signal_connect()

    def signal_connect(self):
        '''信号连接'''
        self.topbar.btn_help.clicked.connect(self.OpenHelpAction.trigger)
        self.topbar.QLE.returnPressed.connect(lambda:self.search(self.topbar.QLE.text().strip()))
        
    def stackPageConnectMenu(self):
        '''切换页面设置与菜单的连接'''
        self.page_home=CoverBrowser(randomRec())
        self.page_management=ManagementPage()
        self.page_statistics=StatisticsPage()
        self.page_work=WorkPage()
        self.page_actress=ActressPage()
        self.page_actor=ActorPage()
        self.page_av=AvPage()
        self.page_single_actress=SingleActressPage()
        self.page_single_work=SingleWorkPage()
        self.page_modify_actress=ModifyActressPage()
        self.page_modify_actor=ModifyActorPage()
        self.page_setting=SettingPage()

        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_management)
        self.stack.addWidget(self.page_statistics)
        self.stack.addWidget(self.page_work)
        self.stack.addWidget(self.page_actress)
        self.stack.addWidget(self.page_actor)
        self.stack.addWidget(self.page_av)

        self.stack.addWidget(self.page_single_actress)
        self.stack.addWidget(self.page_single_work)
        self.stack.addWidget(self.page_modify_actress)
        self.stack.addWidget(self.page_modify_actor)
        self.stack.addWidget(self.page_setting)

        self.sidebar.btn_home.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.sidebar.btn_database.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.sidebar.btn_chart.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        self.sidebar.btn_work.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        self.sidebar.btn_actress.clicked.connect(lambda: self.stack.setCurrentIndex(4))
        self.sidebar.btn_actor.clicked.connect(lambda: self.stack.setCurrentIndex(5))
        self.sidebar.btn_av.clicked.connect(lambda: self.stack.setCurrentIndex(6))
        self.sidebar.btn_settings.clicked.connect(lambda: self.stack.setCurrentIndex(11))

        #self.btn_settings.clicked.connect(lambda: self._on_menu_item_clicked(self.btn_settings))

    def closeEvent(self, event):
        logging.info("--------------------程序关闭--------------------")
        set_max_window(self.isMaximized())
        #if not self.isMaximized():
            #set_size_pos(self.size(), self.pos())
        super().closeEvent(event)
        #数据库
        from core.database.connection import QSqlDatabaseManager
        #这个QSqlDatabase是长连接，最后关闭
        db_manager = QSqlDatabaseManager()
        db_manager.close_all()
        from core.database.db_utils import clear_temp_folder
        clear_temp_folder()#退出时清理临时数据

    def init_actions(self):
        """统一管理所有动作和默认快捷键"""
        from ui.dialogs.open import openAddMasturbationDialog,openAddQuickWorkDialog,openAddMakeLoveDialog,openAddSexualArousalDialog,on_help

        self.AddMasturbationRecordAction=QAction("添加撸管记录",self)
        self.AddMasturbationRecordAction.setShortcut(QKeySequence(self.registry.get_shortcut("add_masturbation_record")))
        self.AddMasturbationRecordAction.triggered.connect(openAddMasturbationDialog)
        self.registry.actions_map["add_masturbation_record"]=self.AddMasturbationRecordAction

        self.AddQuickWorkAction=QAction("快速添加番号",self)
        self.AddQuickWorkAction.setShortcut(QKeySequence(self.registry.get_shortcut("add_quick_work")))
        self.AddQuickWorkAction.triggered.connect(openAddQuickWorkDialog)
        self.registry.actions_map["add_quick_work"]=self.AddQuickWorkAction

        self.AddMakeLoveAction=QAction("添加做爱记录",self)
        self.AddMakeLoveAction.setShortcut(QKeySequence(self.registry.get_shortcut("add_makelove_record")))
        self.AddMakeLoveAction.triggered.connect(openAddMakeLoveDialog)
        self.registry.actions_map["add_makelove_record"]=self.AddMakeLoveAction

        self.AddSexualArousalAction=QAction("添加晨勃记录",self)
        self.AddSexualArousalAction.setShortcut(QKeySequence(self.registry.get_shortcut("add_sexual_rousal_record")))
        self.AddSexualArousalAction.triggered.connect(openAddSexualArousalDialog)
        self.registry.actions_map["add_sexual_rousal_record"]=self.AddSexualArousalAction

        self.OpenHelpAction=QAction("打开帮助",self)
        self.OpenHelpAction.setShortcut(QKeySequence(self.registry.get_shortcut("open_help")))
        self.OpenHelpAction.triggered.connect(on_help)
        self.registry.actions_map["open_help"]=self.OpenHelpAction

        self.FocusSearchAction=QAction("搜索",self)
        self.FocusSearchAction.setShortcut(QKeySequence(self.registry.get_shortcut("search")))
        self.FocusSearchAction.triggered.connect(lambda:self.topbar.QLE.setFocus())
        self.registry.actions_map["search"]=self.FocusSearchAction

        self.AllCaptureAction=QAction("全软件截图",self)
        self.AllCaptureAction.setShortcut(QKeySequence(self.registry.get_shortcut("allcapture")))
        self.AllCaptureAction.triggered.connect(lambda:capture_full(self))
        self.registry.actions_map["allcapture"]=self.AllCaptureAction

        self.CaptureAction=QAction("部分截图",self)
        self.CaptureAction.setShortcut(QKeySequence(self.registry.get_shortcut("capture")))
        self.CaptureAction.triggered.connect(self.handle_capture)
        self.registry.actions_map["capture"]=self.CaptureAction

        # 核心：必须将 Action 添加到窗口，否则快捷键全局无效
        self.addActions(list(self.registry.actions_map.values()))




    def jump_connect(self):
        '''转发信号中心，各种信号都在这里转发'''
        from controller.GlobalSignalBus import global_signals

        global_signals.modify_actress_clicked.connect(self.show_modify_actress)
        global_signals.modify_work_clicked.connect(self.show_modify_work_page)
        global_signals.work_clicked.connect(self.show_single_work_page)
        global_signals.actress_clicked.connect(self.show_single_actress)
        global_signals.tag_clicked.connect(self.search_work_by_tag)
        global_signals.modify_actor_clicked.connect(self.show_modify_actor)
        global_signals.actor_clicked.connect(self.show_single_actor)

        
    @Slot(str)
    def search(self,serial_number):
        '''跳转并搜索'''
        logging.debug("跳转到作品页面")
        self.stack.setCurrentWidget(self.page_work)
        self.sidebar._on_menu_item_clicked(self.sidebar.btn_work)
        self.page_work.serial_number_input.setText(serial_number)

    @Slot(int)
    def show_single_actor(self,actor_id:int):
        logging.debug("跳转到男优过滤页")
        self.stack.setCurrentWidget(self.page_work)
        self.sidebar._on_menu_item_clicked(self.sidebar.btn_work)
        from core.database.query import get_actor_allname
        namelist=get_actor_allname(actor_id)
        name=namelist[0].get("cn")
        self.page_work.actor_input.setText(name)

    @Slot(int)
    def show_modify_actor(self,actor_id:int):
        logging.debug("跳转到修改男优信息页")
        self.stack.setCurrentWidget(self.page_modify_actor)
        self.page_modify_actor.update(actor_id)
        self.sidebar._on_menu_item_clicked(self.sidebar.btn_actor)

    @Slot(int)
    def search_work_by_tag(self,tag_id:int):
        '''跳转到作品搜索页面并添加tag_id'''
        logging.debug("跳转到作品页面")
        self.stack.setCurrentWidget(self.page_work)
        self.page_work.tagselector.load_with_ids([tag_id])
        self.sidebar._on_menu_item_clicked(self.sidebar.btn_work)

    @Slot(int)
    def show_modify_actress(self,actress_id:int):
        '''跳转到编辑女优界面'''
        self.stack.setCurrentWidget(self.page_modify_actress)
        self.page_modify_actress.update(actress_id)
        self.sidebar._on_menu_item_clicked(self.sidebar.btn_actress)

    @Slot(int)
    def show_single_work_page(self,work_id:int):
        '''跳转到单个作品的界面'''
        self.stack.setCurrentWidget(self.page_single_work)
        self.page_single_work.update(work_id)
        self.sidebar._on_menu_item_clicked(self.sidebar.btn_work)

    @Slot(str)
    def show_modify_work_page(self,serial_number:str):#跳转到编辑界面
        '''跳转到管理的界面，然后展示出来'''
        self.stack.setCurrentWidget(self.page_management)
        self.page_management.tab_widget.setCurrentWidget(self.page_management.worktab)
        self.page_management.worktab.input_serial_number.setText(serial_number)
        self.page_management.worktab.btn_load_form_db.click()
        self.sidebar._on_menu_item_clicked(self.sidebar.btn_database)

    @Slot(int)
    def show_single_actress(self,actress_id:int):
        '''跳转到单独的女优界面'''
        self.stack.setCurrentWidget(self.page_single_actress)
        self.page_single_actress.update(actress_id)
        self.sidebar._on_menu_item_clicked(self.sidebar.btn_actress)

    @Slot()
    def handle_capture(self):
        logging.debug("触发快捷键C")
        cur_page=self.stack.currentWidget()
        from utils.utils import capture_full
        match cur_page:
            case self.page_home:
                capture_full(self.page_home)
            case self.page_work:  
                capture_full(self.page_work.lazy_area.widget())
            case self.page_actress:
                capture_full(self.page_actress.lazy_area.widget())
            case self.page_single_actress:
                capture_full(self.page_single_actress.single_actress_info)


    @Slot()
    def update_memory(self):
        '''更新内存'''
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss / 1024 ** 2  # 转换为MB
        self.memlabel.setText(f"内存使用: {mem:.2f} MB")

    @Slot()
    def update_thread_count(self):
        """更新状态栏显示后台线程数量"""
        active = QThreadPool.globalInstance().activeThreadCount()

        self.thread_count_label.setText(f"后台线程: {active}")


