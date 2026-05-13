import os
import socket

# --- SYSTEM SETTINGS ---
PRINTER_IP = "192.168.10.239"
PORT = 9100
DATA_FILE = os.path.join("data", "serial_inputs.txt")

def generate_ppid_variants(line_str):
    """Parses a comma-separated row string and extracts the Dell PPID tokens."""
    tokens = [t.strip().upper() for t in line_str.split(",") if t.strip()]
    if len(tokens) < 6:
        raise ValueError("Line item lacks necessary components (Needs 6 items).")
        
    country, part_num, factory, date_code, sequence, revision = tokens[:6]
    
    # Pad out the 5-digit part number to 6 digits
    pn = "0" + part_num if len(part_num) == 5 else part_num
    
    seq_main = sequence[0:4] if len(sequence) >= 4 else "P001"
    seq_sub = sequence[4] if len(sequence) == 5 else "A"
    
    raw_barcode = f"{country}{pn}{factory}{date_code}{seq_main}{seq_sub}{revision}"
    hyphen_text = f"{country}-{pn}-{fact_code:=factory if len(factory)==5 else factory}-{date_code}-{seq_main}-{seq_sub}{revision}"
    
    # Workaround for raw assignments inside string constructions
    hyphen_text = f"{country}-{pn}-{factory}-{date_code}-{seq_main}-{seq_sub}{revision}"
    
    return raw_barcode, hyphen_text

def build_5x_label_zpl(batch_items):
    """Calculates 300 DPI layout placement across a 162x101mm label area."""
    # ^PW1914 sets label width, ^MND sets media tracking, ^LL1192 sets length tracking
    zpl = ["^XA", "^CI28", "^PW1914", "^LL1192"]
    
    # Vertical starting coordinate position
    y_start = 60
    # Step difference between successive rows
    row_gap = 220 
    
    for i, item in enumerate(batch_items):
        raw_bc, hyphen_txt = item
        current_y = y_start + (i * row_gap)
        
        # Row Layout Map:
        # Left side: High-Resolution Data Matrix (Module scale 8)
        # Right side: Sharp text display tracking baseline
        zpl.append(f"^FO100,{current_y}^BXN,8,200,,,,^FS^FH\\^FD{raw_bc}^FS")
        zpl.append(f"^FO320,{current_y + 20}^A0N,28,24^FDItem #{i+1}: {hyphen_txt}^FS")
        
        # Draw a thin partition divider beneath the item (Skip on the final item row)
        if i < 4:
            zpl.append(f"^FO100,{current_y + 160}^GB1714,2,2^FS")
            
    zpl.append("^XZ")
    return "\n".join(zpl)

def process_and_print():
    if not os.path.exists(DATA_FILE):
        print(f"[Error] The text dataset file cannot be found at path: {DATA_FILE}")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    parsed_items = []
    for index, line in enumerate(lines):
        try:
            parsed_items.append(generate_ppid_variants(line))
        except Exception as e:
            print(f"[Skipping Line {index+1}] Parsing failure: {e}")

    # Process parsed array records into chunks of exactly 5 elements each
    chunks = [parsed_items[i:i + 5] for i in range(0, len(parsed_items), 5)]
    
    if not chunks:
        print("No valid records to process.")
        return

    print(f"Discovered {len(parsed_items)} clean items. Preparing {len(chunks)} composite labels...")

    for label_idx, chunk in enumerate(chunks):
        # Fill missing positions with blank lines if the final chunk has fewer than 5 items
        while len(chunk) < 5:
            chunk.append(("BLANK_SLOT", "------------------------"))
            
        zpl_payload = build_5x_label_zpl(chunk)
        
        # Fire raw bytes payload down the network pipeline straight to the ZT411
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)
                s.connect((PRINTER_IP, PORT))
                s.sendall(bytes(zpl_payload, "utf-8"))
                print(f"[Sent] Composite label {label_idx + 1}/{len(chunks)} successfully sent to ZT411.")
        except Exception as err:
            print(f"[Network Loss] Failed to deliver data matrix chunk {label_idx + 1}: {err}")

if __name__ == "__main__":
    process_and_print()
