"""
Skype-Inspired Private Chat Widget
Clean, modern 1:1 chat interface with smooth animations
"""
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import qtawesome as qta
from datetime import datetime

class PrivateChatWidget(QWidget):
    """Modern private 1:1 chat widget with Skype-inspired design"""
    message_sent = pyqtSignal(str, str)
    
    def __init__(self, client_id, username, color, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.username = username
        self.color = color
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Modern header with clean design
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-bottom: 1px solid #e8e8e8;
                padding: 16px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(12)
        
        # Avatar with soft shadow
        avatar_label = QLabel(self.username[0].upper())
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_label.setStyleSheet(f"""
            background-color: {self.color.name()};
            color: white;
            border-radius: 22px;
            font-weight: 600;
            font-size: 16px;
        """)
        avatar_label.setFixedSize(44, 44)
        header_layout.addWidget(avatar_label)
        
        # Name and status with refined typography
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        name_label = QLabel(f"<b>{self.username}</b>")
        name_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #242424;")
        info_layout.addWidget(name_label)
        
        status_label = QLabel("Private conversation")
        status_label.setStyleSheet("color: #737373; font-size: 12px;")
        info_layout.addWidget(status_label)
        header_layout.addLayout(info_layout)
        
        header_layout.addStretch()
        
        # Close button with hover effect
        close_btn = QPushButton(qta.icon('fa5s.times', color='#737373'), "")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 18px;
                min-width: 36px;
                max-width: 36px;
                min-height: 36px;
                max-height: 36px;
            }
            QPushButton:hover {
                background-color: #f3f3f3;
            }
            QPushButton:pressed {
                background-color: #e8e8e8;
            }
        """)
        close_btn.clicked.connect(self.hide)
        header_layout.addWidget(close_btn)
        
        layout.addWidget(header)
        
        # Chat display with modern styling
        self.chat_list = QListWidget()
        self.chat_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: #fafafa;
                padding: 12px;
            }
        """)
        self.chat_list.setSpacing(8)
        self.chat_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.chat_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.chat_list)
        
        # Modern input area
        input_container = QFrame()
        input_container.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-top: 1px solid #e8e8e8;
                padding: 12px 16px;
            }
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(12, 12, 12, 12)
        input_layout.setSpacing(8)
        
        self.message_input = QLineEdit()
        self.message_input.setStyleSheet("""
            QLineEdit {
                background-color: #fafafa;
                border: 2px solid #e8e8e8;
                border-radius: 20px;
                padding: 10px 16px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #0078d4;
                background-color: #ffffff;
            }
        """)
        self.message_input.setPlaceholderText(f"Message {self.username}...")
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        
        send_btn = QPushButton(qta.icon('fa5s.paper-plane', color='white'), "")
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 20px;
                min-width: 40px;
                max-width: 40px;
                min-height: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(send_btn)
        
        layout.addWidget(input_container)
        
    def send_message(self):
        text = self.message_input.text().strip()
        if text:
            self.message_sent.emit(self.client_id, text)
            self.message_input.clear()
            self.add_message("You", text, True)
            
    def add_message(self, sender, text, is_self=False):
        """Add a message with modern bubble design"""
        time_str = datetime.now().strftime("%H:%M")
        
        message_widget = QFrame()
        message_widget.setStyleSheet("background-color: transparent; border: none;")
        
        main_layout = QHBoxLayout(message_widget)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(10)
        
        if is_self:
            main_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Message bubble with refined styling
        bubble = QFrame()
        bubble_style = """
            QFrame {
                background-color: %s;
                border-radius: 12px;
                border: %s;
                padding: 2px;
            }
        """ % ("#0078d4" if is_self else "#ffffff", 
               "1px solid #0078d4" if is_self else "1px solid #e8e8e8")
        bubble.setStyleSheet(bubble_style)
        bubble.setMaximumWidth(400)
        
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 10, 12, 10)
        bubble_layout.setSpacing(4)
        
        if not is_self:
            sender_label = QLabel(f"<b>{sender}</b>")
            sender_label.setStyleSheet(f"color: {self.color.name()}; font-size: 12px; font-weight: 600;")
            bubble_layout.addWidget(sender_label)
        
        message_label = QLabel(text)
        message_label.setWordWrap(True)
        # Removed text selection to avoid black highlights
        message_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        message_label.setStyleSheet(f"""
            color: {'white' if is_self else '#242424'};
            font-size: 14px;
            line-height: 1.4;
        """)
        bubble_layout.addWidget(message_label)
        
        timestamp_label = QLabel(time_str)
        timestamp_label.setStyleSheet(f"""
            color: {'rgba(255, 255, 255, 0.85)' if is_self else '#737373'};
            font-size: 11px;
        """)
        bubble_layout.addWidget(timestamp_label, 0, Qt.AlignmentFlag.AlignRight)
        
        main_layout.addWidget(bubble)
        
        if not is_self:
            main_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Add to list with animation
        item = QListWidgetItem()
        item.setSizeHint(message_widget.sizeHint())
        self.chat_list.addItem(item)
        self.chat_list.setItemWidget(item, message_widget)
        self.chat_list.scrollToBottom()

