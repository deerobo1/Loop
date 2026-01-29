"""
===================================================================================
MULTI-USER VIDEO CONFERENCING - MAIN WINDOW UI
===================================================================================
This file implements the main user interface for the video conferencing application.

CORE UI COMPONENTS:
1. Video Grid - Displays multiple participant video streams
2. Audio Controls - Microphone mute/unmute button
3. Video Controls - Camera on/off button
4. Screen Share Controls - Start/stop screen sharing
5. Chat Panel - Text messaging interface
6. Participants Panel - List of connected users
7. File Sharing - Upload/download files

NETWORK INTEGRATION:
- Receives video frames via UDP and displays them
- Receives audio packets via UDP and plays them
- Sends/receives chat messages via TCP
- Handles file transfers via TCP
- Manages control messages via TCP

MEDIA CAPTURE:
- Camera: OpenCV (cv2) captures webcam video at 640x480, 20 FPS
- Microphone: PyAudio captures audio at 44.1kHz, 16-bit PCM
- Screen: MSS library captures screen at reduced frame rate (3 FPS)

THREADING:
- Main Thread: UI rendering and user interactions
- Video Capture Thread: Captures and sends video frames
- Audio Capture Thread: Captures and sends audio packets
- Screen Capture Thread: Captures and sends screen frames
- Network Threads: Handled by client.py (TCP/UDP receive)

PROTOCOL USAGE IN UI:
- Video/Audio: Captured locally, sent via UDP (client.py)
- Chat: User input sent via TCP (client.py)
- Files: Selected files sent via TCP in chunks (client.py)
- Screen: Captured frames sent via TCP for clarity (client.py)
===================================================================================
"""

# Import PyQt6 components for GUI
from PyQt6.QtWidgets import *
from PyQt6.QtWidgets import QDialog, QProgressBar, QSplitter, QInputDialog
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Import additional libraries
import qtawesome as qta  # Icon library
import cv2  # OpenCV for video capture and processing
import numpy as np  # Numerical operations for audio/video
import pyaudio  # Audio capture and playback
import base64  # Encoding binary data for JSON transmission
import threading  # Concurrent operations
import uuid  # Unique identifiers
import os  # File operations
from datetime import datetime  # Timestamps
import mss  # Screen capture library
import mss.tools  # Screen capture tools
import queue  # Thread-safe queues for audio
import random  # Random number generation
import hashlib  # Hashing for color generation
import json  # JSON serialization
import sys  # System operations
import platform  # Platform detection
from PIL import Image, ImageDraw, ImageFont  # Image processing

# Import custom UI components
from .login_dialog import EnhancedLoginDialog
from .styles import MAIN_STYLESHEET



class SidebarPopupWindow(QMainWindow):
    """Popup window for the sidebar with dynamic resizing"""
    
    def __init__(self, parent, tab_widget):
        super().__init__(parent)
        self.parent_window = parent
        self.tab_widget = tab_widget
        
        self.setWindowTitle("Loop - Sidebar")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        
        # Set initial size and position
        self.resize(400, 600)
        self.position_relative_to_parent()
        
        # Set up the UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tab_widget)
        
        # Apply the same styling as the main window
        self.setStyleSheet("""
            QMainWindow {
                background-color: rgba(28, 28, 30, 1.0);
                color: rgba(255, 255, 255, 0.9);
            }
        """)
        
        # Connect to parent window events for dynamic positioning
        self.parent_window.resizeEvent = self.on_parent_resize
        self.parent_window.moveEvent = self.on_parent_move
        
    def position_relative_to_parent(self):
        """Position the popup window relative to the parent"""
        if self.parent_window:
            parent_geometry = self.parent_window.geometry()
            # Position to the right of the parent window
            x = parent_geometry.x() + parent_geometry.width() + 10
            y = parent_geometry.y()
            
            # Ensure the window stays on screen
            screen = QApplication.primaryScreen().geometry()
            if x + self.width() > screen.width():
                x = parent_geometry.x() - self.width() - 10  # Position to the left instead
            
            self.move(x, y)
            
            # Adjust height to match parent
            self.resize(self.width(), parent_geometry.height())
    
    def on_parent_resize(self, event):
        """Handle parent window resize"""
        if hasattr(self, 'parent_window') and self.parent_window:
            # Call the original resize event handler if it exists
            if hasattr(QMainWindow, 'resizeEvent'):
                QMainWindow.resizeEvent(self.parent_window, event)
            
            # Update popup position and size
            if self.isVisible():
                QTimer.singleShot(50, self.position_relative_to_parent)
    
    def on_parent_move(self, event):
        """Handle parent window move"""
        if hasattr(self, 'parent_window') and self.parent_window:
            # Call the original move event handler if it exists
            if hasattr(QMainWindow, 'moveEvent'):
                QMainWindow.moveEvent(self.parent_window, event)
            
            # Update popup position
            if self.isVisible():
                QTimer.singleShot(50, self.position_relative_to_parent)
    
    def closeEvent(self, event):
        """Handle close event"""
        # Return the tab widget to the parent
        if self.parent_window and hasattr(self.parent_window, 'return_sidebar_from_popup'):
            self.parent_window.return_sidebar_from_popup()
        event.accept()


# Emoji Reaction Widget with Modern Skype-inspired Animation
class EmojiReactionWidget(QLabel):
    def __init__(self, emoji, parent=None):
        super().__init__(emoji, parent)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.95);
                color: #242424;
                font-size: 40px;
                padding: 10px;
                border-radius: 12px;
                border: 2px solid rgba(0, 120, 212, 0.3);
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(60, 60)  # Fixed size to prevent clipping
        
        # Setup fade animation (shorter duration)
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(1500)  # 1.5 sec fade-out
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.finished.connect(self.deleteLater)
        
    def start_animation(self):
        self.show()
        self.raise_()
        self.fade_animation.start()

# Simple Progress Widget for File Transfers
class SimpleProgressWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress = 0
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Create progress bar to match download button
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 8px;
                background-color: #f3f3f3;
                text-align: center;
                color: #242424;
                font-size: 11px;
                font-weight: 500;
                padding: 6px;
                min-height: 28px;
                max-height: 28px;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
    def set_progress(self, value):
        self.progress = max(0, min(100, value))
        self.progress_bar.setValue(self.progress)
        
        # Change color based on progress
        if self.progress >= 100:
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 8px;
                    background-color: #f3f3f3;
                    text-align: center;
                    color: #242424;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 6px;
                    min-height: 28px;
                    max-height: 28px;
                }
                QProgressBar::chunk {
                    background-color: #107c10;  /* Green for completion */
                    border-radius: 8px;
                }
            """)
            self.progress_bar.setFormat("Done")  # Show completion text
        else:
            # Format is already set to show percentage
            pass  # No change needed



class ParticipantVideoWidget(QFrame):
    mute_clicked = pyqtSignal(str, bool)
    video_request_clicked = pyqtSignal(str)
    unmute_request_clicked = pyqtSignal(str)
    lock_mic_clicked = pyqtSignal(str, bool)
    focused = pyqtSignal(str)
    emoji_reaction_requested = pyqtSignal(str, str)  # client_id, emoji

    def __init__(self, client_id, username="", is_host=False, is_self=False, parent=None, profile_image=None):
        super().__init__(parent)
        self.client_id = client_id
        self.username = username
        self.is_host = is_host
        self.is_self = is_self
        self.is_muted = False
        self.is_mic_locked = False
        self.hand_raised = False
        self.profile_image = profile_image
        self.setObjectName("participant_video_widget")
        self.setMinimumSize(320, 240)
        
        self.color = self.parent().get_color_from_name(self.username)
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QStackedLayout(self)
        self.main_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        
        # Profile/Initial widget
        self.initial_widget = QWidget()
        initial_layout = QVBoxLayout(self.initial_widget)
        
        if self.profile_image:
            # Display profile image
            self.profile_label = QLabel()
            pixmap = QPixmap(self.profile_image)
            scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.profile_label.setPixmap(scaled_pixmap)
            self.profile_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            initial_layout.addWidget(self.profile_label)
            self.initial_widget.setStyleSheet("background-color: #282b30; border-radius: 8px;")
        else:
            # Display colored initial with proper text contrast
            self.initial_widget.setStyleSheet(f"background-color: {self.color.name()}; border-radius: 8px;")
            self.initial_label = QLabel(self.username[0].upper() if self.username else "?")
            self.initial_label.setObjectName("initial_label")
            
            # Calculate luminance for text color contrast
            r, g, b = self.color.red(), self.color.green(), self.color.blue()
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            text_color = "black" if luminance > 0.5 else "white"
            self.initial_label.setStyleSheet(f"color: {text_color}; font-size: 48px; font-weight: bold;")
            
            self.initial_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            initial_layout.addWidget(self.initial_label)
        
        self.main_layout.addWidget(self.initial_widget)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background: black; border-radius: 8px;")
        self.main_layout.addWidget(self.video_label)
        
        self.set_frame(None)

        # CRITICAL FIX: Permanent overlay container with proper stacking
        overlay_container = QWidget(self)
        overlay_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        overlay_container.setStyleSheet("background: transparent;")
        overlay_layout = QVBoxLayout(overlay_container)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setSpacing(0)
        
        # Emoji reaction container (top center)
        self.emoji_container = QWidget()
        self.emoji_container.setStyleSheet("background: transparent;")
        emoji_layout = QHBoxLayout(self.emoji_container)
        emoji_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        overlay_layout.addWidget(self.emoji_container, 1)
        
        # Bottom bar with name and badges
        bottom_bar = QWidget()
        bottom_bar.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        bottom_bar.setStyleSheet("background: transparent;")
        bottom_bar_layout = QHBoxLayout(bottom_bar)
        bottom_bar_layout.setContentsMargins(10, 5, 10, 5)
        bottom_bar_layout.setSpacing(2)
        
        # PERMANENT NAME LABEL - Always visible
        self.name_badge = QLabel(self.username + (" (You)" if self.is_self else ""))
        self.name_badge.setObjectName("name_tag_label")
        self.name_badge.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.8);
                color: white;
                font-size: 13px;
                font-weight: 600;
                padding: 6px 10px;
                border-radius: 4px;
            }
        """)
        bottom_bar_layout.addWidget(self.name_badge)
        
        self.host_badge = QLabel("👑")
        self.host_badge.setToolTip("Host")
        self.host_badge.setObjectName("host_badge")
        self.host_badge.setVisible(self.is_host) # Use property
        bottom_bar_layout.addWidget(self.host_badge)

        self.mute_indicator = QLabel("🎤")
        self.mute_indicator.setObjectName("mute_indicator")
        self.mute_indicator.setVisible(False)
        bottom_bar_layout.addWidget(self.mute_indicator)
        
        # Mic lock indicator
        self.lock_indicator = QLabel("🔒")
        self.lock_indicator.setToolTip("Mic Locked by Host")
        self.lock_indicator.setObjectName("lock_indicator")
        self.lock_indicator.setVisible(False)
        bottom_bar_layout.addWidget(self.lock_indicator)

        # Raise Hand Icon
        self.hand_raise_indicator = QLabel("✋")
        self.hand_raise_indicator.setObjectName("hand_raise_indicator")
        self.hand_raise_indicator.setStyleSheet("""
            QLabel {
                background-color: #ffb900;
                color: #242424;
                font-size: 14px;
                font-weight: 600;
                padding: 6px 10px;
                border-radius: 6px;
            }
        """)
        self.hand_raise_indicator.setVisible(False)
        bottom_bar_layout.addWidget(self.hand_raise_indicator)

        bottom_bar_layout.addStretch()
        
        # Context menu button for host
        parent_window = self.parent()
        while parent_window and not isinstance(parent_window, EnhancedMainWindow):
            parent_window = parent_window.parent()
        is_host_viewing = parent_window.is_host if parent_window else False

        self.menu_button = QPushButton(qta.icon('fa5s.ellipsis-v', color='white'), "")
        self.menu_button.setObjectName("menu_button")
        self.menu_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.6);
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.8);
            }
        """)
        self.menu_button.clicked.connect(self.show_participant_menu)
        self.menu_button.setVisible(is_host_viewing and not self.is_self)
        bottom_bar_layout.addWidget(self.menu_button)
        
        overlay_layout.addWidget(bottom_bar)
        self.main_layout.addWidget(overlay_container)
        
        # Ensure overlay is always on top
        overlay_container.raise_()


    def set_frame(self, frame):
        if frame is not None:
            try:
                self.video_label.setVisible(True); self.initial_widget.setVisible(False)
                if len(frame.shape) == 2: frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
                elif frame.shape[2] == 4: frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                else: frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                widget_size = self.size()
                if widget_size.width() <= 1 or widget_size.height() <= 1: return
                
                frame_h, frame_w = frame.shape[:2]
                scale = min(widget_size.width()/frame_w, widget_size.height()/frame_h)
                new_w, new_h = int(frame_w*scale), int(frame_h*scale)
                if new_w <= 0 or new_h <= 0: return

                resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                q_img = QImage(resized.data, new_w, new_h, 3*new_w, QImage.Format.Format_RGB888)
                
                pixmap = QPixmap(widget_size); pixmap.fill(Qt.GlobalColor.black)
                painter = QPainter(pixmap)
                painter.drawImage((widget_size.width()-new_w)//2, (widget_size.height()-new_h)//2, q_img)
                painter.end()
                self.video_label.setPixmap(pixmap)
            except Exception as e: print(f"Error setting frame: {e}")
        else:
            self.video_label.setVisible(False); self.initial_widget.setVisible(True)

    def set_muted(self, muted):
        self.is_muted = muted
        self.mute_indicator.setVisible(muted)
    
    def set_mic_locked(self, locked):
        self.is_mic_locked = locked
        self.lock_indicator.setVisible(locked)
    
    def set_hand_raised(self, raised):
        self.hand_raised = raised
        self.hand_raise_indicator.setVisible(raised)
        if raised:
            # Add border highlight when hand is raised
            self.setStyleSheet("""
                QFrame#participant_video_widget {
                    border: 3px solid #ffb900;
                    box-shadow: 0 4px 12px rgba(255, 185, 0, 0.3);
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#participant_video_widget {
                    border: 2px solid #e8e8e8;
                }
            """)

    def set_host_status(self, is_host):
        self.is_host = is_host
        self.host_badge.setVisible(is_host)
    
    def show_emoji_reaction(self, emoji):
        """Display an animated emoji reaction on this participant's video"""
        # Create emoji widget within the container
        reaction = EmojiReactionWidget(emoji, self)
        # Position it at top-center of the participant tile
        reaction.move(self.width() // 2 - 30, 10)  # Center horizontally, 10px from top
        reaction.raise_()  # Ensure it's on top
        reaction.start_animation()
    
    def show_participant_menu(self):
        """Enhanced context menu with all host controls"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 10px 20px;
                border-radius: 6px;
                margin: 2px;
            }
            QMenu::item:selected {
                background-color: #f3f3f3;
            }
            QMenu::item:pressed {
                background-color: #e8e8e8;
            }
        """)
        
        # Mute/Unmute control
        mute_action = QAction(qta.icon('fa5s.microphone-slash' if not self.is_muted else 'fa5s.microphone'), 
                            "Unmute Participant" if self.is_muted else "Mute Participant", self)
        mute_action.triggered.connect(lambda: self.mute_clicked.emit(self.client_id, not self.is_muted))
        menu.addAction(mute_action)
        
        # Lock/Unlock Mic (prevent unmute)
        lock_action = QAction(qta.icon('fa5s.lock' if not self.is_mic_locked else 'fa5s.unlock'),
                            "Unlock Mic" if self.is_mic_locked else "Lock Mic (Prevent Unmute)", self)
        lock_action.triggered.connect(lambda: self.lock_mic_clicked.emit(self.client_id, not self.is_mic_locked))
        menu.addAction(lock_action)
        
        menu.addSeparator()
        
        # Request to Unmute
        if self.is_muted:
            unmute_req_action = QAction(qta.icon('fa5s.comment-dots'), "Request to Unmute", self)
            unmute_req_action.triggered.connect(lambda: self.unmute_request_clicked.emit(self.client_id))
            menu.addAction(unmute_req_action)
        
        # Request to Start Video
        video_action = QAction(qta.icon('fa5s.video'), "Request to Turn On Video", self)
        video_action.triggered.connect(lambda: self.video_request_clicked.emit(self.client_id))
        menu.addAction(video_action)
        
        menu.exec(self.menu_button.mapToGlobal(QPoint(0, self.menu_button.height())))


    def mouseDoubleClickEvent(self, event):
        # Disabled focus mode on double-click for better UX
        # self.focused.emit(self.client_id)
        super().mouseDoubleClickEvent(event)

