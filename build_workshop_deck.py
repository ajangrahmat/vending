"""Build the English, two-hour mini vending machine workshop deck."""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


BASE = Path(r"D:\workshop-sukabumi\vending")
DECK_PATH = BASE / "mini_vending_qris_workshop_2_hours.pptx"

deck = Presentation()
deck.slide_width = Inches(13.333)
deck.slide_height = Inches(7.5)

WHITE = RGBColor(255, 255, 255)
INK = RGBColor(30, 39, 49)
MUTED = RGBColor(92, 103, 114)
BLUE = RGBColor(39, 101, 161)
TEAL = RGBColor(35, 125, 126)
ORANGE = RGBColor(167, 111, 43)
PALE_BLUE = RGBColor(238, 245, 251)
PALE_TEAL = RGBColor(237, 246, 244)
PALE_ORANGE = RGBColor(249, 244, 235)
PALE_GRAY = RGBColor(244, 246, 248)
RULE = RGBColor(215, 221, 226)


def add_text(slide, value, x, y, w, h, size=16, color=INK, bold=False,
             align=PP_ALIGN.LEFT, font="Aptos"):
    shape = slide.shapes.add_textbox(
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = Inches(0.02)
    frame.margin_right = Inches(0.02)
    frame.margin_top = Inches(0.01)
    frame.margin_bottom = Inches(0.01)
    for index, line in enumerate(value.split("\n")):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.alignment = align
        paragraph.space_after = Pt(2)
        paragraph.font.name = font
        paragraph.font.size = Pt(size)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = color
    return shape


def add_rect(slide, x, y, w, h, color):
    shape = slide.shapes.add_shape(
        1, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def add_card(slide, x, y, w, h, heading, body, accent=BLUE,
             fill=PALE_BLUE, body_size=13):
    add_rect(slide, x, y, w, h, fill)
    add_rect(slide, x, y, 0.06, h, accent)
    add_text(slide, heading, x + 0.2, y + 0.12, w - 0.4, 0.25,
             size=11, color=accent, bold=True)
    add_text(slide, body, x + 0.2, y + 0.43, w - 0.4, h - 0.48,
             size=body_size)


def add_code(slide, source, y=1.95, h=4.35, size=14):
    x = 1.0
    w = 11.25
    add_rect(slide, x, y, w, h, PALE_GRAY)
    add_rect(slide, x, y, 0.055, h, BLUE)
    shape = slide.shapes.add_textbox(
        Inches(x + 0.2), Inches(y + 0.12), Inches(w - 0.4), Inches(h - 0.24)
    )
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = False
    for index, line in enumerate(source.strip("\n").splitlines()):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.space_after = Pt(2)
        paragraph.font.name = "Consolas"
        paragraph.font.size = Pt(size)
        paragraph.font.color.rgb = INK


def add_slide(section, title, subtitle=""):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = WHITE
    add_text(slide, section.upper(), 0.72, 0.33, 11.9, 0.23,
             size=10, color=BLUE, bold=True)
    add_rect(slide, 0.72, 0.78, 0.055, 0.45, BLUE)
    add_text(slide, title, 0.93, 0.71, 11.55, 0.58,
             size=25, bold=True)
    if subtitle:
        add_text(slide, subtitle, 0.95, 1.36, 11.35, 0.38,
                 size=12, color=MUTED)
    add_rect(slide, 0.72, 7.08, 11.9, 0.012, RULE)
    add_text(slide, "MINI VENDING MACHINE · 2-HOUR WORKSHOP",
             0.74, 7.15, 7, 0.18, size=8, color=MUTED)
    add_text(slide, f"{len(deck.slides):02d}", 12.02, 7.13, 0.58, 0.2,
             size=9, color=MUTED, align=PP_ALIGN.RIGHT)
    return slide


def add_cover():
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = WHITE
    add_text(slide, "2-HOUR HANDS-ON WORKSHOP",
             0.78, 0.72, 11.8, 0.3, size=12, color=BLUE, bold=True)
    add_text(
        slide,
        "Workshop on Building a Mini Vending Machine\n"
        "Integrated with QRIS Payments",
        0.78, 1.35, 11.8, 1.5, size=30, bold=True,
    )
    add_text(slide, "Live demonstration · Python application · Arduino Uno · QRIS sandbox",
             0.82, 3.12, 11.3, 0.45, size=17, color=MUTED)
    add_rect(slide, 0.82, 4.05, 11.55, 0.02, RULE)
    add_text(slide, "Presented by", 0.84, 4.35, 2.0, 0.28,
             size=11, color=BLUE, bold=True)
    add_text(slide, "Ajang Rahmat, S.Kom", 0.84, 4.72, 5.8, 0.42,
             size=21, bold=True)
    add_text(slide, "Electrical Engineering · Nusa Putra University",
             0.84, 5.22, 6.4, 0.3, size=14, color=MUTED)
    add_text(slide, "nutral.id", 0.84, 5.62, 4.0, 0.28,
             size=13, color=BLUE, bold=True)
    add_text(slide, "Build with the supplied source code. Learn by observing, wiring, "
                     "uploading, and testing.",
             0.84, 6.3, 11.3, 0.32, size=12, color=MUTED)
    add_rect(slide, 0.72, 7.08, 11.9, 0.012, RULE)
    add_text(slide, "MINI VENDING MACHINE · 2-HOUR WORKSHOP",
             0.74, 7.15, 7, 0.18, size=8, color=MUTED)
    add_text(slide, "01", 12.02, 7.13, 0.58, 0.2,
             size=9, color=MUTED, align=PP_ALIGN.RIGHT)


add_cover()

slide = add_slide(
    "01 · Opening demonstration",
    "Watch the complete experience first",
    "The instructor demonstrates the goal before explaining the parts.",
)
demo_steps = [
    ("1", "Select a product", BLUE, PALE_BLUE),
    ("2", "Show the QRIS checkout", TEAL, PALE_TEAL),
    ("3", "Confirm the test payment", ORANGE, PALE_ORANGE),
    ("4", "Light the matching LED", BLUE, PALE_BLUE),
]
for index, (number, label, accent, fill) in enumerate(demo_steps):
    x = 0.78 + index * 3.12
    add_rect(slide, x, 2.35, 2.83, 1.18, fill)
    add_text(slide, number, x + 0.18, 2.52, 0.4, 0.4,
             size=23, color=accent, bold=True)
    add_text(slide, label, x + 0.65, 2.52, 2.0, 0.55,
             size=14, bold=True)
    if index < len(demo_steps) - 1:
        add_text(slide, "→", x + 2.87, 2.72, 0.23, 0.25,
                 size=17, color=MUTED, bold=True)
add_card(slide, 0.95, 4.25, 5.45, 1.1, "NOTICE",
         "The QR payment shown in the workshop must use instructor-approved sandbox credentials.",
         TEAL, PALE_TEAL, 12)
add_card(slide, 6.75, 4.25, 5.45, 1.1, "ASK",
         "What did the application do? What did the Arduino do? Where did the QR payment fit?",
         ORANGE, PALE_ORANGE, 12)

slide = add_slide(
    "02 · The project in 5W1H",
    "Answer the big questions before we build",
    "Start with the purpose and user experience—not with code.",
)
questions = [
    ("WHAT?", "A desktop vending interface connected to an Arduino-controlled LED demo.", BLUE, PALE_BLUE),
    ("WHY?", "To make software, payment status, serial messages, and physical output tangible.", TEAL, PALE_TEAL),
    ("WHO?", "A customer selects a product; an operator configures and monitors the machine.", ORANGE, PALE_ORANGE),
    ("WHERE?", "Python runs on a computer; Arduino Uno runs the hardware sketch.", BLUE, PALE_BLUE),
    ("WHEN?", "The output is requested only after the payment flow reports success.", TEAL, PALE_TEAL),
    ("HOW?", "Python sends a serial command; Arduino maps the requested slot to an LED output.", ORANGE, PALE_ORANGE),
]
for index, (heading, body, accent, fill) in enumerate(questions):
    column = index % 2
    row = index // 2
    x = 0.95 + column * 5.8
    y = 1.95 + row * 1.33
    add_card(slide, x, y, 5.45, 1.08, heading, body, accent, fill, 12)

slide = add_slide(
    "03 · System overview",
    "Four parts work together",
    "The workshop uses LEDs as a safe, visible stand-in for vending hardware.",
)
parts = [
    ("CUSTOMER", "Selects a product\nand scans a QR", BLUE, PALE_BLUE),
    ("PYTHON APP", "Shows products,\ncart, and payment", TEAL, PALE_TEAL),
    ("SERIAL LINK", "Carries commands\nthrough USB", ORANGE, PALE_ORANGE),
    ("ARDUINO", "Turns on the LED\nfor the chosen slot", BLUE, PALE_BLUE),
]
for index, (heading, body, accent, fill) in enumerate(parts):
    x = 0.74 + index * 3.17
    add_rect(slide, x, 2.55, 2.75, 1.3, fill)
    add_text(slide, heading, x + 0.16, 2.75, 2.4, 0.24,
             size=11, color=accent, bold=True)
    add_text(slide, body, x + 0.16, 3.12, 2.4, 0.55,
             size=13, bold=True)
    if index < len(parts) - 1:
        add_text(slide, "→", x + 2.83, 2.98, 0.28, 0.3,
                 size=18, color=MUTED, bold=True)
add_card(slide, 0.95, 4.6, 11.25, 0.95, "IMPORTANT DISTINCTION",
         "The application, payment provider, serial connection, and output circuit are separate layers. "
         "A success message is not proof that a physical product was dispensed.",
         ORANGE, PALE_ORANGE, 12)

slide = add_slide(
    "04 · Why these tools?",
    "Use the right tool for each responsibility",
    "A small prototype is easier to understand when each part has one clear job.",
)
tool_rows = [
    ("Python", "Fast to read and change; coordinates the interface, cart, and payment flow.", BLUE, PALE_BLUE),
    ("Tkinter", "Included with standard Python; creates the desktop window and buttons.", TEAL, PALE_TEAL),
    ("Arduino Uno", "Reads a small sketch and controls hardware outputs predictably.", ORANGE, PALE_ORANGE),
    ("USB serial", "Simple text messages connect the computer to the microcontroller.", BLUE, PALE_BLUE),
    ("QRIS sandbox", "Allows a controlled payment-flow demonstration without production payments.", TEAL, PALE_TEAL),
]
for index, (name, detail, accent, fill) in enumerate(tool_rows):
    y = 1.95 + index * 0.86
    add_rect(slide, 0.95, y, 2.2, 0.62, fill)
    add_rect(slide, 3.35, y, 8.85, 0.62, fill)
    add_text(slide, name, 1.15, y + 0.17, 1.8, 0.22,
             size=13, bold=True, color=accent)
    add_text(slide, detail, 3.55, y + 0.15, 8.3, 0.3, size=12)

slide = add_slide(
    "05 · Two-hour roadmap",
    "A demonstration, then a guided build",
    "Installers and hardware should be ready before the hands-on session begins.",
)
agenda = [
    ("00–08", "Instructor live demonstration", BLUE, PALE_BLUE),
    ("08–20", "Project purpose and 5W1H", TEAL, PALE_TEAL),
    ("20–40", "Install tools, create a virtual environment, install packages", ORANGE, PALE_ORANGE),
    ("40–55", "Run and explore the supplied Python application", BLUE, PALE_BLUE),
    ("55–65", "Electronics, pin map, and safety", TEAL, PALE_TEAL),
    ("65–80", "Wire one LED; extend to three or six", ORANGE, PALE_ORANGE),
    ("80–100", "Write, upload, and test the Arduino sketch", BLUE, PALE_BLUE),
    ("100–110", "Test the serial protocol and integration path", TEAL, PALE_TEAL),
    ("110–115", "Review and evaluation", ORANGE, PALE_ORANGE),
    ("115–120", "Questions and answers", BLUE, PALE_BLUE),
]
for index, (minutes, task, accent, fill) in enumerate(agenda):
    column = index % 2
    row = index // 2
    x = 0.95 + column * 5.8
    y = 1.82 + row * 0.91
    add_rect(slide, x, y, 5.45, 0.68, fill)
    add_text(slide, minutes, x + 0.17, y + 0.2, 1.0, 0.24,
             size=12, color=accent, bold=True)
    add_text(slide, task, x + 1.25, y + 0.13, 3.95, 0.42,
             size=12, bold=True)

slide = add_slide(
    "06 · Before the session",
    "Prepare computers and kits",
    "Pre-downloading installers saves hands-on time; installation and verification happen together.",
)
add_card(slide, 0.95, 1.95, 5.45, 1.38, "SOFTWARE",
         "Python 3.11.9 (Windows installer)\nVisual Studio Code\nArduino IDE\nProject source folder",
         BLUE, PALE_BLUE, 12)
add_card(slide, 6.75, 1.95, 5.45, 1.38, "HARDWARE PER PARTICIPANT / TEAM",
         "Arduino Uno and USB data cable\nBreadboard and jumper wires\n1–6 LEDs\nOne 220–330 Ω resistor per LED",
         TEAL, PALE_TEAL, 12)
add_card(slide, 0.95, 3.75, 11.25, 1.0, "INSTRUCTOR PREPARATION",
         "Share the project source and installers in advance. Prepare a verified sandbox account for the opening demo; "
         "participants must not use production payment credentials.",
         ORANGE, PALE_ORANGE, 12)

slide = add_slide(
    "07 · Install the software",
    "Install Python 3.11.9, VS Code, and Arduino IDE",
    "Use official download sources; choose the Windows versions that match the classroom computers.",
)
install_rows = [
    ("1", "Install Python 3.11.9. Enable the Python Launcher if offered.", BLUE, PALE_BLUE),
    ("2", "Install Visual Studio Code and open the supplied project folder.", TEAL, PALE_TEAL),
    ("3", "Install Arduino IDE and the Arduino AVR Boards / Uno support.", ORANGE, PALE_ORANGE),
    ("4", "Connect the Uno with a USB data cable; note its COM port.", BLUE, PALE_BLUE),
]
for index, (number, text, accent, fill) in enumerate(install_rows):
    y = 1.95 + index * 0.88
    add_rect(slide, 0.95, y, 11.25, 0.66, fill)
    add_text(slide, number, 1.15, y + 0.18, 0.35, 0.24,
             size=13, bold=True, color=accent)
    add_text(slide, text, 1.75, y + 0.15, 9.9, 0.3,
             size=13, bold=True)
add_code(slide, "py -3.11 --version", y=5.72, h=0.7, size=15)
add_text(slide, "Expected: Python 3.11.9", 1.05, 6.55, 10.8, 0.25,
         size=12, color=TEAL, bold=True)

slide = add_slide(
    "08 · Set up the Python environment",
    "Create a project-local virtual environment",
    "Run commands in the VS Code terminal with the supplied project folder as the current directory.",
)
add_code(slide, """py -3.11 -m venv .venv
.venv\\Scripts\\python.exe -m pip install --upgrade pip
.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.venv\\Scripts\\python.exe -c "import tkinter, serial, PIL, qrcode; print('Setup OK')"
.venv\\Scripts\\python.exe main.py""", y=1.95, h=2.65, size=14)
add_card(slide, 0.95, 4.95, 5.45, 0.95, "WHY A VIRTUAL ENVIRONMENT?",
         "It keeps this project's packages separate from other Python projects.",
         BLUE, PALE_BLUE, 12)
add_card(slide, 6.75, 4.95, 5.45, 0.95, "IF SOMETHING FAILS",
         "Check the current folder, Python version, and full error message before retrying.",
         ORANGE, PALE_ORANGE, 12)

slide = add_slide(
    "09 · Explore the supplied source",
    "Read the project map before changing anything",
    "Participants use the finished Python source; this workshop is not a from-scratch Python build.",
)
file_rows = [
    ("main.py", "Connects the application flow and button actions."),
    ("vending_ui.py", "Builds the Tkinter interface."),
    ("inventory.py · cart.py", "Define products, stock, and cart rules."),
    ("configuration.py", "Selects demo, sandbox, or production settings."),
    ("serial_controller.py", "Sends commands and checks Arduino responses."),
    ("firmware/.../vending_controller.ino", "Arduino sketch for the vending controller."),
]
for index, (filename, purpose) in enumerate(file_rows):
    y = 1.88 + index * 0.68
    fill = [PALE_BLUE, PALE_TEAL, PALE_ORANGE][index % 3]
    add_rect(slide, 0.95, y, 3.35, 0.5, fill)
    add_rect(slide, 4.5, y, 7.7, 0.5, fill)
    add_text(slide, filename, 1.12, y + 0.13, 3.1, 0.23,
             size=11, bold=True, font="Consolas")
    add_text(slide, purpose, 4.7, y + 0.11, 7.2, 0.26, size=12)
add_text(slide, "Goal: recognize responsibilities and follow one event across files.",
         1.0, 6.2, 11, 0.28, size=12, color=BLUE, bold=True)

slide = add_slide(
    "10 · Run the existing application",
    "Start with a working baseline",
    "Do not edit the payment configuration or copy secrets into the workshop folder.",
)
add_code(slide, """.venv\\Scripts\\python.exe main.py""", y=2.0, h=1.2, size=18)
add_card(slide, 0.95, 3.65, 5.45, 1.25, "CHECK THE APP",
         "Window opens\nProduct cards and stock are visible\nSelect a product and observe the cart",
         BLUE, PALE_BLUE, 12)
add_card(slide, 6.75, 3.65, 5.45, 1.25, "PAYMENT DEMO",
         "No provider key: local simulation only. With an approved sandbox key: sandbox QRIS checkout. "
         "Never scan or test production credentials in class.",
         TEAL, PALE_TEAL, 11)
add_card(slide, 0.95, 5.3, 11.25, 0.75, "SAFE PRACTICE",
         "Keep MODE_DEMO=1 and SUMOPOD_SANDBOX=1. Do not display .env or share API keys.",
         ORANGE, PALE_ORANGE, 12)

slide = add_slide(
    "11 · Electronics and safety",
    "Start with a low-voltage LED circuit",
    "An LED is a simple output indicator; it is not a motor or a vending mechanism.",
)
add_card(slide, 0.95, 1.95, 5.45, 1.3, "ONE LED NEEDS",
         "Arduino Uno\nBreadboard\nLED\n220–330 Ω series resistor\nJumper wires",
         BLUE, PALE_BLUE, 12)
add_card(slide, 6.75, 1.95, 5.45, 1.3, "SAFETY RULES",
         "Disconnect USB before rewiring. Use one resistor per LED. Never connect an LED directly to a pin. "
         "Do not connect mains voltage, motors, or relay loads in this activity.",
         ORANGE, PALE_ORANGE, 12)
add_text(slide, "Long LED leg = anode (+)     Short leg / flat edge = cathode (−)",
         1.0, 3.7, 11.0, 0.35, size=14, bold=True, color=TEAL)
add_card(slide, 0.95, 4.45, 11.25, 0.9, "UNO PIN BUDGET",
         "Each output pin drives only its own LED through a resistor. Stay within Arduino Uno pin-current limits; "
         "use the instructor-approved circuit and do not power external loads from GPIO pins.",
         BLUE, PALE_BLUE, 12)

slide = add_slide(
    "12 · Wire the first LED",
    "Build and inspect one complete circuit",
    "Keep the Arduino disconnected from USB until the wiring has been checked.",
)
add_code(slide, """Arduino D2 ── 220–330 Ω resistor ── LED anode (+)
Arduino GND ─────────────────────────── LED cathode (−)""",
         y=2.0, h=1.45, size=16)
add_card(slide, 0.95, 3.9, 5.45, 1.0, "CHECK THE PATH",
         "D2 → resistor → long LED leg → short LED leg → GND",
         BLUE, PALE_BLUE, 12)
add_card(slide, 6.75, 3.9, 5.45, 1.0, "BEFORE POWER",
         "Check polarity, resistor placement, and that no rail is shorted.",
         TEAL, PALE_TEAL, 12)
add_text(slide, "When the one-LED test works, duplicate the circuit on D3–D7.",
         1.0, 5.45, 11.0, 0.3, size=13, color=ORANGE, bold=True)

slide = add_slide(
    "13 · Scale to three or six LEDs",
    "One product slot maps to one output pin",
    "Start with one LED. Add more only after the first output works.",
)
pin_map = [
    ("Slot 1", "D2"),
    ("Slot 2", "D3"),
    ("Slot 3", "D4"),
    ("Slot 4", "D5"),
    ("Slot 5", "D6"),
    ("Slot 6", "D7"),
]
for index, (slot, pin) in enumerate(pin_map):
    column = index % 3
    row = index // 3
    x = 0.95 + column * 3.85
    y = 2.15 + row * 1.3
    add_card(slide, x, y, 3.5, 0.88, slot, f"{pin} → resistor → LED → GND",
             [BLUE, TEAL, ORANGE][column],
             [PALE_BLUE, PALE_TEAL, PALE_ORANGE][column], 11)
add_card(slide, 0.95, 5.15, 11.25, 0.9, "WIRING CHALLENGE",
         "Each LED has its own resistor and its own output pin. Keep every cathode on the common GND rail.",
         ORANGE, PALE_ORANGE, 12)

slide = add_slide(
    "14 · Write the Arduino sketch",
    "Use the same serial protocol as the Python app",
    "This classroom sketch drives LEDs directly with active-HIGH outputs; it is not the relay firmware.",
)
add_code(slide, """const byte LEDS[] = {2, 3, 4, 5, 6, 7};
const byte SLOT_COUNT = sizeof(LEDS) / sizeof(LEDS[0]);

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(100);
  for (byte i = 0; i < SLOT_COUNT; i++) {
    pinMode(LEDS[i], OUTPUT);
    digitalWrite(LEDS[i], LOW);
  }
  Serial.println("READY");
}

void loop() {
  if (!Serial.available()) return;
  String command = Serial.readStringUntil('\\n');
  command.trim();
  if (command == "PING") { Serial.println("PONG"); return; }
  if (!command.startsWith("DISPENSE,")) {
    Serial.println("ERROR,UNKNOWN_COMMAND"); return;
  }
  int slot = command.substring(9).toInt();
  if (slot < 1 || slot > SLOT_COUNT) {
    Serial.println("ERROR,INVALID_SLOT"); return;
  }
  byte led = LEDS[slot - 1];
  digitalWrite(led, HIGH);
  delay(500);
  digitalWrite(led, LOW);
  Serial.print("DONE,"); Serial.println(slot);
}""", y=1.83, h=4.85, size=10)

slide = add_slide(
    "15 · Upload and test the sketch",
    "Compile first, then upload to the Uno",
    "Use the USB cable, correct board, correct port, and the serial speed configured in the sketch.",
)
steps = [
    ("1", "Open the sketch in Arduino IDE.", BLUE, PALE_BLUE),
    ("2", "Tools → Board → Arduino Uno; Tools → Port → the Uno COM port.", TEAL, PALE_TEAL),
    ("3", "Click Verify. Resolve compile errors before uploading.", ORANGE, PALE_ORANGE),
    ("4", "Click Upload; wait for the upload-complete message.", BLUE, PALE_BLUE),
    ("5", "Open Serial Monitor at 9600 baud; select Newline as line ending.", TEAL, PALE_TEAL),
]
for index, (number, detail, accent, fill) in enumerate(steps):
    y = 1.9 + index * 0.76
    add_rect(slide, 0.95, y, 11.25, 0.58, fill)
    add_text(slide, number, 1.15, y + 0.16, 0.35, 0.22,
             size=12, bold=True, color=accent)
    add_text(slide, detail, 1.75, y + 0.13, 9.9, 0.27,
             size=12, bold=True)
add_text(slide, "Close Serial Monitor before Python opens the same COM port.",
         1.0, 6.15, 11, 0.3, size=13, color=ORANGE, bold=True)

slide = add_slide(
    "16 · Verify the serial protocol",
    "Test the board before connecting the desktop app",
    "Send each command in Serial Monitor and compare the expected response.",
)
protocol = [
    ("Board startup", "READY", "Printed after reset"),
    ("Send: PING", "PONG", "Board is responsive"),
    ("Send: DISPENSE,1", "DONE,1", "D2 LED flashes once"),
    ("Send: DISPENSE,3", "DONE,3", "D4 LED flashes once, if wired"),
    ("Send: DISPENSE,9", "ERROR,INVALID_SLOT", "Invalid slot is rejected"),
]
for index, (action, response, meaning) in enumerate(protocol):
    y = 1.9 + index * 0.82
    fill = [PALE_BLUE, PALE_TEAL, PALE_ORANGE][index % 3]
    add_rect(slide, 0.95, y, 11.25, 0.62, fill)
    add_text(slide, action, 1.15, y + 0.17, 3.2, 0.22,
             size=11, bold=True)
    add_text(slide, response, 4.55, y + 0.15, 2.9, 0.24,
             size=12, bold=True, font="Consolas", color=BLUE)
    add_text(slide, meaning, 7.6, y + 0.15, 4.3, 0.24, size=11)
add_text(slide, "Every command ends with a newline. Both sides must use 9600 baud.",
         1.0, 6.25, 11, 0.27, size=12, color=MUTED)

slide = add_slide(
    "17 · Follow the Python-to-Arduino path",
    "The supplied serial module checks every response",
    "Find these functions in serial_controller.py; do not rewrite them during the workshop.",
)
add_code(slide, """serial_controller.connect("COM3", 9600)
serial_controller.check_ready()       # Python sends PING; expects PONG
serial_controller.dispense(slot)      # sends DISPENSE,<slot>
                                       # waits for DONE,<slot>
serial_controller.disconnect()""",
         y=2.0, h=2.1, size=16)
add_card(slide, 0.95, 4.55, 5.45, 1.0, "PORT",
         "Replace COM3 with the port shown by Device Manager / Arduino IDE.",
         BLUE, PALE_BLUE, 12)
add_card(slide, 6.75, 4.55, 5.45, 1.0, "PORT OWNERSHIP",
         "Close Arduino Serial Monitor before launching the Python app.",
         TEAL, PALE_TEAL, 12)

slide = add_slide(
    "18 · Optional instructor-led integration",
    "Demonstrate QRIS sandbox to LED output",
    "Only the instructor should run this step with approved sandbox credentials.",
)
integration = [
    ("MODE_DEMO=0", "Enables the application's dispenser path."),
    ("SUMOPOD_SANDBOX=1", "Keeps the payment endpoint in sandbox."),
    ("Arduino connected", "The app must receive READY and answer PING with PONG."),
    ("Sandbox payment confirmed", "The selected slot LED flashes after the payment is confirmed."),
]
for index, (setting, detail) in enumerate(integration):
    y = 1.95 + index * 0.83
    add_rect(slide, 0.95, y, 3.4, 0.6,
             [PALE_BLUE, PALE_TEAL, PALE_ORANGE, PALE_BLUE][index])
    add_rect(slide, 4.55, y, 7.65, 0.6,
             [PALE_BLUE, PALE_TEAL, PALE_ORANGE, PALE_BLUE][index])
    add_text(slide, setting, 1.15, y + 0.17, 3.0, 0.22,
             size=11, bold=True, font="Consolas")
    add_text(slide, detail, 4.75, y + 0.15, 7.1, 0.25, size=12)
add_card(slide, 0.95, 5.55, 11.25, 0.82, "STOP SAFELY",
         "Never change SUMOPOD_SANDBOX to 0 during this workshop. Do not share API keys. "
         "Sandbox payments can still create test transactions and must use approved test credentials.",
         ORANGE, PALE_ORANGE, 11)

slide = add_slide(
    "19 · Troubleshooting",
    "Check one layer at a time",
    "Read the exact error and verify the nearest connection before changing code.",
)
troubleshooting = [
    ("Python command not found", "Check Python 3.11.9 installation and the py launcher."),
    ("Package import error", "Use the .venv Python executable and install requirements.txt."),
    ("Upload / COM error", "Check USB data cable, board selection, port selection, and driver."),
    ("No READY / PONG", "Close Serial Monitor; verify 9600 baud, newline, and the uploaded sketch."),
    ("Wrong LED lights", "Compare the slot-to-pin map and check LED polarity / wiring."),
]
for index, (problem, action) in enumerate(troubleshooting):
    y = 1.92 + index * 0.78
    fill = [PALE_BLUE, PALE_TEAL, PALE_ORANGE][index % 3]
    add_rect(slide, 0.95, y, 3.55, 0.58, fill)
    add_rect(slide, 4.7, y, 7.5, 0.58, fill)
    add_text(slide, problem, 1.12, y + 0.17, 3.2, 0.22,
             size=11, bold=True)
    add_text(slide, action, 4.9, y + 0.14, 7.1, 0.28, size=11)

slide = add_slide(
    "20 · Evaluation",
    "Explain the system back in your own words",
    "Use the diagram and your successful test as evidence of understanding.",
)
add_card(slide, 0.95, 1.95, 5.45, 1.15, "PYTHON APPLICATION",
         "Where are the products, cart rules, UI, payment configuration, and serial calls?",
         BLUE, PALE_BLUE, 12)
add_card(slide, 6.75, 1.95, 5.45, 1.15, "ARDUINO SKETCH",
         "What do setup(), loop(), pinMode(), digitalWrite(), and Serial do?",
         TEAL, PALE_TEAL, 12)
add_card(slide, 0.95, 3.55, 5.45, 1.15, "COMMUNICATION",
         "What does PING/PONG verify? Why does DISPENSE include a slot number?",
         ORANGE, PALE_ORANGE, 12)
add_card(slide, 6.75, 3.55, 5.45, 1.15, "PAYMENT AND SAFETY",
         "When may the output happen? Why must sandbox and production credentials stay separate?",
         BLUE, PALE_BLUE, 12)
add_text(slide, "Success criteria: app runs · circuit is safe · sketch uploads · serial test passes",
         1.0, 5.45, 11.2, 0.3, size=13, color=TEAL, bold=True)

slide = add_slide(
    "21 · Reflection and Q&A",
    "What worked, and what would you improve?",
    "Take one minute to reflect, then bring your questions.",
)
add_card(slide, 0.95, 2.0, 5.45, 1.15, "REFLECT",
         "Which part was easiest? Which part failed first? How did you isolate the problem?",
         BLUE, PALE_BLUE, 13)
add_card(slide, 6.75, 2.0, 5.45, 1.15, "NEXT CHALLENGE",
         "Add three LEDs, then six. Map each product slot to one LED and confirm the serial response.",
         TEAL, PALE_TEAL, 13)
add_text(slide, "Questions and answers", 1.0, 4.05, 11.0, 0.65,
         size=30, color=BLUE, bold=True, align=PP_ALIGN.CENTER)
add_text(slide, "Ajang Rahmat, S.Kom  ·  Electrical Engineering, Nusa Putra University  ·  nutral.id",
         1.0, 5.25, 11.0, 0.35, size=12, color=MUTED,
         align=PP_ALIGN.CENTER)

deck.save(DECK_PATH)
print(f"Created {len(deck.slides)} slides at {DECK_PATH}")
