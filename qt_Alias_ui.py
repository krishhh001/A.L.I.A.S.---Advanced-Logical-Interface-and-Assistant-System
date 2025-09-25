from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize
from PyQt6.QtGui import QColor, QPainter, QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QProgressBar,
    QFrame,
    QSplashScreen,
)
import sys
import html
import os
import threading

try:
    import speech_recognition as sr
except Exception:
    sr = None  # voice optional

from qt_backend import FridayBackend
from qt_backend import set_tts_enabled
from qt_backend import TTS_ENABLED
try:
    from Alias import stop_speaking
except Exception:
    def stop_speaking():
        pass
try:
    # For identity check
    from Alias import eye_scan_gate
except Exception:
    def eye_scan_gate():
        return True


# ---------------- Splash Screen ----------------
class IdentitySplash(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(640, 360)
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)
        self.setStyleSheet("background-color: #000;")

    def _tick(self):
        self._t += 0.016
        self.repaint()

    def drawContents(self, painter):  # type: ignore
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(0, 0, 0))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Scanning lines
        for i in range(0, h, 12):
            alpha = 50 if (int(self._t * 60) + i // 12) % 2 == 0 else 20
            painter.fillRect(0, i, w, 2, QColor(255, 255, 255, alpha))
        # Pulsing orb
        cx, cy = w // 2, h // 2
        radius = 60 + int(8 * (1 + os.getpid() % 2) * abs((self._t * 2 % 2) - 1))
        for k in range(3):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 30 - k * 8))
            painter.drawEllipse(cx - radius - k * 15, cy - radius - k * 15, (radius + k * 15) * 2, (radius + k * 15) * 2)
        # Text
        painter.setPen(QColor("white"))
        font = QFont("Consolas", 18)
        painter.setFont(font)
        painter.drawText(0, cy + radius + 40, w, 30, Qt.AlignmentFlag.AlignHCenter, "ALIAS Identity Check")
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Consolas", 10))
        painter.drawText(0, h - 30, w, 20, Qt.AlignmentFlag.AlignHCenter, "Scanning retina • Verifying token • Establishing link")


# ---------------- Chat Bubble ----------------
class ChatBubble(QFrame):
    def __init__(self, text: str, is_user: bool):
        super().__init__()
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setObjectName("user" if is_user else "assistant")
        layout = QVBoxLayout(self)

        if not is_user and text.strip().startswith("```"):
            import re
            m = re.match(r"```([a-zA-Z0-9_+-]*)\n([\s\S]*?)\n```\s*$", text.strip())
            if m:
                lang = m.group(1) or "code"
                code = m.group(2)
                top = QHBoxLayout()
                lang_label = QLabel(lang)
                lang_label.setStyleSheet("color: #bfbfbf; font-weight: 600;")
                copy_btn = QPushButton("Copy code")
                copy_btn.setFixedHeight(24)
                copy_btn.setStyleSheet("QPushButton{background:#1a1a1a;border:1px solid #333;border-radius:6px;padding:4px 8px;} QPushButton:hover{border-color:#666}")
                def do_copy():
                    QApplication.clipboard().setText(code)
                copy_btn.clicked.connect(do_copy)
                top.addWidget(lang_label)
                top.addStretch(1)
                top.addWidget(copy_btn)
                layout.addLayout(top)
                code_label = QLabel(f"<pre>{html.escape(code)}</pre>")
                code_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                code_label.setStyleSheet("QLabel{background:#0b0b0b;border:1px solid #222;border-radius:8px;padding:10px;font-family:'Consolas','Cascadia Code',monospace;font-size:13px;color:#e6e6e6}")
                layout.addWidget(code_label)
            else:
                label = QLabel(text)
                label.setWordWrap(True)
                layout.addWidget(label)
        else:
            label = QLabel(text)
            label.setWordWrap(True)
            layout.addWidget(label)

        self.setStyleSheet(
            """
            QFrame#user { background: #1a1a1a; border-radius: 12px; padding: 10px; }
            QFrame#assistant { background: #0f0f0f; border-radius: 12px; padding: 10px; }
            QLabel { color: #e6e6e6; font-family: 'Consolas', 'Cascadia Code', monospace; font-size: 13px; }
            """
        )


