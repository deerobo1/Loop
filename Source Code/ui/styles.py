"""
LOOP-Inspired Modern UI Stylesheet
Deep blue background with cream/white buttons and clean design
"""

MAIN_STYLESHEET = """
/* ===== GLOBAL STYLES - DARK MODE ===== */
QMainWindow, QDialog {
    background-color: #1e1e1e;
}

QWidget {
    color: #ffffff;
    font-family: 'Segoe UI', 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
    selection-background-color: transparent;
    selection-color: #ffffff;
}

/* Remove black selection highlights globally */
QLabel {
    selection-background-color: transparent;
    selection-color: #ffffff;
}

/* ===== VIDEO PANEL ===== */
QFrame#video_panel {
    background-color: #2d2d2d;
    border: none;
}

QFrame#side_panel {
    background-color: #252525;
    border-left: 1px solid #404040;
}

QFrame#top_bar {
    background-color: transparent;
    padding: 8px 0px;
}

/* ===== PARTICIPANT VIDEO TILES ===== */
QFrame#participant_video_widget {
    background-color: #3a3a3a;
    border-radius: 12px;
    border: 2px solid #505050;
}

QFrame#participant_video_widget:hover {
    border: 2px solid #1e90ff;
}

QLabel#initial_label {
    background-color: transparent;
    color: white;
    font-size: 64px;
    font-weight: 300;
    letter-spacing: -1px;
}

/* ===== NAME TAGS & BADGES ===== */
QLabel#name_tag_label {
    background-color: rgba(0, 0, 0, 0.75);
    color: white;
    font-size: 12px;
    font-weight: 500;
    padding: 6px 12px;
    border-radius: 6px;
    letter-spacing: 0.3px;
}

QLabel#host_badge {
    background-color: #ffb900;
    color: #242424;
    font-size: 11px;
    font-weight: 600;
    padding: 6px 10px;
    border-radius: 6px;
    margin-left: 4px;
}

QLabel#mute_indicator {
    background-color: #e81123;
    color: white;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 600;
    margin-left: 4px;
}

QLabel#lock_indicator {
    background-color: #737373;
    color: white;
    font-size: 11px;
    padding: 6px 10px;
    border-radius: 6px;
    margin-left: 4px;
}

QLabel#hand_raise_indicator {
    background-color: #ffb900;
    color: #242424;
    font-size: 11px;
    font-weight: 600;
    padding: 6px 10px;
    border-radius: 6px;
    margin-left: 4px;
}

/* ===== MENU BUTTON ===== */
QPushButton#menu_button {
    background-color: rgba(0, 0, 0, 0.6);
    border: none;
    border-radius: 6px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
}

QPushButton#menu_button:hover {
    background-color: rgba(0, 0, 0, 0.8);
}

/* ===== CONTROLS BAR ===== */
QFrame#controls_bar {
    background-color: rgba(42, 42, 42, 0.95);
    border-radius: 16px;
    border: 1px solid rgba(80, 80, 80, 0.5);
}

/* ===== BUTTONS ===== */
QPushButton {
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 500;
    background-color: #404040;
    color: #ffffff;
}

QPushButton:hover {
    background-color: #505050;
}

QPushButton:pressed {
    background-color: #353535;
}

QPushButton:disabled {
    background-color: #2a2a2a;
    color: #666666;
}

/* ===== CONTROL BUTTONS (CIRCULAR) ===== */
QPushButton[class~="control_button"] {
    border-radius: 26px;
    min-width: 52px;
    max-width: 52px;
    min-height: 52px;
    max-height: 52px;
    padding: 0px;
    background-color: #404040;
    border: 2px solid transparent;
}

QPushButton[class~="control_button"]:hover {
    background-color: #505050;
}

/* Active/On State - Blue */
QPushButton[class~="on"] {
    background-color: #1e90ff;
    border: 2px solid #1e90ff;
}

QPushButton[class~="on"]:hover {
    background-color: #4169e1;
}

/* Off/Danger State - Red */
QPushButton[class~="off"],
QPushButton#leave_button {
    background-color: #dc3545;
    border: 2px solid #dc3545;
}

QPushButton[class~="off"]:hover,
QPushButton#leave_button:hover {
    background-color: #c82333;
}

/* ===== GRID CONTROLS ===== */
QPushButton#grid_button {
    font-size: 12px;
    font-weight: 500;
    padding: 8px 14px;
    border-radius: 6px;
    background-color: transparent;
    color: #616161;
}

QPushButton#grid_button:hover {
    background-color: #f3f3f3;
    color: #242424;
}

QPushButton#grid_button:checked {
    background-color: #0078d4;
    color: white;
    font-weight: 600;
}

/* ===== TABS ===== */
QTabWidget::pane {
    border: none;
    background-color: #252525;
}

QTabBar::tab {
    background-color: transparent;
    color: #b0b0b0;
    padding: 14px 24px;
    font-weight: 500;
    font-size: 13px;
    border: none;
    border-bottom: 3px solid transparent;
    margin-right: 4px;
}

QTabBar::tab:hover {
    color: #ffffff;
    background-color: rgba(30, 144, 255, 0.1);
}

QTabBar::tab:selected {
    color: #1e90ff;
    border-bottom: 3px solid #1e90ff;
    font-weight: 600;
}

/* ===== CHAT LIST ===== */
QListWidget#chat_display_list {
    background-color: transparent;
    border: none;
    padding: 20px 12px;
}

QListWidget#chat_display_list::item {
    border: none;
    padding: 12px 0px;
    margin: 8px 0px;
}

/* ===== SYSTEM MESSAGES ===== */
QLabel#system_message_label {
    color: #b0b0b0;
    font-size: 12px;
    font-style: italic;
    padding: 8px;
    background-color: transparent;
}

QLabel#system_message_label[class="success"] {
    color: #28a745;
}

QLabel#system_message_label[class="error"] {
    color: #dc3545;
}

/* ===== CHAT AVATARS ===== */
QLabel#chat_avatar {
    background-color: #1e90ff;
    color: white;
    font-weight: 600;
    font-size: 14px;
    border-radius: 18px;
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    qproperty-alignment: 'AlignCenter';
}

/* ===== CHAT BUBBLES ===== */
QFrame#chat_bubble {
    background-color: #3a3a3a;
    border-radius: 12px;
    border: 1px solid #505050;
    max-width: 70%;
}

QFrame#chat_message_widget[is_self="true"] > QFrame#chat_bubble {
    background-color: #1e90ff;
    border: 1px solid #1e90ff;
}

QFrame#chat_message_widget QLabel {
    color: #ffffff;
    font-size: 14px;
    line-height: 1.4;
}

QFrame#chat_message_widget[is_self="true"] QLabel {
    color: white;
}

QLabel#chat_timestamp {
    color: #b0b0b0;
    font-size: 11px;
    font-weight: 400;
}

QFrame#chat_message_widget[is_self="true"] QLabel#chat_timestamp {
    color: rgba(255, 255, 255, 0.85);
}

/* ===== CHAT INPUT ===== */
QFrame#chat_input_container {
    background-color: rgba(58, 58, 60, 0.8);
    border: 1px solid rgba(99, 99, 102, 0.6);
    border-radius: 20px;
    min-height: 48px;
}

QFrame#chat_input_container:focus-within {
    border: 2px solid #1e90ff;
}

QLineEdit#chat_input {
    background-color: transparent;
    border: none;
    padding: 10px 4px;
    font-size: 14px;
    color: #ffffff;
}

QLineEdit#chat_input::placeholder {
    color: #888888;
}

/* ===== CHAT BUTTONS ===== */
QPushButton#chat_icon_button {
    background-color: transparent;
    border-radius: 20px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
    padding: 0;
}

QPushButton#chat_icon_button:hover {
    background-color: #f3f3f3;
}

QPushButton#send_button {
    background-color: #1e90ff;
    border-radius: 20px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
    padding: 0;
}

QPushButton#send_button:hover {
    background-color: #4169e1;
}

/* ===== FILE TRANSFER ===== */
QFrame#file_transfer_widget {
    background-color: #3a3a3a;
    border: 1px solid #505050;
    border-radius: 12px;
    padding: 14px;
    max-width: 70%;
}

QPushButton#download_button {
    background-color: #1e90ff;
    color: white;
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton#download_button:hover {
    background-color: #4169e1;
}

QProgressBar {
    border: none;
    border-radius: 8px;
    background-color: #2a2a2a;
    text-align: center;
    color: #ffffff;
    font-weight: 500;
    font-size: 11px;
}

QProgressBar::chunk {
    border-radius: 8px;
    background-color: #1e90ff;
}

/* ===== MENUS ===== */
QMenu {
    background-color: #2a2a2a;
    border: 1px solid #505050;
    border-radius: 8px;
    padding: 6px;
    color: #ffffff;
}

QMenu::item {
    padding: 10px 20px;
    border-radius: 6px;
    margin: 2px;
}

QMenu::item:selected {
    background-color: #404040;
}

QMenu::item:pressed {
    background-color: #505050;
}

/* ===== SCROLLBARS ===== */
QScrollBar:vertical {
    background-color: transparent;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #d0d0d0;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #b0b0b0;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""

LOGIN_STYLESHEET = """
/* ===== LOGIN DIALOG - DARK BLUE STYLE ===== */
QDialog {
    background-color: #002250;
}

