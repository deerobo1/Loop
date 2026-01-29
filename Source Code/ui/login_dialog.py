"""
LOOP-Inspired Login Dialog
Deep blue background with cream/white buttons and fixed sizing
"""
import socket
import re
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QStackedWidget,
                             QSpacerItem, QSizePolicy, QGraphicsOpacityEffect, QCompleter)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QSize, QStringListModel
from PyQt6.QtGui import QFont, QIntValidator
from .styles import LOGIN_STYLESHEET

class EnhancedLoginDialog(QDialog):
    connection_requested = pyqtSignal(str, str, int, str, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LOOP - Welcome")
        self.setMinimumSize(600, 700)  # Set minimum size instead of fixed
        self.resize(700, 850)  # Set initial size
        self.setModal(True)
        self.setStyleSheet(LOGIN_STYLESHEET)
        
        # Get suggested IP addresses for auto-completion
        self.suggested_ips = self.get_suggested_ip_addresses()
        
        self.setup_ui()
        self.setup_animations()
    
    def get_suggested_ip_addresses(self):
        """Get a list of suggested IP addresses for auto-completion"""
        suggested_ips = ['127.0.0.1']  # Always include localhost
        
        try:
            # Get local machine's IP addresses
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip and local_ip != '127.0.0.1':
                suggested_ips.append(local_ip)
            
            # Try to get network interface IPs
            try:
                # Connect to a remote address to determine the local IP
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 80))
                    network_ip = s.getsockname()[0]
                    if network_ip and network_ip not in suggested_ips:
                        suggested_ips.append(network_ip)
            except:
                pass
            
            # Add common local network ranges
            common_ranges = [
                '192.168.1.1', '192.168.0.1', '192.168.1.100', 
                '10.0.0.1', '172.16.0.1'
            ]
            for ip in common_ranges:
                if ip not in suggested_ips:
                    suggested_ips.append(ip)
                    
        except Exception as e:
            print(f"Warning: Could not detect network IPs: {e}")
        
        return suggested_ips
    
    def validate_ip_address(self, ip):
        """Validate IP address format"""
        if not ip:
            return False
        
        # Allow localhost
        if ip.lower() in ['localhost', 'local']:
            return True
        
        # Validate IPv4 format
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        
        # Check each octet is valid (0-255)
        octets = ip.split('.')
        for octet in octets:
            if not (0 <= int(octet) <= 255):
                return False
        
        return True
    
    def auto_detect_ip(self):
        """Auto-detect the local IP address"""
        try:
            # Try to get the most likely local network IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                
            if local_ip and local_ip != '127.0.0.1':
                self.ip_input.setText(local_ip)
                self.show_info(f"Auto-detected IP: {local_ip}")
            else:
                # Fallback to hostname resolution
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                if local_ip and local_ip != '127.0.0.1':
                    self.ip_input.setText(local_ip)
                    self.show_info(f"Auto-detected IP: {local_ip}")
                else:
                    self.show_error("Could not auto-detect IP. Using localhost (127.0.0.1)")
                    self.ip_input.setText("127.0.0.1")
                    
        except Exception as e:
            print(f"Auto-detect IP failed: {e}")
            self.show_error("Could not auto-detect IP. Using localhost (127.0.0.1)")
            self.ip_input.setText("127.0.0.1")
    
    def show_info(self, message):
        """Show an info message"""
        self.error_label.setText(f"ℹ️  {message}")
        self.error_label.setStyleSheet("""
            QLabel {
                color: #3498db;
                background-color: rgba(52, 152, 219, 0.1);
                border: 1px solid rgba(52, 152, 219, 0.3);
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        self.error_label.setVisible(True)
        QTimer.singleShot(3000, lambda: self.error_label.setVisible(False))
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main container with blue background
        main_container = QFrame()
        main_container.setObjectName("mainContainer")
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(40, 40, 40, 40)  # Reduced margins for better scaling
        main_layout.setSpacing(0)
        
        # Logo/Title
        logo_label = QLabel("LOOP")
        logo_label.setObjectName("logoLabel")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setMinimumHeight(80)  # Use minimum height instead of fixed
        logo_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        main_layout.addWidget(logo_label)
        
        # Catchphrase
        catchphrase_label = QLabel("Stay in the Loop")
        catchphrase_label.setObjectName("catchphraseLabel")
        catchphrase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        catchphrase_label.setMinimumHeight(20)
        catchphrase_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        main_layout.addWidget(catchphrase_label)
        
        # Add flexible spacing
        main_layout.addSpacerItem(QSpacerItem(20, 30, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Input fields container
        inputs_container = QFrame()
        inputs_container.setObjectName("transparentFrame")
        inputs_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        inputs_layout = QVBoxLayout(inputs_container)
        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.setSpacing(15)  # Slightly reduced spacing for better scaling
        
        # Name input
        name_label = QLabel("Name")
        name_label.setObjectName("inputLabel")
        inputs_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setObjectName("loopInput")
        self.name_input.setMinimumHeight(45)  # Use minimum height for flexibility
        self.name_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        inputs_layout.addWidget(self.name_input)
        
        inputs_layout.addSpacing(8)
        
        # Server IP input with auto-completion
        ip_label = QLabel("Server IP")
        ip_label.setObjectName("inputLabel")
        inputs_layout.addWidget(ip_label)
        
        self.ip_input = QLineEdit("127.0.0.1")
        self.ip_input.setObjectName("loopInput")
        self.ip_input.setMinimumHeight(45)
        self.ip_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.ip_input.setPlaceholderText("Enter server IP address (e.g., 192.168.1.100)")
        
        # Add auto-completion for IP addresses
        completer = QCompleter(self.suggested_ips)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self.ip_input.setCompleter(completer)
        
        # Create IP input container with auto-detect button
        ip_container = QFrame()
        ip_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        ip_container_layout = QHBoxLayout(ip_container)
        ip_container_layout.setContentsMargins(0, 0, 0, 0)
        ip_container_layout.setSpacing(10)
        
        ip_container_layout.addWidget(self.ip_input)
        
        # Auto-detect IP button
        self.auto_detect_button = QPushButton("Auto")
        self.auto_detect_button.setObjectName("autoDetectButton")
        self.auto_detect_button.setMinimumSize(50, 45)
        self.auto_detect_button.setMaximumSize(70, 55)
        self.auto_detect_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self.auto_detect_button.setToolTip("Auto-detect local IP address")
        self.auto_detect_button.clicked.connect(self.auto_detect_ip)
        self.auto_detect_button.setStyleSheet("""
            QPushButton#autoDetectButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.8);
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#autoDetectButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                border: 2px solid rgba(255, 255, 255, 0.4);
            }
            QPushButton#autoDetectButton:pressed {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)
        ip_container_layout.addWidget(self.auto_detect_button)
        
        inputs_layout.addWidget(ip_container)
        
        inputs_layout.addSpacing(8)
        
        # Port input
        port_label = QLabel("Port")
        port_label.setObjectName("inputLabel")
        inputs_layout.addWidget(port_label)
        
        self.port_input = QLineEdit("5001")
        self.port_input.setObjectName("loopInput")
        self.port_input.setValidator(QIntValidator(1024, 65535))
        self.port_input.setMinimumHeight(45)
        self.port_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        inputs_layout.addWidget(self.port_input)
        
        inputs_layout.addSpacing(15)  # Consistent spacing after port input
        
        main_layout.addWidget(inputs_container)
        
        # Add flexible spacing
        main_layout.addSpacerItem(QSpacerItem(20, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Stacked widget for different views
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setMinimumHeight(150)  # Use minimum height for flexibility
        self.stacked_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # Page 1: Choose action (Create/Join buttons)
        action_page = QFrame()
        action_page.setObjectName("transparentFrame")
        action_layout = QVBoxLayout(action_page)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(20)
        
        self.create_button = QPushButton("Create")
        self.create_button.setObjectName("loopButton")
        self.create_button.setMinimumHeight(50)
        self.create_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_button.clicked.connect(self.on_create_clicked)
        action_layout.addWidget(self.create_button)
        
        self.join_button = QPushButton("Join")
        self.join_button.setObjectName("loopButton")
        self.join_button.setMinimumHeight(50)
        self.join_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.join_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.join_button.clicked.connect(self.show_join_page)
        action_layout.addWidget(self.join_button)
        
        action_layout.addStretch()
        self.stacked_widget.addWidget(action_page)
        
        # Page 2: Join meeting (Code input + buttons)
        join_page = QFrame()
        join_page.setObjectName("transparentFrame")
        join_layout = QVBoxLayout(join_page)
        join_layout.setContentsMargins(0, 0, 0, 0)
        join_layout.setSpacing(15)
        
        join_title = QLabel("Enter Meeting Code")
        join_title.setObjectName("joinTitleLabel")
        join_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        join_title.setMinimumHeight(25)
        join_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        join_layout.addWidget(join_title)
        
        self.code_input = QLineEdit()
        self.code_input.setObjectName("codeInput")
        self.code_input.setPlaceholderText("XXXXXX")
        self.code_input.setMaxLength(6)
        self.code_input.setMinimumHeight(50)
        self.code_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.code_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        join_layout.addWidget(self.code_input)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("loopButton")
        self.back_button.setMinimumHeight(45)
        self.back_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_button.clicked.connect(self.show_action_page)
        buttons_layout.addWidget(self.back_button)
        
        self.join_meeting_button = QPushButton("Join Meeting")
        self.join_meeting_button.setObjectName("loopButton")
        self.join_meeting_button.setMinimumHeight(45)
        self.join_meeting_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.join_meeting_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.join_meeting_button.clicked.connect(self.on_join_clicked)
        buttons_layout.addWidget(self.join_meeting_button)
        join_layout.addLayout(buttons_layout)
        
        join_layout.addStretch()
        self.stacked_widget.addWidget(join_page)
        
        # Page 3: Creating meeting (Code display)
        creating_page = QFrame()
        creating_page.setObjectName("transparentFrame")
        creating_layout = QVBoxLayout(creating_page)
        creating_layout.setContentsMargins(0, 0, 0, 0)
        creating_layout.setSpacing(20)
        
        creating_title = QLabel("Meeting Code")
        creating_title.setObjectName("joinTitleLabel")
        creating_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        creating_title.setMinimumHeight(25)
        creating_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        creating_layout.addWidget(creating_title)
        
        self.code_display = QLabel("")
        self.code_display.setObjectName("codeDisplayLabel")
        self.code_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_display.setMinimumHeight(60)
        self.code_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        creating_layout.addWidget(self.code_display)
        
        share_label = QLabel("Share this code with participants")
        share_label.setObjectName("shareTitleLabel")
        share_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        share_label.setMinimumHeight(20)
        share_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        creating_layout.addWidget(share_label)
        
        creating_layout.addStretch()
        self.stacked_widget.addWidget(creating_page)
        
        main_layout.addWidget(self.stacked_widget)
        
        # Add flexible spacing
        main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Error label
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setMinimumHeight(30)
        self.error_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.error_label.setVisible(False)
        main_layout.addWidget(self.error_label)
        
        # Add flexible spacing at bottom
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        layout.addWidget(main_container)
        self.setLayout(layout)
        
        # Connect enter key
        self.name_input.returnPressed.connect(self.create_button.click)
        self.code_input.returnPressed.connect(self.join_meeting_button.click)
    
    def setup_animations(self):
        """Setup smooth fade animations for page transitions"""
        self.fade_effect = QGraphicsOpacityEffect()
        self.stacked_widget.setGraphicsEffect(self.fade_effect)
        
        self.fade_animation = QPropertyAnimation(self.fade_effect, b"opacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
    def animate_page_change(self, page_index):
        """Smooth fade transition between pages"""
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(lambda: self._complete_page_change(page_index))
        self.fade_animation.start()
    
    def _complete_page_change(self, page_index):
        self.stacked_widget.setCurrentIndex(page_index)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.finished.disconnect()
        self.fade_animation.start()
        
    def show_action_page(self):
        self.animate_page_change(0)
        self.error_label.setVisible(False)
        
    def show_join_page(self):
        if not self._validate_common_inputs():
            return
        self.animate_page_change(1)
        QTimer.singleShot(250, self.code_input.setFocus)
        
    def _validate_common_inputs(self):
        # Validate name
        if not self.name_input.text().strip():
            self.show_error("Please enter your name")
            return False
        
        # Validate IP address
        ip_text = self.ip_input.text().strip()
        if not ip_text:
            # Auto-fill with localhost if empty
            self.ip_input.setText("127.0.0.1")
            ip_text = "127.0.0.1"
        
        # Convert common aliases
        if ip_text.lower() in ['localhost', 'local']:
            self.ip_input.setText("127.0.0.1")
            ip_text = "127.0.0.1"
        
        if not self.validate_ip_address(ip_text):
            self.show_error("Please enter a valid IP address (e.g., 192.168.1.100)")
            return False
        
        # Validate port
        if not self.port_input.text().strip():
            # Auto-fill with default port if empty
            self.port_input.setText("5001")
        
        try:
            port = int(self.port_input.text())
            if not (1024 <= port <= 65535):
                self.show_error("Port must be between 1024 and 65535")
                return False
        except ValueError:
            self.show_error("Please enter a valid port number")
            return False
        
        return True

    def on_create_clicked(self):
        if not self._validate_common_inputs():
            return
            
        self.animate_page_change(2)
        QTimer.singleShot(250, lambda: self.connection_requested.emit(
            self.name_input.text().strip(),
            self.ip_input.text().strip(),
            int(self.port_input.text()),
            "", 
            True
        ))
        
    def on_join_clicked(self):
        if not self._validate_common_inputs():
            return
        
        code = self.code_input.text().strip().upper()
        if not code or len(code) != 6:
            self.show_error("Please enter a valid 6-character meeting code")
            return
            
        self.connection_requested.emit(
            self.name_input.text().strip(),
            self.ip_input.text().strip(),
            int(self.port_input.text()),
            code, 
            False
        )
        
    def show_meeting_code(self, code):
        self.code_display.setText(code)
        QTimer.singleShot(2500, self.accept)
        
    def show_error(self, message):
        self.error_label.setText(f"⚠️  {message}")
        # Reset to error styling
        self.error_label.setStyleSheet("")  # Use default error styling from LOGIN_STYLESHEET
        self.error_label.setVisible(True)
        QTimer.singleShot(4000, lambda: self.error_label.setVisible(False))
        
    def reset(self):
        self.show_action_page()
        
    def connection_successful(self, meeting_code=None):
        if meeting_code:
            self.show_meeting_code(meeting_code)
        else:
            self.accept()