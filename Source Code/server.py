"""
===================================================================================
MULTI-USER VIDEO CONFERENCING SERVER - SERVER.PY
===================================================================================
This is the central server application that manages all network communications
between multiple clients in a video conferencing session.

CORE FUNCTIONALITY:
1. Multi-User Video Conferencing - Receives and broadcasts video streams (UDP)
2. Multi-User Audio Conferencing - Mixes and broadcasts audio streams (UDP)
3. Slide & Screen Sharing - Relays screen/slide content (TCP)
4. Group Text Chat - Broadcasts text messages (TCP)
5. File Sharing - Manages file transfers between clients (TCP)

NETWORK ARCHITECTURE:
- Uses CLIENT-SERVER architecture
- TCP/IP sockets for reliable communication (chat, files, control messages)
- UDP sockets for real-time media streaming (audio, video)
- Operates over LAN without internet connectivity requirement

PROTOCOLS USED:
- TCP (Transmission Control Protocol): For reliable, ordered delivery of:
  * Control messages (join/leave, mute/unmute)
  * Chat messages
  * File transfers
  * Screen sharing frames
- UDP (User Datagram Protocol): For low-latency, real-time streaming of:
  * Video frames
  * Audio packets
===================================================================================
"""

# Import required libraries for network programming and data handling
import socket          # For TCP/UDP socket programming
import threading       # For concurrent handling of multiple clients
import struct          # For packing/unpacking binary data in network packets
import time            # For timestamps and timing operations
import json            # For serializing/deserializing messages
import numpy as np     # For efficient audio mixing operations
import random          # For generating meeting codes
import string          # For meeting code character set
import os              # For file system operations
import subprocess      # For system operations
import logging         # For session logging
from datetime import datetime  # For timestamps
from typing import Dict, Set, Optional  # For type hints
from collections import deque  # For efficient queue operations
from pathlib import Path  # For file path handling

# Try to import msgpack for efficient binary serialization (fallback to JSON)
try:
    import msgpack
    # Force JSON for compatibility - can be changed back later
    USE_MSGPACK = False  # Temporarily disabled for debugging
    print("📝 Using JSON protocol for better compatibility")
except ImportError:
    print("⚠️  msgpack not available, falling back to JSON")
    USE_MSGPACK = False

# Try to import uvloop for better async performance (optional optimization)
try:
    import uvloop
    import asyncio
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    USE_ASYNCIO = True
    print("✅ Using uvloop for better performance")
except ImportError:
    print("⚠️  uvloop not available, using threading model")
    USE_ASYNCIO = False

"""
===================================================================================
DATA STRUCTURES FOR SESSION MANAGEMENT
===================================================================================
"""

class Meeting:
    """
    Represents a single meeting/conference session.
    
    PURPOSE: Manages all participants and state for one meeting room
    
    ATTRIBUTES:
    - code: Unique 6-character meeting identifier
    - host_id: Client ID of the meeting host (has admin privileges)
    - participants: Dictionary of all connected participants
    - created_at: Timestamp when meeting was created
    - audio_buffers: Temporary storage for audio mixing (UDP audio data)
    - muted_participants: Set of client IDs that are muted by host
    - locked_mics: Set of client IDs whose mics are locked by host
    - current_presenter: Client ID of user currently screen sharing (only one at a time)
    """
    def __init__(self, code, host_id):
        self.code = code
        self.host_id = host_id
        self.participants = {}
        self.created_at = datetime.now()
        self.audio_buffers = {}  # For audio mixing functionality
        self.muted_participants = set()
        self.locked_mics = set()
        self.current_presenter = None  # Track who is currently screen sharing

class ClientInfo:
    """
    Stores information about a connected client.
    
    PURPOSE: Maintains connection state and metadata for each client
    
    ATTRIBUTES:
    - socket: TCP socket connection for reliable messaging
    - username: Display name of the user
    - meeting_code: Which meeting this client belongs to
    - is_host: Whether this client has host privileges
    - udp_address: (IP, port) tuple for UDP streaming (video/audio)
    - last_seen: Timestamp of last activity (for connection monitoring)
    """
    def __init__(self, socket_conn, username, meeting_code, is_host):
        self.socket = socket_conn  # TCP socket for control messages
        self.username = username
        self.meeting_code = meeting_code
        self.is_host = is_host
        self.udp_address = None  # Will be set when UDP packets arrive
        self.last_seen = time.time()

"""
===================================================================================
MAIN SERVER CLASS
===================================================================================
"""