QFrame#mainContainer {
    background-color: #002250;
    border: none;
}

QFrame#transparentFrame {
    background-color: transparent;
    border: none;
}

/* ===== LOGO/TITLE ===== */
QLabel#logoLabel {
    color: #1E90FF;
    font-size: 72px;  /* Slightly smaller for better scaling */
    font-weight: 700;
    letter-spacing: 8px;
    font-family: 'Arial', 'Segoe UI', sans-serif;
}

/* ===== CATCHPHRASE ===== */
QLabel#catchphraseLabel {
    color: rgba(255, 255, 255, 0.8);
    font-size: 14px;
    font-weight: 400;
    letter-spacing: 1px;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    background-color: transparent;
    margin-top: -10px;
}

/* ===== INPUT LABELS ===== */
QLabel#inputLabel {
    color: white;
    font-size: 15px;
    font-weight: 500;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    background-color: transparent;
}

QLabel#joinTitleLabel {
    color: white;
    font-size: 17px;
    font-weight: 600;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    background-color: transparent;
}

QLabel#shareTitleLabel {
    color: #cccccc;
    font-size: 14px;
    font-weight: 400;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    background-color: transparent;
}

/* ===== INPUT FIELDS ===== */
QLineEdit#loopInput {
    background-color: #003366;
    border: 2px solid #4488cc;
    border-radius: 8px;
    padding: 10px 14px;  /* Slightly reduced padding for better scaling */
    font-size: 15px;     /* Slightly smaller font for better fit */
    color: white;
    font-family: 'Segoe UI', 'Arial', sans-serif;
}

