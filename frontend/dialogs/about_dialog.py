"""About dialog window displaying application metadata and technology stack."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from frontend.version import APP_NAME, BUILD, BUILD_DATE, COPYRIGHT, VERSION


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setMinimumWidth(520)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        icon = QLabel()
        try:
            from PySide6.QtGui import QIcon
            icon.setPixmap(QIcon.fromTheme("help-about", QIcon("assets/icons/zime.svg")).pixmap(72, 72))
        except Exception:
            from PySide6.QtWidgets import QWidget
            icon_ = QLabel("ZIME")
            icon_.setStyleSheet("font-size:28pt;font-weight:bold;")
            hl.addWidget(icon_)
        hl.addSpacing(16)
        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size:24pt;font-weight:bold;")
        version = QLabel(f"Version {VERSION}")
        version.setStyleSheet("font-size:14pt;")
        hl.addWidget(title)
        layout.addWidget(header)
        layout.addSpacing(8)
        layout.addWidget(version)
        layout.addWidget(QLabel(COPYRIGHT))
        build_info = QLabel(f"Build {BUILD} | {BUILD_DATE}")
        build_info.setStyleSheet("font-size:10pt;color:#666;")
        layout.addWidget(build_info)

        stack = QLabel(getattr(parent, "_stack", None).__class__.__name__ if hasattr(parent, "_stack") else "MainWindow")
        from platform import python_version

        from PySide6.QtCore import QT_VERSION_STR
        py = QLabel(f"Python {python_version()}")
        py.setStyleSheet("font-size:10pt;")
        qt = QLabel(f"Qt {QT_VERSION_STR}")
        qt.setStyleSheet("font-size:10pt;")
        oslabel = QLabel("Windows" if "win" in sys.platform else "Linux" if "linux" in sys.platform else "macOS")
        oslabel.setStyleSheet("font-size:10pt;")
        layout.addSpacing(12)
        layout.addWidget(QLabel("Runtime:"))
        layout.addWidget(py)
        layout.addWidget(QWidget())
        layout.addWidget(qt)
        layout.addWidget(QWidget())
        layout.addWidget(oslabel)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(self.accept)
        layout.addWidget(bb)

        del sys  # avoid leaking symbols in module scope