# ---------------- Orb Widget ----------------
class OrbWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.active = False
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)
        self.setFixedSize(QSize(60, 60))

    def setActive(self, active: bool):
        self.active = active
        self.update()

    def _tick(self):
        self._t += 0.016
        self.update()

    def paintEvent(self, event):  # type: ignore
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        base = 20
        pulse = 6 if self.active else 2
        radius = base + int(pulse * abs((self._t * (3 if self.active else 1) % 2) - 1))
        # Glow layers
        for i in range(3):
            alpha = 90 - i * 25
            color = QColor(255, 255, 255, alpha if self.active else alpha // 2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(cx - radius - i * 8, cy - radius - i * 8, (radius + i * 8) * 2, (radius + i * 8) * 2)


# ---------------- Signals Bridge ----------------
class UiSignals(QObject):
    add_user = pyqtSignal(str)
    add_assistant = pyqtSignal(str)
    set_active = pyqtSignal(bool)
    progress = pyqtSignal(int)
    scroll_bottom = pyqtSignal()


# ---------------- Main Window ----------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.backend = FridayBackend()
        self.signals = UiSignals()
        self._selected_file: str | None = None

        self._init_palette()
        self._init_ui()
        self._wire_signals()
        self._init_voice()

    def _init_palette(self):
        p = self.palette()
        p.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        p.setColor(QPalette.ColorRole.Base, QColor(10, 10, 10))
        p.setColor(QPalette.ColorRole.Text, QColor(230, 230, 230))
        p.setColor(QPalette.ColorRole.Button, QColor(20, 20, 20))
        p.setColor(QPalette.ColorRole.ButtonText, QColor(230, 230, 230))
        self.setPalette(p)
        self.setStyleSheet(
            """
            QWidget { background: #000; color: #e6e6e6; }
            QLineEdit { background: #0f0f0f; border: 1px solid #222; border-radius: 12px; padding: 10px; font-family: 'Consolas'; }
            QPushButton { background: #0f0f0f; border: 1px solid #333; border-radius: 12px; padding: 10px 14px; font-weight: 600; }
            QPushButton:hover { border-color: #666; }
            QProgressBar { background: #0f0f0f; border: 1px solid #222; border-radius: 10px; text-align: center; }
            QProgressBar::chunk { background-color: #e6e6e6; border-radius: 10px; }
            QScrollArea { border: none; }
            """
        )

    def _init_ui(self):
        self.setWindowTitle("ALIAS")
        self.resize(960, 640)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # Chat area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.addStretch(1)
        self.scroll.setWidget(self.chat_container)
        root.addWidget(self.scroll, 1)

        # Bottom bar
        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message…")
        self.input.returnPressed.connect(self._send_text)
        self.upload = QPushButton("Upload File")
        self.upload.clicked.connect(self._choose_file)
        self.send = QPushButton("Send")
        self.send.clicked.connect(self._send_text)
        self.tts_toggle = QPushButton("🔊 On")
        self.tts_toggle.setCheckable(True)
        self.tts_toggle.setChecked(True)
        self.tts_toggle.clicked.connect(self._toggle_tts)
        self.pause_btn = QPushButton("⏸️ Pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.clicked.connect(self._toggle_pause)
        self.orb = OrbWidget()

        bottom.addWidget(self.orb, 0)
        bottom.addWidget(self.input, 1)
        bottom.addWidget(self.upload, 0)
        bottom.addWidget(self.tts_toggle, 0)
        bottom.addWidget(self.pause_btn, 0)
        bottom.addWidget(self.send, 0)
        root.addLayout(bottom)

        # File info and progress
        info_row = QHBoxLayout()
        self.file_label = QLabel("")
        self.file_label.setStyleSheet("color: #bfbfbf;")
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        info_row.addWidget(self.file_label, 1)
        info_row.addWidget(self.progress, 0)
        root.addLayout(info_row)

        # Welcome text - check if user name is stored
        welcome_msg = "Hello, I am ALIAS. I remember our conversations and learn from them. How can I assist you?"
        try:
            import sqlite3
            conn = sqlite3.connect("alias_chat_history.db")
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM user_preferences WHERE key = ?', ("user_name",))
            result = cursor.fetchone()
            if result:
                user_name = result[0]
                welcome_msg = f"Hello {user_name}, I am ALIAS. I remember our conversations and learn from them. How can I assist you?"
            conn.close()
        except Exception:
            pass
        self._append_assistant(welcome_msg)

    def _wire_signals(self):
        self.signals.add_user.connect(lambda t: self._append_bubble(t, True))
        self.signals.add_assistant.connect(lambda t: self._append_bubble(t, False))
        self.signals.set_active.connect(self.orb.setActive)
        self.signals.progress.connect(self._set_progress)
        self.signals.scroll_bottom.connect(self._scroll_to_bottom)

    # ------------ Chat helpers ------------
    def _append_bubble(self, text: str, is_user: bool):
        bubble = ChatBubble(text, is_user)
        # Align left for assistant, right for user
        wrapper = QHBoxLayout()
        spacer_left = QWidget()
        spacer_right = QWidget()
        spacer_left.setFixedWidth(60)
        spacer_right.setFixedWidth(60)
        if is_user:
            wrapper.addWidget(spacer_left)
            wrapper.addWidget(bubble, 1)
        else:
            wrapper.addWidget(bubble, 1)
            wrapper.addWidget(spacer_right)
        cont = QWidget()
        cont.setLayout(wrapper)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, cont)
        self.signals.scroll_bottom.emit()

    def _append_assistant(self, text: str):
        self._append_bubble(text, False)

    def _scroll_to_bottom(self):
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def _set_progress(self, val: int):
        self.progress.setVisible(val < 100)
        self.progress.setValue(val)

    # ------------ Actions ------------
    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select file to analyze", "", "Documents (*.txt *.pdf *.docx);;All Files (*)")
        if path:
            self._selected_file = path
            name = os.path.basename(path)
            self.file_label.setText(f"Selected: {name}")
            # Kick off analysis immediately
            self._append_bubble(f"Uploaded {name}", True)
            self.signals.progress.emit(5)
            self.backend.analyze_file_async(
                path,
                on_progress=self.signals.progress.emit,
                on_result=lambda r: self.signals.add_assistant.emit(r),
                on_error=lambda e: self.signals.add_assistant.emit(f"Error: {e}"),
                on_activity=self.signals.set_active.emit,
            )

    def _send_text(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.signals.add_user.emit(text)
        self.backend.analyze_text_async(
            text,
            on_result=lambda r: self.signals.add_assistant.emit(r),
            on_error=lambda e: self.signals.add_assistant.emit(f"Error: {e}"),
            on_activity=self.signals.set_active.emit,
        )

    def _toggle_tts(self):
        on = self.tts_toggle.isChecked()
        set_tts_enabled(on)
        self.tts_toggle.setText("🔊 On" if on else "🔇 Off")
        if not on:
            try:
                stop_speaking()
            except Exception:
                pass

    def _toggle_pause(self):
        paused = self.pause_btn.isChecked()
        self.pause_btn.setText("▶️ Resume" if paused else "⏸️ Pause")
        if paused:
            try:
                stop_speaking()
            except Exception:
                pass

    # ------------ Always-on Voice ------------
    def _init_voice(self):
        if sr is None:
            return
        self._voice_thread_started = False
        self._always_listen = True
        # Keep orb subtly active to indicate listening
        self.signals.set_active.emit(True)
        threading.Thread(target=self._continuous_listen_worker, daemon=True).start()

    def _continuous_listen_worker(self):
        if self._voice_thread_started:
            return
        self._voice_thread_started = True
        try:
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.8)
                while self._always_listen:
                    try:
                        audio = recognizer.listen(source, timeout=2, phrase_time_limit=6)
                    except sr.WaitTimeoutError:
                        continue
                    try:
                        text = recognizer.recognize_google(audio)
                        if text:
                            self.signals.add_user.emit(text)
                            self.backend.analyze_text_async(
                                text,
                                on_result=lambda r: self.signals.add_assistant.emit(r),
                                on_error=lambda e: self.signals.add_assistant.emit(f"Error: {e}"),
                                on_activity=self.signals.set_active.emit,
                            )
                    except sr.UnknownValueError:
                        # ignore unrecognized noise
                        pass
                    except sr.RequestError as e:
                        self.signals.add_assistant.emit(f"Speech service error: {e}")
                        # brief backoff on service errors
                        QTimer.singleShot(1000, lambda: None)
        except Exception as e:
            self.signals.add_assistant.emit(f"Mic error: {e}")


def show_friday_qt():
    app = QApplication.instance() or QApplication(sys.argv)
    splash = IdentitySplash()
    splash.show()

    # Run identity check in background while splash animates
    result_holder = {"ok": None}

    def run_check():
        try:
            result_holder["ok"] = bool(eye_scan_gate())
        except Exception:
            result_holder["ok"] = True

    threading.Thread(target=run_check, daemon=True).start()

    # Poll for completion
    def try_transition():
        if result_holder["ok"] is None:
            QTimer.singleShot(150, try_transition)
            return
        splash.close()
        if result_holder["ok"]:
            win = MainWindow()
            win.show()
            # Keep a reference to avoid garbage collection
            setattr(app, "_friday_win", win)
        else:
            # Failed identity: exit app silently
            app.quit()

    # Start polling after small delay to let splash render
    QTimer.singleShot(300, try_transition)
    return app.exec()


if __name__ == "__main__":
    sys.exit(show_friday_qt())

