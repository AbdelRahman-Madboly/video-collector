"""Colours and styles, in the same dark look as Tools Hub and Bills Ledger."""

DARK = """
QMainWindow, QWidget#page, QScrollArea, QStackedWidget { background: #12141c; }
QWidget { color: #e5e7eb; font-size: 13px; }
QLabel[role="title"] { font-size: 20px; font-weight: 700; }
QLabel[role="h2"] { font-size: 15px; font-weight: 700; }
QLabel[role="muted"] { color: #9ca3af; font-size: 12px; }
QLabel[role="ok"] { color: #34d399; }
QLabel[role="warn"] { color: #fbbf24; }
QFrame[card="true"] { background: #1b1e2a; border: 1px solid #2a2f3f; border-radius: 12px; }
QListWidget#nav { background: #161925; border: none; padding: 8px; font-size: 14px; }
QListWidget#nav::item { padding: 10px 14px; border-radius: 8px; }
QListWidget#nav::item:selected { background: #2b3150; color: #ffffff; }
QPlainTextEdit, QLineEdit, QComboBox, QListWidget { background: #1f2333; border: 1px solid #343a4f;
    border-radius: 8px; padding: 6px; selection-background-color: #4f46e5; }
QPushButton { background: #262b3b; border: 1px solid #343a4f; border-radius: 8px; padding: 7px 14px; }
QPushButton:hover { background: #313852; }
QPushButton:disabled { color: #6b7280; }
QPushButton[primary="true"] { background: #6366f1; border-color: #6366f1; color: white; font-weight: 600; }
QPushButton[chip="true"] { border-radius: 14px; padding: 6px 14px; }
QPushButton[chip="true"]:checked { background: #4f46e5; border-color: #6366f1; color: white; }
QCheckBox { spacing: 8px; }
QProgressBar { background: #1f2333; border: 1px solid #343a4f; border-radius: 6px; text-align: center; height: 14px; }
QProgressBar::chunk { background: #6366f1; border-radius: 6px; }
"""

LIGHT = """
QMainWindow, QWidget#page, QScrollArea, QStackedWidget { background: #f4f5f8; }
QWidget { color: #1a1d23; font-size: 13px; }
QLabel[role="title"] { font-size: 20px; font-weight: 700; }
QLabel[role="h2"] { font-size: 15px; font-weight: 700; }
QLabel[role="muted"] { color: #6b7280; font-size: 12px; }
QLabel[role="ok"] { color: #15803d; }
QLabel[role="warn"] { color: #b45309; }
QFrame[card="true"] { background: #ffffff; border: 1px solid #dde1ea; border-radius: 12px; }
QListWidget#nav { background: #e9ebf2; border: none; padding: 8px; font-size: 14px; }
QListWidget#nav::item { padding: 10px 14px; border-radius: 8px; }
QListWidget#nav::item:selected { background: #c7cbf7; color: #111; }
QPlainTextEdit, QLineEdit, QComboBox, QListWidget { background: #ffffff; border: 1px solid #d0d5e0;
    border-radius: 8px; padding: 6px; }
QPushButton { background: #ffffff; border: 1px solid #d0d5e0; border-radius: 8px; padding: 7px 14px; }
QPushButton[primary="true"] { background: #4f46e5; border-color: #4f46e5; color: white; font-weight: 600; }
QPushButton[chip="true"] { border-radius: 14px; padding: 6px 14px; }
QPushButton[chip="true"]:checked { background: #4f46e5; border-color: #4f46e5; color: white; }
QProgressBar { border: 1px solid #d0d5e0; border-radius: 6px; text-align: center; height: 14px; }
QProgressBar::chunk { background: #4f46e5; border-radius: 6px; }
"""