QLineEdit#loopInput:focus {
    background-color: #003366;
    border: 2px solid #1E90FF;
}

QLineEdit#loopInput::placeholder {
    color: #aaaaaa;
}

/* ===== CODE INPUT ===== */
QLineEdit#codeInput {
    background-color: #003366;
    border: 2px solid #4488cc;
    border-radius: 8px;
    padding: 10px 14px;  /* Reduced padding for better scaling */
    font-size: 22px;     /* Slightly smaller font */
    font-weight: 600;
    letter-spacing: 6px; /* Reduced letter spacing */
    color: white;
    font-family: 'Courier New', monospace;
    text-transform: uppercase;
}

QLineEdit#codeInput:focus {
    background-color: #003366;
    border: 2px solid #1E90FF;
}

QLineEdit#codeInput::placeholder {
    color: #aaaaaa;
    letter-spacing: 8px;
}

/* ===== BUTTONS ===== */
QPushButton#loopButton {
    background-color: #1E90FF;
    color: white;
    border: 2px solid #1E90FF;
    border-radius: 10px;
    padding: 12px 20px;  /* Reduced padding for better scaling */
    font-size: 16px;     /* Slightly smaller font */
    font-weight: 600;
    font-family: 'Segoe UI', 'Arial', sans-serif;
}

QPushButton#loopButton:hover {
    background-color: #4da6ff;
    border: 2px solid #4da6ff;
    color: white;
}

QPushButton#loopButton:pressed {
    background-color: #1873CC;
    border: 2px solid #1873CC;
    color: white;
}

/* ===== ERROR LABEL ===== */
QLabel#errorLabel {
    color: #dc3545;
    font-size: 13px;
    font-weight: 500;
    padding: 10px 16px;
    background-color: rgba(220, 53, 69, 0.1);
    border-radius: 8px;
    border: 1px solid rgba(220, 53, 69, 0.3);
}

/* ===== CODE DISPLAY ===== */
QLabel#codeDisplayLabel {
    font-size: 42px;     /* Smaller font for better scaling */
    font-weight: 700;
    color: #1E90FF;
    letter-spacing: 10px; /* Reduced letter spacing */
    padding: 16px;       /* Reduced padding */
    background-color: #003366;
    border-radius: 12px;
    border: 3px solid #1E90FF;
    font-family: 'Courier New', monospace;
}
"""