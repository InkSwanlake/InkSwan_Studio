#!/usr/bin/env python3
import os
import socket

# --- SYSTEM CONFIGURATION ---
PRINTER_IP = "192.168.10.239"
PORT = 9100
DATA_FILE = os.path.join("data", "serial_inputs.txt")

# --- 300 DPI LABEL MATRIX MATH (162x101mm) ---
LABEL_WIDTH = 1914
LABEL_HEIGHT = 1192

def parse_solid_ppid(raw_line):
    """
    Takes a solid Dell PPID string and slices it into the 
    exact hyphenated text format while keeping the raw barcode intact.
    """
    ppid = str(raw_line).strip().upper().replace("-", "") # Strip any accidental hyphens
    
    # Handle standard 23-character Dell PPID format
    if len(ppid) == 23:
        country   = ppid[0:2]
        part_num  = ppid[2:8]   # 6 chars: '0HG5D7' or '0HG5D' + next char
        factory   = ppid[8:13]  # 5 chars
        date_code = ppid[13:16] # 3 chars
        seq_main  = ppid[16:20] # 4 chars (e.g., 'P001')
        seq_sub   = ppid[20:21] # 1 char  (e.g., 'A')
        revision  = ppid[21:23] # 2 chars (e.g., '00')
    
    # Handle common 22-character variations (where part number has no leading zero)
    elif len(ppid) == 22:
        country   = ppid[0:2]
        part_num  = "0" + ppid[2:7] # Pad the 5-digit part number out to 6 digits
        factory   = ppid[7:12]
        date_code = ppid[12:15]
        seq_main  = ppid[15:19]
        seq_sub   = ppid[19:20]
        revision  = ppid[20:22]
        # Re-build a clean 23-character string for the barcode matrix
        ppid = f"{country}{part_num}{factory}{date_code}{seq_main}{seq_sub}{revision}"
        
    else:
        raise ValueError(f"Invalid PPID length ({len(ppid)} chars). Must be 22 or 23 characters.")

    # Reconstruct the exact hyphenated display variant matching your target look
    hyphenated_text = f"{country}-{part_num}-{factory}-{date_code}-{seq_main}-{seq_sub}{revision}"
    
    return ppid, hyphenated_text

def build_composite_label_zpl(batch_items):
    """Arranges up to 5 items vertically across a single 162x101mm canvas."""
    zpl = [
        "^XA",
        "^CI28",                       # Force clean string rendering
        f"^PW{LABEL_WIDTH}",          # Label width boundary
        f"^LL{LABEL_HEIGHT}",         # Label height boundary
    ]
    
    y_start = 50       
    row_step = 225     
    
    for idx, item in enumerate(batch_items):
        raw_bc, hyphen_txt = item
        current_y = y_start + (idx * row_step)
        
        if raw_bc == "EMPTY_ROW":
            zpl.append(f"^FO100,{current_y + 40}^A0N,28,24^FDRow #{idx+1}: {hyphen_txt}^FS")
        else:
            # Column A: Raw unhyphenated string inside the Data Matrix barcode
            zpl.append(f"^FO100,{current_y}^BXN,8,200,,,,^FS^FH\\^FD{raw_bc}^FS")
            
            # Column B: Hyphenated layout text printed next to it
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
        raw_lines = [line.strip() for line in f if line.strip()]

    valid_records = []
    for line_num, line in enumerate(raw_lines):
        try:
            valid_records.append(parse_solid_ppid(line))
        except Exception as err:
            print(f"[Warning] Skipping Line {line_num + 1} ('{line}'): {err}")

    if not valid_records:
        print("[Abort] No valid records parsed.")
        return

    # Group into batches of 5
    label_chunks = [valid_records[i:i + 5] for i in range(0, len(valid_records), 5)]
    print(f"\nProcessing {len(valid_records)} solid lines into {len(label_chunks)} labels...")

    for label_idx, chunk in enumerate(label_chunks):
        while len(chunk) < 5:
            chunk.append(("EMPTY_ROW", "--------------------------------------"))
            
        zpl_output = build_composite_label_zpl(chunk)
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(6.0)
                s.connect((PRINTER_IP, PORT))
                s.sendall(bytes(zpl_output, "utf-8"))
                print(f" -> [Dispatched] Label sheet {label_idx + 1}/{len(label_chunks)} sent.")
        except Exception as net_err:
            print(f" -> [Network Error] Failed to send sheet {label_idx + 1}: {net_err}")

if __name__ == "__main__":
    run_batch_printing()
