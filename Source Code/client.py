"""
===================================================================================
MULTI-USER VIDEO CONFERENCING CLIENT - CLIENT.PY
===================================================================================
This is the client application that connects to the conference server and manages
local media capture (camera, microphone, screen) and network communication.

CORE FUNCTIONALITY:
1. Video Capture & Transmission - Captures webcam video and sends via UDP
2. Audio Capture & Transmission - Captures microphone audio and sends via UDP
3. Screen Sharing - Captures screen content and sends via TCP
4. Chat Messaging - Sends/receives text messages via TCP
5. File Sharing - Uploads/downloads files via TCP

NETWORK PROTOCOLS:
- TCP (Transmission Control Protocol): For reliable communication
  * Meeting join/create
  * Chat messages
  * File transfers
  * Control messages (mute, video state, etc.)
  * Screen sharing frames (for clarity and integrity)

- UDP (User Datagram Protocol): For real-time media streaming
  * Video frames (low latency, acceptable packet loss)
  * Audio packets (real-time delivery, minor loss tolerable)

CONNECTION FLOW:
1. User enters server IP and port in login dialog
2. Client creates TCP connection to server
3. Client creates UDP socket for media streaming
4. Client sends join/create meeting request via TCP
5. Server responds with meeting code and participant list
6. Client starts background threads for receiving TCP/UDP data
7. Client captures and sends media via UDP
8. Client sends/receives control messages via TCP
===================================================================================
"""

# Import required libraries
import sys
import socket          # For TCP/UDP socket programming
import threading       # For concurrent operations (send/receive)
import struct          # For packing/unpacking binary network data
import json            # For serializing/deserializing messages
import time            # For timestamps and delays
import base64          # For encoding binary data (files, images) in JSON
import logging         # For session logging
import os              # For file operations
from pathlib import Path  # For file path handling
from datetime import datetime  # For timestamps
from PyQt6.QtWidgets import QApplication  # Qt GUI framework
from PyQt6.QtCore import QObject, pyqtSignal, QTimer  # Qt signals for thread-safe UI updates
from ui.main_window import EnhancedMainWindow  # Main application window

# Try to import msgpack for efficient binary serialization (fallback to JSON)
try:
    import msgpack
    # Force JSON for compatibility - can be changed back later
    USE_MSGPACK = False  # Temporarily disabled for debugging
    print("📝 Using JSON protocol for better compatibility")
except ImportError:
    print("⚠️  msgpack not available, falling back to JSON")
    USE_MSGPACK = False

"""
===================================================================================
SIGNAL CLASS FOR THREAD-SAFE UI UPDATES
===================================================================================
"""

class StreamSignals(QObject):
    """
    Qt signals for thread-safe communication between network threads and UI thread.
    
    PURPOSE: Network operations run in background threads, but Qt UI can only be
    updated from the main thread. These signals bridge the gap safely.
    
    SIGNALS:
    - video_received: Emitted when video frame arrives (client_id, frame_data)
    - audio_received: Emitted when audio packet arrives (client_id, audio_data)
    - message_received: Emitted when TCP message arrives (message_dict)
    """
    video_received = pyqtSignal(str, bytes)  # (client_id, video_data)
    audio_received = pyqtSignal(object, bytes)  # (client_id, audio_data)
    message_received = pyqtSignal(dict)  # (message_dictionary)

"""
===================================================================================
MAIN CLIENT CLASS
===================================================================================
"""

