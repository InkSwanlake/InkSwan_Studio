#!/usr/bin/env python3
import os
import socket

# --- SYSTEM CONFIGURATION ---
PRINTER_IP = "192.168.10.239"
PORT = 9100
DATA_FILE = os.path.join("data", "serial_inputs.txt")

# --- 300 DPI LABEL MATRIX MATH ---
# 162mm Width * 11.81 dots/mm = 1914 dots
# 101mm Height * 11.81 dots/mm = 1192 dots
LABEL_WIDTH = 1914
LABEL_HEIGHT = 1192

def parse_line_to_ppid(line_str):
    """
    Parses a single row string and converts it into a raw solid 
    23-character barcode token and a clean hyphenated text string.
    """
    # Clean whitespace strings out of array elements
    tokens = [t.strip().upper() for t in line_str.split(",") if t.strip()]
    if len(tokens) < 6:
        raise ValueError("Line item lacks all 6 necessary Dell PPID components.")
        
    country, part_num, factory, date_code, sequence, revision = tokens[:6]
    
    # Standardize part numbers to exactly 6 digits (pad 5-digit items with a leading 0)
    pn = "0" + part_num if len(part_num) == 5 else part_num
    
    # Separate sequence field to match the template formatting rule
    seq_main = sequence[0:4] if len(sequence) >= 4 else "P001"
    seq_sub = sequence[-1] if len(sequence) == 5 else "A"
    
    # Variant A: Solid token for barcode reading mapping
    raw_barcode = f"{country}{pn}{factory}{date_code}{seq_main}{seq_sub}{revision}"
    
    # Variant B: Exact layout hyphen matching matching your picture target
    hyphen_text = f"{country}-{pn}-{factory}-{date_code}-{seq_main}-{seq_sub}{revision}"
    
    return raw_barcode, hyphen_text

def build_composite_label_zpl(batch_items):
    """
    Arranges up to 5 items vertically across a single 162x101mm canvas.
    """
    # Base layout header initialization
    zpl = [
        "^XA",
        "^CI28",                       # Force clean UTF-8 string rendering
        f"^PW{LABEL_WIDTH}",          # Enforce hardware boundary constraints
        f"^LL{LABEL_HEIGHT}",         # Force page length height matching
    ]
    
    y_start = 50       # Top margin spacing padding
    row_step = 225     # Vertical distance between row instances
    
    for idx, item in enumerate(batch_items):
        raw_bc, hyphen_txt = item
        current_y = y_start + (idx * row_step)
        
        # If a row item position is empty, skip printing code data matrix elements
        if raw_bc == "EMPTY_ROW":
            zpl.append(f"^FO100,{current_y + 40}^A0N,28,24^FDRow #{idx+1}: {hyphen_txt}^FS")
        else:
            # Column A: Draw High-Density Data Matrix (Element thickness 8 is optimal for 300 DPI)
            zpl.append(f"^FO100,{current_y}^BXN,8,200,,,,^FS^FH\\^FD{raw_bc}^FS")
            
            # Column B: Draw clean descriptive text strings shifted right (X=340)
            zpl.append(f"^FO340,{current_y + 35}^A0N,30,26^FD#{idx+1}: {hyphen_txt}^FS")
            
        # Draw a thin horizontal dividing line underneath rows 1 through 4
        if idx < 4:
            zpl.append(f"^FO80,{current_y + 185}^GB1754,2,2^FS")
            
    zpl.append("^XZ")
    return "\n".join(zpl)

def run_batch_printing():
    if not os.path.exists(DATA_FILE):
        print(f"[Execution Halt] Data input sheet missing from path: {DATA_FILE}")
        return

    # Extract non-empty text lines from source document
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_lines = [line.strip() for line in f if line.strip()]

    valid_records = []
    for line_num, line in enumerate(raw_lines):
        try:
            valid_records.append(parse_line_to_ppid(line))
        except Exception as err:
            print(f"[Data Check Warning] Skipping Line {line_num + 1} due to parsing error: {err}")

    if not valid_records:
        print("[Abort] Zero clean records parsed successfully. Nothing to send to printer.")
        return

    # Slice list database array records into sub-arrays of exactly 5 chunks each
    label_chunks = [valid_records[i:i + 5] for i in range(0, len(valid_records), 5)]
    print(f"\nProcessing {len(valid_records)} total lines into {len(label_chunks)} physical print jobs...")

    for label_idx, chunk in enumerate(label_chunks):
        # Pad remaining rows if final chunk has fewer than 5 items
        while len(chunk) < 5:
            chunk.append(("EMPTY_ROW", "--------------------------------------"))
            
        # Generate the ZPL block for this batch of 5 items
        zpl_output = build_composite_label_zpl(chunk)
        
        # Fire raw bytes payload over standard TCP socket to Zebra ZT411 port 9100
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(6.0) # Prevent code locking if printer goes offline
                s.connect((PRINTER_IP, PORT))
                s.sendall(bytes(zpl_output, "utf-8"))
                print(f" -> [Dispatched] Composite sheet label {label_idx + 1}/{len(label_chunks)} sent.")
        except Exception as net_err:
            print(f" -> [Network Drop] Communication failed on sheet {label_idx + 1}: {net_err}")

if __name__ == "__main__":
    run_batch_printing()