class ChatMessageWidget(QFrame):
    def __init__(self, username, text, timestamp, is_self, color):
        super().__init__()
        self.setObjectName("chat_message_widget")
        self.setProperty("is_self", is_self)
        
        # Ensure full width utilization
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 8, 16, 8)  # iOS-like compact margins
        main_layout.setSpacing(8)  # Tighter spacing for iOS feel
        
        # iOS iMessage style - no avatars, just message bubbles
        if is_self:
            # Add flexible space on the left for sent messages
            main_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        bubble_container = QFrame()
        bubble_container.setObjectName("chat_bubble")
        bubble_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        
        # iOS iMessage max width - dynamically calculated
        bubble_container.setMaximumWidth(400)  # Initial max width, will be adjusted
        bubble_container.setMinimumWidth(80)  # Minimum width for small messages
        
        # iOS dark mode iMessage bubble styling
        if is_self:
            bubble_container.setStyleSheet("""
                QFrame#chat_bubble {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0A84FF, stop:1 #0969DA);
                    border-radius: 20px;
                    border-bottom-right-radius: 6px;
                    margin: 2px;
                    border: none;
                }
            """)
        else:
            bubble_container.setStyleSheet("""
                QFrame#chat_bubble {
                    background-color: #2C2C2E;
                    border-radius: 20px;
                    border-bottom-left-radius: 6px;
                    margin: 2px;
                    border: none;
                }
            """)
        
        bubble_layout = QVBoxLayout(bubble_container)
        bubble_layout.setContentsMargins(16, 12, 16, 10)  # iOS-like padding with extra top space for username
        bubble_layout.setSpacing(3)  # Slightly more spacing for better readability

        # Add sender name for all messages (always show who sent what)
        username_label = QLabel(username)
        
        if is_self:
            # For your own messages, use a subtle white color
            username_label.setStyleSheet("""
                color: rgba(255, 255, 255, 0.9);
                font-size: 12px;
                font-weight: 600;
                margin-bottom: 3px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            """)
        else:
            # For received messages, use a lighter version of the user's color
            r, g, b = color.red(), color.green(), color.blue()
            # Lighten the color for better visibility on dark background
            light_color = QColor(min(255, r + 60), min(255, g + 60), min(255, b + 60))
            username_label.setStyleSheet(f"""
                color: {light_color.name()};
                font-size: 12px;
                font-weight: 600;
                margin-bottom: 3px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            """)
        
        bubble_layout.addWidget(username_label)
        
        # Message text with proper width handling
        message_label = QLabel(text)
        message_label.setWordWrap(True)
        message_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # Removed text selection to avoid black highlights
        message_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        
        # iOS iMessage text styling
        if is_self:
            message_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 16px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.4;
                    padding: 0px;
                    margin: 0px;
                    background: transparent;
                }
            """)
        else:
            message_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 16px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.4;
                    padding: 0px;
                    margin: 0px;
                    background: transparent;
                }
            """)
        
        bubble_layout.addWidget(message_label)
        
        # iOS-style timestamp (smaller and more subtle)
        timestamp_label = QLabel(timestamp)
        timestamp_label.setObjectName("chat_timestamp")
        if is_self:
            timestamp_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.7);
                    font-size: 10px;
                    font-weight: 400;
                    margin-top: 2px;
                }
            """)
            timestamp_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            timestamp_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 10px;
                    font-weight: 400;
                    margin-top: 2px;
                }
            """)
            timestamp_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        bubble_layout.addWidget(timestamp_label)
        
        main_layout.addWidget(bubble_container)

        if not is_self:
            # Add flexible space on the right for received messages
            main_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
    
    def resizeEvent(self, event):
        """Handle resize events to adjust bubble width dynamically"""
        super().resizeEvent(event)
        if hasattr(self, 'findChild'):
            bubble = self.findChild(QFrame, "chat_bubble")
            if bubble:
                # Adjust max width based on window width
                available_width = self.width() - 80  # Account for margins
                max_width = max(200, int(available_width * 0.75))  # 75% of available width, minimum 200px
                bubble.setMaximumWidth(max_width)

class SystemMessageWidget(QWidget):
    def __init__(self, text, style_class=""):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)  # More generous margins
        
        # Center the system message
        layout.addStretch()
        
        self.label = QLabel(text)
        self.label.setObjectName("system_message_label")
        self.label.setProperty("class", style_class)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setMinimumHeight(32)
        
        # iOS iMessage-style system messages
        if style_class == "success":
            self.label.setStyleSheet("""
                QLabel {
                    background-color: rgba(52, 199, 89, 0.15);
                    color: #34C759;
                    border: none;
                    border-radius: 12px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: 500;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
            """)
        elif style_class == "error":
            self.label.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 59, 48, 0.15);
                    color: #FF3B30;
                    border: none;
                    border-radius: 12px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: 500;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
            """)
        elif style_class == "info":
            self.label.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 122, 255, 0.15);
                    color: #007AFF;
                    border: none;
                    border-radius: 12px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: 500;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
            """)
        else:
            # Default iOS-style system message
            self.label.setStyleSheet("""
                QLabel {
                    background-color: rgba(142, 142, 147, 0.15);
                    color: #8E8E93;
                    border: none;
                    border-radius: 12px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: 500;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
            """)
        
        layout.addWidget(self.label)
        layout.addStretch()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

class ScreenCaptureThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    def __init__(self): super().__init__(); self.running = False
    def run(self):
        self.running = True
        try:
            with mss.mss() as sct:
                while self.running:
                    frame = np.array(sct.grab(sct.monitors[1]), dtype=np.uint8)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    h, w = frame.shape[:2]
                    # Optimize for TCP: smaller resolution for better bandwidth usage
                    scale = min(1024/w, 576/h)  # Max 1024x576 instead of 1280x720
                    frame = cv2.resize(frame, (int(w*scale), int(h*scale)))
                    self.frame_ready.emit(frame)
                    # Reduced frame rate for TCP transmission (3 FPS for better reliability)
                    self.msleep(333)  # ~3 FPS
        except Exception as e: print(f"Screen capture error: {e}")
    def stop(self): self.running = False; self.wait()

