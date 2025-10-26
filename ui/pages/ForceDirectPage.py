#个人女优详细的面板
from PySide6.QtWidgets import QHBoxLayout, QWidget, QLabel,QVBoxLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt,Slot
from core.database.query import get_record_count_in_days,get_top_actress_by_masturbation_count
import logging
from ui.widgets import ActressCard
from ui.basic.Effect import ShadowEffectMixin
from ui.base import LazyWidget
#from ui.statistics import ForceDirectedView
from controller.GlobalSignalBus import global_signals
from ui.statistics.forec_view_bh import ForceDirectedView
from ui.statistics.force_view_d3_numpy import ForceView
from ui.statistics.force_view_d3_numpy import generate_graph

class ForceDirectPage(LazyWidget):
    def __init__(self):
        super().__init__()

    def _lazy_load(self):
        logging.info("----------个人数据界面----------")
        mainlayout = QVBoxLayout(self)
        mainlayout.setContentsMargins(0, 0, 0, 0)
        forcedirectedview=ForceView(generate_graph())
        mainlayout.addWidget(forcedirectedview)

        #1.每个作品算一个点，相似度算法，计算每两个作品之间的相似度[0,1]

        #2.当阈值>0.8时，作品间连线

        #3.发现图中的团，从大到小，团可以稍微缺少几条边

        #4.确定团的中心，团内相似度最高的线，取消团内的所有连接线，改成从团中心发散

        #5加上特殊结构线

        #6力导向图绘制，这个优化性能，至少1000个点不卡顿
        