class OptimizedConferenceServer:
    """
    Main server class that handles all client connections and data relay.
    
    NETWORK PROTOCOLS:
    - TCP (port 5001 by default): For reliable control messages, chat, files
    - UDP (port 5002 by default): For real-time audio/video streaming
    
    ARCHITECTURE:
    - Multi-threaded design for concurrent client handling
    - Separate threads for TCP connections and UDP streaming
    - Thread-safe data structures with locks for concurrent access
    """
    
    def __init__(self, host='0.0.0.0', tcp_port=5001):
        """
        Initialize the conference server.
        
        PARAMETERS:
        - host: IP address to bind to (0.0.0.0 allows connections from any network interface)
        - tcp_port: Port for TCP connections (UDP will use tcp_port + 1)
        
        NETWORK SETUP:
        - Creates TCP socket for reliable messaging
        - Creates UDP socket for real-time media streaming
        """
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = tcp_port + 1  # UDP port is always TCP port + 1
        
        # Data structures for managing meetings and clients
        self.meetings: Dict[str, Meeting] = {}  # meeting_code -> Meeting object
        self.client_to_meeting: Dict[str, str] = {}  # client_id -> meeting_code
        self.clients: Dict[str, ClientInfo] = {}  # client_id -> ClientInfo object
        
        # Thread locks for concurrent access safety
        self.clients_lock = threading.Lock()  # Protects clients dictionary
        self.meetings_lock = threading.Lock()  # Protects meetings dictionary
        
        # Network sockets (will be initialized in start())
        self.tcp_socket = None  # TCP socket for reliable communication
        self.udp_socket = None  # UDP socket for real-time streaming
        
        # Pre-allocated buffers for performance optimization
        # Reason: Reusing buffers reduces memory allocation overhead
        self.udp_send_buffer = bytearray(65536)  # 64KB buffer for UDP packets
        self.audio_mix_buffer = np.zeros(8000, dtype=np.float32)  # Audio mixing buffer
        
        self.running = False  # Server running state
        
        # Performance monitoring statistics
        self.stats = {
            'messages_processed': 0,  # Count of TCP messages handled
            'audio_packets': 0,  # Count of UDP audio packets
            'video_packets': 0,  # Count of UDP video packets
            'start_time': time.time()
        }
        
        # Setup logging system for session tracking
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging system with session-based log files"""
        # Create logs directory structure
        log_dir = Path('logs/server')
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
        
        self.logger = logging.getLogger('SERVER')
        self.logger.info('='*80)
        self.logger.info(f'Server Session Started')
        self.logger.info(f'Date: {session_time.strftime("%A, %B %d, %Y")}')
        self.logger.info(f'Time: {session_time.strftime("%I:%M:%S %p")}')
        self.logger.info(f'Log File: {log_path}')
        self.logger.info('='*80)
    
    def generate_meeting_code(self) -> str:
        """Generate meeting code using faster method"""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choices(chars, k=6))
            if code not in self.meetings:
                self.logger.info(f'Generated meeting code: {code}')
                return code
    
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
    
    def find_available_port(self, start_port):
        """Find an available port starting from start_port"""
        for port in range(start_port, start_port + 100):
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_socket.bind((self.host, port))
                test_socket.close()
                return port
            except OSError:
                continue
        raise OSError("No available ports found")
    
    def start(self):
        """
        Start the conference server and initialize network sockets.
        
        NETWORK PROTOCOL SETUP:
        This method creates and binds both TCP and UDP sockets for the server.
        
        TCP SOCKET (Transmission Control Protocol):
        - Purpose: Reliable, ordered delivery of control messages, chat, and files
        - Socket Type: SOCK_STREAM (connection-oriented)
        - Port: self.tcp_port (default 5001)
        - Why TCP: Guarantees message delivery and order, essential for:
          * Meeting join/leave notifications
          * Chat messages (no message loss acceptable)
          * File transfers (data integrity critical)
          * Control commands (mute, video state, etc.)
        
        UDP SOCKET (User Datagram Protocol):
        - Purpose: Low-latency streaming of audio and video
        - Socket Type: SOCK_DGRAM (connectionless)
        - Port: self.tcp_port + 1 (default 5002)
        - Why UDP: Minimal latency for real-time media, acceptable packet loss
          * Video frames (minor loss not noticeable)
          * Audio packets (human ear tolerates small gaps)
          * No connection overhead or retransmission delays
        
        SOCKET OPTIONS:
        - SO_REUSEADDR: Allows immediate port reuse after server restart
        """
        self.logger.info('Starting server initialization...')
        
        # ============================================================================
        # TCP SOCKET INITIALIZATION (Reliable Communication)
        # ============================================================================
        # Try to bind to the specified ports, if they're in use, find available ones
        try:
            # Create TCP socket: AF_INET = IPv4, SOCK_STREAM = TCP
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # SO_REUSEADDR allows the socket to bind to a port that's in TIME_WAIT state
            # This is useful for quick server restarts without waiting for port release
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind TCP socket to the specified host and port
            # This reserves the port for incoming TCP connections
            self.tcp_socket.bind((self.host, self.tcp_port))
            self.logger.info(f'TCP socket bound to {self.host}:{self.tcp_port}')
        except OSError as e:
            if e.errno == 48:  # Address already in use
                self.logger.warning(f'Port {self.tcp_port} already in use, finding available port...')
                print(f"⚠️  Port {self.tcp_port} is already in use, finding available port...")
                self.tcp_port = self.find_available_port(self.tcp_port)
                self.tcp_socket.close()
                self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.tcp_socket.bind((self.host, self.tcp_port))
                self.logger.info(f'TCP socket bound to alternate port {self.host}:{self.tcp_port}')
            else:
                self.logger.error(f'Failed to bind TCP socket: {e}')
                raise
        
        # ============================================================================
        # UDP SOCKET INITIALIZATION (Real-Time Media Streaming)
        # ============================================================================
        try:
            # Create UDP socket: AF_INET = IPv4, SOCK_DGRAM = UDP
            # UDP is connectionless - no handshake, just send/receive packets
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # SO_REUSEADDR for UDP allows multiple processes to bind to same port
            # Useful for server restart scenarios
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind UDP socket to port (TCP port + 1)
            # Convention: UDP port is always one more than TCP port
            self.udp_socket.bind((self.host, self.tcp_port + 1))
            self.udp_port = self.tcp_port + 1
            self.logger.info(f'UDP socket bound to {self.host}:{self.udp_port}')
        except OSError as e:
            if e.errno == 48:  # Address already in use
                self.logger.warning(f'UDP port {self.tcp_port + 1} already in use, finding available port...')
                print(f"⚠️  UDP port {self.tcp_port + 1} is already in use, finding available port...")
                self.udp_port = self.find_available_port(self.tcp_port + 1)
                self.udp_socket.close()
                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.udp_socket.bind((self.host, self.udp_port))
                self.logger.info(f'UDP socket bound to alternate port {self.host}:{self.udp_port}')
            else:
                self.logger.error(f'Failed to bind UDP socket: {e}')
                raise
        
        # ============================================================================
        # TCP LISTEN MODE (Accept Incoming Connections)
        # ============================================================================
        # Put TCP socket in listening mode with backlog of 10 connections
        # This allows the server to queue up to 10 pending connections
        self.tcp_socket.listen(10)
        self.running = True
        
        self.logger.info('='*80)
        self.logger.info('🚀 Server Started Successfully!')
        self.logger.info(f'📡 TCP: {self.host}:{self.tcp_port}')
        self.logger.info(f'📡 UDP: {self.host}:{self.udp_port}')
        self.logger.info('Waiting for client connections...')
        self.logger.info('='*80)
        
        print(f"🚀 Optimized Server started!")
        print(f"📡 TCP: {self.host}:{self.tcp_port}")
        print(f"📡 UDP: {self.host}:{self.udp_port}")
        
        # ============================================================================
        # START BACKGROUND THREADS (Concurrent Processing)
        # ============================================================================
        # Multi-threading allows the server to handle multiple operations simultaneously:
        # 1. Accept new TCP connections
        # 2. Process UDP packets (audio/video)
        # 3. Display performance statistics
        # 4. Clean up stale data
        self.logger.info('Starting background threads...')
        
        # Thread 1: Accept incoming TCP connections (control messages, chat, files)
        threading.Thread(target=self.accept_connections, daemon=True).start()
        
        # Thread 2: Handle UDP packets (real-time audio/video streaming)
        threading.Thread(target=self.handle_udp_streams, daemon=True).start()
        
        # Thread 3: Display server statistics periodically
        threading.Thread(target=self.display_stats, daemon=True).start()
        
        # Thread 4: Clean up old audio buffers to prevent memory bloat
        threading.Thread(target=self.cleanup_stale_buffers, daemon=True).start()
        
        self.logger.info('All background threads started')
    
    def cleanup_stale_buffers(self):
        """Remove old audio buffers to prevent memory bloat"""
        while self.running:
            time.sleep(1.0)
            current_time = time.time()
            with self.meetings_lock:
                for meeting in self.meetings.values():
                    stale_keys = [
                        k for k, v in meeting.audio_buffers.items()
                        if current_time - v['timestamp'] > 0.5
                    ]
                    for k in stale_keys:
                        del meeting.audio_buffers[k]
    
    def display_stats(self):
        """Display performance statistics"""
        while self.running:
            time.sleep(10)
            try:
                elapsed = time.time() - self.stats['start_time']
                msgs_per_sec = self.stats['messages_processed'] / elapsed if elapsed > 0 else 0
                audio_per_sec = self.stats['audio_packets'] / elapsed if elapsed > 0 else 0
                video_per_sec = self.stats['video_packets'] / elapsed if elapsed > 0 else 0
                
                with self.meetings_lock, self.clients_lock:
                    print("-" * 60)
                    print(f"📊 STATS [{datetime.now().strftime('%H:%M:%S')}]")
                    print(f"  Meetings: {len(self.meetings)} | Clients: {len(self.clients)}")
                    print(f"  Msgs/s: {msgs_per_sec:.1f} | Audio/s: {audio_per_sec:.1f} | Video/s: {video_per_sec:.1f}")
                    print("-" * 60)
            except Exception as e:
                print(f"Error displaying stats: {e}")
    
    def accept_connections(self):
        """
        Accept incoming TCP connections from clients.
        
        PROTOCOL: TCP (Transmission Control Protocol)
        PURPOSE: Establish reliable connections for control messages, chat, and file transfers
        
        PROCESS:
        1. Wait for incoming connection on TCP socket (blocking call)
        2. Accept connection, get client socket and address
        3. Spawn new thread to handle this client independently
        4. Return to waiting for next connection
        
        WHY THREADING:
        - Each client needs independent handling
        - Blocking operations (recv) shouldn't block other clients
        - Allows concurrent communication with multiple clients
        """
        while self.running:
            try:
                # TCP accept() blocks until a client connects
                # Returns: (client_socket, (client_ip, client_port))
                client_socket, address = self.tcp_socket.accept()
                
                # Spawn a new thread to handle this client's TCP messages
                # daemon=True means thread will exit when main program exits
                threading.Thread(target=self.handle_client, args=(client_socket, address), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"❌ Error accepting connection: {e}")
    
    def handle_udp_streams(self):
        """
        Handle incoming UDP packets for audio and video streaming.
        
        PROTOCOL: UDP (User Datagram Protocol)
        PURPOSE: Receive real-time audio/video packets with minimal latency
        
        PACKET STRUCTURE:
        [Stream Type (1 byte)][Client ID Length (2 bytes)][Client ID][Media Data]
        
        Stream Types:
        - 'V': Video frame data (JPEG compressed)
        - 'A': Audio packet data (PCM format)
        - 'I': Initialization packet (establishes UDP address)
        
        WHY UDP:
        - No connection overhead (connectionless protocol)
        - No retransmission delays (lost packets are skipped)
        - Lower latency than TCP (critical for real-time media)
        - Acceptable packet loss (human perception tolerates minor glitches)
        
        TIMEOUT:
        - 0.1 second timeout prevents blocking indefinitely
        - Allows checking self.running flag periodically
        """
        # Set socket timeout to prevent indefinite blocking
        self.udp_socket.settimeout(0.1)
        
        while self.running:
            try:
                # UDP recvfrom() receives one packet (up to 65535 bytes)
                # Returns: (data, (sender_ip, sender_port))
                # Note: UDP has no connection, just receives packets from any source
                data, addr = self.udp_socket.recvfrom(65535)
                
                # Process the received UDP packet (video or audio)
                self.handle_udp_packet(data, addr)
            except socket.timeout:
                # Timeout is normal, just continue loop to check self.running
                continue
            except Exception as e:
                if self.running:
                    print(f"UDP error: {e}")
                time.sleep(0.01)
    
    def handle_client(self, client_socket, address):
        """Handle TCP client connection"""
        client_id = None
        meeting_code = None
        
        try:
            # Read initial message
            data = client_socket.recv(4096)
            if not data:
                print(f"No data received from {address}")
                client_socket.close()
                return
            
            print(f"Received {len(data)} bytes from {address}: {data[:100]}...")
            
            try:
                message = self._deserialize_message(data)
                print(f"Parsed message: {message}")
            except Exception as e:
                print(f"Failed to deserialize message from {address}: {e}")
                print(f"Raw data: {data}")
                error_response = self._serialize_message({
                    'type': 'error',
                    'message': 'Invalid message format'
                })
                client_socket.send(error_response)
                client_socket.close()
                return
            
            if message['type'] == 'create_meeting':
                client_id = f"{message['username']}_{address[0]}_{address[1]}"
                meeting_code = self.generate_meeting_code()
                
                self.logger.info(f'Creating meeting: {meeting_code} for {message["username"]} (ID: {client_id})')
                
                # Create meeting and client
                with self.meetings_lock:
                    meeting = Meeting(meeting_code, client_id)
                    meeting.participants[client_id] = {
                        'username': message['username'], 
                        'is_host': True
                    }
                    self.meetings[meeting_code] = meeting
                    self.client_to_meeting[client_id] = meeting_code
                
                self.logger.info(f'Meeting {meeting_code} created successfully with host {message["username"]}')
                
                with self.clients_lock:
                    client_info = ClientInfo(client_socket, message['username'], meeting_code, True)
                    self.clients[client_id] = client_info
                
                response_data = self._serialize_message({
                    'type': 'meeting_created',
                    'meeting_code': meeting_code,
                    'client_id': client_id,
                    'is_host': True
                })
                print(f"Sending meeting_created response: {len(response_data)} bytes")
                client_socket.send(response_data)
                
            elif message['type'] == 'join_meeting':
                meeting_code = message.get('meeting_code', '').upper()
                
                self.logger.info(f'{message["username"]} attempting to join meeting: {meeting_code}')
                
                with self.meetings_lock:
                    if meeting_code not in self.meetings:
                        self.logger.warning(f'Invalid meeting code: {meeting_code}')
                        response_data = self._serialize_message({
                            'type': 'error',
                            'message': 'Invalid meeting code'
                        })
                        print(f"Sending error response: {len(response_data)} bytes")
                        client_socket.send(response_data)
                        client_socket.close()
                        return
                    
                    client_id = f"{message['username']}_{address[0]}_{address[1]}"
                    meeting = self.meetings[meeting_code]
                    meeting.participants[client_id] = {
                        'username': message['username'],
                        'is_host': False
                    }
                    self.client_to_meeting[client_id] = meeting_code
                    
                    self.logger.info(f'{message["username"]} (ID: {client_id}) joined meeting {meeting_code}')
                
                with self.clients_lock:
                    client_info = ClientInfo(client_socket, message['username'], meeting_code, False)
                    self.clients[client_id] = client_info
                
                # Get participants list
                with self.meetings_lock:
                    participants = [
                        {
                            'client_id': pid,
                            'username': pinfo['username'],
                            'is_host': pinfo['is_host']
                        }
                        for pid, pinfo in self.meetings[meeting_code].participants.items()
                    ]
                
                response_data = self._serialize_message({
                    'type': 'join_success',
                    'meeting_code': meeting_code,
                    'client_id': client_id,
                    'is_host': False,
                    'participants': participants
                })
                print(f"Sending join_success response: {len(response_data)} bytes")
                client_socket.send(response_data)
                
                # Notify others
                self.broadcast_to_meeting(
                    meeting_code,
                    {
                        'type': 'user_joined',
                        'client_id': client_id,
                        'username': message['username']
                    },
                    exclude_id=client_id
                )
            
            # Message loop
            while self.running and client_id:
                try:
                    length_bytes = client_socket.recv(4)
                    if not length_bytes:
                        break
                    msg_length = struct.unpack('!I', length_bytes)[0]
                    
                    if msg_length > 10485760:  # 10MB limit
                        break
                    
                    data = b''
                    while len(data) < msg_length:
                        chunk = client_socket.recv(min(4096, msg_length - len(data)))
                        if not chunk:
                            break
                        data += chunk
                    
                    if len(data) == msg_length:
                        message = self._deserialize_message(data)
                        self.stats['messages_processed'] += 1
                        self.handle_tcp_message(client_id, message)
                except Exception:
                    break
                
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            if client_id:
                self.handle_client_disconnect(client_id)
            client_socket.close()
    
    def handle_client_disconnect(self, client_id: str):
        """Handle client disconnection efficiently"""
        with self.clients_lock:
            client_info = self.clients.pop(client_id, None)
        if not client_info:
            return
        
        meeting_code = client_info.meeting_code
        username = client_info.username
        is_host = client_info.is_host
        new_host_id = None
        
        with self.meetings_lock:
            meeting = self.meetings.get(meeting_code)
            if meeting:
                meeting.participants.pop(client_id, None)
                self.client_to_meeting.pop(client_id, None)
                meeting.audio_buffers.pop(client_id, None)
                
                # Clear presenter if this client was presenting
                if meeting.current_presenter == client_id:
                    meeting.current_presenter = None
                    self.broadcast_to_meeting(
                        meeting_code,
                        {'type': 'screen_share_stopped', 'presenter_id': client_id}
                    )
                
                # Transfer host if needed
                if is_host and meeting.participants:
                    new_host_id = next(iter(meeting.participants))
                    meeting.host_id = new_host_id
                    meeting.participants[new_host_id]['is_host'] = True
                    
                    with self.clients_lock:
                        if new_host_id in self.clients:
                            self.clients[new_host_id].is_host = True
                elif not meeting.participants:
                    del self.meetings[meeting_code]
                    return
        
        if new_host_id:
            self.broadcast_to_meeting(
                meeting_code,
                {'type': 'host_changed', 'new_host_id': new_host_id}
            )
        
        self.broadcast_to_meeting(
            meeting_code,
            {
                'type': 'user_left',
                'client_id': client_id,
                'username': username
            }
        )
    
    def handle_tcp_message(self, client_id: str, message: dict):
        """Handle TCP messages efficiently"""
        msg_type = message.get('type')
        
        with self.clients_lock:
            client_info = self.clients.get(client_id)
        if not client_info:
            return
        
        meeting_code = client_info.meeting_code
        is_host = client_info.is_host
        
        if msg_type == 'chat':
            self.broadcast_to_meeting(
                meeting_code,
                {
                    'type': 'chat',
                    'client_id': client_id,
                    'username': client_info.username,
                    'message': message['message']
                },
                exclude_id=client_id
            )
        
        elif msg_type == 'video_state':
            state = message.get('state')
            
            # If video stopped and this client was presenting, clear presenter
            meeting = self.meetings.get(meeting_code)
            if meeting and state == 'stopped' and meeting.current_presenter == client_id:
                meeting.current_presenter = None
                self.broadcast_to_meeting(
                    meeting_code,
                    {'type': 'screen_share_stopped', 'presenter_id': client_id}
                )
            
            self.broadcast_to_meeting(
                meeting_code,
                {
                    'type': 'participant_video_state',
                    'client_id': client_id,
                    'state': state
                },
                exclude_id=client_id
            )
        
        elif msg_type == 'raise_hand':
            self.broadcast_to_meeting(
                meeting_code,
                {
                    'type': 'participant_hand_state',
                    'client_id': client_id,
                    'username': client_info.username,
                    'state': message.get('state', False)
                }
            )
        
        elif msg_type == 'emoji_reaction':
            emoji = message.get('emoji')
            if emoji:
                self.broadcast_to_meeting(
                    meeting_code,
                    {
                        'type': 'emoji_reaction',
                        'client_id': client_id,
                        'username': client_info.username,
                        'emoji': emoji
                    }
                )
        
        elif msg_type == 'file_offer':
            self.logger.info(f'File offer from {client_info.username}: {message.get("filename", "unknown")} ({message.get("filesize", 0)} bytes)')
            self.broadcast_to_meeting(meeting_code, {'type': 'file_offer','sender_id': client_id, 'username': client_info.username, **message}, exclude_id=client_id)
        elif msg_type == 'file_request':
            sender_id = message.get('sender_id')
            file_id = message.get('file_id')
            self.logger.info(f'File request from {client_info.username} to {sender_id} for file {file_id}')
            self.send_to_client(sender_id, {'type': 'file_request', 'downloader_id': client_id, 'username': client_info.username, 'file_id': file_id})
        elif msg_type in ['file_chunk', 'file_end']:
            recipient_id = message.get('recipient_id')
            if msg_type == 'file_chunk':
                self.logger.debug(f'File chunk from {client_info.username} to {recipient_id}')
            else:
                self.logger.info(f'File transfer complete from {client_info.username} to {recipient_id}')
            self.send_to_client(recipient_id, {'sender_id': client_id, **message})
        
        elif is_host:
            self.handle_host_command(client_id, meeting_code, msg_type, message)
    
    def handle_host_command(self, client_id: str, meeting_code: str, 
                           msg_type: str, message: dict):
        """Handle host-specific commands"""
        with self.meetings_lock:
            meeting = self.meetings.get(meeting_code)
        if not meeting:
            return
        
        if msg_type in ['mute_participant', 'unmute_participant']:
            target_id = message.get('target_client_id')
            with self.meetings_lock:
                if msg_type == 'mute_participant':
                    meeting.muted_participants.add(target_id)
                else:
                    meeting.muted_participants.discard(target_id)
            
            self.send_to_client(
                target_id,
                {'type': 'muted_by_host' if msg_type == 'mute_participant' else 'unmuted_by_host'}
            )
            self.broadcast_to_meeting(
                meeting_code,
                {
                    'type': 'participant_muted' if msg_type == 'mute_participant' else 'participant_unmuted',
                    'client_id': target_id
                }
            )
        
        elif msg_type in ['lock_mic', 'unlock_mic']:
            target_id = message.get('target_client_id')
            with self.meetings_lock:
                if msg_type == 'lock_mic':
                    meeting.locked_mics.add(target_id)
                else:
                    meeting.locked_mics.discard(target_id)
            
            self.send_to_client(
                target_id,
                {'type': 'mic_locked' if msg_type == 'lock_mic' else 'mic_unlocked'}
            )
            self.broadcast_to_meeting(
                meeting_code,
                {
                    'type': 'participant_mic_locked' if msg_type == 'lock_mic' else 'participant_mic_unlocked',
                    'client_id': target_id
                }
            )
        
        elif msg_type == 'request_video':
            self.send_to_client(
                message.get('target_client_id'),
                {'type': 'request_video'}
            )
        
        elif msg_type == 'request_all_video':
            self.broadcast_to_meeting(
                meeting_code,
                {'type': 'request_all_video'},
                exclude_id=client_id
            )
        
        elif msg_type == 'request_unmute':
            self.send_to_client(
                message.get('target_client_id'),
                {'type': 'request_unmute'}
            )
        
        elif msg_type == 'request_all_unmute':
            self.broadcast_to_meeting(
                meeting_code,
                {'type': 'request_all_unmute'},
                exclude_id=client_id
            )
        
        elif msg_type == 'request_screen_share':
            # Handle screen share request from client
            if 'target_client_id' in message:
                # Host requesting screen share from specific client
                target_id = message.get('target_client_id')
                if target_id:
                    self.send_to_client(
                        target_id,
                        {'type': 'request_screen_share'}
                    )
            else:
                # Client requesting to start screen sharing
                meeting = self.meetings.get(meeting_code)
                if meeting:
                    if meeting.current_presenter and meeting.current_presenter != client_id:
                        # Someone else is already presenting
                        self.send_to_client(
                            client_id,
                            {'type': 'screen_share_denied', 'current_presenter': meeting.current_presenter}
                        )
                    else:
                        # Allow screen sharing
                        meeting.current_presenter = client_id
                        self.broadcast_to_meeting(
                            meeting_code,
                            {'type': 'screen_share_started', 'presenter_id': client_id},
                            exclude_id=client_id
                        )
        
        elif msg_type == 'stop_screen_share':
            # Handle screen share stop request
            meeting = self.meetings.get(meeting_code)
            if meeting and meeting.current_presenter == client_id:
                meeting.current_presenter = None
                self.broadcast_to_meeting(
                    meeting_code,
                    {'type': 'screen_share_stopped', 'presenter_id': client_id},
                    exclude_id=client_id
                )
        
        elif msg_type == 'screen_frame':
            # Handle screen frame from presenter
            meeting = self.meetings.get(meeting_code)
            if meeting and meeting.current_presenter == client_id:
                frame_data = message.get('frame_data')
                if frame_data:
                    self.logger.debug(f"Broadcasting screen frame from {client_id} to meeting {meeting_code}")
                    # Broadcast screen frame to all other participants via TCP
                    self.broadcast_to_meeting(
                        meeting_code,
                        {
                            'type': 'screen_frame',
                            'presenter_id': client_id,
                            'frame_data': frame_data
                        },
                        exclude_id=client_id
                    )
                else:
                    self.logger.warning(f"Received screen frame from {client_id} with no frame data")
            else:
                self.logger.warning(f"Received screen frame from {client_id} but they are not the current presenter")
    
    def handle_udp_packet(self, data: bytes, addr: tuple):
        """Handle UDP packets with improved error handling"""
        if len(data) < 3:
            return
        
        try:
            stream_type = chr(data[0])
            client_id_len = struct.unpack('!H', data[1:3])[0]
            
            if 3 + client_id_len > len(data) or client_id_len > 255:
                return
            
            client_id = data[3:3+client_id_len].decode('utf-8')
            stream_data = data[3+client_id_len:]
            
            # Update UDP address
            with self.clients_lock:
                client_info = self.clients.get(client_id)
                if client_info:
                    if client_info.udp_address is None:
                        client_info.udp_address = addr
                    client_info.last_seen = time.time()
            
            meeting_code = self.client_to_meeting.get(client_id)
            if not meeting_code:
                return
            
            # Handle different stream types
            if stream_type == 'V' and len(stream_data) > 0:
                self.stats['video_packets'] += 1
                self.broadcast_udp_to_meeting(
                    meeting_code, 'V', client_id, stream_data, exclude_id=client_id
                )
            elif stream_type == 'A' and len(stream_data) > 0:
                self.stats['audio_packets'] += 1
                self.mix_and_broadcast_audio(meeting_code, client_id, stream_data)
            elif stream_type == 'I':
                # Initialization packet - just update address
                pass
                
        except (struct.error, UnicodeDecodeError, ValueError) as e:
            print(f"UDP packet decode error: {e}")
            return
    
    def mix_and_broadcast_audio(self, meeting_code: str, sender_id: str, audio_data: bytes):
        """Improved audio mixing with better error handling"""
        with self.meetings_lock:
            meeting = self.meetings.get(meeting_code)
        if not meeting:
            return
        
        # Validate audio data
        if len(audio_data) == 0 or len(audio_data) % 2 != 0:
            return
        
        # Parse and store audio buffer
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            if len(audio_array) == 0:
                return
                
            with self.meetings_lock:
                meeting.audio_buffers[sender_id] = {
                    'data': audio_array,
                    'timestamp': time.time()
                }
        except (ValueError, TypeError) as e:
            print(f"Audio buffer error: {e}")
            return
        
        with self.meetings_lock:
            participants = list(meeting.participants.keys())
        if len(participants) < 2:
            return
        
        current_time = time.time()
        target_len = len(audio_array)
        
        # Pre-filter valid sources with better validation
        valid_buffers = {}
        with self.meetings_lock:
            for pid in participants:
                if (pid in meeting.audio_buffers and
                    current_time - meeting.audio_buffers[pid]['timestamp'] < 0.3 and
                    pid not in meeting.muted_participants and
                    pid not in meeting.locked_mics):
                    try:
                        buffer_data = meeting.audio_buffers[pid]['data']
                        if len(buffer_data) > 0:
                            valid_buffers[pid] = buffer_data
                    except (KeyError, TypeError):
                        continue
        
        if not valid_buffers:
            return
        
        # Get recipient addresses with lock
        recipient_addrs = {}
        with self.clients_lock:
            for rid in participants:
                if (rid != sender_id and
                    rid in self.clients and
                    self.clients[rid].udp_address):
                    recipient_addrs[rid] = self.clients[rid].udp_address
        
        if not recipient_addrs:
            return
        
        # Mix audio for each recipient
        for recipient_id, addr in recipient_addrs.items():
            sources = [
                sid for sid in valid_buffers
                if sid != recipient_id
            ]
            
            if not sources:
                continue
            
            try:
                # Vectorized audio mixing with bounds checking
                if len(self.audio_mix_buffer) < target_len:
                    self.audio_mix_buffer = np.zeros(target_len, dtype=np.float32)
                else:
                    self.audio_mix_buffer[:target_len] = 0
                
                for source_id in sources:
                    source_audio = valid_buffers[source_id]
                    add_len = min(target_len, len(source_audio))
                    if add_len > 0:
                        self.audio_mix_buffer[:add_len] += source_audio[:add_len].astype(np.float32)
                
                # Clip and convert with volume normalization
                if len(sources) > 1:
                    # Normalize volume when mixing multiple sources
                    self.audio_mix_buffer[:target_len] /= len(sources)
                
                mixed = np.clip(
                    self.audio_mix_buffer[:target_len],
                    -32768, 32767
                ).astype(np.int16)
                
                # Send with header
                packet = b'A\x00\x00' + mixed.tobytes()
                self.udp_socket.sendto(packet, addr)
                
            except Exception as e:
                print(f"Audio mixing error for {recipient_id}: {e}")
                continue
    
    def broadcast_udp_to_meeting(self, meeting_code: str, stream_type: str,
                                 sender_id: str, data: bytes, exclude_id: Optional[str] = None):
        """Broadcast UDP with zero-copy"""
        sender_id_bytes = sender_id.encode('utf-8')
        sender_len = len(sender_id_bytes)
        
        # Build packet once
        packet_size = 1 + 2 + sender_len + len(data)
        if packet_size > len(self.udp_send_buffer):
            packet = bytearray(packet_size)
        else:
            packet = self.udp_send_buffer[:packet_size]
        
        packet[0] = ord(stream_type)
        struct.pack_into('!H', packet, 1, sender_len)
        packet[3:3+sender_len] = sender_id_bytes
        packet[3+sender_len:] = data
        
        # Send to all recipients
        clients_to_send = []
        with self.clients_lock:
            for cid, cinfo in self.clients.items():
                if (cid != exclude_id and
                    cinfo.meeting_code == meeting_code and
                    cinfo.udp_address):
                    clients_to_send.append(cinfo.udp_address)
        
        for addr in clients_to_send:
            try:
                self.udp_socket.sendto(bytes(packet), addr)
            except:
                pass
    
    def broadcast_to_meeting(self, meeting_code: str, message: dict,
                            exclude_id: Optional[str] = None):
        """Broadcast TCP message to meeting"""
        data = self._serialize_message(message)
        length = struct.pack('!I', len(data))
        packet = length + data
        
        # Collect sockets
        sockets_to_send = []
        with self.clients_lock:
            for cid, cinfo in self.clients.items():
                if (cid != exclude_id and
                    cinfo.meeting_code == meeting_code):
                    sockets_to_send.append(cinfo.socket)
        
        # Send to all
        for sock in sockets_to_send:
            try:
                sock.sendall(packet)
            except:
                pass
    
    def send_to_client(self, client_id: str, message: dict):
        """Send message to specific client"""
        with self.clients_lock:
            client_info = self.clients.get(client_id)
        if not client_info:
            return
        
        data = self._serialize_message(message)
        length = struct.pack('!I', len(data))
        
        try:
            client_info.socket.sendall(length + data)
        except:
            pass

    def stop(self):
        """Stop the server"""
        self.running = False
        
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
        
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
        
        with self.clients_lock:
            for client_id, client_info in self.clients.items():
                try:
                    client_info.socket.close()
                except:
                    pass
            self.clients.clear()

def main():
    server = OptimizedConferenceServer()
    server.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        server.stop()

if __name__ == '__main__':
    main()