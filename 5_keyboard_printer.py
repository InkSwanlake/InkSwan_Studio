#!/usr/bin/env python3
import os
import re
import socket
from datetime import datetime

# --- SYSTEM CONFIGURATION ---
PRINTER_IP = "192.168.10.239"
PORT = 9100
DATA_FILE = os.path.join("data", "serial_inputs.txt")
ERROR_LOG_FILE = os.path.join("data", "error_log.txt")

# --- 300 DPI LABEL MATRIX MATH (162x101mm) ---
LABEL_WIDTH = 1914
LABEL_HEIGHT = 1192

# --- VALIDATION CONSTANTS ---
VALID_COUNTRIES = {"CN", "TW", "US", "KR", "MX", "ID", "VN", "JP", "MY", "SG"}
ALPHANUMERIC_REGEX = re.compile(r"^[A-Z0-9]+$")

def log_parsing_error(raw_line, line_num, reason):
    """Writes failed string inputs to an isolated log file for audit reviews."""
    os.makedirs(os.path.dirname(ERROR_LOG_FILE), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Line {line_num} | Data: '{raw_line.strip()}' | Reason: {reason}\n"
    
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as err_file:
        err_file.write(log_entry)

def parse_and_validate_ppid(raw_line, line_num):
    """Validates the input string and slices it into raw barcode data and layout string."""
    ppid = str(raw_line).strip().upper().replace("-", "").replace(" ", "")
    
    if not ppid:
        raise ValueError("Line is empty or contains only whitespace.")

    if len(ppid) not in (22, 23):
        raise ValueError(f"Invalid length ({len(ppid)} chars). Must be exactly 22 or 23 characters.")

    if not ALPHANUMERIC_REGEX.match(ppid):
        raise ValueError("String contains illegal characters, symbols, or lowercase letters.")

    country_prefix = ppid[0:2]
    if country_prefix not in VALID_COUNTRIES:
        if not country_prefix.isalpha():
            raise ValueError(f"Invalid country code prefix format: '{country_prefix}'")

    # --- CORRECTED STRUCTURAL SLICING MATRIX ---
    if len(ppid) == 23:
        country   = ppid[0:2]
        part_num  = ppid[2:8]   
        factory   = ppid[8:13]  
        date_code = ppid[13:16] 
        sequence  = ppid[16:21] 
        revision  = ppid[21:23] 
    else:  # 22-character format conversion
        country   = ppid[0:2]
        part_num  = "0" + ppid[2:7] 
        factory   = ppid[7:12]
        date_code = ppid[12:15]
        sequence  = ppid[15:20]
        revision  = ppid[20:22]
        ppid = f"{country}{part_num}{factory}{date_code}{sequence}{revision}"

    hyphenated_text = f"{country}-{part_num}-{factory}-{date_code}-{sequence}-{revision}"
    return ppid, hyphenated_text

def build_composite_label_zpl(batch_items):
    """Arranges up to 5 items vertically across a single 162x101mm canvas."""
    zpl = [
        "^XA",
        "^CI28",                       
        f"^PW{LABEL_WIDTH}",          
        f"^LL{LABEL_HEIGHT}",         
    ]
    
    y_start = 50       
    row_step = 225     
    
    for idx, item in enumerate(batch_items):
        raw_bc, hyphen_txt = item
        current_y = y_start + (idx * row_step)
        
        if raw_bc == "EMPTY_ROW":
            zpl.append(f"^FO100,{current_y + 40}^A0N,28,24^FDRow #{idx+1}: {hyphen_txt}^FS")
        else:
            zpl.append(f"^FO100,{current_y}^BXN,8,200,,,,^FS^FH\\^FD{raw_bc}^FS")
            zpl.append(f"^FO340,{current_y + 35}^A0N,30,26^FD#{idx+1}: {hyphen_txt}^FS")
            
        if idx < 4:
            zpl.append(f"^FO80,{current_y + 185}^GB1754,2,2^FS")
            
    zpl.append("^XZ")
    return "\n".join(zpl)

def run_batch_printing():
    if not os.path.exists(DATA_FILE):
        print(f"[Error] Data input file missing at: {DATA_FILE}")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    valid_records = []
    print("Executing Input Verification Engine...")
    
    for idx, line in enumerate(raw_lines):
        line_num = idx + 1
        # Skip empty lines or stray text segments
        if not line.strip() or line.strip().startswith("#"):
            continue
        try:
            validated_pair = parse_and_validate_ppid(line, line_num)
            valid_records.append(validated_pair)
        except ValueError as err:
            print(f" -> [REJECTED] Line {line_num}: {err}")
            log_parsing_error(line, line_num, str(err))

    if not valid_records:
        print("\n[Abort] Zero strings passed verification. No labels were sent to the printer.")
        print(f"Review error details here: {ERROR_LOG_FILE}")
        return

    label_chunks = [valid_records[i:i + 5] for i in range(0, len(valid_records), 5)]
    print(f"\nVerification complete. Printing {len(valid_records)} clean lines across {len(label_chunks)} labels...")

    for label_idx, chunk in enumerate(label_chunks):
        while len(chunk) < 5:
            chunk.append(("EMPTY_ROW", "--------------------------------------"))
            
        zpl_output = build_composite_label_zpl(chunk)
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(6.0)
                s.connect((PRINTER_IP, PORT))
                s.sendall(bytes(zpl_output, "utf-8"))
                print(f" -> [Dispatched] Label sheet {label_idx + 1}/{len(label_chunks)} sent to ZT411.")
        except Exception as net_err:
            print(f" -> [Network Error] Failed to send sheet {label_idx + 1}: {net_err}")

if __name__ == "__main__":
    # Setup test file directory environment locally
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as test_file:
        test_file.write("CN02NG7FDFC0055QP001A00\nCN02NG7FDFC0055QP002B00\n")
        
    run_batch_printing()
