def build_composite_label_zpl(batch_items):
    """Arranges up to 5 items vertically with text stacked directly under barcodes."""
    zpl = [
        "^XA",
        "^CI28",                       
        f"^PW{LABEL_WIDTH}",          
        f"^LL{LABEL_HEIGHT}",         
    ]
    
    y_start = 40       
    row_step = 230  # Tightened spacing to cleanly fit 5 stacked blocks on the canvas   
    
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
            # Horizontal dividing line pushed further down to clear the text envelope
            zpl.append(f"^FO80,{current_y + 218}^GB1754,2,2^FS")
            
    zpl.append("^XZ")
    return "\n".join(zpl)
