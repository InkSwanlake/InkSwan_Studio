This complete solution provides a production-ready system to run on your Ubuntu 26.04 LTS environment. It includes a structured dataset, an automatic 5-item batch parsing loop, and raw TCP socket delivery designed for your Zebra ZT411 (300 DPI) network printer at 192.168.10.239.Project Directory StructureRun these commands in your Ubuntu terminal to build the environment structure cleanly:bashmkdir -p dell_batch_printer/data
cd dell_batch_printer
touch data/serial_inputs.txt batch_printer.py
Use code with caution.Step 1: Create Your Dataset (data/serial_inputs.txt)Open data/serial_inputs.txt in your text editor (e.g., nano data/serial_inputs.txt) and paste your raw target entries. Each line must contain exactly 6 comma-separated values:textCN,2NG7F,DFC00,55Q,P001A,00
CN,2NG7F,DFC00,55Q,P002B,00
CN,2NG7F,DFC00,55Q,P003C,00
CN,2NG7F,DFC00,55Q,P004D,00
CN,2NG7F,DFC00,55Q,P005E,00
CN,0HG5D,WI012,56A,A012B,01
CN,0HG5D,WI012,56A,A013C,01
Use code with caution.Note: The script automatically groups these into batches of 5. If your file has fewer than 5 items or leaves remaining items at the end, the script fills the empty slots safely with a blank indicator text line.Step 2: The Production Printing Engine (batch_printer.py)Paste this code directly into your batch_printer.py file. It parses your source file, converts millimeter metrics to 300 DPI coordinates, formats individual entries, and fires them to the printer.python#!/usr/bin/env python3
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
Use code with caution.Step 3: Run the Script on UbuntuYou do not need to install any external dependencies to run this script, as it relies entirely on native Python system library bindings (os and socket).To start printing your batch jobs, execute the script in your terminal window:bashpython3 batch_printer.py
Use code with caution.Key Operational Protections Built-InMedia Configuration Calibration (^PW1914^LL1192): Locks the printer canvas specifically to your 162x101mm dimensions, ensuring the ZT411 feeds exactly one label sheet per run.Safe Empty Chunk Padding: If your text dataset has 7 lines, it prints label 1 with items 1–5, then prints label 2 with items 6–7 followed by 3 blank rows. This prevents array out-of-bounds crashes during execution loops.Module Sharpness Calibration (^BXN,8): An element dimension value of 8 dots provides crisp edge definitions on 300 DPI printheads, allowing standard handheld barcode scanners to read the printed labels instantly.If you want to tweak this solution further, let me know:Do you want the script to move or rename the serial_inputs.txt file after a successful print job to prevent printing duplicate items?Should the script generate an error log file if a row contains broken or corrupted data formatting?
