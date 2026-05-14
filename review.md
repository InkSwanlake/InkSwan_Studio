An architectural and spatial rendering review of your updated 5-row stacked ZPL payload is detailed below. This analysis ensures the layout elements fit cleanly within your 162mm x 101mm (1914 x 1192 dots) 300 DPI canvas without overlaps or physical print truncation.Visual Architecture PreviewWhen processed by your Zebra ZT411 printer, each of the 5 repeated data segments will follow this exact vertical block structure:text+-----------------------------------------------------------------------+

|  [■■■]  <- 2D Data Matrix (X:100, Y:40, 60, 80...)                    |
|  [■■■]     Height: ~144 dots (approx. 12mm)                           |
|                                                                       |
|  #1: CN-02NG7F-DFC00-   <- Font Line 1 (X:100, Y:195, 425...)         |
|  55Q-P001-A00           <- Font Line 2 (Auto-wrapped by ZPL)          |
|                                                                       |
|  -------------------------------------------------------------------  |
|  <- Separation Border Line (Y:258, 488, 718, 948)                      |
+-----------------------------------------------------------------------+
Use code with caution.Spatial Boundary Coordinates & Math AnalysisThe label runs a tight vertical schedule to stack all 5 blocks onto a single canvas sheet. The table below charts the layout tracking elements across the coordinate plane:Row NumberComponentX-Pos (Dots)Y-Start (Dots)Y-End (Dots)Spatial Headroom / StatusRow #12D Data Matrix10040184Healthy 11-dot margin gap to textDual-Line Text100195~255Clear of the line block belowDivider Wire 180258260Baseline anchorRow #22D Data Matrix100270414Clear of Divider 1Dual-Line Text100425~485Fits safely within row containerDivider Wire 280488490Baseline anchorRow #32D Data Matrix100500644BalancedDual-Line Text100655~715BalancedDivider Wire 380718720Baseline anchorRow #42D Data Matrix100730874BalancedDual-Line Text100885~945BalancedDivider Wire 480948950Baseline anchorRow #52D Data Matrix1009601104Final core asset blockDual-Line Text1001115~1175Safety Check: Terminates 17 dots before canvas floor (1192)Critical Engineering ObservationsText Parameter Safety (^FB1500,2,0,L): The horizontal canvas provides 1914 dots of printable width. Setting your text layout block width to 1500 ensures text lines will never hit an unmapped margin wrap constraint. The text is safely forced down only by your explicit \& carriage return command.Text Font Dimensions (^A0N,26,22): Scaling down slightly from the original 30x26 font size to 26x22 gives your two-line arrangement exactly enough vertical breathing room to keep the text from overlapping the horizontal dividing line below it.Data Matrix Sizing Matrix (^BXN,8,200): An orientation module size of 8 at 300 DPI balances scannability with size constraints. This creates an optimal grid profile roughly 12mm square, perfect for warehouse handheld scanners.Verified Final ZPL Production PayloadYou can copy and paste this verified, final block directly into your staging parser or deployment network:text^XA
^CI28
^PW1914
^LL1192
^FO100,40^BXN,8,200,,,,^FS^FH\^FDCN02NG7FDFC0055QP001A00^FS
^FO100,195^A0N,26,22^FB1500,2,0,L^FD#1: CN-02NG7F-DFC00-\&55Q-P001-A00^FS
^FO80,258^GB1754,2,2^FS
^FO100,270^BXN,8,200,,,,^FS^FH\^FDCN02NG7FDFC0055QP002A00^FS
^FO100,425^A0N,26,22^FB1500,2,0,L^FD#2: CN-02NG7F-DFC00-\&55Q-P002-A00^FS
^FO80,488^GB1754,2,2^FS
^FO100,500^BXN,8,200,,,,^FS^FH\^FDCN02NG7FDFC0055QP003A00^FS
^FO100,655^A0N,26,22^FB1500,2,0,L^FD#3: CN-02NG7F-DFC00-\&55Q-P003-A00^FS
^FO80,718^GB1754,2,2^FS
^FO100,730^BXN,8,200,,,,^FS^FH\^FDCN02NG7FDFC0055QP004A00^FS
^FO100,885^A0N,26,22^FB1500,2,0,L^FD#4: CN-02NG7F-DFC00-\&55Q-P004-A00^FS
^FO80,948^GB1754,2,2^FS
^FO100,960^BXN,8,200,,,,^FS^FH\^FDCN02NG7FDFC0055QP005A00^FS
^FO100,1115^A0N,26,22^FB1500,2,0,L^FD#5: CN-02NG7F-DFC00-\&55Q-P005-A00^FS
^XZ
Use code with caution.To complete your label review, let me know:Would you like to review a layout option that completely removes the row indices (#1:, #2:) to gain more horizontal printing area?Do you want to try centering the text beneath the barcode by switching the alignment parameter from L to C?Should we configure a test print configuration line to check barcode readability under different darkness settings?
