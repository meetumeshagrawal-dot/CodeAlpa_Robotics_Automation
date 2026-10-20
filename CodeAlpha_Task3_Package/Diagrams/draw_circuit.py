"""Draws Circuit_Diagram.(png|svg): wiring schematic of the Arduino conveyor controller."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon

INK = "#1f2933"; W = 1.9
fig, ax = plt.subplots(figsize=(17, 12.4), dpi=150)
ax.set_xlim(-1, 171); ax.set_ylim(-6, 146); ax.set_aspect("equal"); ax.axis("off")

def line(*pts, c=INK, lw=W, z=2, ls="-"):
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=c, lw=lw, zorder=z, solid_capstyle="round", ls=ls)
def dot(x, y): ax.add_patch(Circle((x, y), 0.9, color=INK, zorder=5))
def txt(x, y, s, size=9.5, ha="left", va="center", c=INK, bold=False):
    ax.text(x, y, s, fontsize=size, ha=ha, va=va, color=c, fontweight="bold" if bold else "normal", zorder=6, linespacing=1.25)
def box(x0, y0, x1, y1, label, fc, ec, size=10, bold=False):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fc, ec=ec, lw=2.2, zorder=3))
    txt((x0 + x1) / 2, (y0 + y1) / 2, label, size, "center", c=INK, bold=bold)
def gnd(x, y):
    line((x, y), (x, y - 2.5)); 
    for i, w in enumerate((3.4, 2.2, 1.0)): line((x - w, y - 2.5 - i * 1.1), (x + w, y - 2.5 - i * 1.1), lw=1.8)
def net(x, y, label):  # supply tag with stub going up
    line((x, y), (x, y + 3)); txt(x, y + 4.4, label, 9, "center", bold=True, c="#C62828" if "12" in label else "#E65100")
def res_h(x0, x1, y, label, above=True):
    m = (x1 - x0) / 8; pts = [(x0, y)]
    for i in range(1, 8): pts.append((x0 + i * m, y + (1.8 if i % 2 else -1.8)))
    pts.append((x1, y)); line(*pts); txt((x0 + x1) / 2, y + (4.2 if above else -4.2), label, 8.5, "center")
def res_v(x, y0, y1, label, left=False):
    m = (y1 - y0) / 8; pts = [(x, y0)]
    for i in range(1, 8): pts.append((x + (1.8 if i % 2 else -1.8), y0 + i * m))
    pts.append((x, y1)); line(*pts); txt(x + (-3.2 if left else 3.2), (y0 + y1) / 2, label, 8.5, "right" if left else "left")
def diode_v(x, y0, y1, label):  # cathode (bar) at top
    ym = (y0 + y1) / 2; line((x, y0), (x, ym - 2.5)); line((x, ym + 2.5), (x, y1))
    ax.add_patch(Polygon([(x - 3, ym - 2.5), (x + 3, ym - 2.5), (x, ym + 2.5)], fc=INK, ec=INK, zorder=4)); line((x - 3, ym + 2.5), (x + 3, ym + 2.5), lw=2.6)
    txt(x - 4.5, ym, label, 8.5, "right")
def led_h(x0, x1, y, color, label):
    xm = (x0 + x1) / 2; line((x0, y), (xm - 2.5, y)); line((xm + 2.5, y), (x1, y))
    ax.add_patch(Polygon([(xm - 2.5, y - 3), (xm - 2.5, y + 3), (xm + 2.5, y)], fc=color, ec=INK, lw=1.4, zorder=4)); line((xm + 2.5, y - 3), (xm + 2.5, y + 3), lw=2.4)
    txt(xm, y + 5.4, label, 8.5, "center")
def switch_h(x0, x1, y, label, nc):
    line((x0, y), (x0 + 1.5, y)); line((x1 - 1.5, y), (x1, y)); dot(x0 + 1.5, y); dot(x1 - 1.5, y)
    line((x0 + 1.5, y), (x1 - 1.5, y + (0.6 if nc else 3.4)), lw=1.8)
    txt((x0 + x1) / 2, y + 6.2, label, 8.5, "center")
def switch_v(x, y0, y1, label):  # NC contact drawn vertically
    line((x, y0), (x, y0 - 2)); line((x, y1), (x, y1 + 2)); dot(x, y0 - 2); dot(x, y1 + 2)
    line((x, y0 - 2), (x + 0.6, y1 + 2), lw=1.8); txt(x + 4, (y0 + y1) / 2, label, 8.5)

# ---------------- title
txt(85, 143, "CONVEYOR CONTROL - WIRING DIAGRAM (low-voltage prototype)", 16, "center", c="#16365C", bold=True)
txt(85, 139.3, "Arduino Uno + logic-level MOSFET driver. Every ground symbol is the same 0 V net.", 10, "center", c="#6b7785")

# ---------------- power
box(3, 127, 14, 141, "12 V DC\nsupply\n2 A", "#FFF3E0", "#EF6C00", 9)
line((14, 134), (16, 134)); ax.add_patch(Rectangle((16, 132.4), 8, 3.2, fc="white", ec=INK, lw=1.8, zorder=4)); line((16, 134), (24, 134), lw=0.9)
txt(20, 138, "F1  2 A fuse", 8.5, "center")
line((24, 134), (78, 134)); txt(46, 137.2, "+12 V (fused)", 9, "center", c="#C62828", bold=True)
line((8.5, 127), (8.5, 124)); gnd(8.5, 124)
# E-stop in motor power path
line((44, 134), (44, 129)); dot(44, 134); switch_v(44, 120, 127, "")
txt(48, 123.5, "S1a  E-STOP (NC)\nmotor power path:\nhardware cut-off", 8.5)
line((44, 118), (44, 111)); dot(44, 114)
# motor
ax.add_patch(Circle((44, 105.5), 5.8, fc="#E3F2FD", ec="#1565C0", lw=2.2, zorder=3)); txt(44, 105.5, "M", 13, "center", bold=True)
txt(51.5, 105.5, "12 V DC\ngear motor\n(<= 1 A)", 8.5)
line((44, 111.3), (44, 114)); line((44, 99.7), (44, 94))
line((44, 114), (34, 114)); diode_v(34, 114, 94, "D1 1N5819\nflyback"); line((34, 94), (44, 94)); dot(44, 94)
line((44, 94), (44, 88))
# MOSFET
box(38, 70, 50, 88, "Q1\nIRLZ44N\nN-MOSFET", "#EDE7F6", "#5E35B1", 8.5)
txt(41, 85.3, "D", 8, "center"); txt(52, 81.5, "G", 8, "left"); txt(41, 72.7, "S", 8, "center")
line((44, 70), (44, 67)); gnd(44, 67)
line((50, 79), (62, 79)); dot(62, 79); res_v(62, 79, 65, "R2 10 k\npull-down"); line((62, 65), (62, 63)); gnd(62, 63)
line((62, 79), (76, 79)); res_h(76, 84, 79, "R1 220 Ω"); line((84, 79), (92, 79))
# buck
line((78, 134), (78, 124)); dot(78, 134)
box(71, 108, 88, 124, "5 V buck\n(LM2596)", "#FFF3E0", "#EF6C00", 8.5)
line((80, 108), (80, 105)); gnd(80, 105)
line((88, 118), (91, 118), (91, 126), (100, 126), c="#E65100"); txt(93, 128.8, "+5 V", 9, "left", c="#E65100", bold=True)

# ---------------- Arduino
box(92, 6, 126, 122, "", "#E8F5E9", "#2E7D32")
txt(109, 114, "ARDUINO UNO", 12, "center", bold=True); txt(109, 109.5, "(ATmega328P)", 9, "center", c="#37474F")
line((100, 122), (100, 126), c="#E65100"); dot(100, 126); txt(100, 118.6, "5V", 8.5, "center")
line((109, 6), (109, 3)); gnd(109, 3); txt(109, 9, "GND", 8.5, "center")
for y, name in [(112, "D2"), (96, "D3"), (80, "D4"), (64, "D5"), (54, "D8"), (42, "D9"), (10, "D10")]:
    txt(123.5, y + 2.6, name, 8.5, "right", bold=True)
txt(94.5, 82, "D6", 8.5, "left", bold=True)

# ---------------- inputs
def sensor(y, tag, name):
    box(138, y - 5, 164, y + 5, f"{tag}  {name}\nE18-D80NK, NPN-NO", "#E0F7FA", "#00838F", 8.5)
    line((126, y), (138, y)); txt(132, y - 3.4, "BLK", 7.5, "center", c="#37474F")
    line((144, y + 5), (144, y + 8)); txt(144, y + 9.6, "+5 V (BRN)", 8, "center", c="#E65100", bold=True)
    line((158, y - 5), (158, y - 7)); gnd(158, y - 7); txt(162, y - 9.5, "0 V (BLU)", 7.5, "left", c="#37474F")
sensor(112, "IR1", "object sensor")
line((126, 96), (141, 96)); switch_h(141, 153, 96, "", True); line((153, 96), (158, 96), (158, 94)); gnd(158, 94)
txt(128, 99.5, "S1b  E-STOP 2 (NC)", 8.5, "left")
sensor(80, "IR2", "exit sensor")
line((126, 64), (141, 64)); switch_h(141, 153, 64, "", False); line((153, 64), (158, 64), (158, 62)); gnd(158, 62)
txt(128, 67.5, "S2  START/RESET (NO)", 8.5, "left")

# ---------------- outputs
def led_row(y, col, name, label):
    line((126, y), (132, y)); res_h(132, 142, y, label); line((142, y), (146, y)); led_h(146, 156, y, col, "")
    txt(142, y - 5.6, name, 8.5, "left"); line((156, y), (167, y), (167, y - 3)); gnd(167, y - 3)
led_row(54, "#43A047", "LED1 green: run", "R3 330 \u03a9"); led_row(42, "#E53935", "LED2 red: stop / fault", "R4 330 \u03a9")
line((126, 10), (130, 10)); res_h(130, 140, 10, "R5 1 k\u03a9"); line((140, 10), (146, 10))
box(146, 2, 158, 18, "Q2\nBC547", "#F3E5F5", "#8E24AA", 8.5); txt(147.5, 10, "B", 8, "left")
line((152, 2), (152, -1)); gnd(152, -1)
line((152, 18), (152, 21)); box(142, 21, 162, 27, "BZ1 5 V active buzzer", "#F3E5F5", "#8E24AA", 7.5)
line((152, 27), (152, 30)); txt(152, 32.2, "+5 V", 9, "center", c="#E65100", bold=True)
# gate label
txt(2, 7, "Notes\n1. Motor is switched by Q1, never driven from a pin.\n2. S1 is a 2-contact NC E-stop: S1a breaks motor power, S1b tells the Arduino.\n3. D1 must sit across the motor (cathode to +12 V) to absorb switch-off spikes.\n4. Size F1, Q1 and D1 for the real motor stall current; use a contactor for larger motors.\n5. IR1/IR2 outputs go LOW on detection (INPUT_PULLUP).\n6. S1b reads LOW when healthy, HIGH when pressed or a wire breaks.", 8.5, "left", c="#37474F")
fig.savefig("Circuit_Diagram.png", bbox_inches="tight", pad_inches=0.15); fig.savefig("Circuit_Diagram.svg", bbox_inches="tight", pad_inches=0.15)