class PrivateChatManager(QWidget):
    """Manager for all private chat conversations with tab interface"""
    message_sent = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chats = {}
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Modern tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #fafafa;
            }
            QTabBar::tab {
                background-color: transparent;
                color: #616161;
                padding: 12px 20px;
                font-weight: 500;
                font-size: 13px;
                border: none;
                border-bottom: 3px solid transparent;
                margin-right: 4px;
            }
            QTabBar::tab:hover {
                color: #242424;
                background-color: rgba(0, 120, 212, 0.05);
            }
            QTabBar::tab:selected {
                color: #0078d4;
                border-bottom: 3px solid #0078d4;
                font-weight: 600;
            }
            QTabBar::close-button {
                image: url(none);
                subcontrol-position: right;
            }
        """)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_chat)
        layout.addWidget(self.tab_widget)
        
        # Elegant placeholder
        self.placeholder = QLabel("No private conversations open.\n\nClick on a participant to start chatting.")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("""
            color: #737373;
            font-size: 14px;
            line-height: 1.6;
            padding: 40px;
        """)
        layout.addWidget(self.placeholder)
        
        self.update_visibility()
        
    def open_chat(self, client_id, username, color):
        """Open or focus a private chat"""
        if client_id not in self.chats:
            chat_widget = PrivateChatWidget(client_id, username, color)
            chat_widget.message_sent.connect(self.message_sent.emit)
            self.chats[client_id] = chat_widget
            self.tab_widget.addTab(chat_widget, username)
            
        index = self.tab_widget.indexOf(self.chats[client_id])
        self.tab_widget.setCurrentIndex(index)
        self.update_visibility()
        
    def close_chat(self, index):
        """Close a private chat tab"""
        widget = self.tab_widget.widget(index)
        for client_id, chat_widget in self.chats.items():
            if chat_widget == widget:
                del self.chats[client_id]
                break
        self.tab_widget.removeTab(index)
        self.update_visibility()
        
    def update_visibility(self):
        """Toggle between tabs and placeholder"""
        has_chats = len(self.chats) > 0
        self.tab_widget.setVisible(has_chats)
        self.placeholder.setVisible(not has_chats)
        
    def add_message(self, client_id, sender, text, is_self=False):
        """Add a message to a specific chat"""
        if client_id in self.chats:
            self.chats[client_id].add_message(sender, text, is_self)
            
            # Show notification if not currently selected
            current_widget = self.tab_widget.currentWidget()
            if current_widget != self.chats[client_id]:
                index = self.tab_widget.indexOf(self.chats[client_id])
                # Could add unread indicator here