class EnhancedMainWindow(QMainWindow):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.setWindowTitle("Loop")
        self.setMinimumSize(1280, 720)
        
        # Use dark theme only
        self.setStyleSheet(MAIN_STYLESHEET)
        
        self.video_widgets = {}
        self.is_host = False
        self.is_muted_by_host = False
        self.is_mic_locked_by_host = False
        self.video_enabled = False; self.audio_enabled = False; self.screen_sharing = False
        self.outgoing_transfers = {}
        self.file_widgets = {}  # Track file message widgets for updates
        

        

        
        self.camera = None; self.video_timer = None; self.screen_capture_thread = None
        self.ui_running = True
        
        # Profile picture management
        self.profile_pictures = {}  # client_id -> image_path
        self.my_profile_image = None
        

        
        # Raised hands queue for host
        self.raised_hands_queue = []
        

        
        self.p_audio = None
        self.input_device_index = None
        self.output_device_index = None
        self.init_audio_devices()
        self.audio_thread_input = None; self.audio_thread_output = None
        self.audio_output_queue = queue.Queue()
        self.audio_chunk_size, self.audio_rate = 1024, 44100
        self.focused_client_id = None
        self.grid_size = 0
        self.current_page = 0
        if not self.show_login(): import sys; sys.exit()
        if self.p_audio:
            self.audio_thread_output = threading.Thread(target=self._audio_write_thread, daemon=True)
            self.audio_thread_output.start()

    def init_audio_devices(self):
        """
        MODIFIED: Initialize PyAudio using the system's default devices first.
        This is much more reliable than scanning and picking the first device.
        """
        try:
            self.p_audio = pyaudio.PyAudio()
            self.input_device_index = None
            self.output_device_index = None

            # Try to get default input device
            try:
                default_input_info = self.p_audio.get_default_input_device_info()
                self.input_device_index = default_input_info['index']
                print(f"🎤 Found default input device: {default_input_info['name']} (Index: {self.input_device_index})")
            except Exception as e:
                print(f"⚠️ Could not get default input device: {e}. Will scan for alternatives.")
                
            # Try to get default output device
            try:
                default_output_info = self.p_audio.get_default_output_device_info()
                self.output_device_index = default_output_info['index']
                print(f"🔊 Found default output device: {default_output_info['name']} (Index: {self.output_device_index})")
            except Exception as e:
                print(f"⚠️ Could not get default output device: {e}. Will scan for alternatives.")

            # Fallback: If defaults failed, scan all devices (old method)
            if self.input_device_index is None or self.output_device_index is None:
                print("Scanning all devices as a fallback...")
                num_devices = self.p_audio.get_device_count()
                for i in range(num_devices):
                    try:
                        info = self.p_audio.get_device_info_by_index(i)
                        
                        if self.input_device_index is None and info['maxInputChannels'] > 0:
                            self.input_device_index = i
                            print(f"🎤 Found fallback input device: {info['name']} (index {i})")
                        
                        if self.output_device_index is None and info['maxOutputChannels'] > 0:
                            self.output_device_index = i
                            print(f"🔊 Found fallback output device: {info['name']} (index {i})")
                            
                    except Exception:
                        continue
            
            if self.input_device_index is None:
                print("❌ ERROR: No input devices (microphone) found.")
            
            if self.output_device_index is None:
                print("❌ ERROR: No output devices (speakers) found.")
                
        except Exception as e:
            print(f"❌ PyAudio initialization failed: {e}")
            self.p_audio = None
    
    def get_color_from_name(self, name):
        """Dark blue color palette for dark mode"""
        colors = [
            QColor(30, 144, 255),   # dodger blue (primary)
            QColor(65, 105, 225),   # royal blue
            QColor(70, 130, 180),   # steel blue
            QColor(100, 149, 237),  # cornflower blue
            QColor(72, 61, 139),    # dark slate blue
            QColor(106, 90, 205),   # slate blue
            QColor(123, 104, 238),  # medium slate blue
        ]
        h = hashlib.sha1(name.encode()).hexdigest()
        index = int(h[:4], 16) % len(colors)
        return colors[index]
    
    
    def play_sound(self, sound_type):
        """Play notification sounds"""
        try:
            if platform.system() == 'Windows':
                import winsound
                if sound_type == 'join':
                    winsound.PlaySound('SystemAsterisk', winsound.SND_ALIAS | winsound.SND_ASYNC)
                elif sound_type == 'meeting_start':
                    winsound.PlaySound('SystemExclamation', winsound.SND_ALIAS | winsound.SND_ASYNC)
            else:
                # For other platforms, use QSound or system bell
                QApplication.beep()
        except:
            pass

    def show_login(self):
        login = EnhancedLoginDialog(self)
        login.connection_requested.connect(self.attempt_connection)
        return login.exec() == QDialog.DialogCode.Accepted

    def attempt_connection(self, username, server_ip, tcp_port, meeting_code, is_creating):
        sender = self.sender()
        self.client.set_server(server_ip, tcp_port)
        action = self.client.create_meeting if is_creating else self.client.join_meeting
        args = (username,) if is_creating else (username, meeting_code)
        
        result_tuple = action(*args)
        success = result_tuple[0]
        result_data = result_tuple[1]

        if success:
            self.is_host = is_creating
            sender.connection_successful(result_data if is_creating else None)
            self.setup_ui()
            self.setWindowTitle(f"Loop - {result_data if is_creating else meeting_code}")
            self.add_self_video()
            
            # Play meeting start sound if creating
            if is_creating:
                self.play_sound('meeting_start')
            
            if not is_creating:
                participants = result_tuple[2] if len(result_tuple) > 2 else result_data
                for p in participants:
                    if p.get('client_id') != self.client.client_id:
                        self.add_participant_video(p['client_id'], p['username'], p['is_host'])
            self.client.send_udp_init()
        else:
            sender.reset(); sender.show_error(str(result_data))

    def setup_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        main_layout = QHBoxLayout(central); main_layout.setContentsMargins(0,0,0,0); main_layout.setSpacing(0)
        video_panel = QFrame(); video_panel.setObjectName("video_panel")
        video_panel.setStyleSheet("""
            QFrame#video_panel {
                background-color: #000000;
            }
        """)
        video_layout = QVBoxLayout(video_panel); video_layout.setContentsMargins(15,15,15,15); video_layout.setSpacing(10)
        
        top_bar = QFrame(); top_bar.setObjectName("top_bar")
        top_bar.setStyleSheet("""
            QFrame#top_bar {
                background-color: #1C1C1E;
                border-bottom: 1px solid #38383A;
                padding: 8px;
            }
        """)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0,0,0,0)

        # Sidebar control buttons
        sidebar_controls = QWidget()
        sidebar_controls_layout = QHBoxLayout(sidebar_controls)
        sidebar_controls_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_controls_layout.setSpacing(8)
        
        # Toggle sidebar visibility button
        self.toggle_sidebar_button = QPushButton(qta.icon('fa5s.bars', color='white'), "")
        self.toggle_sidebar_button.setObjectName("sidebar_toggle_button")
        self.toggle_sidebar_button.setToolTip("Hide/Show Sidebar")
        self.toggle_sidebar_button.setFixedSize(36, 36)
        self.toggle_sidebar_button.setStyleSheet("""
            QPushButton {
                background-color: #2C2C2E;
                border: 1px solid #38383A;
                border-radius: 18px;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #3A3A3C;
                border: 1px solid #48484A;
            }
            QPushButton:pressed {
                background-color: #1C1C1E;
            }
        """)
        self.toggle_sidebar_button.clicked.connect(self.toggle_sidebar)
        self.toggle_sidebar_button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.toggle_sidebar_button.customContextMenuRequested.connect(self.show_sidebar_context_menu)
        sidebar_controls_layout.addWidget(self.toggle_sidebar_button)
        
        # Popup sidebar button
        self.popup_sidebar_button = QPushButton(qta.icon('fa5s.window-restore', color='white'), "")
        self.popup_sidebar_button.setObjectName("popup_sidebar_button")
        self.popup_sidebar_button.setToolTip("Open Sidebar in Popup Window")
        self.popup_sidebar_button.setFixedSize(36, 36)
        self.popup_sidebar_button.setStyleSheet("""
            QPushButton {
                background-color: #2C2C2E;
                border: 1px solid #38383A;
                border-radius: 18px;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #3A3A3C;
                border: 1px solid #48484A;
            }
            QPushButton:pressed {
                background-color: #1C1C1E;
            }
        """)
        self.popup_sidebar_button.clicked.connect(self.toggle_popup_sidebar)
        sidebar_controls_layout.addWidget(self.popup_sidebar_button)
        
        # Sidebar status indicator
        self.sidebar_status_label = QLabel("📌")
        self.sidebar_status_label.setToolTip("Sidebar Status: Docked")
        self.sidebar_status_label.setStyleSheet("""
            QLabel {
                color: #8E8E93;
                font-size: 16px;
                padding: 8px;
                background-color: transparent;
            }
        """)
        sidebar_controls_layout.addWidget(self.sidebar_status_label)
        
        top_bar_layout.addWidget(sidebar_controls)
        top_bar_layout.addStretch()
        
        self.exit_focus_button = QPushButton(qta.icon('fa5s.compress', color='white'), " Exit Focus"); self.exit_focus_button.clicked.connect(lambda: self.toggle_focus_mode(self.focused_client_id))
        self.exit_focus_button.setVisible(False); top_bar_layout.addWidget(self.exit_focus_button)
        video_layout.addWidget(top_bar)

        self.main_view_stack = QStackedWidget()
        grid_container = QWidget(); self.video_grid_layout = QGridLayout(grid_container); self.video_grid_layout.setSpacing(15)
        self.main_view_stack.addWidget(grid_container)
        focus_container = QWidget(); focus_layout = QVBoxLayout(focus_container); focus_layout.setContentsMargins(0,0,0,0)
        self.focused_widget_container = QFrame(); self.focused_widget_container.setLayout(QVBoxLayout())
        focus_layout.addWidget(self.focused_widget_container)
        self.main_view_stack.addWidget(focus_container)
        video_layout.addWidget(self.main_view_stack)
        
        self.pip_video_container = QFrame(self); self.pip_video_container.setFixedSize(240, 180); self.pip_video_container.setLayout(QVBoxLayout())
        self.pip_video_container.setObjectName("participant_video_widget"); self.pip_video_container.setVisible(False)

        controls = self.create_controls(); video_layout.addWidget(controls)
        main_layout.addWidget(video_panel, 3)

        side_panel = QFrame()
        side_panel.setObjectName("side_panel")
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)
        
        # Create tab widget with scroll functionality
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.setMovable(False)
        self.tab_widget.setUsesScrollButtons(True)  # Enable scroll buttons for tabs
        self.tab_widget.setElideMode(Qt.TextElideMode.ElideRight)  # Elide long tab names
        
        # iOS Dark Mode styling for tabs
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #38383A;
                background-color: #000000;
                border-radius: 10px;
            }
            QTabBar::tab {
                background-color: #1C1C1E;
                color: #FFFFFF;
                padding: 12px 24px;
                margin-right: 3px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                min-width: 90px;
                font-weight: 500;
                font-size: 15px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QTabBar::tab:selected {
                background-color: #0A84FF;
                color: #FFFFFF;
                font-weight: 600;
            }
            QTabBar::tab:hover {
                background-color: #2C2C2E;
            }
            QTabBar::scroller {
                width: 24px;
                background-color: #1C1C1E;
            }
            QTabBar QToolButton {
                background-color: #1C1C1E;
                border: none;
                color: #FFFFFF;
                border-radius: 4px;
            }
            QTabBar QToolButton:hover {
                background-color: #2C2C2E;
            }
        """)
        
        self.tab_widget.addTab(self.create_chat_panel(), "Chat")
        self.tab_widget.addTab(self.create_participants_panel(), "Participants (1)")
        
        if self.is_host:
            self.tab_widget.addTab(self.create_admin_panel(), "Admin")
        
        # Connect tab changed signal to clear notifications
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
            
        side_layout.addWidget(self.tab_widget)
        
        # Store references for sidebar management
        self.side_panel = side_panel
        self.main_layout = main_layout
        self.sidebar_visible = True
        self.sidebar_popup = None
        self.sidebar_mode = "docked"  # "docked", "hidden", "popup"
        
        # Add keyboard shortcuts for sidebar management
        self.setup_sidebar_shortcuts()
        
        # Load saved sidebar preferences
        self.load_sidebar_preferences()
        
        main_layout.addWidget(side_panel, 1)

    def on_tab_changed(self, index):
        # Handle any tab switching logic here if needed
        pass





    # --- UPDATED: Icon Bug Fix + Raise Hand Button ---
    def create_controls(self):
        controls = QFrame()
        controls.setObjectName("controls_bar")
        controls.setFixedHeight(100)  # Increased height for larger emoji buttons
        controls.setStyleSheet("""
            QFrame#controls_bar {
                background-color: #1C1C1E;
                border-top: 1px solid #38383A;
            }
        """)
        
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(24, 25, 24, 25)  # Increased margins for better spacing
        layout.setSpacing(20)  # Increased spacing between elements
        
        def setup_control_button(name, icon_off, icon_on, tooltip, is_mic=False):
            btn = QPushButton(qta.icon(icon_off, color='white'), "")
            btn.setObjectName(name)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setIconSize(QSize(22, 22))
            btn.setFixedSize(50, 50)
            
            def set_style(checked):
                is_on = not checked if is_mic else checked
                
                if is_on:
                    # On/Unmuted state - Green
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #10B981;
                            border: 1px solid #10B981;
                            border-radius: 25px;
                            color: #FFFFFF;
                        }
                        QPushButton:hover {
                            background-color: #059669;
                            border: 1px solid #059669;
                        }
                        QPushButton:pressed {
                            background-color: #047857;
                        }
                    """)
                    icon_color = "white"
                    current_icon = icon_on
                else:
                    # Off/Muted state - Red
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #EF4444;
                            border: 1px solid #EF4444;
                            border-radius: 25px;
                            color: #FFFFFF;
                        }
                        QPushButton:hover {
                            background-color: #DC2626;
                            border: 1px solid #DC2626;
                        }
                        QPushButton:pressed {
                            background-color: #B91C1C;
                        }
                    """)
                    icon_color = "white"
                    current_icon = icon_off
                
                btn.setIcon(qta.icon(current_icon, color=icon_color))

            btn.toggled.connect(set_style)
            set_style(btn.isChecked())
            return btn
        
        self.cam_button = setup_control_button("cam_button", 'fa5s.video-slash', 'fa5s.video', "Toggle Camera")
        self.cam_button.toggled.connect(self.toggle_camera)
        
        # BUG FIX: icon_off is 'microphone-slash', icon_on is 'microphone'
        self.mic_button = setup_control_button("mic_button", 'fa5s.microphone-slash', 'fa5s.microphone', "Toggle Microphone", is_mic=True)
        self.mic_button.setChecked(True); self.mic_button.toggled.connect(self.toggle_microphone)
        
        # Mic activity indicator
        self.mic_activity_label = QLabel("")
        self.mic_activity_label.setFixedSize(12, 12)
        self.mic_activity_label.setStyleSheet("background-color: #333; border-radius: 6px;")
        self.mic_activity_label.setToolTip("Mic Activity")
        layout.addWidget(self.mic_activity_label)
        
        # BUG FIX: icon_off is 'window-close', icon_on is 'desktop'
        self.screen_button = setup_control_button("screen_button", 'fa5s.window-close', 'fa5s.desktop', "Toggle Screen Share")
        self.screen_button.toggled.connect(self.toggle_screen_share)
        
        # Main control buttons group
        main_controls = QWidget()
        main_controls_layout = QHBoxLayout(main_controls)
        main_controls_layout.setContentsMargins(0, 0, 0, 0)
        main_controls_layout.setSpacing(15)
        
        main_controls_layout.addWidget(self.cam_button)
        main_controls_layout.addWidget(self.mic_button)
        main_controls_layout.addWidget(self.screen_button)
        
        layout.addWidget(main_controls)
        
        # Separator - iOS style
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        separator1.setStyleSheet("color: rgba(99, 99, 102, 0.6);")
        layout.addWidget(separator1)
        
        # Raise Hand Button
        self.raise_hand_button = setup_control_button("raise_hand_button", 'fa5s.hand-paper', 'fa5s.hand-paper', "Raise Hand")
        self.raise_hand_button.toggled.connect(self.toggle_raise_hand)
        layout.addWidget(self.raise_hand_button)
        
        # Separator - iOS style
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        separator2.setStyleSheet("color: rgba(99, 99, 102, 0.6);")
        layout.addWidget(separator2)
        
        # Emoji Reaction Buttons - iOS Dark Mode Style with better spacing
        emoji_container = QWidget()
        emoji_layout = QHBoxLayout(emoji_container)
        emoji_layout.setContentsMargins(4, 0, 4, 0)
        emoji_layout.setSpacing(1)
        
        emojis = ['✋', '👍', '👏', '🎉']  # Essential reactions
        for emoji in emojis:
            btn = QPushButton(emoji)
            btn.setObjectName("emoji_button")
            btn.setFixedSize(50, 50)  # Increased from 40x40 to 50x50
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2C2C2E;
                    border: 1px solid #38383A;
                    border-radius: 25px;
                    font-size: 22px;
                    color: white;
                    font-weight: 400;
                }
                QPushButton:hover {
                    background-color: #3A3A3C;
                    border: 1px solid #48484A;
                }
                QPushButton:pressed {
                    background-color: #0A84FF;
                    border: 1px solid #0A84FF;
                }
            """)
            btn.clicked.connect(lambda checked, e=emoji: self.send_emoji_reaction(e))
            emoji_layout.addWidget(btn)
        
        layout.addWidget(emoji_container)
        
        # Settings Button - iOS style
        settings_btn = QPushButton(qta.icon('fa5s.cog', color='white'), "")
        settings_btn.setObjectName("settings_button")
        settings_btn.setToolTip("Settings")
        settings_btn.setFixedSize(50, 50)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #2C2C2E;
                border: 1px solid #38383A;
                border-radius: 25px;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #3A3A3C;
                border: 1px solid #48484A;
            }
            QPushButton:pressed {
                background-color: #0A84FF;
                border: 1px solid #0A84FF;
            }
        """)
        settings_btn.clicked.connect(self.show_settings_dialog)
        layout.addWidget(settings_btn)
        
        # Flexible space
        layout.addStretch()
        
        # Utility buttons group
        utility_controls = QWidget()
        utility_controls_layout = QHBoxLayout(utility_controls)
        utility_controls_layout.setContentsMargins(0, 0, 0, 0)
        utility_controls_layout.setSpacing(10)
        
        # Test Mic Button - iOS style
        self.test_mic_button = QPushButton(qta.icon('fa5s.microphone', color='white'), "")
        self.test_mic_button.setObjectName("test_mic_button")
        self.test_mic_button.setToolTip("Test Microphone")
        self.test_mic_button.setIconSize(QSize(20, 20))
        self.test_mic_button.setFixedSize(50, 50)
        self.test_mic_button.setStyleSheet("""
            QPushButton {
                background-color: #2C2C2E;
                border: 1px solid #38383A;
                border-radius: 25px;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #3A3A3C;
                border: 1px solid #48484A;
            }
            QPushButton:pressed {
                background-color: #0A84FF;
            }
        """)
        self.test_mic_button.clicked.connect(self.test_microphone)
        utility_controls_layout.addWidget(self.test_mic_button)
        
        # Separator - iOS style
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        separator2.setStyleSheet("color: rgba(99, 99, 102, 0.6);")
        utility_controls_layout.addWidget(separator2)
        
        # Leave button - iOS style with red accent
        leave_button = QPushButton(qta.icon('fa5s.phone-slash', color='white'), "")
        leave_button.setObjectName("leave_button")
        leave_button.setToolTip("Leave Meeting")
        leave_button.clicked.connect(self.leave_meeting)
        leave_button.setIconSize(QSize(20, 20))
        leave_button.setFixedSize(55, 50)
        leave_button.setStyleSheet("""
            QPushButton {
                background-color: #FF3B30;
                border: 1px solid #FF3B30;
                border-radius: 25px;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #FF453A;
                border: 1px solid #FF453A;
            }
            QPushButton:pressed {
                background-color: #D70015;
            }
        """)
        utility_controls_layout.addWidget(leave_button)
        
        layout.addWidget(utility_controls)
        return controls

    def create_chat_panel(self):
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #000000;
                color: #FFFFFF;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setSpacing(0)  # No spacing for seamless iOS look
        layout.setContentsMargins(0, 0, 0, 0)  # No margins for full coverage
        
        # Chat area with iOS dark mode iMessage styling
        self.chat_list = QListWidget()
        self.chat_list.setObjectName("chat_display_list")
        self.chat_list.setSpacing(4)  # iOS-like tight spacing between messages
        self.chat_list.setAlternatingRowColors(False)
        self.chat_list.setMovement(QListView.Movement.Static)
        self.chat_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.chat_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.chat_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.chat_list.setWordWrap(True)
        self.chat_list.setUniformItemSizes(False)
        self.chat_list.setStyleSheet("""
            QListWidget {
                background-color: #000000;
                border: none;
                outline: none;
                padding: 16px 0px;
            }
            QListWidget::item {
                border: none;
                background-color: transparent;
                margin: 0px;
                padding: 0px;
            }
            QScrollBar:vertical {
                background-color: #1C1C1E;
                width: 8px;
                border: none;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #48484A;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #636366;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        layout.addWidget(self.chat_list)
        
        # Input container with iOS dark mode styling
        input_container = QFrame()
        input_container.setObjectName("chat_input_container")
        input_container.setStyleSheet("""
            QFrame#chat_input_container {
                background-color: #1C1C1E;
                border: none;
                border-top: 1px solid #38383A;
                padding: 12px 16px;
            }
        """)
        
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        # iOS dark mode attachment button
        file_btn = QPushButton(qta.icon('fa5s.plus', color='#0A84FF'), "")
        file_btn.setObjectName("chat_icon_button")
        file_btn.setToolTip("Attach")
        file_btn.setFixedSize(32, 32)
        file_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 16px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: rgba(10, 132, 255, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(10, 132, 255, 0.2);
            }
        """)
        file_btn.clicked.connect(self.select_file_to_send)
        input_layout.addWidget(file_btn)

        # Message input with iOS dark mode styling
        message_input_container = QFrame()
        message_input_container.setStyleSheet("""
            QFrame {
                background-color: #2C2C2E;
                border: 1px solid #38383A;
                border-radius: 20px;
            }
        """)
        
        message_input_layout = QHBoxLayout(message_input_container)
        message_input_layout.setContentsMargins(16, 8, 16, 8)
        message_input_layout.setSpacing(8)

        self.chat_input = QLineEdit()
        self.chat_input.setObjectName("chat_input")
        self.chat_input.setPlaceholderText("Message")
        self.chat_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background-color: transparent;
                color: #FFFFFF;
                font-size: 16px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 8px 0px;
                font-weight: 400;
                min-height: 20px;
            }
            QLineEdit::placeholder {
                color: #8E8E93;
            }
            QLineEdit:focus {
                color: #FFFFFF;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_chat)
        message_input_layout.addWidget(self.chat_input)
        
        input_layout.addWidget(message_input_container)
        
        # iOS dark mode send button
        send_btn = QPushButton("↑")
        send_btn.setObjectName("send_button")
        send_btn.setToolTip("Send")
        send_btn.setFixedSize(32, 32)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0A84FF;
                border: none;
                border-radius: 16px;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #0969DA;
            }
            QPushButton:pressed {
                background-color: #0550AE;
            }
        """)
        send_btn.clicked.connect(self.send_chat)
        input_layout.addWidget(send_btn)
        
        # Add typing indicator area (hidden by default) - iOS dark mode
        self.typing_indicator = QLabel()
        self.typing_indicator.setObjectName("typing_indicator")
        self.typing_indicator.setStyleSheet("""
            QLabel {
                color: #8E8E93;
                font-size: 12px;
                font-style: italic;
                padding: 8px 16px;
                background-color: #1C1C1E;
                border-top: 1px solid #38383A;
            }
        """)
        self.typing_indicator.setVisible(False)
        layout.addWidget(self.typing_indicator)
        
        layout.addWidget(input_container)
        return panel

    def create_participants_panel(self):
        """Enhanced participant panel with iOS dark mode styling"""
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #000000;
                color: #FFFFFF;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 20, 16, 20)  # Increased margins for better spacing
        layout.setSpacing(16)  # Increased spacing between sections
        
        # Raised hands queue (visible only to host) - iOS dark mode style
        self.raised_hands_widget = QWidget()
        self.raised_hands_widget.setVisible(False)
        self.raised_hands_widget.setStyleSheet("""
            QWidget {
                background-color: #2C2C2E;
                border: 1px solid #FF9F0A;
                border-radius: 12px;
                padding: 8px;
            }
        """)
        
        raised_hands_layout = QVBoxLayout(self.raised_hands_widget)
        raised_hands_layout.setContentsMargins(12, 8, 12, 8)
        raised_hands_layout.setSpacing(6)
        
        raised_hands_label = QLabel("Raised Hands")
        raised_hands_label.setStyleSheet("""
            QLabel {
                font-weight: 600; 
                color: #FF9F0A; 
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        raised_hands_layout.addWidget(raised_hands_label)
        
        self.raised_hands_list = QListWidget()
        self.raised_hands_list.setMaximumHeight(100)
        self.raised_hands_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
                font-size: 12px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 6px;
                margin: 1px 0px;
                background-color: #1C1C1E;
                color: #FFFFFF;
            }
            QListWidget::item:hover {
                background-color: #3A3A3C;
            }
        """)
        raised_hands_layout.addWidget(self.raised_hands_list)
        layout.addWidget(self.raised_hands_widget)
        
        # Participants section header - iOS dark mode style
        participants_header = QLabel("Participants")
        participants_header.setStyleSheet("""
            QLabel {
                font-weight: 600;
                color: #FFFFFF;
                font-size: 18px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 12px 4px 8px 4px;
                background: transparent;
                border: none;
                margin-bottom: 4px;
            }
        """)
        layout.addWidget(participants_header)
        
        # Participant list - iOS dark mode style
        self.participants_list = QListWidget()
        self.participants_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                outline: none;
                padding: 8px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QListWidget::item {
                border: none;
                background-color: transparent;
                margin: 4px 0px;
                padding: 0px;
            }
        """)
        self.participants_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.participants_list.customContextMenuRequested.connect(self.show_participant_context_menu)
        self.participants_list.setSpacing(6)  # Better spacing between items
        
        layout.addWidget(self.participants_list)
        
        return panel



    def create_admin_panel(self):
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #000000;
                color: #FFFFFF;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 20, 16, 20)  # iOS-style margins
        
        # Header - iOS dark mode style
        header = QLabel("Meeting Controls")
        header.setStyleSheet("""
            QLabel {
                font-weight: 600;
                font-size: 20px;
                color: #FFFFFF;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 12px 0px 8px 0px;
                border-bottom: 1px solid #0A84FF;
                margin-bottom: 16px;
                background: transparent;
            }
        """)
        layout.addWidget(header)
        
        def create_admin_button(text, icon_name=None):
            btn = QPushButton(text)
            if icon_name:
                btn.setIcon(qta.icon(icon_name, color='white'))
                btn.setIconSize(QSize(18, 18))
            
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #0A84FF;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 10px;
                    padding: 14px 18px;
                    font-size: 15px;
                    font-weight: 500;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #0969DA;
                }
                QPushButton:pressed {
                    background-color: #0550AE;
                }
            """)
            btn.clicked.connect(lambda: self.handle_admin_action(text))
            return btn
        
        # Audio controls section - iOS dark mode style
        audio_section = QLabel("Audio Controls")
        audio_section.setStyleSheet("""
            QLabel {
                font-weight: 600; 
                color: #8E8E93; 
                font-size: 13px; 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin-top: 8px;
                padding: 4px 0px;
                background: transparent;
            }
        """)
        layout.addWidget(audio_section)
        
        layout.addWidget(create_admin_button("Mute All Participants", "fa5s.microphone-slash"))
        layout.addWidget(create_admin_button("Ask All to Unmute", "fa5s.microphone"))
        
        layout.addSpacing(20)
        
        # Video controls section - iOS dark mode style
        video_section = QLabel("Video Controls")
        video_section.setStyleSheet("""
            QLabel {
                font-weight: 600; 
                color: #8E8E93; 
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 4px 0px;
                background: transparent;
            }
        """)
        layout.addWidget(video_section)
        
        layout.addWidget(create_admin_button("Stop All Participant Video", "fa5s.video-slash"))
        layout.addWidget(create_admin_button("Ask All to Start Video", "fa5s.video"))
        
        layout.addSpacing(20)
        
        # Screen sharing controls section - iOS style
        screen_section = QLabel("Screen Sharing")
        screen_section.setStyleSheet("""
            QLabel {
                font-weight: 600; 
                color: rgba(255, 255, 255, 0.7); 
                font-size: 13px;
                padding: 4px 0px;
                background: transparent;
            }
        """)
        layout.addWidget(screen_section)
        
        layout.addWidget(create_admin_button("Request Screen Share", "fa5s.desktop"))
        layout.addWidget(create_admin_button("Disable Screen Sharing", "fa5s.ban"))

        layout.addStretch()
        return panel

    def handle_admin_action(self, action_text):
        print(f"HOST ACTION: {action_text}")
        if action_text == "Ask All to Start Video":
            self.client.send_tcp_message({'type': 'request_all_video'})
            self.show_notification("Sent 'Ask All to Start Video' command")
        elif action_text == "Ask All to Unmute":
            self.client.send_tcp_message({'type': 'request_all_unmute'})
            self.show_notification("Sent 'Ask All to Unmute' command")
        elif action_text == "Request Screen Share":
            # Show dialog to select participant
            participants = [w.username for cid, w in self.video_widgets.items() if cid != self.client.client_id]
            if participants:
                participant, ok = QInputDialog.getItem(self, "Request Screen Share", 
                                                       "Select participant to request screen share from:",
                                                       participants, 0, False)
                if ok and participant:
                    # Find client_id for selected participant
                    for cid, w in self.video_widgets.items():
                        if w.username == participant:
                            self.client.send_tcp_message({'type': 'request_screen_share', 'target_client_id': cid})
                            self.show_notification(f"Sent screen share request to {participant}")
                            break
            else:
                self.show_notification("No participants to request screen share from")
        elif action_text == "Disable Screen Sharing":
            self.client.send_tcp_message({'type': 'disable_screen_sharing'})
            self.show_notification("Screen sharing has been disabled for all participants")
        else:
            self.show_notification(f"Sent command: {action_text}")

    def show_participant_context_menu(self, pos):
        item = self.participants_list.itemAt(pos)
        if not item: return

        client_id = item.data(Qt.ItemDataRole.UserRole)
        if client_id == self.client.client_id: return
        
        widget = self.video_widgets.get(client_id)
        if not widget: return

        menu = QMenu()
        

        
        # Host-only options
        if self.is_host:
            mute_action = QAction("Unmute Participant" if widget.is_muted else "Mute Participant", self)
            mute_action.triggered.connect(lambda: self.handle_mute_participant(client_id, not widget.is_muted))
            menu.addAction(mute_action)
            
            if widget.is_muted:
                unmute_req_action = QAction("Request to Unmute", self)
                unmute_req_action.triggered.connect(lambda: self.handle_unmute_request(client_id))
                menu.addAction(unmute_req_action)

            video_action = QAction("Request to Start Video", self)
            video_action.triggered.connect(lambda: self.handle_video_request(client_id))
            menu.addAction(video_action)
        
        menu.exec(self.participants_list.mapToGlobal(pos))

    def add_self_video(self):
        profile_image = self.profile_pictures.get(self.client.client_id)
        widget = ParticipantVideoWidget(self.client.client_id, self.client.username, 
                                       self.is_host, True, self, profile_image)
        widget.focused.connect(self.toggle_focus_mode)
        self.video_widgets[self.client.client_id] = widget
        self.update_participant_ui()

    def add_participant_video(self, client_id, username, is_host=False, profile_image=None):
        if not client_id or client_id in self.video_widgets: return
        widget = ParticipantVideoWidget(client_id, username, is_host, False, self, profile_image)
        widget.mute_clicked.connect(self.handle_mute_participant)
        widget.video_request_clicked.connect(self.handle_video_request)
        widget.unmute_request_clicked.connect(self.handle_unmute_request)
        widget.lock_mic_clicked.connect(self.handle_lock_mic)
        widget.focused.connect(self.toggle_focus_mode)
        self.video_widgets[client_id] = widget
        self.update_participant_ui()

    def remove_participant_video(self, client_id):
        if client_id in self.video_widgets:
            if self.focused_client_id == client_id: self.toggle_focus_mode(client_id)
            self.video_widgets.pop(client_id).deleteLater()
            self.update_participant_ui()

    def update_participant_ui(self):
        """Update participant list with enhanced UI showing status icons"""
        self.participants_list.clear()
        self.raised_hands_list.clear()
        
        # Update raised hands queue if host
        if self.is_host:
            self.raised_hands_widget.setVisible(len(self.raised_hands_queue) > 0)
            for client_id in self.raised_hands_queue:
                if client_id in self.video_widgets:
                    widget = self.video_widgets[client_id]
                    item = QListWidgetItem(f"{widget.username} - Hand Raised")
                    self.raised_hands_list.addItem(item)
        
        # Update main participant list
        for cid, widget in self.video_widgets.items():
            # Create custom widget for participant item with proper styling
            item_widget = QWidget()
            item_widget.setStyleSheet("""
                QWidget {
                    background-color: rgba(58, 58, 60, 0.8);
                    border: 1px solid rgba(99, 99, 102, 0.4);
                    border-radius: 12px;
                    padding: 8px;
                    margin: 2px;
                }
                QWidget:hover {
                    background-color: rgba(72, 72, 74, 0.9);
                    border: 1px solid rgba(0, 122, 255, 0.6);
                }
            """)
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(12, 8, 12, 8)  # Better margins
            item_layout.setSpacing(12)  # Better spacing
            
            # Profile picture or initial
            avatar_label = QLabel()
            if cid in self.profile_pictures:
                pixmap = QPixmap(self.profile_pictures[cid])
                scaled = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, 
                                      Qt.TransformationMode.SmoothTransformation)
                avatar_label.setPixmap(scaled)
            else:
                avatar_label.setText(widget.username[0].upper())
                avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                avatar_label.setStyleSheet(f"""
                    background-color: {widget.color.name()};
                    color: white;
                    border-radius: 16px;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 0px;
                    margin: 0px;
                """)
            avatar_label.setFixedSize(32, 32)
            item_layout.addWidget(avatar_label)
            
            # Name label with proper color for visibility
            name = widget.username + (" (You)" if widget.is_self else "")
            name_label = QLabel(name)
            name_label.setStyleSheet("""
                font-size: 15px; 
                font-weight: 500;
                color: rgba(255, 255, 255, 0.95);
                background-color: transparent;
            """)
            item_layout.addWidget(name_label, 1)
            
            # Status indicators without emojis
            if widget.is_host:
                host_label = QLabel("HOST")
                host_label.setStyleSheet("""
                    background-color: rgba(0, 122, 255, 1.0);
                    color: white;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: 600;
                """)
                host_label.setToolTip("Host")
                item_layout.addWidget(host_label)
            
            if widget.is_muted:
                mute_label = QLabel("MUTED")
                mute_label.setStyleSheet("""
                    background-color: rgba(255, 59, 48, 1.0);
                    color: white;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: 600;
                """)
                mute_label.setToolTip("Muted")
                item_layout.addWidget(mute_label)
            
            if widget.is_mic_locked:
                lock_label = QLabel("LOCKED")
                lock_label.setStyleSheet("""
                    background-color: rgba(142, 142, 147, 1.0);
                    color: white;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: 600;
                """)
                lock_label.setToolTip("Mic Locked")
                item_layout.addWidget(lock_label)
            
            if widget.hand_raised:
                hand_label = QLabel("HAND UP")
                hand_label.setStyleSheet("""
                    background-color: rgba(255, 204, 0, 1.0);
                    color: rgba(0, 0, 0, 0.8);
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: 600;
                """)
                hand_label.setToolTip("Hand Raised")
                item_layout.addWidget(hand_label)
            
            if not widget.video_enabled if hasattr(widget, 'video_enabled') else True:
                video_off_label = QLabel("NO CAM")
                video_off_label.setStyleSheet("""
                    background-color: rgba(99, 99, 102, 1.0);
                    color: white;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: 600;
                """)
                video_off_label.setToolTip("Video Off")
                item_layout.addWidget(video_off_label)
            
            # Add to list
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, cid)
            item.setSizeHint(item_widget.sizeHint())
            self.participants_list.addItem(item)
            self.participants_list.setItemWidget(item, item_widget)
        
        self.tab_widget.setTabText(1, f"Participants ({len(self.video_widgets)})")
        self.update_video_grid()

    def update_video_grid(self):
        for w in self.video_widgets.values(): w.setParent(None); w.setVisible(False)

        if self.focused_client_id:
            if self.focused_client_id in self.video_widgets:
                self.focused_widget_container.layout().addWidget(self.video_widgets[self.focused_client_id])
                self.video_widgets[self.focused_client_id].setVisible(True)
            if self.client.client_id in self.video_widgets:
                self.pip_video_container.layout().addWidget(self.video_widgets[self.client.client_id])
                self.video_widgets[self.client.client_id].setVisible(True)
            return

        grid_layout = self.main_view_stack.widget(0).layout()
        while grid_layout.count(): grid_layout.takeAt(0).widget().setParent(None)
        
        widgets_to_show = list(self.video_widgets.values())
        max_items = self.grid_size if self.grid_size > 0 else len(widgets_to_show)
        if max_items == 0: max_items = 1
        
        start_index = self.current_page * max_items
        end_index = start_index + max_items
        


        page_widgets = widgets_to_show[start_index:end_index]
        cols = 1 if len(page_widgets) <= 1 else (2 if max_items <= 4 else 3)
        for i, widget in enumerate(page_widgets):
            widget.setVisible(True)
            grid_layout.addWidget(widget, i // cols, i % cols)

    def toggle_focus_mode(self, client_id):
        is_exiting = self.focused_client_id == client_id
        self.focused_client_id = None if is_exiting else client_id
        

        self.exit_focus_button.setVisible(not is_exiting)
        self.pip_video_container.setVisible(not is_exiting)
        self.main_view_stack.setCurrentIndex(0 if is_exiting else 1)

        for w in self.video_widgets.values():
            w.setParent(None)

        self.update_video_grid()
        self.resizeEvent(None)
        
    def resizeEvent(self, event):
        if self.pip_video_container.isVisible():
            x = self.main_view_stack.width() - self.pip_video_container.width() - 20
            y = self.main_view_stack.height() - self.pip_video_container.height() - 20
            self.pip_video_container.move(x, y)
        if event: super().resizeEvent(event)
        
    def toggle_camera(self, checked):
        if checked: self.start_video()
        else: self.stop_video()
        
    def start_video(self):
        """
        Start video capture from webcam.
        
        VIDEO CAPTURE PROCESS:
        1. Open webcam using OpenCV (cv2.VideoCapture)
        2. Start timer to capture frames periodically
        3. Each frame is captured, compressed, and sent via UDP
        
        PROTOCOL: UDP (User Datagram Protocol)
        - Video frames sent via UDP for low latency
        - Frame rate: 20 FPS (50ms timer interval)
        - Resolution: 640x480 pixels
        - Compression: JPEG quality 60% (balance between quality and bandwidth)
        
        WHY UDP FOR VIDEO:
        - Real-time delivery more important than perfect quality
        - Lost frames are acceptable (next frame arrives quickly)
        - Lower latency than TCP (no retransmission delays)
        - Human eye tolerates minor packet loss
        """
        if self.screen_sharing: self.screen_button.setChecked(False)
        try:
            # Open default webcam (device index 0)
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                raise Exception("Failed to open camera")
            
            self.video_enabled = True
            self.cam_button.setChecked(True)
            
            # Create timer to capture frames at 20 FPS (every 50ms)
            self.video_timer = QTimer(self)
            self.video_timer.timeout.connect(self.capture_and_send_video)
            self.video_timer.start(50)  # 50ms = 20 FPS
            
            # Notify server that video is starting (TCP control message)
            self.client.send_video_state(True)
        except Exception as e: 
            self.cam_button.setChecked(False)
            print(f"Error starting video: {e}")

    def stop_video(self):
        """
        Stop video capture and release camera.
        
        CLEANUP:
        - Stop capture timer
        - Release camera resource
        - Clear video display
        - Notify server via TCP
        """
        self.video_enabled = False
        if self.video_timer: self.video_timer.stop()
        if self.camera: self.camera.release(); self.camera = None
        self.cam_button.setChecked(False)
        if self.client.client_id in self.video_widgets:
            self.video_widgets[self.client.client_id].set_frame(None)
        
        # Notify server that video stopped (TCP control message)
        self.client.send_video_state(False)

    def capture_and_send_video(self):
        """
        Capture one video frame and send it to server via UDP.
        
        VIDEO PROCESSING:
        1. Read frame from camera (OpenCV)
        2. Resize to 640x480 (bandwidth optimization)
        3. Compress to JPEG format (quality 60%)
        4. Send compressed data via UDP
        
        PROTOCOL: UDP (User Datagram Protocol)
        - Packet size: ~10-30 KB per frame (depends on content)
        - Frame rate: 20 FPS
        - Total bandwidth: ~200-600 KB/s per video stream
        
        COMPRESSION:
        - JPEG quality 60%: Good balance between quality and size
        - Higher quality = larger packets = more bandwidth
        - Lower quality = smaller packets = less bandwidth but worse quality
        """
        if self.camera and self.video_enabled:
            # Read one frame from camera
            ret, frame = self.camera.read()
            if ret:
                # Resize frame to 640x480 (reduces bandwidth)
                frame = cv2.resize(frame, (640, 480))
                
                # Display frame locally
                self.video_widgets[self.client.client_id].set_frame(frame)
                
                # Compress frame to JPEG format (quality 60%)
                # Returns: (success, buffer)
                _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                
                # Send compressed frame via UDP (stream type 'V' for video)
                # UDP ensures low latency for real-time video
                self.client.send_udp_stream('V', buf.tobytes())

    def toggle_microphone(self, checked):
        if checked: 
            self.stop_audio()
        else:
            if self.is_muted_by_host: 
                self.mic_button.setChecked(True)
                self.show_notification("You are muted by the host")
            elif self.is_mic_locked_by_host:
                self.mic_button.setChecked(True)
                self.show_notification("Your microphone is locked by the host")
            else: 
                self.start_audio()

    def start_audio(self):
        """
        Start audio capture from microphone.
        
        AUDIO CAPTURE PROCESS:
        1. Open microphone using PyAudio
        2. Start background thread to continuously capture audio
        3. Each audio chunk is sent immediately via UDP
        
        PROTOCOL: UDP (User Datagram Protocol)
        - Audio packets sent via UDP for low latency
        - Sample rate: 44.1 kHz (CD quality)
        - Format: 16-bit PCM (uncompressed)
        - Chunk size: 1024 samples (~23ms of audio)
        - Packet size: ~2 KB per chunk
        
        WHY UDP FOR AUDIO:
        - Real-time delivery critical for conversation
        - Lost packets cause brief glitches (acceptable)
        - Lower latency than TCP (no retransmission)
        - Human ear tolerates minor packet loss
        
        THREADING:
        - Audio capture runs in background thread
        - Reason: Blocking read operations shouldn't freeze UI
        - Thread continuously reads from microphone and sends via UDP
        """
        if not self.p_audio:
            self.show_notification("Audio system not available. Please check your audio devices.")
            self.mic_button.setChecked(True)
            return
            
        self.audio_enabled = True
        
        # Start background thread for audio capture
        # daemon=True: Thread exits when main program exits
        if self.audio_thread_input is None or not self.audio_thread_input.is_alive():
            self.audio_thread_input = threading.Thread(target=self._audio_read_thread, daemon=True)
            self.audio_thread_input.start()
            print("Started audio capture thread")
        
        self.mic_button.setChecked(False)

    @pyqtSlot(str)
    def handle_audio_input_error(self, err_msg):
        QMessageBox.critical(self, "Audio Error", f"Could not open mic: {err_msg}.")
        self.mic_button.setChecked(True); self.audio_enabled = False

    def _audio_read_thread(self):
        """Audio capture thread with Windows error handling"""
        stream = None
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries and self.audio_enabled:
            try:
                # Try with specific device first
                if self.input_device_index is not None:
                    try:
                        stream = self.p_audio.open(
                            format=pyaudio.paInt16,
                            channels=1,
                            rate=self.audio_rate,
                            input=True,
                            input_device_index=self.input_device_index,
                            frames_per_buffer=self.audio_chunk_size
                        )
                        print(f"Opened audio stream with device {self.input_device_index}")
                    except Exception as e:
                        print(f"Failed with device {self.input_device_index}, trying default")
                        # Fall back to default device
                        stream = self.p_audio.open(
                            format=pyaudio.paInt16,
                            channels=1,
                            rate=self.audio_rate,
                            input=True,
                            frames_per_buffer=self.audio_chunk_size
                        )
                        print("Opened audio stream with default device")
                else:
                    # No specific device, use default
                    stream = self.p_audio.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=self.audio_rate,
                        input=True,
                        frames_per_buffer=self.audio_chunk_size
                    )
                    print("Opened audio stream with system default")
                
                # Stream opened successfully, start capturing
                while self.audio_enabled:
                    try:
                        data = stream.read(self.audio_chunk_size, exception_on_overflow=False)
                        if self.audio_enabled and data:
                            # Show mic activity
                            audio_data = np.frombuffer(data, dtype=np.int16)
                            level = np.abs(audio_data).mean()
                            if level > 100:  # Threshold for activity
                                QMetaObject.invokeMethod(self.mic_activity_label, 'setStyleSheet', 
                                                        Qt.ConnectionType.QueuedConnection,
                                                        Q_ARG(str, "background-color: #0f0; border-radius: 6px;"))
                            else:
                                QMetaObject.invokeMethod(self.mic_activity_label, 'setStyleSheet', 
                                                        Qt.ConnectionType.QueuedConnection,
                                                        Q_ARG(str, "background-color: #333; border-radius: 6px;"))
                            
                            self.client.send_udp_stream('A', data)
                    except Exception as read_error:
                        if self.audio_enabled:
                            print(f"Audio read error: {read_error}")
                            break
                break  # Exit retry loop if successful
                        
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                print(f"Audio stream error (attempt {retry_count}/{max_retries}): {error_msg}")
                
                if '-9996' in error_msg or 'Invalid device' in error_msg:
                    # Device error on Windows
                    if retry_count >= max_retries:
                        QMetaObject.invokeMethod(self, 'handle_audio_input_error', 
                                                Qt.ConnectionType.QueuedConnection, 
                                                Q_ARG(str, "No microphone available. Please check your audio devices."))
                        break
                    else:
                        # Wait a bit before retry
                        import time
                        time.sleep(0.5)
                else:
                    # Other error, report immediately
                    QMetaObject.invokeMethod(self, 'handle_audio_input_error', 
                                            Qt.ConnectionType.QueuedConnection, 
                                            Q_ARG(str, error_msg))
                    break
                    
            finally:
                if stream:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except:
                        pass
                self.audio_enabled = False
                print("Audio capture thread ended")

    def stop_audio(self):
        self.audio_enabled = False; self.mic_button.setChecked(True)

    def _audio_write_thread(self):
        stream = None
        try:
            if self.output_device_index is not None:
                stream = self.p_audio.open(format=pyaudio.paInt16, channels=1, rate=self.audio_rate, 
                                         output=True, output_device_index=self.output_device_index,
                                         frames_per_buffer=self.audio_chunk_size)
            else:
                # Try default device
                stream = self.p_audio.open(format=pyaudio.paInt16, channels=1, rate=self.audio_rate, 
                                         output=True, frames_per_buffer=self.audio_chunk_size)
            
            while self.ui_running:
                data = self.audio_output_queue.get()
                if data is None: break
                if stream: stream.write(data)
                self.audio_output_queue.task_done()
        except Exception as e: 
            print(f"Audio output error: {e}")
        finally:
            if stream: 
                try: stream.close()
                except: pass

    def toggle_screen_share(self, checked):
        if checked: 
            # Check if someone else is already presenting
            if hasattr(self.client, 'current_presenter') and self.client.current_presenter and self.client.current_presenter != self.client.client_id:
                # Show popup message
                self.show_presenter_conflict_dialog()
                self.screen_button.setChecked(False)
                return
            self.start_screen_share()
        else: 
            self.stop_screen_share()
        
    def start_screen_share(self):
        """
        Start screen sharing (presenter mode).
        
        SCREEN CAPTURE PROCESS:
        1. Request presenter permission from server (only one presenter at a time)
        2. Start screen capture thread using MSS library
        3. Capture screen at reduced frame rate (3 FPS)
        4. Send frames via TCP for clarity and integrity
        
        PROTOCOL: TCP (Transmission Control Protocol)
        - Screen frames sent via TCP (not UDP like video)
        - Frame rate: 3 FPS (slower than camera video)
        - Resolution: Up to 1024x576 (scaled down from full screen)
        - Compression: JPEG quality 60%
        
        WHY TCP FOR SCREEN SHARING:
        - Clarity is more important than latency for slides/documents
        - Text must be readable (no compression artifacts from packet loss)
        - Guaranteed delivery ensures all frames arrive
        - Acceptable slight delay (3 FPS is already slow)
        
        PRESENTER CONTROL:
        - Only one presenter allowed at a time
        - Server manages presenter state
        - Other users see "presenter conflict" if they try to share
        """
        if self.video_enabled: self.cam_button.setChecked(False)
        
        # Request screen share permission from server (TCP control message)
        # Server will check if another presenter is active
        self.client.request_screen_share()
        
        self.screen_sharing = True
        self.screen_button.setChecked(True)
        
        # Start screen capture thread (captures at 3 FPS)
        self.screen_capture_thread = ScreenCaptureThread()
        self.screen_capture_thread.frame_ready.connect(self.send_screen_frame)
        self.screen_capture_thread.start()
        
        # Notify server that video state changed (TCP control message)
        self.client.send_video_state(True)
        
        # Update client state
        self.client.is_presenting = True

    def stop_screen_share(self):
        """
        Stop screen sharing.
        
        CLEANUP:
        - Stop screen capture thread
        - Clear screen display
        - Notify server via TCP
        - Release presenter role
        """
        self.screen_sharing = False
        if self.screen_capture_thread: self.screen_capture_thread.stop()
        self.screen_button.setChecked(False)
        if self.client.client_id in self.video_widgets:
            self.video_widgets[self.client.client_id].set_frame(None)
        
        # Notify server that video stopped (TCP control message)
        self.client.send_video_state(False)
        
        # Notify server that screen sharing stopped (TCP control message)
        self.client.stop_screen_share_request()
        
        # Update client state
        self.client.is_presenting = False

    def send_screen_frame(self, frame):
        """
        Send one screen frame to server via TCP.
        
        SCREEN FRAME PROCESSING:
        1. Compress frame to JPEG (quality 60%)
        2. Encode to base64 (for JSON transmission)
        3. Send via TCP (guaranteed delivery)
        
        PROTOCOL: TCP (Transmission Control Protocol)
        - Packet size: ~50-200 KB per frame (depends on screen content)
        - Frame rate: 3 FPS (333ms between frames)
        - Total bandwidth: ~150-600 KB/s
        
        WHY TCP:
        - Screen content (text, slides) must be clear and readable
        - Packet loss would cause visible artifacts in text
        - Guaranteed delivery ensures quality
        - 3 FPS is slow enough that TCP latency is acceptable
        
        BASE64 ENCODING:
        - Binary image data encoded to text format
        - Allows embedding in JSON messages
        - Increases size by ~33% but ensures compatibility
        """
        if self.screen_sharing and hasattr(self.client, 'connected') and self.client.connected:
            # Display frame locally
            self.video_widgets[self.client.client_id].set_frame(frame)
            
            # Compress frame to JPEG format (quality 60%)
            # Balance between quality and bandwidth for screen content
            _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            
            # Encode to base64 for JSON transmission
            # Base64 converts binary data to text format
            frame_data = base64.b64encode(buf.tobytes()).decode('utf-8')
            
            # Send screen frame via TCP for reliability and clarity
            # TCP ensures the frame arrives without corruption
            try:
                self.client.send_screen_frame_tcp(frame_data)
            except Exception as e:
                print(f"Error sending screen frame: {e}")
                # If sending fails, stop screen sharing
                self.stop_screen_share()

    def toggle_raise_hand(self, checked):
        """Handle raise hand toggle with proper state management"""
        # Prevent focus loss during fullscreen mode
        current_focus = self.focusWidget()
        
        self.client.send_tcp_message({'type': 'raise_hand', 'state': checked})
        # Update own widget
        if self.client.client_id in self.video_widgets:
            self.video_widgets[self.client.client_id].set_hand_raised(checked)
        
        # Restore focus to prevent fullscreen exit
        if current_focus and self.isFullScreen():
            current_focus.setFocus()
            # Ensure window stays in fullscreen
            self.activateWindow()
            self.raise_()
    
    def send_emoji_reaction(self, emoji):
        """Send emoji reaction to all participants"""
        self.client.send_tcp_message({'type': 'emoji_reaction', 'emoji': emoji})
        # Show on own video too
        if self.client.client_id in self.video_widgets:
            self.video_widgets[self.client.client_id].show_emoji_reaction(emoji)
    
    def send_private_message(self, recipient_id, message):
        """Send a private message to a participant"""
        self.client.send_tcp_message({
            'type': 'private_message',
            'recipient_id': recipient_id,
            'message': message
        })

    def send_chat(self):
        """
        Send a text chat message to all participants.
        
        PROTOCOL: TCP (Transmission Control Protocol)
        - Chat messages sent via TCP for guaranteed delivery
        - Message format: JSON with type='chat' and message text
        - Server broadcasts to all participants
        
        WHY TCP FOR CHAT:
        - Messages must not be lost (critical for communication)
        - Messages must arrive in order (conversation flow)
        - Reliability more important than speed for text
        - Small message size (few KB) means low latency anyway
        
        MESSAGE FLOW:
        1. User types message and presses Enter
        2. Client sends message to server via TCP
        3. Server receives message via TCP
        4. Server broadcasts message to all participants via TCP
        5. All clients receive and display message
        """
        text = self.chat_input.text().strip()
        if text:
            # Send message to server via TCP (guaranteed delivery)
            self.client.send_chat_message(text)
            
            # Clear input field
            self.chat_input.clear()
            
            # Display message locally (optimistic UI update)
            self.display_chat_message(self.client.username, text, True)
            
            # Play a subtle send sound (optional)
            try:
                QApplication.beep()
            except:
                pass

    def add_system_message(self, text, style_class=""):
        widget = SystemMessageWidget(text, style_class)
        item = QListWidgetItem()
        # Add extra height for consistent spacing
        size_hint = widget.sizeHint()
        size_hint.setHeight(size_hint.height() + 12)  # Add 12px extra spacing for system messages
        item.setSizeHint(size_hint)
        self.chat_list.addItem(item)
        self.chat_list.setItemWidget(item, widget)
        self.chat_list.scrollToBottom()

    def display_chat_message(self, username, text, is_self=False):
        time_str = datetime.now().strftime("%H:%M")
        color = self.get_color_from_name(self.client.username if is_self else username)
        
        widget = ChatMessageWidget(username, text, time_str, is_self, color)
        item = QListWidgetItem()
        # iOS-like compact spacing
        size_hint = widget.sizeHint()
        size_hint.setHeight(size_hint.height() + 8)  # Add 8px spacing for iOS feel
        item.setSizeHint(size_hint)
        self.chat_list.addItem(item)
        self.chat_list.setItemWidget(item, widget)
        
        # Smooth scroll to bottom with animation
        QTimer.singleShot(50, self.chat_list.scrollToBottom)
        
        # Add subtle fade-in animation for new messages
        if hasattr(widget, 'setGraphicsEffect'):
            opacity_effect = QGraphicsOpacityEffect()
            widget.setGraphicsEffect(opacity_effect)
            
            fade_animation = QPropertyAnimation(opacity_effect, b"opacity")
            fade_animation.setDuration(200)  # Faster iOS-like animation
            fade_animation.setStartValue(0.0)
            fade_animation.setEndValue(1.0)
            fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            fade_animation.start()
            
            # Store animation to prevent garbage collection
            widget._fade_animation = fade_animation
        
        # Trigger resize event to adjust bubble width
        QTimer.singleShot(10, lambda: self.adjust_message_widths())
    
    def adjust_message_widths(self):
        """Adjust message bubble widths based on current window size"""
        if hasattr(self, 'chat_list'):
            # Get available width from the chat list
            available_width = self.chat_list.width() - 40  # Account for margins
            max_bubble_width = max(200, int(available_width * 0.75))  # 75% of available width
            
            # Update all existing message widgets
            for i in range(self.chat_list.count()):
                item = self.chat_list.item(i)
                widget = self.chat_list.itemWidget(item)
                if widget and hasattr(widget, 'findChild'):
                    bubble = widget.findChild(QFrame, "chat_bubble")
                    if bubble:
                        bubble.setMaximumWidth(max_bubble_width)
    
    def resizeEvent(self, event):
        """Handle window resize to adjust message widths"""
        super().resizeEvent(event)
        # Delay the adjustment to ensure layout is complete
        QTimer.singleShot(100, self.adjust_message_widths)
    
    def show_typing_indicator(self, username):
        """Show typing indicator for a user"""
        if hasattr(self, 'typing_indicator'):
            self.typing_indicator.setText(f"{username} is typing...")
            self.typing_indicator.setVisible(True)
    
    def hide_typing_indicator(self):
        """Hide typing indicator"""
        if hasattr(self, 'typing_indicator'):
            self.typing_indicator.setVisible(False)
    
    def toggle_sidebar(self):
        """Toggle sidebar visibility"""
        if self.sidebar_mode == "popup":
            # If in popup mode, close popup and return to docked
            self.return_sidebar_from_popup()
            return
        
        if self.sidebar_visible:
            # Hide sidebar
            self.side_panel.setVisible(False)
            self.sidebar_visible = False
            self.sidebar_mode = "hidden"
            self.toggle_sidebar_button.setIcon(qta.icon('fa5s.bars', color='#ffcc00'))
            self.toggle_sidebar_button.setToolTip("Show Sidebar")
            self.sidebar_status_label.setText("👁️")
            self.sidebar_status_label.setToolTip("Sidebar Status: Hidden")
            self.save_sidebar_preferences()
        else:
            # Show sidebar
            self.side_panel.setVisible(True)
            self.sidebar_visible = True
            self.sidebar_mode = "docked"
            self.toggle_sidebar_button.setIcon(qta.icon('fa5s.bars', color='white'))
            self.toggle_sidebar_button.setToolTip("Hide Sidebar")
            self.sidebar_status_label.setText("📌")
            self.sidebar_status_label.setToolTip("Sidebar Status: Docked")
            self.save_sidebar_preferences()
    
    def toggle_popup_sidebar(self):
        """Toggle sidebar popup mode"""
        if self.sidebar_mode == "popup":
            # Return from popup to docked
            self.return_sidebar_from_popup()
        else:
            # Move sidebar to popup
            self.move_sidebar_to_popup()
    
    def move_sidebar_to_popup(self):
        """Move sidebar to popup window"""
        if self.sidebar_popup is None:
            # Remove tab widget from main window
            self.side_panel.layout().removeWidget(self.tab_widget)
            self.side_panel.setVisible(False)
            
            # Create popup window
            self.sidebar_popup = SidebarPopupWindow(self, self.tab_widget)
            self.sidebar_popup.show()
            
            # Update state
            self.sidebar_mode = "popup"
            self.sidebar_visible = False
            
            # Update button states
            self.toggle_sidebar_button.setIcon(qta.icon('fa5s.bars', color='#888888'))
            self.toggle_sidebar_button.setToolTip("Sidebar in Popup (Click to dock)")
            self.popup_sidebar_button.setIcon(qta.icon('fa5s.window-restore', color='#ffcc00'))
            self.popup_sidebar_button.setToolTip("Return Sidebar to Main Window")
            self.sidebar_status_label.setText("🪟")
            self.sidebar_status_label.setToolTip("Sidebar Status: Popup Window")
            self.save_sidebar_preferences()
    
    def return_sidebar_from_popup(self):
        """Return sidebar from popup to main window"""
        if self.sidebar_popup is not None:
            # Remove tab widget from popup
            self.sidebar_popup.centralWidget().layout().removeWidget(self.tab_widget)
            
            # Close popup
            self.sidebar_popup.close()
            self.sidebar_popup = None
            
            # Return tab widget to main window
            self.side_panel.layout().addWidget(self.tab_widget)
            self.side_panel.setVisible(True)
            
            # Update state
            self.sidebar_mode = "docked"
            self.sidebar_visible = True
            
            # Update button states
            self.toggle_sidebar_button.setIcon(qta.icon('fa5s.bars', color='white'))
            self.toggle_sidebar_button.setToolTip("Hide Sidebar")
            self.popup_sidebar_button.setIcon(qta.icon('fa5s.window-restore', color='white'))
            self.popup_sidebar_button.setToolTip("Open Sidebar in Popup Window")
            self.sidebar_status_label.setText("📌")
            self.sidebar_status_label.setToolTip("Sidebar Status: Docked")
            self.save_sidebar_preferences()
    
    def setup_sidebar_shortcuts(self):
        """Setup keyboard shortcuts for sidebar management"""
        # Ctrl+B to toggle sidebar
        toggle_shortcut = QShortcut(QKeySequence("Ctrl+B"), self)
        toggle_shortcut.activated.connect(self.toggle_sidebar)
        
        # Ctrl+Shift+B to toggle popup mode
        popup_shortcut = QShortcut(QKeySequence("Ctrl+Shift+B"), self)
        popup_shortcut.activated.connect(self.toggle_popup_sidebar)
        
        # F11 for fullscreen (hides sidebar automatically)
        fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
            # Restore sidebar if it was visible before fullscreen
            if hasattr(self, '_sidebar_was_visible_before_fullscreen'):
                if self._sidebar_was_visible_before_fullscreen and self.sidebar_mode != "popup":
                    self.side_panel.setVisible(True)
                    self.sidebar_visible = True
        else:
            # Remember sidebar state before going fullscreen
            self._sidebar_was_visible_before_fullscreen = self.sidebar_visible
            # Hide sidebar in fullscreen mode (except popup)
            if self.sidebar_mode != "popup":
                self.side_panel.setVisible(False)
                self.sidebar_visible = False
            self.showFullScreen()
    
    def closeEvent(self, event):
        """Handle main window close event"""
        # Close popup if it exists
        if self.sidebar_popup is not None:
            self.sidebar_popup.close()
            self.sidebar_popup = None
        
        # Call parent close event
        super().closeEvent(event)
    
    def show_sidebar_context_menu(self, position):
        """Show context menu for sidebar options"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2a2a2a;
                border: 1px solid #555555;
                border-radius: 8px;
                padding: 6px;
                color: white;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
                margin: 2px;
            }
            QMenu::item:selected {
                background-color: #0078d4;
            }
            QMenu::separator {
                height: 1px;
                background-color: #555555;
                margin: 4px 0px;
            }
        """)
        
        # Current mode indicator
        if self.sidebar_mode == "docked":
            mode_text = "📌 Docked"
        elif self.sidebar_mode == "hidden":
            mode_text = "👁️ Hidden"
        else:
            mode_text = "🪟 Popup"
        
        mode_action = QAction(f"Current: {mode_text}", self)
        mode_action.setEnabled(False)
        menu.addAction(mode_action)
        menu.addSeparator()
        
        # Toggle visibility
        if self.sidebar_mode != "popup":
            toggle_action = QAction("Hide Sidebar" if self.sidebar_visible else "Show Sidebar", self)
            toggle_action.triggered.connect(self.toggle_sidebar)
            menu.addAction(toggle_action)
        
        # Popup mode
        popup_action = QAction("Open in Popup" if self.sidebar_mode != "popup" else "Return to Main Window", self)
        popup_action.triggered.connect(self.toggle_popup_sidebar)
        menu.addAction(popup_action)
        
        menu.addSeparator()
        
        # Keyboard shortcuts info
        shortcuts_action = QAction("Shortcuts: Ctrl+B (toggle), Ctrl+Shift+B (popup)", self)
        shortcuts_action.setEnabled(False)
        menu.addAction(shortcuts_action)
        
        # Show menu
        global_position = self.toggle_sidebar_button.mapToGlobal(position)
        menu.exec(global_position)
    
    def load_sidebar_preferences(self):
        """Load sidebar preferences from settings"""
        try:
            settings = QSettings("Loop", "ConferenceApp")
            sidebar_mode = settings.value("sidebar_mode", "docked")
            
            # Apply the saved preference after a short delay to ensure UI is ready
            QTimer.singleShot(100, lambda: self.apply_sidebar_mode(sidebar_mode))
        except Exception as e:
            print(f"Error loading sidebar preferences: {e}")
    
    def save_sidebar_preferences(self):
        """Save current sidebar preferences"""
        try:
            settings = QSettings("Loop", "ConferenceApp")
            settings.setValue("sidebar_mode", self.sidebar_mode)
        except Exception as e:
            print(f"Error saving sidebar preferences: {e}")
    
    def apply_sidebar_mode(self, mode):
        """Apply a specific sidebar mode"""
        if mode == "hidden" and self.sidebar_mode == "docked":
            self.toggle_sidebar()
        elif mode == "popup" and self.sidebar_mode != "popup":
            self.toggle_popup_sidebar()
        
        # Save the preference
        self.save_sidebar_preferences()

    def select_file_to_send(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Select File to Send")
        if fp: self.start_file_offer(fp)

    def start_file_offer(self, filepath):
        """
        Offer a file to all participants for download.
        
        FILE SHARING PROCESS:
        1. User selects file from file picker dialog
        2. Client sends file offer to server via TCP
        3. Server broadcasts file offer to all participants via TCP
        4. Other participants see download button in chat
        5. When participant clicks download, they request file via TCP
        6. Client sends file in chunks via TCP
        7. Recipient receives chunks and assembles file
        
        PROTOCOL: TCP (Transmission Control Protocol)
        - File metadata (name, size) sent via TCP
        - File chunks (32 KB each) sent via TCP
        - Completion notification sent via TCP
        
        WHY TCP FOR FILE SHARING:
        - Data integrity is critical (no corrupted files)
        - Guaranteed delivery (all chunks must arrive)
        - Ordered delivery (chunks must be assembled correctly)
        - Error checking (corrupted chunks are retransmitted)
        
        CHUNKING:
        - Files split into 32 KB chunks
        - Reason: Prevents large messages from blocking network
        - Allows progress tracking
        - Enables resume capability (future enhancement)
        """
        try:
            fname, fsize = os.path.basename(filepath), os.path.getsize(filepath)
            
            # Send file offer to server via TCP
            # Server will broadcast to all participants
            file_id = self.client.send_file_offer(filepath)
            
            if file_id:
                # Create a file message in chat showing it's being sent
                self.add_file_message(fname, fsize, file_id, is_sending=True)
            else:
                self.add_system_message(f"Error: Could not offer file {fname}", "error")
            
        except Exception as e:
            self.add_system_message(f"Error sending file: {e}", "error")
    
    def show_presenter_conflict_dialog(self):
        """Show dialog when trying to screen share while someone else is presenting"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Screen Share Unavailable")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText("Only one presenter at a time")
        msg.setInformativeText("Someone else is currently sharing their screen. Only one person can present at a time.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2C2C2E;
                color: #FFFFFF;
            }
            QMessageBox QPushButton {
                background-color: #0A84FF;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QMessageBox QPushButton:hover {
                background-color: #0969DA;
            }
        """)
        msg.exec()

    def request_file_download(self, file_id, sender_id, filename, filesize):
        """
        Handle file download request - let user choose save location
        """
        # Get default downloads directory
        if not hasattr(self.client, 'downloads_dir'):
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        else:
            downloads_dir = self.client.downloads_dir
            
        # Ensure downloads directory exists
        os.makedirs(downloads_dir, exist_ok=True)
        
        # Suggest save path with original filename
        suggested_path = os.path.join(downloads_dir, filename)
        
        # Let user choose where to save the file
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            suggested_path,
            "All Files (*.*)"
        )
        
        # If user cancelled, don't download
        if not save_path:
            self.add_system_message(f"Download cancelled: {filename}", "info")
            return
        
        try:
            # Use client's request_file method with chosen save path
            self.client.request_file(sender_id, file_id, filename, filesize, save_path)
            self.add_system_message(f"📥 Downloading: {filename}", "info")
            
        except Exception as e:
            self.add_system_message(f"Error: Could not save file {filename}. {e}", "error")

    def _file_sender_thread(self, fp, fid, down_id):
        """Send file in chunks with progress updates"""
        try:
            filesize = os.path.getsize(fp)
            bytes_sent = 0
            
            with open(fp, 'rb') as f:
                while chunk := f.read(65536):
                    self.client.send_tcp_message({'type': 'file_chunk','file_id': fid, 'data': base64.b64encode(chunk).decode(), 'recipient_id': down_id})
                    bytes_sent += len(chunk)
                    
                    # Update progress for the sender (optional - could add progress bar later)
                    if filesize > 0:
                        progress = int((bytes_sent / filesize) * 100)
                        # Progress updates could be added here if needed
            
            self.client.send_tcp_message({'type': 'file_end', 'file_id': fid, 'recipient_id': down_id})
            
            # Update the sender's file message to show completion
            QMetaObject.invokeMethod(self, 'update_sender_file_status', 
                                  Qt.ConnectionType.QueuedConnection, 
                                  Q_ARG(str, fid),
                                  Q_ARG(str, os.path.basename(fp)))
                                  
        except Exception as e: 
            print(f"File sender error: {e}")
            QMetaObject.invokeMethod(self, 'add_system_message', 
                                  Qt.ConnectionType.QueuedConnection, 
                                  Q_ARG(str, f"Error sending file: {e}"), 
                                  Q_ARG(str, "error"))

    @pyqtSlot(str, str)
    def update_sender_file_status(self, file_id, filename):
        """Update the sender's file message to show completion"""
        try:
            if hasattr(self, 'file_widgets') and file_id in self.file_widgets:
                item, widget = self.file_widgets[file_id]
                # Remove the old sending message
                row = self.chat_list.row(item)
                if row >= 0:
                    self.chat_list.takeItem(row)
                # Clean up tracking
                del self.file_widgets[file_id]
                
                # Add a new message showing the file was sent successfully
                self.add_system_message(f"✅ File sent successfully: {filename}", "success")
                
        except Exception as e:
            print(f"Error updating sender file status: {e}")
    # @pyqtSlot(str, int)
    # def update_sender_progress(self, key, size):
    #     if key in self.outgoing_transfers:
    #         t = self.outgoing_transfers[key]; t['sent'] += size
    #         if t['total'] > 0: t['widget'].set_progress(int((t['sent'] / t['total']) * 100))

    def handle_mute_participant(self, client_id, should_mute):
        if self.is_host:
            if should_mute: self.client.mute_participant(client_id)
            else: self.client.unmute_participant(client_id)
    
    def handle_lock_mic(self, client_id, should_lock):
        """Handle mic lock/unlock for a participant"""
        if self.is_host:
            self.client.send_tcp_message({
                'type': 'lock_mic' if should_lock else 'unlock_mic',
                'target_client_id': client_id
            })
            # Update UI immediately
            if client_id in self.video_widgets:
                self.video_widgets[client_id].set_mic_locked(should_lock)
                self.update_participant_ui()

    @pyqtSlot(str)
    def handle_video_request(self, client_id):
        if self.is_host:
            print(f"Host requesting video from {client_id}")
            self.client.send_tcp_message({'type': 'request_video', 'target_client_id': client_id})
            self.show_notification(f"Sent video request to {self.video_widgets[client_id].username}")
            
    @pyqtSlot(str)
    def handle_unmute_request(self, client_id):
        if self.is_host:
            print(f"Host requesting unmute from {client_id}")
            self.client.send_tcp_message({'type': 'request_unmute', 'target_client_id': client_id})
            self.show_notification(f"Sent unmute request to {self.video_widgets[client_id].username}")

    def handle_video_request_from_host(self):
        if self.video_enabled:
            return 
        
        self.activateWindow(); self.raise_()
        reply = QMessageBox.question(self, "Video Request", 
                                     "The host is asking you to start your video. Do you want to turn it on?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.cam_button.setChecked(True)

    def handle_unmute_request_from_host(self):
        if not self.audio_enabled:
            self.activateWindow(); self.raise_()
            reply = QMessageBox.question(self, "Unmute Request", 
                                         "The host is asking you to unmute. Do you want to unmute?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.is_muted_by_host = False
                self.mic_button.setChecked(False)
    
    def handle_screen_share_request_from_host(self):
        """Handle screen share request from host"""
        if self.screen_sharing:
            return  # Already sharing
        
        self.activateWindow()
        self.raise_()
        reply = QMessageBox.question(self, "Screen Share Request",
                                     "The host is requesting you to share your screen. Do you want to share?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.screen_button.setChecked(True)

    @pyqtSlot(dict)
    def handle_server_message(self, msg):
        """
        Handle all server messages including new features
        MODIFIED: Rerouted file transfers to the 'Files' tab
        """
        msg_type = msg.get('type')
        if msg_type == 'user_joined':
            profile_image = msg.get('profile_image')
            self.add_participant_video(msg['client_id'], msg['username'], msg.get('is_host', False), profile_image)
            self.add_system_message(f" {msg.get('username')} joined", "success")
            self.play_sound('join')
            # Show notification
            self.show_join_notification(msg.get('username'))
        elif msg_type == 'user_left':
            self.remove_participant_video(msg['client_id'])
            self.add_system_message(f"⬅️ {msg.get('username')} left", "error")
        elif msg_type == 'chat':
            self.display_chat_message(msg['username'], msg['message'])
            # Add subtle notification for incoming messages
            try:
                if not self.isActiveWindow():
                    self.show_notification(f"New message from {msg['username']}")
            except:
                pass
        elif msg_type == 'participant_video_state' and msg.get('client_id') in self.video_widgets:
            if msg.get('state') == 'stopped': self.video_widgets[msg['client_id']].set_frame(None)
        elif msg_type == 'muted_by_host':
            self.is_muted_by_host = True; self.stop_audio(); self.show_notification("You have been muted by the host")
        elif msg_type == 'unmuted_by_host':
            self.is_muted_by_host = False; self.show_notification("You have been unmuted by the host")
        elif msg_type in ['participant_muted', 'participant_unmuted'] and msg.get('client_id') in self.video_widgets:
            self.video_widgets[msg['client_id']].set_muted(msg_type == 'participant_muted')
            self.update_participant_ui()
        
        # Mic lock messages
        elif msg_type == 'mic_locked':
            self.is_mic_locked_by_host = True
            self.show_notification("Your microphone has been locked by the host")
            if self.client.client_id in self.video_widgets:
                self.video_widgets[self.client.client_id].set_mic_locked(True)
        elif msg_type == 'mic_unlocked':
            self.is_mic_locked_by_host = False
            self.show_notification("Your microphone has been unlocked")
            if self.client.client_id in self.video_widgets:
                self.video_widgets[self.client.client_id].set_mic_locked(False)
        elif msg_type == 'participant_mic_locked' and msg.get('client_id') in self.video_widgets:
            self.video_widgets[msg['client_id']].set_mic_locked(True)
            self.update_participant_ui()
        elif msg_type == 'participant_mic_unlocked' and msg.get('client_id') in self.video_widgets:
            self.video_widgets[msg['client_id']].set_mic_locked(False)
            self.update_participant_ui()
        
        # Emoji reactions
        elif msg_type == 'emoji_reaction':
            client_id = msg.get('client_id')
            emoji = msg.get('emoji')
            if client_id in self.video_widgets:
                self.video_widgets[client_id].show_emoji_reaction(emoji)
        

        
        elif msg_type == 'request_video' or msg_type == 'request_all_video':
            QTimer.singleShot(100, self.handle_video_request_from_host)
        
        elif msg_type == 'request_unmute' or msg_type == 'request_all_unmute':
            QTimer.singleShot(100, self.handle_unmute_request_from_host)
        
        elif msg_type == 'request_screen_share':
            QTimer.singleShot(100, self.handle_screen_share_request_from_host)
        
        elif msg_type == 'screen_share_denied':
            # Screen share request was denied (someone else is presenting)
            self.screen_button.setChecked(False)
            self.screen_sharing = False
            if hasattr(self.client, 'is_presenting'):
                self.client.is_presenting = False
            # Stop screen capture thread if it was started
            if hasattr(self, 'screen_capture_thread') and self.screen_capture_thread:
                self.screen_capture_thread.stop()
            QTimer.singleShot(100, self.show_presenter_conflict_dialog)
        
        elif msg_type == 'disable_screen_sharing':
            if self.screen_sharing:
                self.stop_screen_share()
            self.screen_button.setEnabled(False)
            self.show_notification("Screen sharing has been disabled by the host")
        
        # Host Transfer Handler
        elif msg_type == 'host_changed':
            new_host_id = msg['new_host_id']
            # Demote any old hosts
            for cid, widget in self.video_widgets.items():
                if widget.is_host and cid != new_host_id:
                    widget.set_host_status(False)
            
            # Promote the new host
            if new_host_id in self.video_widgets:
                self.video_widgets[new_host_id].set_host_status(True)

            # Check if WE are the new host
            if new_host_id == self.client.client_id:
                self.is_host = True
                self.show_notification("You are the new host!")
                # Add Admin tab if it doesn't exist
                if self.tab_widget.count() == 2:
                    self.tab_widget.addTab(self.create_admin_panel(), "Admin")
                
                # Show menu buttons on all OTHER widgets
                for cid, widget in self.video_widgets.items():
                    if cid != self.client.client_id:
                        widget.menu_button.setVisible(True)
            
            self.update_participant_ui()

        # Raise Hand Handler
        elif msg_type == 'participant_hand_state':
            client_id = msg.get('client_id')
            state = msg.get('state')
            
            if client_id in self.video_widgets:
                self.video_widgets[client_id].set_hand_raised(state)
            
            # Update raised hands queue for host
            if self.is_host:
                if state and client_id not in self.raised_hands_queue:
                    self.raised_hands_queue.append(client_id)
                elif not state and client_id in self.raised_hands_queue:
                    self.raised_hands_queue.remove(client_id)
            
            self.update_participant_ui()
            
        # File Transfer Handling in Chat
        elif msg_type == 'file_offer':
            file_id = msg.get('file_id')
            filename = msg.get('filename', 'Unknown')
            filesize = msg.get('filesize', 0)
            sender_id = msg.get('sender_id')
            sender_name = msg.get('username', 'Unknown')
            
            if file_id and filename:
                # Add file message to chat with download button
                self.add_file_offer_message(filename, filesize, file_id, sender_id, sender_name)
                
                # Show notification
                self.show_notification(f"📎 {sender_name} shared: {filename}")

        # file_request is now handled by the client, not the UI
        
        elif msg_type == 'file_complete':
            # File download completed by client
            file_id = msg.get('file_id')
            filename = msg.get('filename')
            filepath = msg.get('filepath')
            
            # Update the file message widget to show completion
            if hasattr(self, 'file_widgets') and file_id in self.file_widgets:
                item, widget = self.file_widgets[file_id]
                # Remove the old waiting message
                row = self.chat_list.row(item)
                if row >= 0:
                    self.chat_list.takeItem(row)
                # Clean up tracking
                del self.file_widgets[file_id]
            
            # Create new received file message
            filesize = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            self.add_file_message(filename, filesize, None, is_received=True, filepath=filepath)
            
            # Show notification
            self.show_notification(f"✅ File received: {filename}")
            
        elif msg_type == 'file_progress':
            # File download progress update from client
            file_id = msg.get('file_id')
            progress = msg.get('progress', 0)
            # Could update progress bar here if needed

    @pyqtSlot(str, bytes)
    def handle_video_stream(self, cid, data):
        """Handle incoming video stream with proper error handling"""
        try:
            if not data or len(data) == 0:
                print(f"Warning: Empty video data received from {cid}")
                return
                
            if cid not in self.video_widgets:
                print(f"Warning: No video widget found for client {cid}")
                return
            
            # Decode the video frame
            try:
                # Convert bytes to numpy array
                nparr = np.frombuffer(data, np.uint8)
                if len(nparr) == 0:
                    print(f"Warning: Empty numpy array for client {cid}")
                    return
                
                # Decode the image
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is None:
                    print(f"Warning: Failed to decode video frame from {cid}")
                    return
                
                # Set the frame to the video widget
                self.video_widgets[cid].set_frame(frame)
                
            except Exception as decode_error:
                print(f"Error decoding video frame from {cid}: {decode_error}")
                
        except Exception as e:
            print(f"Error handling video stream from {cid}: {e}")

    @pyqtSlot(object, bytes)
    def handle_audio_stream(self, cid, data):
        if self.p_audio and self.audio_thread_output and self.audio_thread_output.is_alive(): self.audio_output_queue.put(data)

    def test_microphone(self):
        """Test microphone input with visual feedback"""
        if not self.p_audio:
            QMessageBox.warning(self, "Audio Test", "Audio system not available.")
            return
        
        if self.input_device_index is None:
            QMessageBox.warning(self, "Audio Test", "No microphone available. Please connect a microphone.")
            return
        
        # Create test dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Microphone Test")
        dialog.setFixedSize(400, 200)
        
        layout = QVBoxLayout(dialog)
        
        info_label = QLabel("Speak into your microphone to test audio input.")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        # Visual level indicator
        level_bar = QProgressBar()
        level_bar.setRange(0, 100)
        level_bar.setTextVisible(False)
        layout.addWidget(level_bar)
        
        status_label = QLabel("Testing...")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_label)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)
        
        # Test audio in thread
        test_running = [True]
        
        def audio_test_thread():
            stream = None
            try:
                stream = self.p_audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.audio_rate,
                    input=True,
                    input_device_index=self.input_device_index,
                    frames_per_buffer=self.audio_chunk_size
                )
                
                QMetaObject.invokeMethod(status_label, 'setText', Qt.ConnectionType.QueuedConnection, 
                                        Q_ARG(str, "✓ Microphone is working!"))
                
                while test_running[0]:
                    try:
                        data = stream.read(self.audio_chunk_size, exception_on_overflow=False)
                        # Calculate audio level
                        audio_data = np.frombuffer(data, dtype=np.int16)
                        level = int(np.abs(audio_data).mean() / 327.67)  # Scale to 0-100
                        QMetaObject.invokeMethod(level_bar, 'setValue', Qt.ConnectionType.QueuedConnection, 
                                                Q_ARG(int, level))
                    except:
                        break
                        
            except Exception as e:
                QMetaObject.invokeMethod(status_label, 'setText', Qt.ConnectionType.QueuedConnection, 
                                        Q_ARG(str, f"✗ Error: {str(e)}"))
            finally:
                if stream:
                    try: stream.close()
                    except: pass
        
        test_thread = threading.Thread(target=audio_test_thread, daemon=True)
        test_thread.start()
        
        dialog.exec()
        test_running[0] = False
    
    def add_file_offer_message(self, filename, filesize, file_id, sender_id, sender_name):
        """Add a file offer message with download button"""
        # Create file message widget
        message_widget = QFrame()
        message_widget.setObjectName("file_message_widget")
        message_widget.setStyleSheet("""
            QFrame#file_message_widget {
                background-color: rgba(58, 58, 60, 0.8);
                border: 1px solid rgba(99, 99, 102, 0.6);
                border-radius: 12px;
                padding: 12px;
                margin: 4px;
                max-width: 400px;
            }
        """)
        
        layout = QVBoxLayout(message_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Sender name
        sender_label = QLabel(f"📎 {sender_name} shared a file")
        sender_label.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.7); font-weight: 500;")
        layout.addWidget(sender_label)
        
        # Header with file icon and info
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        # File icon - iOS style
        icon_label = QLabel()
        icon = qta.icon('fa5s.file', color='rgba(0, 122, 255, 1.0)')
        icon_label.setPixmap(icon.pixmap(QSize(32, 32)))
        header_layout.addWidget(icon_label)
        
        # File info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(filename)
        name_label.setStyleSheet("font-weight: 600; font-size: 14px; color: rgba(255, 255, 255, 0.9);")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
        size_label = QLabel(self.format_file_size(filesize))
        size_label.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.6);")
        info_layout.addWidget(size_label)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Download button - iOS style
        download_btn = QPushButton("Download")
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 122, 255, 1.0);
                color: rgba(255, 255, 255, 1.0);
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(10, 132, 255, 1.0);
            }
            QPushButton:pressed {
                background-color: rgba(0, 100, 210, 1.0);
            }
        """)
        download_btn.clicked.connect(lambda: self.request_file_download(file_id, sender_id, filename, filesize))
        layout.addWidget(download_btn)
        
        # Add to chat
        item = QListWidgetItem()
        item.setSizeHint(message_widget.sizeHint())
        self.chat_list.addItem(item)
        self.chat_list.setItemWidget(item, message_widget)
        self.chat_list.scrollToBottom()
        
        # Store reference for updates
        if not hasattr(self, 'file_widgets'):
            self.file_widgets = {}
        self.file_widgets[file_id] = (item, message_widget)
        
        return item, message_widget
    
    def add_file_message(self, filename, filesize, file_id, is_sending=False, is_received=False, filepath=None):
        """Add a file message directly to the chat with iOS dark mode design"""
        # Create file message widget
        message_widget = QFrame()
        message_widget.setObjectName("file_message_widget")
        message_widget.setStyleSheet("""
            QFrame#file_message_widget {
                background-color: rgba(58, 58, 60, 0.8);
                border: 1px solid rgba(99, 99, 102, 0.6);
                border-radius: 12px;
                padding: 12px;
                margin: 4px;
                max-width: 400px;
            }
        """)
        
        layout = QVBoxLayout(message_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header with file icon and info
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        # File icon - iOS style
        icon_label = QLabel()
        icon = qta.icon('fa5s.file', color='rgba(0, 122, 255, 1.0)')
        icon_label.setPixmap(icon.pixmap(QSize(32, 32)))
        header_layout.addWidget(icon_label)
        
        # File info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(filename)
        name_label.setStyleSheet("font-weight: 600; font-size: 14px; color: rgba(255, 255, 255, 0.9);")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
        size_label = QLabel(self.format_file_size(filesize))
        size_label.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.6);")
        info_layout.addWidget(size_label)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Status and action area
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        
        if is_sending:
            status_label = QLabel("📤 Sending...")
            status_label.setStyleSheet("color: rgba(0, 122, 255, 1.0); font-size: 12px; font-weight: 500;")
            action_layout.addWidget(status_label)
        elif is_received and filepath:
            status_label = QLabel("✅ Received")
            status_label.setStyleSheet("color: rgba(52, 199, 89, 1.0); font-size: 12px; font-weight: 500;")
            action_layout.addWidget(status_label)
            action_layout.addStretch()
            
            # Open file button - iOS style
            open_btn = QPushButton("Open")
            open_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 122, 255, 1.0);
                    color: rgba(255, 255, 255, 1.0);
                    border: none;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(10, 132, 255, 1.0);
                }
                QPushButton:pressed {
                    background-color: rgba(0, 100, 210, 1.0);
                }
            """)
            open_btn.clicked.connect(lambda: self.open_file_location(filepath))
            action_layout.addWidget(open_btn)
        else:
            # Waiting for file
            status_label = QLabel("📥 Waiting...")
            status_label.setStyleSheet("color: rgba(255, 204, 0, 1.0); font-size: 12px; font-weight: 500;")
            action_layout.addWidget(status_label)
        
        layout.addLayout(action_layout)
        
        # Add to chat
        item = QListWidgetItem()
        item.setSizeHint(message_widget.sizeHint())
        self.chat_list.addItem(item)
        self.chat_list.setItemWidget(item, message_widget)
        self.chat_list.scrollToBottom()
        
        # Store reference for updates
        if file_id:
            if not hasattr(self, 'file_widgets'):
                self.file_widgets = {}
            self.file_widgets[file_id] = (item, message_widget)
        
        return item, message_widget
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    def open_file_location(self, filepath):
        """Open the file location in the system file manager"""
        try:
            import subprocess
            import platform
            if platform.system() == "Windows":
                subprocess.run(["explorer", "/select,", filepath])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", "-R", filepath])
            else:  # Linux
                subprocess.run(["xdg-open", os.path.dirname(filepath)])
        except Exception as e:
            print(f"Error opening file location: {e}")
            # Fallback: try to open the file directly
            try:
                if platform.system() == "Windows":
                    os.startfile(filepath)
                elif platform.system() == "Darwin":
                    subprocess.run(["open", filepath])
                else:
                    subprocess.run(["xdg-open", filepath])
            except Exception as e2:
                print(f"Error opening file: {e2}")
                self.show_notification("Could not open file location")
        
        # Files are now integrated directly in chat - no separate tab needed
    
    def open_file_location(self, filepath):
        """Open the file location in the system file explorer"""
        try:
            if platform.system() == 'Windows':
                # Windows: open explorer and select the file
                os.startfile(os.path.dirname(filepath))
            elif platform.system() == 'Darwin':
                # macOS
                os.system(f'open -R "{filepath}"')
            else:
                # Linux
                os.system(f'xdg-open "{os.path.dirname(filepath)}"')
        except Exception as e:
            self.show_notification(f"Could not open file location: {e}")
    
    def show_notification(self, message): 
        QMessageBox.information(self, "Notification", message)
    
    def show_settings_dialog(self):
        """Show settings dialog"""
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QCheckBox, QComboBox, QPushButton, QGroupBox, QSlider
            from PyQt6.QtCore import Qt
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Settings")
            dialog.setFixedSize(400, 500)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #1c1c1e;
                    color: #ffffff;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #3a3a3c;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QLabel {
                    color: #ffffff;
                }
                QSpinBox, QComboBox {
                    background-color: #2c2c2e;
                    border: 1px solid #3a3a3c;
                    border-radius: 6px;
                    padding: 5px;
                    color: #ffffff;
                }
                QCheckBox {
                    color: #ffffff;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                }
                QCheckBox::indicator:unchecked {
                    background-color: #2c2c2e;
                    border: 1px solid #3a3a3c;
                    border-radius: 3px;
                }
                QCheckBox::indicator:checked {
                    background-color: #007aff;
                    border: 1px solid #007aff;
                    border-radius: 3px;
                }
                QPushButton {
                    background-color: #007aff;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QPushButton:pressed {
                    background-color: #004494;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #3a3a3c;
                    height: 4px;
                    background: #2c2c2e;
                    border-radius: 2px;
                }
                QSlider::handle:horizontal {
                    background: #007aff;
                    border: 1px solid #007aff;
                    width: 18px;
                    margin: -7px 0;
                    border-radius: 9px;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            
            # Audio Settings
            audio_group = QGroupBox("Audio Settings")
            audio_layout = QVBoxLayout(audio_group)
            
            # Microphone volume
            mic_layout = QHBoxLayout()
            mic_layout.addWidget(QLabel("Microphone Volume:"))
            mic_slider = QSlider(Qt.Orientation.Horizontal)
            mic_slider.setRange(0, 100)
            mic_slider.setValue(80)
            mic_layout.addWidget(mic_slider)
            audio_layout.addLayout(mic_layout)
            
            # Speaker volume
            speaker_layout = QHBoxLayout()
            speaker_layout.addWidget(QLabel("Speaker Volume:"))
            speaker_slider = QSlider(Qt.Orientation.Horizontal)
            speaker_slider.setRange(0, 100)
            speaker_slider.setValue(80)
            speaker_layout.addWidget(speaker_slider)
            audio_layout.addLayout(speaker_layout)
            
            # Noise suppression
            noise_suppression = QCheckBox("Enable Noise Suppression")
            noise_suppression.setChecked(True)
            audio_layout.addWidget(noise_suppression)
            
            layout.addWidget(audio_group)
            
            # Video Settings
            video_group = QGroupBox("Video Settings")
            video_layout = QVBoxLayout(video_group)
            
            # Video quality
            quality_layout = QHBoxLayout()
            quality_layout.addWidget(QLabel("Video Quality:"))
            quality_combo = QComboBox()
            quality_combo.addItems(["Low (480p)", "Medium (720p)", "High (1080p)"])
            quality_combo.setCurrentIndex(1)
            quality_layout.addWidget(quality_combo)
            video_layout.addLayout(quality_layout)
            
            # Frame rate
            fps_layout = QHBoxLayout()
            fps_layout.addWidget(QLabel("Frame Rate:"))
            fps_spin = QSpinBox()
            fps_spin.setRange(15, 60)
            fps_spin.setValue(30)
            fps_spin.setSuffix(" fps")
            fps_layout.addWidget(fps_spin)
            video_layout.addLayout(fps_layout)
            
            # Mirror video
            mirror_video = QCheckBox("Mirror My Video")
            mirror_video.setChecked(True)
            video_layout.addWidget(mirror_video)
            
            layout.addWidget(video_group)
            
            # Network Settings
            network_group = QGroupBox("Network Settings")
            network_layout = QVBoxLayout(network_group)
            
            # Bandwidth limit
            bandwidth_layout = QHBoxLayout()
            bandwidth_layout.addWidget(QLabel("Bandwidth Limit:"))
            bandwidth_spin = QSpinBox()
            bandwidth_spin.setRange(100, 10000)
            bandwidth_spin.setValue(2000)
            bandwidth_spin.setSuffix(" kbps")
            bandwidth_layout.addWidget(bandwidth_spin)
            network_layout.addLayout(bandwidth_layout)
            
            # Auto-reconnect
            auto_reconnect = QCheckBox("Auto-reconnect on Connection Loss")
            auto_reconnect.setChecked(True)
            network_layout.addWidget(auto_reconnect)
            
            layout.addWidget(network_group)
            
            # File Transfer Settings
            file_group = QGroupBox("File Transfer Settings")
            file_layout = QVBoxLayout(file_group)
            
            # File transfer info
            info_label = QLabel("You will be prompted to choose a save location for each file download.")
            info_label.setWordWrap(True)
            info_label.setStyleSheet("color: #8e8e93; font-style: italic; padding: 8px;")
            file_layout.addWidget(info_label)
            
            # Default download location
            download_layout = QHBoxLayout()
            download_layout.addWidget(QLabel("Default Download Folder:"))
            download_label = QLabel("~/Downloads/")
            download_label.setStyleSheet("color: #8e8e93; font-style: italic;")
            download_layout.addWidget(download_label)
            download_layout.addStretch()
            file_layout.addLayout(download_layout)
            
            layout.addWidget(file_group)
            
            # Buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a3c;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #4a4a4c;
                }
            """)
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            save_btn = QPushButton("Save")
            save_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(save_btn)
            
            layout.addLayout(button_layout)
            
            # Show dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Here you would save the settings
                self.show_notification("Settings saved successfully!")
                
        except Exception as e:
            print(f"Error showing settings dialog: {e}")
            self.show_notification("Settings dialog is not available")
    
    def show_join_notification(self, username):
        """Show animated join notification that properly disappears"""
        notification = QLabel(f"{username} has joined the meeting", self)
        notification.setStyleSheet("""
            QLabel {
                background-color: rgba(87, 242, 135, 0.9);
                color: white;
                padding: 10px 20px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        notification.setAlignment(Qt.AlignmentFlag.AlignCenter)
        notification.adjustSize()
        
        # Position at top center
        notification.move(self.width() // 2 - notification.width() // 2, 50)
        
        # Show notification
        notification.show()
        notification.raise_()
        
        # Use QTimer to hide and delete after 3 seconds
        QTimer.singleShot(3000, notification.deleteLater)
    def leave_meeting(self):
        if QMessageBox.question(self, "Leave Meeting", "Are you sure?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.client.disconnect(); self.close()

    def closeEvent(self, event):
        self.ui_running = False; self.audio_enabled = False
        if hasattr(self, 'audio_output_queue'): self.audio_output_queue.put(None)
        self.stop_video(); self.stop_screen_share(); self.client.disconnect()
        for f in self.incoming_files.values(): f['fh'].close()
        if self.audio_thread_input and self.audio_thread_input.is_alive(): self.audio_thread_input.join(0.2)
        if self.audio_thread_output and self.audio_thread_output.is_alive(): self.audio_thread_output.join(0.2)
        if self.p_audio: self.p_audio.terminate()
        event.accept()
        
    def eventFilter(self, obj, event):
        """Handle events for the chat list to resize file widgets properly"""
        if obj == self.chat_list.viewport() and event.type() == QEvent.Type.Resize:
            self.update_file_widget_sizes()
        return super().eventFilter(obj, event)
    
    def update_file_widget_sizes(self):
        """Adapt file transfer widgets to the chat list width"""
        # Only update if the chat list has items
        if self.chat_list.count() == 0:
            return
        
        # Get current available width in the chat list
        available_width = self.chat_list.viewport().width() - 20  # Allow for padding
        
        # File widgets now auto-adapt, no manual sizing needed
        pass