class OptimizedConferenceClient:
    """
    Main client class managing connection to server and local media capture.
    
    NETWORK ARCHITECTURE:
    - TCP Socket: Reliable connection for control messages, chat, files
    - UDP Socket: Connectionless socket for real-time audio/video streaming
    
    THREADING MODEL:
    - Main Thread: UI and user interactions
    - TCP Receive Thread: Continuously receives TCP messages from server
    - UDP Receive Thread: Continuously receives UDP packets from server
    - Audio Capture Thread: Captures microphone input and sends via UDP
    - Video Capture Thread: Captures camera frames and sends via UDP
    """
    
    def __init__(self):
        """
        Initialize the conference client.
        
        NETWORK COMPONENTS:
        - tcp_socket: TCP connection to server (reliable messaging)
        - udp_socket: UDP socket for media streaming (low latency)
        - server_address: (IP, UDP_port) tuple for UDP packets
        """
        # Network sockets (initialized when connecting)
        self.tcp_socket = None  # TCP socket for reliable communication
        self.udp_socket = None  # UDP socket for real-time media
        self.server_address = None  # Server's UDP address (IP, port)
        
        # User and session information
        self.username = None  # User's display name
        self.client_id = None  # Unique identifier assigned by server
        self.meeting_code = None  # 6-character meeting code
        self.is_host = False  # Whether this client is the meeting host
        self.connected = False  # Connection status
        self.running = False  # Whether background threads should run
        
        # Server connection details
        self.server_ip = '127.0.0.1'  # Default to localhost
        self.tcp_port = 5001  # Default TCP port
        
        # Screen sharing state
        self.current_presenter = None  # Who is currently presenting
        self.is_presenting = False  # Whether this client is presenting
        
        # UI reference
        self.ui = None  # Will be set to main window
        
        # File download directory
        self.downloads_dir = Path.home() / 'Downloads' / 'LANMeet'
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        
        # Qt signals for thread-safe UI updates
        self.signals = StreamSignals()
        
        # Pre-allocated buffers for performance optimization
        # Reason: Reusing buffers reduces memory allocation overhead
        self.tcp_send_buffer = bytearray(65536)  # 64KB buffer for TCP messages
        self.udp_send_buffer = bytearray(65536)  # 64KB buffer for UDP packets
        
        # Background threads for network operations
        self.tcp_thread = None  # Thread for receiving TCP messages
        self.udp_thread = None  # Thread for receiving UDP packets
        
        # File transfer tracking
        self.pending_files = {}  # Files we're offering: file_id -> file_path
        self.receiving_files = {}  # Files we're downloading: file_id -> file_info
        self.file_lock = threading.Lock()  # Thread-safe access to file dictionaries
        
        # Setup logging system
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging system with session-based log files"""
        # Create logs directory structure
        log_dir = Path('logs/client')
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate session log filename with timestamp
        session_time = datetime.now()
        log_filename = session_time.strftime('session_%Y%m%d_%H%M%S.log')
        log_path = log_dir / log_filename
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()  # Also print to console
            ]
        )
        
        self.logger = logging.getLogger('CLIENT')
        self.logger.info('='*80)
        self.logger.info(f'Client Session Started')
        self.logger.info(f'Date: {session_time.strftime("%A, %B %d, %Y")}')
        self.logger.info(f'Time: {session_time.strftime("%I:%M:%S %p")}')
        self.logger.info(f'Log File: {log_path}')
        self.logger.info('='*80)
        
    def set_ui(self, ui):
        self.ui = ui
        self.signals.video_received.connect(ui.handle_video_stream)
        self.signals.audio_received.connect(ui.handle_audio_stream)
        self.signals.message_received.connect(ui.handle_server_message)

    def set_server(self, ip, port):
        """Set server details from the login UI."""
        # Validate and clean IP address
        ip = ip.strip()
        if not ip:
            ip = '127.0.0.1'  # Default to localhost if empty
        
        # Update server settings
        self.server_ip = ip
        self.tcp_port = port
        
        self.logger.info(f'Server settings updated: {self.server_ip}:{self.tcp_port}')
        print(f"🌐 Server set to: {self.server_ip}:{self.tcp_port}")
    
    def test_connection(self):
        """Test if we can connect to the server"""
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(5)
            result = test_socket.connect_ex((self.server_ip, self.tcp_port))
            test_socket.close()
            
            if result == 0:
                print(f"✅ Can connect to {self.server_ip}:{self.tcp_port}")
                return True
            else:
                print(f"❌ Cannot connect to {self.server_ip}:{self.tcp_port} (Error: {result})")
                return False
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    def _serialize_message(self, message):
        """Serialize message using msgpack or json"""
        if USE_MSGPACK:
            return msgpack.packb(message)
        else:
            return json.dumps(message).encode('utf-8')
    
    def _deserialize_message(self, data):
        """Deserialize message using msgpack or json with fallback"""
        if not data:
            raise ValueError("Empty data received")
        
        # Try msgpack first if enabled
        if USE_MSGPACK:
            try:
                return msgpack.unpackb(data, raw=False)
            except Exception as e:
                print(f"msgpack deserialization failed: {e}, trying JSON...")
        
        # Try JSON (either as primary or fallback)
        try:
            decoded_data = data.decode('utf-8')
            if not decoded_data.strip():
                raise ValueError("Empty JSON data")
            return json.loads(decoded_data)
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as json_error:
            # If JSON also fails, try msgpack as last resort
            if not USE_MSGPACK:
                try:
                    return msgpack.unpackb(data, raw=False)
                except Exception as msgpack_error:
                    print(f"Both JSON and msgpack deserialization failed:")
                    print(f"  JSON error: {json_error}")
                    print(f"  msgpack error: {msgpack_error}")
            else:
                print(f"JSON deserialization error: {json_error}")
            
            print(f"Raw data (first 100 bytes): {data[:100]}")
            print(f"Data starts with: {data[:10].hex() if len(data) >= 10 else data.hex()}")
            raise ValueError("Could not deserialize message with any format")
        
    def create_meeting(self, username):
        """
        Create a new meeting by connecting to the server.
        
        PROTOCOL: TCP (Transmission Control Protocol)
        PURPOSE: Establish reliable connection and create new meeting session
        
        NETWORK FLOW:
        1. Create TCP socket (SOCK_STREAM = connection-oriented)
        2. Connect to server's TCP port
        3. Create UDP socket for media streaming
        4. Send 'create_meeting' message via TCP
        5. Receive meeting code from server via TCP
        6. Start background threads for receiving data
        
        TCP SOCKET OPTIONS:
        - TCP_NODELAY: Disables Nagle's algorithm for lower latency
          (sends small packets immediately instead of buffering)
        - SO_REUSEADDR: Allows socket reuse after program restart
        
        UDP SOCKET:
        - Bound to port 0 (OS assigns random available port)
        - Used for sending/receiving audio and video packets
        
        WHY TCP FOR MEETING CREATION:
        - Guarantees message delivery (critical for authentication)
        - Ensures ordered delivery (meeting code must arrive correctly)
        - Connection-oriented (server knows client is ready)
        """
        self.logger.info(f'Attempting to create meeting as user: {username}')
        self.logger.info(f'Server: {self.server_ip}:{self.tcp_port}')
        
        # Test connection first
        if not self.test_connection():
            self.logger.error('Connection test failed')
            return False, "Cannot connect to server. Check IP address and network connection.", []
        
        self.logger.info('Connection test successful')
        
        try:
            # ========================================================================
            # TCP SOCKET CREATION (Reliable Connection)
            # ========================================================================
            self.logger.info('Creating TCP socket...')
            
            # Create TCP socket: AF_INET = IPv4, SOCK_STREAM = TCP
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # TCP_NODELAY: Disable Nagle's algorithm for lower latency
            # Nagle's algorithm buffers small packets to reduce network overhead
            # We disable it because we want immediate transmission of control messages
            self.tcp_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            # SO_REUSEADDR: Allow socket to bind to address in TIME_WAIT state
            # Useful for quick reconnections after disconnect
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Connect to server's TCP port (3-way handshake: SYN, SYN-ACK, ACK)
            # This establishes a reliable, ordered, bidirectional connection
            self.tcp_socket.connect((self.server_ip, self.tcp_port))
            self.logger.info(f'TCP socket connected to {self.server_ip}:{self.tcp_port}')
            
            # ========================================================================
            # UDP SOCKET CREATION (Real-Time Media Streaming)
            # ========================================================================
            self.logger.info('Creating UDP socket...')
            
            # Create UDP socket: AF_INET = IPv4, SOCK_DGRAM = UDP
            # UDP is connectionless - no handshake, just send/receive packets
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # SO_REUSEADDR for UDP
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind to any available port (0 = OS chooses port)
            # 0.0.0.0 = listen on all network interfaces
            self.udp_socket.bind(('0.0.0.0', 0))
            self.logger.info(f'UDP socket bound to port {self.udp_socket.getsockname()[1]}')
            
            # Store server's UDP address (IP, UDP_port)
            # UDP port is always TCP port + 1 by convention
            self.server_address = (self.server_ip, self.tcp_port + 1)
            self.username = username
            
            # ========================================================================
            # SEND CREATE MEETING REQUEST (TCP)
            # ========================================================================
            # Serialize message to JSON format
            message_data = self._serialize_message({'type': 'create_meeting', 'username': username})
            
            # Send via TCP (guaranteed delivery)
            # TCP ensures this message arrives at server correctly
            self.tcp_socket.send(message_data)
            
            # Receive response
            response_data = self.tcp_socket.recv(4096)
            if not response_data:
                raise ConnectionError("No response from server")
            
            try:
                response = self._deserialize_message(response_data)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Failed to parse server response: {e}")
                print(f"Raw response: {response_data}")
                raise ConnectionError("Invalid response from server")
            
            if response['type'] == 'meeting_created':
                self.connected = True
                self.running = True
                self.meeting_code = response['meeting_code']
                self.client_id = response['client_id']
                self.is_host = response['is_host']
                
                self.logger.info('='*80)
                self.logger.info('✅ Meeting Created Successfully!')
                self.logger.info(f'Meeting Code: {self.meeting_code}')
                self.logger.info(f'Client ID: {self.client_id}')
                self.logger.info(f'Role: Host')
                self.logger.info('='*80)
                
                # Start background threads
                self.logger.info('Starting background threads...')
                self.tcp_thread = threading.Thread(target=self._receive_tcp_messages, daemon=True)
                self.udp_thread = threading.Thread(target=self._receive_udp_streams, daemon=True)
                self.tcp_thread.start()
                self.udp_thread.start()
                self.logger.info('Background threads started')
                
                self.send_udp_init()
                return True, self.meeting_code, []
            
            self.logger.warning('Meeting creation failed - unexpected response')
            return False, None, []
            
        except Exception as e:
            self.logger.error(f"Create meeting error: {e}", exc_info=True)
            print(f"Create meeting error: {e}")
            return False, str(e), []
            
    def join_meeting(self, username, meeting_code):
        """Join an existing meeting using optimized protocol."""
        # Test connection first
        if not self.test_connection():
            return False, "Cannot connect to server. Check IP address and network connection."
        
        try:
            # Create TCP socket
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.connect((self.server_ip, self.tcp_port))
            
            # Create UDP socket
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_socket.bind(('0.0.0.0', 0))
            
            self.server_address = (self.server_ip, self.tcp_port + 1)
            self.username = username
            
            # Send join message
            message_data = self._serialize_message({
                'type': 'join_meeting',
                'username': username,
                'meeting_code': meeting_code
            })
            self.tcp_socket.send(message_data)
            
            # Receive response
            response_data = self.tcp_socket.recv(4096)
            if not response_data:
                raise ConnectionError("No response from server")
            
            try:
                response = self._deserialize_message(response_data)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Failed to parse server response: {e}")
                print(f"Raw response: {response_data}")
                raise ConnectionError("Invalid response from server")
            
            if response['type'] == 'join_success':
                self.connected = True
                self.running = True
                self.meeting_code = response['meeting_code']
                self.client_id = response['client_id']
                self.is_host = response['is_host']
                
                # Start background threads
                self.tcp_thread = threading.Thread(target=self._receive_tcp_messages, daemon=True)
                self.udp_thread = threading.Thread(target=self._receive_udp_streams, daemon=True)
                self.tcp_thread.start()
                self.udp_thread.start()
                
                self.send_udp_init()
                return True, response.get('participants', [])
            elif response['type'] == 'error':
                return False, response.get('message', 'Failed to join meeting')
            
            return False, "Unknown error"
            
        except Exception as e:
            print(f"Join meeting error: {e}")
            return False, f"Connection error: {str(e)}"
    
    def _receive_tcp_messages(self):
        """TCP receiver thread for better performance"""
        while self.running:
            try:
                # Read message length
                length_bytes = b''
                while len(length_bytes) < 4 and self.running:
                    chunk = self.tcp_socket.recv(4 - len(length_bytes))
                    if not chunk:
                        raise ConnectionResetError("Connection closed")
                    length_bytes += chunk
                
                if not self.running:
                    break
                    
                msg_length = struct.unpack('!I', length_bytes)[0]
                
                if msg_length > 10485760:  # 10MB limit
                    break
                
                # Read message data
                data = b''
                while len(data) < msg_length and self.running:
                    chunk = self.tcp_socket.recv(min(4096, msg_length - len(data)))
                    if not chunk:
                        raise ConnectionResetError("Connection closed")
                    data += chunk
                
                if not self.running:
                    break
                
                # Decode message
                message = self._deserialize_message(data)
                
                # Handle file transfer messages internally
                if message.get('type') == 'file_chunk':
                    self._handle_file_chunk(message)
                elif message.get('type') == 'file_end':
                    self._handle_file_end(message)
                elif message.get('type') == 'file_request':
                    self._handle_file_request(message)
                elif message.get('type') == 'screen_share_started':
                    self.current_presenter = message.get('presenter_id')
                elif message.get('type') == 'screen_share_stopped':
                    self.current_presenter = None
                elif message.get('type') == 'screen_share_denied':
                    # Emit to UI to handle the denial
                    self.signals.message_received.emit(message)
                elif message.get('type') == 'screen_frame':
                    # Handle incoming screen frame
                    self._handle_screen_frame(message)
                else:
                    # Emit other messages to UI thread
                    self.signals.message_received.emit(message)
                
            except (ConnectionResetError, OSError) as e:
                if self.running:
                    print(f"TCP connection error: {e}")
                break
            except Exception as e:
                if self.running:
                    print(f"TCP receive error: {e}")
                break
        
        if self.running:
            # Schedule disconnect in main thread
            QTimer.singleShot(0, self.disconnect)
    
    def _receive_udp_streams(self):
        """UDP receiver thread with improved video/audio handling"""
        self.udp_socket.settimeout(0.05)
        
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(65535)
                
                if len(data) < 3:
                    continue
                
                stream_type = chr(data[0])
                
                if stream_type == 'A' and data[1:3] == b'\x00\x00':
                    # Audio packet
                    audio_data = data[3:]
                    if len(audio_data) > 0:
                        self.signals.audio_received.emit(None, audio_data)
                    
                elif stream_type == 'V':
                    # Video packet
                    try:
                        client_id_len = struct.unpack('!H', data[1:3])[0]
                        if len(data) < 3 + client_id_len:
                            continue
                        
                        client_id = data[3:3+client_id_len].decode('utf-8')
                        video_data = data[3+client_id_len:]
                        
                        if len(video_data) > 0 and client_id:
                            self.signals.video_received.emit(client_id, video_data)
                    except (struct.error, UnicodeDecodeError) as e:
                        print(f"Video packet decode error: {e}")
                        continue
                    
            except socket.timeout:
                continue
            except OSError as e:
                if self.running and e.errno not in [35, 11]:
                    print(f"UDP receive error: {e}")
                time.sleep(0.001)
            except Exception as e:
                if self.running:
                    print(f"UDP receive error: {e}")
                time.sleep(0.001)
    
    def _handle_file_chunk(self, message):
        """Handle incoming file chunk"""
        try:
            file_id = message.get('file_id')
            chunk_data = message.get('data')
            
            if not file_id or not chunk_data:
                self.logger.warning(f'Invalid file chunk: file_id={file_id}, data_len={len(chunk_data) if chunk_data else 0}')
                return
            
            # Decode base64 data if it's a string
            if isinstance(chunk_data, str):
                chunk_data = base64.b64decode(chunk_data)
            
            chunk_size = len(chunk_data)
            self.logger.debug(f'Received file chunk: file_id={file_id}, size={chunk_size} bytes')
            
            with self.file_lock:
                if file_id in self.receiving_files:
                    file_info = self.receiving_files[file_id]
                    file_info['file'].write(chunk_data)
                    file_info['file'].flush()  # Ensure data is written to disk
                    file_info['bytes_received'] += chunk_size
                    
                    self.logger.debug(f'File progress: {file_info["bytes_received"]}/{file_info["total_size"]} bytes')
                    
                    # Notify UI of progress
                    progress = (file_info['bytes_received'] / file_info['total_size']) * 100
                    if self.ui:
                        self.signals.message_received.emit({
                            'type': 'file_progress',
                            'file_id': file_id,
                            'filename': file_info['filename'],
                            'progress': progress,
                            'bytes_received': file_info['bytes_received'],
                            'total_size': file_info['total_size']
                        })
                else:
                    self.logger.warning(f'Received chunk for unknown file: {file_id}')
                        
        except Exception as e:
            self.logger.error(f"Error handling file chunk: {e}", exc_info=True)
            print(f"Error handling file chunk: {e}")
    
    def _handle_file_end(self, message):
        """Handle file transfer completion"""
        try:
            file_id = message.get('file_id')
            
            with self.file_lock:
                if file_id in self.receiving_files:
                    file_info = self.receiving_files[file_id]
                    file_info['file'].close()
                    
                    # Notify UI
                    if self.ui:
                        self.signals.message_received.emit({
                            'type': 'file_complete',
                            'file_id': file_id,
                            'filename': file_info['filename'],
                            'filepath': file_info.get('save_path', str(self.downloads_dir / file_info['filename']))
                        })
                    
                    del self.receiving_files[file_id]
                    
        except Exception as e:
            print(f"Error handling file end: {e}")
    
    def _handle_screen_frame(self, message):
        """Handle incoming screen frame from presenter"""
        try:
            presenter_id = message.get('presenter_id')
            frame_data = message.get('frame_data')
            
            if not presenter_id or not frame_data:
                self.logger.debug("Screen frame missing presenter_id or frame_data")
                return
            
            # Only process if this is from the current presenter
            if presenter_id != self.current_presenter:
                self.logger.debug(f"Ignoring screen frame from {presenter_id}, current presenter is {self.current_presenter}")
                return
            
            # Decode base64 frame data
            if isinstance(frame_data, str):
                frame_bytes = base64.b64decode(frame_data)
            else:
                frame_bytes = frame_data
            
            self.logger.debug(f"Received screen frame from {presenter_id}, size: {len(frame_bytes)} bytes")
            
            # Emit to UI for display
            self.signals.video_received.emit(presenter_id, frame_bytes)
            
        except Exception as e:
            self.logger.error(f"Error handling screen frame: {e}", exc_info=True)
            print(f"Error handling screen frame: {e}")
    
    def _handle_file_request(self, message):
        """Handle file request from another client"""
        try:
            file_id = message.get('file_id')
            recipient_id = message.get('downloader_id')
            
            self.logger.info(f'Received file request: file_id={file_id}, downloader_id={recipient_id}')
            
            if not file_id or not recipient_id:
                self.logger.warning('Invalid file request: missing file_id or downloader_id')
                return
            
            with self.file_lock:
                if file_id in self.pending_files:
                    file_path = self.pending_files[file_id]
                    self.logger.info(f'Starting file upload: {file_path} to {recipient_id}')
                    
                    # Start sending file in background thread
                    threading.Thread(
                        target=self._send_file_worker,
                        args=(recipient_id, file_id, file_path),
                        daemon=True
                    ).start()
                else:
                    self.logger.warning(f'File not found in pending_files: {file_id}')
                    
        except Exception as e:
            self.logger.error(f"Error handling file request: {e}", exc_info=True)
            print(f"Error handling file request: {e}")
    
    def _send_file_worker(self, recipient_id, file_id, file_path):
        """Worker thread to send file chunks"""
        try:
            chunk_size = 32768  # 32KB chunks
            total_size = os.path.getsize(file_path)
            bytes_sent = 0
            
            self.logger.info(f'Starting file upload: {file_path} ({total_size} bytes) to {recipient_id}')
            
            with open(file_path, 'rb') as f:
                chunk_count = 0
                while self.running:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    chunk_count += 1
                    bytes_sent += len(chunk)
                    
                    # Encode chunk as base64 for JSON compatibility
                    chunk_encoded = base64.b64encode(chunk).decode('utf-8')
                    
                    self.logger.debug(f'Sending chunk {chunk_count}: {len(chunk)} bytes (total: {bytes_sent}/{total_size})')
                    
                    self.send_tcp_message({
                        'type': 'file_chunk',
                        'recipient_id': recipient_id,
                        'file_id': file_id,
                        'data': chunk_encoded
                    })
                    
                    # Small delay to avoid overwhelming the network
                    time.sleep(0.01)
            
            self.logger.info(f'File upload complete: sent {bytes_sent} bytes in {chunk_count} chunks')
            
            # Send completion message
            self.send_file_end(recipient_id, file_id)
            
            # Clean up
            with self.file_lock:
                if file_id in self.pending_files:
                    del self.pending_files[file_id]
                    
        except Exception as e:
            self.logger.error(f"Error sending file: {e}", exc_info=True)
            print(f"Error sending file: {e}")
    
    def send_tcp_message(self, message):
        """
        Send a message to the server via TCP.
        
        PROTOCOL: TCP (Transmission Control Protocol)
        PURPOSE: Reliable delivery of control messages, chat, and file data
        
        MESSAGE FORMAT:
        [Length (4 bytes)][JSON Data (variable length)]
        
        Length Prefix:
        - 4 bytes (unsigned integer, network byte order)
        - Tells receiver how many bytes to expect
        - Prevents message fragmentation issues
        
        WHY TCP:
        - Guarantees delivery (no message loss)
        - Guarantees order (messages arrive in sequence)
        - Error checking (corrupted data is retransmitted)
        - Essential for: chat messages, file transfers, control commands
        
        USED FOR:
        - Chat messages (must not be lost)
        - File chunks (data integrity critical)
        - Control commands (mute, video state, etc.)
        - Screen sharing frames (clarity important)
        """
        if not self.connected:
            return
        
        try:
            # Serialize message to JSON (or msgpack if enabled)
            data = self._serialize_message(message)
            
            # Pack message length as 4-byte unsigned integer (network byte order)
            # '!' = network byte order (big-endian)
            # 'I' = unsigned int (4 bytes)
            length = struct.pack('!I', len(data))
            
            # Send length prefix + data via TCP
            # sendall() ensures all data is sent (handles partial sends)
            self.tcp_socket.sendall(length + data)
        except Exception as e:
            print(f"TCP send error: {e}")
            
    def send_udp_stream(self, stream_type, data):
        """
        Send audio or video data to server via UDP.
        
        PROTOCOL: UDP (User Datagram Protocol)
        PURPOSE: Low-latency streaming of real-time media
        
        PACKET STRUCTURE:
        [Stream Type (1 byte)][Client ID Length (2 bytes)][Client ID][Media Data]
        
        Stream Types:
        - 'V': Video frame (JPEG compressed image)
        - 'A': Audio packet (PCM audio samples)
        - 'I': Initialization packet (establishes UDP address)
        
        WHY UDP:
        - No connection overhead (connectionless protocol)
        - No retransmission delays (lost packets are skipped)
        - Lower latency than TCP (critical for real-time media)
        - Acceptable packet loss (human perception tolerates minor glitches)
        
        PACKET SIZE LIMIT:
        - Maximum UDP packet size: 65,507 bytes
        - Reason: IP packet limit (65,535) - IP header (20) - UDP header (8)
        - Larger data must be split into multiple packets
        
        USED FOR:
        - Video frames (20 FPS, ~10-30 KB per frame)
        - Audio packets (44.1 kHz, 1024 samples, ~2 KB per packet)
        """
        if not self.connected or not self.client_id or not data:
            return
        
        try:
            # Encode client ID to bytes
            client_id_bytes = self.client_id.encode('utf-8')
            client_id_len = len(client_id_bytes)
            
            # Calculate total packet size
            # 1 byte (stream type) + 2 bytes (ID length) + ID + media data
            packet_size = 1 + 2 + client_id_len + len(data)
            
            # Check UDP packet size limit (65,507 bytes maximum)
            if packet_size > 65507:
                print(f"Packet too large: {packet_size} bytes")
                return
            
            # Reuse pre-allocated buffer if possible (performance optimization)
            if packet_size <= len(self.udp_send_buffer):
                packet = self.udp_send_buffer
            else:
                packet = bytearray(packet_size)
            
            # Build UDP packet structure:
            # Byte 0: Stream type ('V' for video, 'A' for audio)
            packet[0] = ord(stream_type)
            
            # Bytes 1-2: Client ID length (2 bytes, network byte order)
            struct.pack_into('!H', packet, 1, client_id_len)
            
            # Bytes 3 to 3+len: Client ID
            packet[3:3+client_id_len] = client_id_bytes
            
            # Remaining bytes: Media data (video frame or audio samples)
            packet[3+client_id_len:packet_size] = data
            
            # Send UDP packet to server
            # sendto() sends one packet (no connection, just fire and forget)
            # No guarantee of delivery or order
            self.udp_socket.sendto(bytes(packet[:packet_size]), self.server_address)
            
        except Exception as e:
            print(f"UDP send error: {e}")
            
    def send_udp_init(self):
        """Send UDP initialization packet"""
        self.send_udp_stream('I', b'init')
            
    def send_chat_message(self, message):
        """Send chat message"""
        self.logger.info(f'Sending chat message: {message[:50]}...' if len(message) > 50 else f'Sending chat message: {message}')
        self.send_tcp_message({'type': 'chat', 'message': message})
        
    def send_video_state(self, is_enabled):
        """Send video state change"""
        self.send_tcp_message({
            'type': 'video_state',
            'state': 'started' if is_enabled else 'stopped'
        })
    
    def send_screen_frame_tcp(self, frame_data):
        """Send screen frame via TCP for reliability and clarity"""
        if not self.connected or not hasattr(self, 'is_presenting') or not self.is_presenting:
            return
        
        try:
            self.send_tcp_message({
                'type': 'screen_frame',
                'frame_data': frame_data,
                'presenter_id': self.client_id
            })
        except Exception as e:
            self.logger.error(f"Error sending screen frame via TCP: {e}")
            print(f"Error sending screen frame via TCP: {e}")
            raise
    
    def request_screen_share(self):
        """Request to start screen sharing"""
        self.send_tcp_message({
            'type': 'request_screen_share'
        })
    
    def stop_screen_share_request(self):
        """Request to stop screen sharing"""
        self.send_tcp_message({
            'type': 'stop_screen_share'
        })
        
    def mute_participant(self, target_client_id):
        """Mute a participant (host only)"""
        if self.is_host:
            self.send_tcp_message({
                'type': 'mute_participant',
                'target_client_id': target_client_id
            })
            
    def unmute_participant(self, target_client_id):
        """Unmute a participant (host only)"""
        if self.is_host:
            self.send_tcp_message({
                'type': 'unmute_participant',
                'target_client_id': target_client_id
            })
    
    def lock_participant_mic(self, target_client_id):
        """Lock a participant's mic (host only)"""
        if self.is_host:
            self.send_tcp_message({
                'type': 'lock_mic',
                'target_client_id': target_client_id
            })
    
    def unlock_participant_mic(self, target_client_id):
        """Unlock a participant's mic (host only)"""
        if self.is_host:
            self.send_tcp_message({
                'type': 'unlock_mic',
                'target_client_id': target_client_id
            })
    
    def send_emoji_reaction(self, emoji):
        """Send emoji reaction"""
        self.send_tcp_message({
            'type': 'emoji_reaction',
            'emoji': emoji
        })
    
    def raise_hand(self, state):
        """Raise/lower hand"""
        self.send_tcp_message({
            'type': 'raise_hand',
            'state': state
        })
    
    def request_participant_video(self, target_client_id):
        """Request video from participant (host only)"""
        if self.is_host:
            self.send_tcp_message({
                'type': 'request_video',
                'target_client_id': target_client_id
            })
    
    def request_all_video(self):
        """Request video from all participants (host only)"""
        if self.is_host:
            self.send_tcp_message({'type': 'request_all_video'})
    
    def request_participant_unmute(self, target_client_id):
        """Request unmute from participant (host only)"""
        if self.is_host:
            self.send_tcp_message({
                'type': 'request_unmute',
                'target_client_id': target_client_id
            })
    
    def request_all_unmute(self):
        """Request unmute from all participants (host only)"""
        if self.is_host:
            self.send_tcp_message({'type': 'request_all_unmute'})
    
    def send_file_offer(self, file_path):
        """Send file offer to all participants"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                self.logger.error(f"File not found: {file_path}")
                print(f"File not found: {file_path}")
                return None
            
            file_id = f"{self.client_id}_{int(time.time() * 1000)}"
            filename = file_path.name
            filesize = file_path.stat().st_size
            
            self.logger.info(f'Offering file: {filename} ({filesize} bytes) - ID: {file_id}')
            
            # Store file for later requests
            with self.file_lock:
                self.pending_files[file_id] = str(file_path)
            
            # Send offer
            self.send_tcp_message({
                'type': 'file_offer',
                'file_id': file_id,
                'filename': filename,
                'filesize': filesize
            })
            
            return file_id
            
        except Exception as e:
            self.logger.error(f"Error sending file offer: {e}", exc_info=True)
            print(f"Error sending file offer: {e}")
            return None
    
    def request_file(self, sender_id, file_id, filename, filesize, save_path=None):
        """Request a file from sender"""
        try:
            # Use provided save path or create default
            if save_path:
                filepath = Path(save_path)
            else:
                filepath = self.downloads_dir / filename
                
                # Handle duplicate filenames
                counter = 1
                while filepath.exists():
                    name_parts = filename.rsplit('.', 1)
                    if len(name_parts) == 2:
                        filepath = self.downloads_dir / f"{name_parts[0]}_{counter}.{name_parts[1]}"
                    else:
                        filepath = self.downloads_dir / f"{filename}_{counter}"
                    counter += 1
            
            self.logger.info(f'Requesting file: {filename} -> {filepath}')
            
            # Open file for writing
            file_handle = open(filepath, 'wb')
            
            with self.file_lock:
                self.receiving_files[file_id] = {
                    'file': file_handle,
                    'filename': filename,
                    'bytes_received': 0,
                    'total_size': filesize,
                    'save_path': str(filepath)
                }
            
            # Send request to server
            self.send_tcp_message({
                'type': 'file_request',
                'sender_id': sender_id,
                'file_id': file_id
            })
            
        except Exception as e:
            self.logger.error(f"Error requesting file: {e}", exc_info=True)
            print(f"Error requesting file: {e}")
    
    def send_file_chunk(self, recipient_id, file_id, chunk_data):
        """Send file chunk to recipient (internal use)"""
        self.send_tcp_message({
            'type': 'file_chunk',
            'recipient_id': recipient_id,
            'file_id': file_id,
            'data': chunk_data
        })
    
    def send_file_end(self, recipient_id, file_id):
        """Send file transfer completion"""
        self.send_tcp_message({
            'type': 'file_end',
            'recipient_id': recipient_id,
            'file_id': file_id
        })
    
    def cancel_file_transfer(self, file_id):
        """Cancel an ongoing file transfer"""
        with self.file_lock:
            # Cancel receiving
            if file_id in self.receiving_files:
                file_info = self.receiving_files[file_id]
                file_info['file'].close()
                del self.receiving_files[file_id]
            
            # Cancel sending
            if file_id in self.pending_files:
                del self.pending_files[file_id]
        
    def disconnect(self):
        """Clean disconnect with proper cleanup"""
        if not self.running:
            return
        
        self.logger.info('Disconnecting from server...')
        self.running = False
        self.connected = False
        
        # Close all file handles
        with self.file_lock:
            for file_info in self.receiving_files.values():
                try:
                    file_info['file'].close()
                except:
                    pass
            self.receiving_files.clear()
            self.pending_files.clear()
        
        # Wait for threads to finish
        if self.tcp_thread and self.tcp_thread.is_alive():
            self.tcp_thread.join(timeout=1.0)
        if self.udp_thread and self.udp_thread.is_alive():
            self.udp_thread.join(timeout=1.0)
        
        # Close sockets
        if self.tcp_socket:
            try:
                self.tcp_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.tcp_socket.close()
            except:
                pass
                
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
        
        self.logger.info('='*80)
        self.logger.info('Client disconnected successfully')
        self.logger.info('Session ended')
        self.logger.info('='*80)

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    client = OptimizedConferenceClient()
    window = EnhancedMainWindow(client)
    client.set_ui(window)
    
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()