Script Execution & FeaturesDouble Escape Handlers (\\&): Python treats backslashes inside multiline strings as escape sequence tags. The script uses a double backslash (\\&) to pass the literal \& ZPL sequence safely into the raw network stream.Timeout Shielding: The 5-second socket timeout ensures your terminal immediately returns an exit error message instead of locking up if the target printer loses power or disconnects from the network switch.No Dependencies: Runs completely on Python's built-in standard library without needing external package downloads like pip install requests.Please let me know if you would like to expand this deployment:Do you want to pass the IP address dynamically as a command-line flag (e.g., python script.py --ip 192.168.10.50)?Do you need to track printer feedback responses to verify whether the media roll or ribbon is out?Should we integrate a file reader function to load data streams on the fly?

#!/usr/bin/env python3
import socket
import sys

# --- PRINTER NETWORK CONFIGURATION ---
# Replace with your Zebra ZT411's actual network IP address
PRINTER_IP = "192.168.10.239"  
PORT = 9100  # Standard raw TCP port for Zebra print servers

# --- STACKED 5-CASE ZPL PAYLOAD ---
ZPL_PAYLOAD = """^XA
^CI28
^PW1914
^LL1192
^FO100,40^BXN,8,200,,,,^FS^FH\\^FDCN02NG7FDFC0055QP001A00^FS
^FO100,195^A0N,26,22^FB1500,2,0,L^FD#1: CN-02NG7F-DFC00-\\&55Q-P001-A00^FS
^FO80,258^GB1754,2,2^FS
^FO100,270^BXN,8,200,,,,^FS^FH\\^FDCN02NG7FDFC0055QP002A00^FS
^FO100,425^A0N,26,22^FB1500,2,0,L^FD#2: CN-02NG7F-DFC00-\\&55Q-P002-A00^FS
^FO80,488^GB1754,2,2^FS
^FO100,500^BXN,8,200,,,,^FS^FH\\^FDCN02NG7FDFC0055QP003A00^FS
^FO100,655^A0N,26,22^FB1500,2,0,L^FD#3: CN-02NG7F-DFC00-\\&55Q-P003-A00^FS
^FO80,718^GB1754,2,2^FS
^FO100,730^BXN,8,200,,,,^FS^FH\\^FDCN02NG7FDFC0055QP004A00^FS
^FO100,885^A0N,26,22^FB1500,2,0,L^FD#4: CN-02NG7F-DFC00-\\&55Q-P004-A00^FS
^FO80,948^GB1754,2,2^FS
^FO100,960^BXN,8,200,,,,^FS^FH\\^FDCN02NG7FDFC0055QP005A00^FS
^FO100,1115^A0N,26,22^FB1500,2,0,L^FD#5: CN-02NG7F-DFC00-\\&55Q-P005-A00^FS
^XZ"""

def send_zpl_to_printer(ip, port, zpl_data):
    """Establishes a raw TCP socket connection and pushes the ZPL string payload."""
    print(f"Connecting to Zebra Printer at {ip}:{port}...")
    
    try:
        # Create a streaming TCP socket channel
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Prevent script from hanging indefinitely if printer is offline
            s.settimeout(5.0) 
            
            # Establish physical handshake
            s.connect((ip, port))
            
            # Encode ZPL text code to a clean UTF-8 byte sequence and dispatch
            s.sendall(zpl_data.encode('utf-8'))
            
            print(" -> [SUCCESS] ZPL payload fully dispatched to print buffer queue.")
            
    except socket.timeout:
        print(" -> [ERROR] Connection timed out. Verify network connection and IP address.", file=sys.stderr)
    except socket.error as e:
        print(f" -> [NETWORK ERROR] Physical connection failure: {e}", file=sys.stderr)
    except Exception as e:
        print(f" -> [UNEXPECTED ERROR] Transmission halted: {e}", file=sys.stderr)

if __name__ == "__main__":
    send_zpl_to_printer(PRINTER_IP, PORT, ZPL_PAYLOAD)
