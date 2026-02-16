
import time
from PySide6.QtCore import QRunnable, QThreadPool, Signal, Slot, QObject,QThread
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget
import logging,threading

# 定义信号类（用于线程间通信）
class WorkerSignals(QObject):
    finished = Signal(object)  # 完成信号，返回结果

# 定义任务类,是那种一个一个的任务
class Worker(QRunnable):
    '''给现程池用的
    QThreadPool+QRunnable
    使用方法：
    worker=Worker(lambda:SearchSingleActressInfo(self.actress_id,self.actress_name[0]["jp"]))#传一个函数名进去
    worker.signals.finished.connect(self.on_result)
    QThreadPool.globalInstance().start(worker)
    '''
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.signals = WorkerSignals()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result=None

    def run(self):
        try:
            #logging.info("开启一个后台线程")
            thread_name = self.func.__name__  # 假设func有名字
            current_qt_thread = QThread.currentThread()
            current_qt_thread.setObjectName(thread_name)
            
            print(f"开始任务 - Python线程名: {threading.current_thread().name}, 线程对象: {current_qt_thread}")
            self.result = self.func(*self.args, **self.kwargs)
            self.signals.finished.emit(self.result)#把爬虫后返回结果传回去
            #logging.info(f"线程完成任务，信号发射，返回结果{self.result}")
            print(f"结束任务 - {threading.current_thread().name}")
        except Exception as e:
            logging.warning(f"出错误:{e}")
            self.signals.finished.emit(None)