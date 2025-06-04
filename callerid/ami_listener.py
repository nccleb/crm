import socket
import datetime
import os

# --- Configuration ---
HOST = '192.168.20.216'  # UCM IP address
PORT = 7777            # AMI Port (default)
USERNAME = 'amiuser1'    # AMI Username
PASSWORD = 'A1A1a1a1'  # AMI Password
OUTPUT_FILE = 'callerid.txt'

# --- Runtime State ---
active_calls = {}
current_displayed_channel = None

# --- File Handling ---
def write_to_file(caller_id, caller_name):
    global current_displayed_channel
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(OUTPUT_FILE, 'w') as f:
        f.write(f"{timestamp} - Caller ID: {caller_id} - Name: {caller_name}\n")
    print(f"[FILE UPDATED] Showing: {caller_id} - {caller_name}")

def clear_file():
    global current_displayed_channel
    with open(OUTPUT_FILE, 'w') as f:
        f.write('')
    print("[FILE CLEARED]")
    current_displayed_channel = None

# --- AMI Event Parser ---
def parse_ami_events(sock):
    global current_displayed_channel
    buffer = ""

    while True:
        data = sock.recv(1024).decode(errors='ignore')
        buffer += data
        while "\r\n\r\n" in buffer:
            chunk, buffer = buffer.split("\r\n\r\n", 1)
            lines = chunk.split("\r\n")
            event = {}
            for line in lines:
                if ": " in line:
                    key, val = line.split(": ", 1)
                    event[key.strip()] = val.strip()

            event_type = event.get("Event")
            channel = event.get("Channel", "unknown")

            # Debug log
            #print(f"[EVENT] {event_type} - {event}")

            # --- Incoming Call Detected ---
            if event_type == "NewCallerid" and event.get("CallerIDNum"):
                caller_id = event.get("CallerIDNum")
                caller_name = event.get("CallerIDName", "")
                active_calls[channel] = (caller_id, caller_name)
                current_displayed_channel = channel
                write_to_file(caller_id, caller_name)

            # --- Call Answered ---
            elif event_type == "Newstate":
                state = event.get("ChannelStateDesc", "")
                if state == "Up" and channel == current_displayed_channel:
                    print(f"[CALL ANSWERED] {channel}")
                    clear_file()
                    if channel in active_calls:
                        del active_calls[channel]

            # --- Call Hung Up ---
            elif event_type == "Hangup":
                if channel in active_calls:
                    print(f"[CALL HUNG UP] {channel}")
                    del active_calls[channel]
                    if channel == current_displayed_channel:
                        if active_calls:
                            # Show another active call (last one received)
                            last_channel = list(active_calls.keys())[-1]
                            cid, cname = active_calls[last_channel]
                            current_displayed_channel = last_channel
                            write_to_file(cid, cname)
                        else:
                            clear_file()

# --- AMI Login and Start Listening ---
def start_ami_listener():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        login_msg = f"Action: Login\r\nUsername: {USERNAME}\r\nSecret: {PASSWORD}\r\n\r\n"
        sock.sendall(login_msg.encode())
        print("[CONNECTED] Listening for AMI events...")
        parse_ami_events(sock)
    except Exception as e:
        print(f"[ERROR] Cannot connect to AMI: {e}")

# --- Start the Listener ---
if __name__ == "__main__":
    start_ami_listener()
