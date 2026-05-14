Here is the updated, production-ready script with an integrated archiving engine.
Once the data file is successfully processed and dispatched to the printer, the script renames the file with a clean timestamp prefix and moves it into a dedicated history/ subfolder. This entirely prevents the printer from processing duplicate rows on subsequent execution loops.

#!/usr/bin/env python3import osimport reimport socketimport sysimport shutilfrom datetime import datetime
# --- SYSTEM CONFIGURATION ---PRINTER_IP = "192.168.10.239"PORT = 9100DATA_FILE = os.path.join("data", "serial_inputs.txt")ERROR_LOG_FILE = os.path.join("data", "error_log.txt")HISTORY_DIR = os.path.join("data", "history")
# --- 300 DPI LABEL CANVAS MATRIX MATH (162x101mm) ---LABEL_WIDTH = 1914LABEL_HEIGHT = 1192
# --- VALIDATION CONSTANTS ---VALID_COUNTRIES = {"CN", "TW", "US", "KR", "MX", "ID", "VN", "JP", "MY", "SG"}ALPHANUMERIC_REGEX = re.compile(r"^[A-Z0-9]+$")
def log_parsing_error(raw_line, line_num, reason):
    """Writes failed string inputs to an isolated log file for audit reviews."""
    os.makedirs(os.path.dirname(ERROR_LOG_FILE), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Line {line_num} | Data: '{raw_line.strip()}' | Reason: {reason}\n"
    
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as err_file:
        err_file.write(log_entry)
def parse_and_validate_ppid(raw_line, line_num):
    """Validates the input string and slices it into barcode data and a two-line layout."""
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

    # --- STRUCTURAL SLICING MATRIX ---
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

    # Use ZPL carriage return marker (\&) to force a split after the factory block
    hyphenated_text = f"{country}-{part_num}-{factory}-\\&{sequence[:3]}-{sequence[3:]}-{revision}"
    return ppid, hyphenated_text
def build_composite_label_zpl(batch_items):
    """Arranges up to 5 items vertically with text stacked directly under barcodes."""
    zpl = [
        "^XA",
        "^CI28",                       
        f"^PW{LABEL_WIDTH}",          
        f"^LL{LABEL_HEIGHT}",         
    ]
    
    y_start = 40       
    row_step = 230  # Grid step size allows exactly 5 stacked rows on a 1192-dot sheet
    
    for idx, item in enumerate(batch_items):
        raw_bc, hyphen_txt = item
        current_y = y_start + (idx * row_step)
        
        if raw_bc == "EMPTY_ROW":
            zpl.append(f"^FO100,{current_y + 40}^A0N,28,24^FD# {idx+1}: EMPTY ROW^FS")
        else:
            # Column A: 2D Data Matrix positioned at X=100
            zpl.append(f"^FO100,{current_y}^BXN,8,200,,,,^FS^FH\\^FD{raw_bc}^FS")
            
            # Text Block: Positioned directly under barcode at X=100, shifted down by 155 dots
            zpl.append(f"^FO100,{current_y + 155}^A0N,26,22^FB1500,2,0,L^FD#{idx+1}: {hyphen_txt}^FS")
            
        if idx < 4:
            zpl.append(f"^FO80,{current_y + 218}^GB1754,2,2^FS")
            
    zpl.append("^XZ")
    return "\n".join(zpl)
def archive_processed_file():
    """Renames and moves the processed input data file into the history directory."""
    try:
        os.makedirs(HISTORY_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.basename(DATA_FILE)
        archive_name = f"{timestamp}_{base_name}"
        destination_path = os.path.join(HISTORY_DIR, archive_name)
        
        shutil.move(DATA_FILE, destination_path)
        print(f" -> [ARCHIVED] Input log safely moved to: {destination_path}")
    except Exception as archive_err:
        print(f" -> [ARCHIVE WARNING] File could not be moved: {archive_err}", file=sys.stderr)
def run_batch_printing():
    """Main process execution engine."""
    if not os.path.exists(DATA_FILE):
        print(f"[Error] Data input file missing at: {DATA_FILE}")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    valid_records = []
    print("Executing Input Verification Engine...")
    
    for idx, line in enumerate(raw_lines):
        line_num = idx + 1
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
        # Even on abort, we archive the file so broken data is cleared out of production
        archive_processed_file()
        return

    label_chunks = [valid_records[i:i + 5] for i in range(0, len(valid_records), 5)]
    print(f"\nVerification complete. Printing {len(valid_records)} clean lines across {len(label_chunks)} labels...")

    transmission_success = True
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
            print(f" -> [Network Error] Failed to send sheet {label_idx + 1}: {net_err}", file=sys.stderr)
            transmission_success = False

    # Trigger safe file cleanup if transmission succeeded
    if transmission_success:
        archive_processed_file()
    else:
        print("\n[Notice] Input file retained in 'data/' due to network dispatch errors. Fix network and retry.")
if __name__ == "__main__":
    # --- OPTIONAL STAGING INITIALIZER ---
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as test_file:
            test_file.write(
                "CN02NG7FDFC0055QP001A00\n"
                "CN02NG7FDFC0055QP002A00\n"
                "CN02NG7FDFC0055QP003A00\n"
                "CN02NG7FDFC0055QP004A00\n"
                "CN02NG7FDFC0055QP005A00\n"
            )
        print(f"[Notice] Created mock sample file with 5 records at: {DATA_FILE}")

    run_batch_printing()

## New Functional Logic

* Network Error Shielding: The file is only moved to history if all ZPL packet dispatches succeed. If a socket drop occurs, the file stays put so you can trigger a reprocessing run once connectivity returns.
* shutil.move Portability: Uses standard library tools to ensure cross-platform safety across both Linux and Windows filesystems.
* Timestamp Prefix (YYYYMMDD_HHMMSS): Appends execution timestamps to archived logs, ensuring files never collide or overwrite one another in the history directory.

If you are satisfied with this core logic, let me know how you would like to package this for the final deployment environment:

* Do you want to add a loop timer that continuously polls the data/ folder for new file drops every few seconds?
* Should we convert the tool into a Windows standalone executable package using PyInstaller?
* Do you need to modify the archive engine to compress logs into a .zip layout format?


