"""PyQt6 HUD: reactive orb, activity log, controls, confirmation banner."""
import math, time
from PyQt6.QtCore import QObject, QPointF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QVBoxLayout, QWidget)
from core import config

VOICES = ["Puck", "Charon", "Kore", "Fenrir", "Aoede"]
STATE_TEXT = {"connecting": "CONNECTING", "listening": "LISTENING", "speaking": "SPEAKING",
              "working": "WORKING", "muted": "MIC MUTED"}


class Bridge(QObject):
    log = pyqtSignal(str)
    state = pyqtSignal(str)
    level = pyqtSignal(float)
    confirm = pyqtSignal(str)


class Orb(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(240)
        self.state, self.target, self.smooth, self.t = "connecting", 0.0, 0.0, 0.0
        timer = QTimer(self); timer.timeout.connect(self._tick); timer.start(33)

    def set_level(self, v): self.target = max(self.target, v)

    def _tick(self):
        self.t += 0.033
        self.smooth = self.smooth * 0.7 + self.target * 0.3
        self.target *= 0.8
        self.update()

    def _color(self):
        accent = QColor(config.get("accent"))
        return {"connecting": QColor("#6b7a8c"), "muted": QColor("#d9534f"),
                "working": QColor("#f0ad4e"), "speaking": QColor("#5cf2a5")}.get(self.state, accent)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        base = min(self.width(), self.height()) * 0.2
        col = self._color()
        for i in range(4):
            r = base * (1 + 0.38 * i) + self.smooth * base * 0.6 / (i + 1) + math.sin(self.t * 2 + i) * 3
            ring = QColor(col); ring.setAlpha(int(170 / (i + 1)))
            p.setPen(QPen(ring, 2)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawEllipse(c, r, r)
        g = QRadialGradient(c, base * 1.1)
        core = QColor(col); core.setAlpha(230); g.setColorAt(0, core)
        edge = QColor(col); edge.setAlpha(20); g.setColorAt(1, edge)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(g))
        rr = base * (1 + self.smooth * 0.4)
        p.drawEllipse(c, rr, rr)


class MainWindow(QWidget):
    def __init__(self, bridge, engine):
        super().__init__()
        self.engine = engine
        self.setWindowTitle(f"{config.get('assistant_name')} HUD")
        self.resize(560, 760)
        self.setStyleSheet("""
            QWidget { background:#0b0f14; color:#cfe8ef; font-family:'Segoe UI',sans-serif; }
            QTextEdit, QLineEdit, QComboBox { background:#111821; border:1px solid #1f2d3a; border-radius:6px; padding:6px; }
            QPushButton { background:#13202c; border:1px solid #24465a; border-radius:6px; padding:7px 12px; }
            QPushButton:hover { background:#1a2f40; } QPushButton:checked { background:#7a2a2a; }
            QFrame#banner { background:#3a2a10; border:1px solid #f0ad4e; border-radius:8px; }
        """)
        lay = QVBoxLayout(self)
        self.orb = Orb(); lay.addWidget(self.orb, 3)
        self.status = QLabel("CONNECTING"); self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.status)

        self.banner = QFrame(); self.banner.setObjectName("banner"); self.banner.hide()
        bl = QHBoxLayout(self.banner)
        self.banner_label = QLabel(""); bl.addWidget(self.banner_label, 1)
        ok, no = QPushButton("CONFIRM"), QPushButton("CANCEL")
        ok.clicked.connect(lambda: (engine.confirm_accept(), self.banner.hide()))
        no.clicked.connect(lambda: (engine.confirm_cancel(), self.banner.hide()))
        bl.addWidget(ok); bl.addWidget(no); lay.addWidget(self.banner)

        self.logbox = QTextEdit(); self.logbox.setReadOnly(True); lay.addWidget(self.logbox, 4)

        row = QHBoxLayout()
        self.input = QLineEdit(); self.input.setPlaceholderText("Type to talk to the assistant…")
        self.input.returnPressed.connect(self._send)
        row.addWidget(self.input, 1); lay.addLayout(row)

        ctl = QHBoxLayout()
        mute = QPushButton("Mute mic"); mute.setCheckable(True); mute.toggled.connect(engine.set_muted)
        ptt = QPushButton("Push-to-talk (Ctrl+Space)"); ptt.setCheckable(True)
        ptt.setChecked(config.get("push_to_talk")); ptt.toggled.connect(engine.set_ptt)
        undo = QPushButton("Undo"); undo.clicked.connect(self._undo)
        self.voice = QComboBox(); self.voice.addItems(VOICES)
        self.voice.setCurrentText(config.get("voice")); self.voice.currentTextChanged.connect(self._voice)
        for w in (mute, ptt, undo, self.voice): ctl.addWidget(w)
        lay.addLayout(ctl)

        bridge.log.connect(self.add_log)
        bridge.state.connect(self.set_state)
        bridge.level.connect(self.orb.set_level)
        bridge.confirm.connect(self.show_confirm)

    def add_log(self, msg):
        self.logbox.append(f"<span style='color:#5b7a8a'>{time.strftime('%H:%M:%S')}</span> "
                           + msg.replace("<", "&lt;").replace("\n", "<br>"))

    def set_state(self, s):
        self.orb.state = s
        self.status.setText(STATE_TEXT.get(s, s.upper()))

    def show_confirm(self, label):
        self.banner_label.setText(f"Confirm: {label}?")
        self.banner.show()

    def _send(self):
        t = self.input.text().strip()
        if t: self.engine.send_text(t); self.input.clear()

    def _undo(self):
        from core import undo
        self.add_log(undo.undo())

    def _voice(self, v):
        config.put("voice", v)
        self.add_log(f"Voice changed to {v}; reconnecting.")
        self.engine.restart_session()

    def closeEvent(self, e):
        self.engine.stop(); super().closeEvent(e)
