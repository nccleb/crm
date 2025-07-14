import socket
import datetime
import os
import sys
import time
import threading
import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class CallInfo:
    """Represents information about an active call."""
    caller_id: str
    caller_name: str
    channel: str
    start_time: float


class AMIConfig:
    """Configuration class for AMI connection and behavior."""
    def __init__(self):
        self.host = '192.168.20.216'
        self.port = 7777
        self.username = 'amiuser1'
        self.password = 'A1A1a1a1'
        self.call_timeout = 60  # seconds
        self.socket_timeout = 30  # seconds - increased for stability
        self.reconnect_delay = 5  # seconds
        self.watchdog_interval = 5  # seconds
        self.keepalive_interval = 60  # seconds - reduced frequency to avoid noise
        self.max_reconnect_attempts = 5  # max consecutive reconnection attempts
        self.backoff_multiplier = 1.5  # exponential backoff for reconnections


class CallerIDMonitor:
    """Main class for monitoring caller ID via AMI."""
    
    def __init__(self, config: AMIConfig):
        self.config = config
        self.output_file = os.path.join(self._get_base_path(), 'callerid.txt')
        self.error_log = os.path.join(self._get_base_path(), 'error.log')
        
        # State management
        self.active_calls: Dict[str, CallInfo] = {}
        self.current_displayed_channel: Optional[str] = None
        self.last_call_time = 0
        self.sock: Optional[socket.socket] = None
        self._running = False
        
        # Connection management
        self._reconnect_attempts = 0
        self._last_keepalive = 0
        self._connection_stable = False
        
        # Setup logging
        self._setup_logging()
        
        # Thread management
        self._watchdog_thread: Optional[threading.Thread] = None
        self._keepalive_thread: Optional[threading.Thread] = None
        
    def _get_base_path(self) -> str:
        """Get the base path for output files."""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.error_log),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Enable debug logging if needed
        if os.environ.get('AMI_DEBUG', '').lower() in ('1', 'true', 'yes'):
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("Debug logging enabled")
    
    @contextmanager
    def _socket_connection(self):
        """Context manager for socket connections."""
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.socket_timeout)
            yield sock
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
    
    def write_caller_info(self, call_info: CallInfo):
        """Write caller information to output file."""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(f"{call_info.caller_id},{timestamp}\n")
            
            self.last_call_time = time.time()
            self.logger.info(f"File updated: {call_info.caller_id} - {call_info.caller_name}")
            
        except IOError as e:
            self.logger.error(f"Failed to write to output file: {e}")
    
    def clear_display(self):
        """Clear the display file and reset state."""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write('')
            
            self.current_displayed_channel = None
            self.active_calls.clear()
            self.logger.info("Display cleared")
            
        except IOError as e:
            self.logger.error(f"Failed to clear display file: {e}")
    
    def _connect_to_ami(self) -> socket.socket:
        """Establish connection to AMI with improved reliability."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Enable TCP keepalive
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        
        # Set socket options for better connection handling
        if hasattr(socket, 'TCP_KEEPIDLE'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
        if hasattr(socket, 'TCP_KEEPINTVL'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        if hasattr(socket, 'TCP_KEEPCNT'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
        
        sock.settimeout(self.config.socket_timeout)
        
        try:
            self.logger.info(f"Connecting to AMI at {self.config.host}:{self.config.port}")
            sock.connect((self.config.host, self.config.port))
            
            # Read the initial banner/greeting
            banner = sock.recv(1024).decode('utf-8', errors='ignore')
            self.logger.info(f"AMI Banner: {banner.strip()}")
            
            # Send login message
            login_msg = (
                f"Action: Login\r\n"
                f"Username: {self.config.username}\r\n"
                f"Secret: {self.config.password}\r\n\r\n"
            )
            sock.sendall(login_msg.encode('utf-8'))
            
            # Wait for login response - may need multiple reads
            response_buffer = ""
            attempts = 0
            max_attempts = 5
            
            while attempts < max_attempts:
                try:
                    response_chunk = sock.recv(1024).decode('utf-8', errors='ignore')
                    if not response_chunk:
                        break
                    
                    response_buffer += response_chunk
                    self.logger.debug(f"Auth response chunk: {response_chunk.strip()}")
                    
                    # Check for complete response (ends with \r\n\r\n)
                    if "\r\n\r\n" in response_buffer:
                        break
                    
                except socket.timeout:
                    attempts += 1
                    self.logger.debug(f"Timeout waiting for auth response (attempt {attempts})")
                    continue
            
            self.logger.debug(f"Full auth response: {response_buffer}")
            
            # Check authentication result
            if ("Authentication accepted" in response_buffer or 
                "Success" in response_buffer or
                "Response: Success" in response_buffer):
                self.logger.info("AMI authentication successful")
                self._connection_stable = True
                self._reconnect_attempts = 0
                self._last_keepalive = time.time()
                return sock
            elif "Authentication failed" in response_buffer or "Error" in response_buffer:
                sock.close()
                raise ConnectionError(f"AMI authentication failed - check username/password: {response_buffer.strip()}")
            else:
                # If we don't get a clear success/failure, log it but continue
                self.logger.warning(f"Unclear authentication response, proceeding: {response_buffer.strip()}")
                self._connection_stable = True
                self._reconnect_attempts = 0
                self._last_keepalive = time.time()
                return sock
            
        except Exception as e:
            sock.close()
            raise ConnectionError(f"Failed to connect to AMI: {e}")
    
    def _parse_ami_event(self, chunk: str) -> Dict[str, str]:
        """Parse AMI event from chunk of data."""
        event = {}
        lines = chunk.split("\r\n")
        
        for line in lines:
            if ": " in line:
                key, val = line.split(": ", 1)
                event[key.strip()] = val.strip()
        
        return event
    
    def _handle_new_caller_id(self, event: Dict[str, str]):
        """Handle NewCallerid event."""
        caller_id = event.get("CallerIDNum", "")
        channel = event.get("Channel", "")
        
        if caller_id and caller_id != "<unknown>" and channel:
            caller_name = event.get("CallerIDName", "")
            call_info = CallInfo(
                caller_id=caller_id,
                caller_name=caller_name,
                channel=channel,
                start_time=time.time()
            )
            
            self.active_calls[channel] = call_info
            self.current_displayed_channel = channel
            self.write_caller_info(call_info)
    
    def _handle_queue_join(self, event: Dict[str, str]):
        """Handle Join/QueueCallerJoin events."""
        caller_id = event.get("CallerIDNum", "")
        channel = event.get("Channel", "")
        
        if caller_id and caller_id != "<unknown>" and channel:
            caller_name = event.get("CallerIDName", "")
            call_info = CallInfo(
                caller_id=caller_id,
                caller_name=caller_name,
                channel=channel,
                start_time=time.time()
            )
            
            self.active_calls[channel] = call_info
            self.current_displayed_channel = channel
            self.write_caller_info(call_info)
            self.logger.info(f"Queue call: {caller_id} joined queue")
    
    def _handle_call_answered(self, event: Dict[str, str]):
        """Handle call answered (Newstate Up) events."""
        channel = event.get("Channel", "")
        state = event.get("ChannelStateDesc", "")
        
        if state == "Up" and channel == self.current_displayed_channel:
            self.logger.info(f"Call answered: {channel}")
            self.clear_display()
    
    def _handle_hangup(self, event: Dict[str, str]):
        """Handle Hangup events."""
        channel = event.get("Channel", "")
        
        if channel in self.active_calls:
            self.logger.info(f"Call hung up: {channel}")
            del self.active_calls[channel]
            
            if channel == self.current_displayed_channel:
                if self.active_calls:
                    # Show the most recent remaining call
                    last_channel = list(self.active_calls.keys())[-1]
                    call_info = self.active_calls[last_channel]
                    self.current_displayed_channel = last_channel
                    self.write_caller_info(call_info)
                else:
                    self.clear_display()
        
        # Handle orphaned Local/ channels
        elif (self.current_displayed_channel and 
              channel.startswith("Local/") and 
              self.current_displayed_channel.startswith("Local/")):
            self.logger.info(f"Local hangup detected: {channel} orphaned. Clearing.")
            self.clear_display()
    
    def _process_ami_event(self, event: Dict[str, str]):
        """Process a single AMI event."""
        event_type = event.get("Event")
        
        if event_type == "NewCallerid":
            self._handle_new_caller_id(event)
        elif event_type in ["Join", "QueueCallerJoin"]:
            self._handle_queue_join(event)
        elif event_type == "Newstate":
            self._handle_call_answered(event)
        elif event_type == "Hangup":
            self._handle_hangup(event)
    
    def _send_keepalive(self):
        """Send periodic ping to keep AMI connection alive."""
        try:
            if self.sock and self._connection_stable:
                ping_msg = "Action: Ping\r\n\r\n"
                self.sock.sendall(ping_msg.encode('utf-8'))
                self._last_keepalive = time.time()
                self.logger.debug("Sent AMI keepalive ping")
        except Exception as e:
            self.logger.warning(f"Failed to send keepalive: {e}")
            self._connection_stable = False
    
    def _keepalive_loop(self):
        """Background thread to send periodic keepalive messages."""
        while self._running:
            time.sleep(self.config.keepalive_interval)
            if self._running and self._connection_stable:
                current_time = time.time()
                # Only send keepalive if we haven't sent one recently
                if current_time - self._last_keepalive >= self.config.keepalive_interval:
                    self._send_keepalive()
    
    def _listen_to_events(self):
        """Main event listening loop with improved timeout handling."""
        buffer = ""
        consecutive_timeouts = 0
        last_activity = time.time()
        
        while self._running:
            try:
                # Use select for better timeout handling
                import select
                ready = select.select([self.sock], [], [], 10.0)  # 10 second timeout
                
                if ready[0]:
                    data = self.sock.recv(4096).decode('utf-8', errors='ignore')  # Larger buffer
                    if not data:
                        raise ConnectionResetError("Empty data from AMI")
                    
                    consecutive_timeouts = 0  # Reset timeout counter on successful read
                    last_activity = time.time()
                    buffer += data
                    
                    # Process complete messages
                    while "\r\n\r\n" in buffer:
                        chunk, buffer = buffer.split("\r\n\r\n", 1)
                        event = self._parse_ami_event(chunk)
                        
                        # Handle pong responses
                        if event.get("Response") == "Pong":
                            self.logger.debug("Received AMI pong")
                            continue
                            
                        self._process_ami_event(event)
                else:
                    # Timeout occurred - this is normal when no calls are active
                    consecutive_timeouts += 1
                    current_time = time.time()
                    
                    # Only log warnings if we haven't had ANY activity for a long time
                    if current_time - last_activity > 300:  # 5 minutes of no activity
                        if consecutive_timeouts % 10 == 0:  # Log every 10th timeout to reduce noise
                            self.logger.warning(f"No AMI activity for {int(current_time - last_activity)}s")
                    
                    # Force reconnection only after extended period of no response
                    if consecutive_timeouts >= 30:  # 5 minutes of timeouts (30 * 10s)
                        self.logger.error("Extended period of no AMI response. Testing connection...")
                        try:
                            self._send_keepalive()
                            # Wait a bit for pong response
                            time.sleep(2)
                        except:
                            self.logger.error("AMI connection appears dead. Reconnecting...")
                            raise socket.timeout("Extended timeout period")
                    
            except (ConnectionResetError, OSError) as e:
                if self._running:
                    self.logger.error(f"AMI connection error: {e}. Reconnecting...")
                    self._connection_stable = False
                    self._reconnect()
                    consecutive_timeouts = 0
                    last_activity = time.time()
            except socket.timeout:
                if self._running:
                    self.logger.info("AMI connection timeout. Reconnecting...")
                    self._connection_stable = False
                    self._reconnect()
                    consecutive_timeouts = 0
                    last_activity = time.time()
    
    def _reconnect(self):
        """Reconnect to AMI with exponential backoff."""
        self._connection_stable = False
        
        try:
            if self.sock:
                self.sock.close()
        except:
            pass
        
        self._reconnect_attempts += 1
        
        if self._reconnect_attempts > self.config.max_reconnect_attempts:
            delay = min(self.config.reconnect_delay * (self.config.backoff_multiplier ** (self._reconnect_attempts - 1)), 60)
            self.logger.warning(f"Multiple reconnection attempts ({self._reconnect_attempts}). Using exponential backoff: {delay:.1f}s")
        else:
            delay = self.config.reconnect_delay
        
        self.logger.info(f"Reconnecting in {delay:.1f}s (attempt {self._reconnect_attempts})")
        time.sleep(delay)
        
        if self._running:
            try:
                self.sock = self._connect_to_ami()
                self.logger.info("Reconnection successful")
            except Exception as e:
                self.logger.error(f"Reconnection failed: {e}")
                if self._reconnect_attempts < 20:  # Prevent infinite reconnection attempts
                    threading.Thread(target=self._reconnect, daemon=True).start()
    
    def _watchdog_loop(self):
        """Watchdog loop to clear stuck calls and report status."""
        status_report_interval = 300  # Report status every 5 minutes
        last_status_report = time.time()
        
        while self._running:
            time.sleep(self.config.watchdog_interval)
            current_time = time.time()
            
            # Clear stuck calls
            if (self.current_displayed_channel and 
                self.last_call_time > 0 and
                (current_time - self.last_call_time > self.config.call_timeout)):
                
                elapsed = int(current_time - self.last_call_time)
                self.logger.info(f"Watchdog: No activity for {elapsed}s. Clearing stuck call.")
                self.clear_display()
            
            # Periodic status report when connection is stable and quiet
            if (current_time - last_status_report >= status_report_interval and 
                self._connection_stable and not self.active_calls):
                self.logger.info(f"AMI Monitor: Connection stable, monitoring for calls...")
                last_status_report = current_time
    
    def test_connection(self) -> bool:
        """Test AMI connection and authentication."""
        try:
            self.logger.info("Testing AMI connection...")
            test_sock = self._connect_to_ami()
            test_sock.close()
            self.logger.info("AMI connection test successful")
            return True
        except Exception as e:
            self.logger.error(f"AMI connection test failed: {e}")
            return False
    
    def start(self):
        """Start the caller ID monitor."""
        self.logger.info("Starting Caller ID Monitor...")
        
        # Test connection first
        if not self.test_connection():
            self.logger.error("Initial connection test failed. Please check:")
            self.logger.error(f"- Host: {self.config.host}")
            self.logger.error(f"- Port: {self.config.port}")
            self.logger.error(f"- Username: {self.config.username}")
            self.logger.error("- Password: [hidden]")
            self.logger.error("- AMI is enabled in Asterisk manager.conf")
            self.logger.error("- Firewall allows connection to AMI port")
            return
        
        self._running = True
        
        try:
            # Connect to AMI
            self.sock = self._connect_to_ami()
            
            # Start watchdog thread
            self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
            self._watchdog_thread.start()
            
            # Start keepalive thread
            self._keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
            self._keepalive_thread.start()
            
            # Start listening to events
            self._listen_to_events()
            
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Critical error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the caller ID monitor."""
        self.logger.info("Stopping Caller ID Monitor...")
        self._running = False
        
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        
        # Clear display on shutdown
        self.clear_display()


def main():
    """Main entry point."""
    config = AMIConfig()
    monitor = CallerIDMonitor(config)
    
    try:
        monitor.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())