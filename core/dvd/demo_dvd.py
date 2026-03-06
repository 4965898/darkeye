"""Qt Quick 3D 加载 DVD 模型演示。"""
from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtCore import QUrl

from config import WORKCOVER_PATH

_IMG_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def path_to_file_url(path: Path) -> str:
    """将本地路径转为 QML 可用的 file:// URL。"""
    return QUrl.fromLocalFile(str(path.resolve())).toString()


class work:
    '''弄一个数据类'''
    def __init__(self,work_id,serial_number,cover_url) -> None:
        self.work_id=work_id
        self.serial_number=serial_number
        self.cover_url=cover_url
        self.actress_list=[]
        self.actor_list=[]
        self.tag_list=[]
        self.release_date=[]
        self.director=[]
        self.maker=None
        self.title=""
        self.story=""

        


def main() -> None:
    app = QApplication(sys.argv)

    dvd_dir = Path(__file__).resolve().parent
    dvd_qml_path = dvd_dir / "Dvd.qml"
    if not dvd_qml_path.exists():
        print(f"Dvd.qml 不存在: {dvd_qml_path}")
        sys.exit(1)
    dvd_qml_url = path_to_file_url(dvd_qml_path)
    print(f"使用 Dvd.qml 模型: {dvd_qml_path}")

    window = QMainWindow()
    window.setWindowTitle("Qt Quick 3D - DVD 模型")
    window.resize(800, 600)
    dvd_count = 100
    quick_widget = QQuickWidget()
    ctx = quick_widget.rootContext()
    ctx.setContextProperty("modelUrl", "")  # 不使用外部 glb
    ctx.setContextProperty("modelScale", 1)
    ctx.setContextProperty("dvdQmlUrl", dvd_qml_url)
    ctx.setContextProperty("dvdCount", dvd_count)
    ctx.setContextProperty("dvdSpacing", 0.0145)
    # 每份 DVD 的贴图：优先用 resources/public/workcovers 下的图片

    workcover_images = sorted(p for p in WORKCOVER_PATH.iterdir() if p.suffix.lower() in _IMG_SUFFIXES) if WORKCOVER_PATH.exists() else []
    if workcover_images:
        texture_urls = [path_to_file_url(workcover_images[i % len(workcover_images)]) for i in range(dvd_count)]
    else:
        texture_urls = ["maps/0.png", "maps/1.png", "maps/0.png"]
    ctx.setContextProperty("dvdTextureSources", texture_urls)
    ctx.setContextProperty("cameraDistance", 0.35)
    ctx.setContextProperty("selectedDvdDistance", 0.28)

    # 默认开启 wireframe，确认模型几何后改为 False
    ctx.setContextProperty("showWireframe", False)
    quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)

    qml_dir = Path(__file__).resolve().parent
    qml_path = qml_dir / "dvd_scene.qml"
    quick_widget.setSource(QUrl.fromLocalFile(str(qml_path)))

    if quick_widget.status() == QQuickWidget.Error:
        print("QML 加载失败，请检查 Qt Quick 3D 模块是否可用")
        sys.exit(1)

    window.setCentralWidget(quick_widget)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
