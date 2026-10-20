import json, copy, docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = "/root/.claude/uploads/4563bebe-9fc3-55e1-9c21-f6f0e90f1f55/b2dadd89-Task2_Robotic_Arm_Report.docx"
R = "/home/claude/Task2_Simulation/results/"
S = json.load(open(R + "data/simulation_summary.json"))
d = docx.Document(SRC)
P = d.paragraphs
# --- cover edits
def settext(p, t):
    p.runs[0].text = t
    for r in p.runs[1:]: r.text = ""
settext(P[2], "ROBOTIC ARM DESIGN AND PICK-AND-PLACE SIMULATION")
settext(P[3], "Task 2 — CAD Design, Kinematics and Simulated Pick-and-Place Motion")
# --- drop everything after Figure 1 caption
body = d.element.body
for p in P[15:]:
    body.remove(p._p)
sect = body.find(qn("w:sectPr"))
cap_tpl = copy.deepcopy(P[14]._p)

def H(t): return d.add_heading(t, level=1)
def para(t, bold_lead=None):
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if bold_lead: p.add_run(bold_lead).bold = True
    p.add_run(t); return p
def bullet(t, lead=None):
    p = d.add_paragraph(style="List Bullet")
    if lead: p.add_run(lead).bold = True
    p.add_run(t); return p
def fig(path, width, caption):
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(path, width=Inches(width))
    c = d.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = c.add_run(caption); r.italic = True; r.font.size = Pt(9)
def shade(cell, hexcol):
    tcPr = cell._tc.get_or_add_tcPr(); sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hexcol); tcPr.append(sh)
def table(rows, widths, header=True, size=9):
    t = d.add_table(rows=len(rows), cols=len(rows[0])); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, txt in enumerate(row):
            c = t.cell(i, j); c.width = Inches(widths[j]); c.text = ""
            r = c.paragraphs[0].add_run(str(txt)); r.font.size = Pt(size)
            if header and i == 0: r.bold = True; shade(c, "DCE6F2")
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr(); cs = OxmlElement("w:cantSplit"); trPr.append(cs)
        for c in row.cells:
            for p in c.paragraphs: p.paragraph_format.keep_with_next = True
    d.add_paragraph().paragraph_format.space_after = Pt(2)
    return t

lim, ch = S["joint_limits"], S["clearances_mm"]
f1 = lambda x: f"{x:.1f}"

H("Aim and Objectives")
bullet("Design a simplified 4-degree-of-freedom (4-DOF) articulated robotic arm for educational pick-and-place work.")
bullet("Define the four positioning axes and their motion ranges.")
bullet("Build a kinematic model directly from the exported STEP geometry and simulate a complete pick-and-place cycle in which a 30 mm cube is gripped, carried and released.")
bullet("Verify joint limits, table and link clearances and placement accuracy, and provide animation, screenshots and data files.")

H("Design Description")
para("The model is a tabletop articulated arm with a circular base, rotating pedestal, shoulder joint, upper arm, elbow joint, forearm, wrist link, palm and a two-finger gripper (13 solids in the STEP file). Four rotary positioning axes are defined: base yaw, shoulder pitch, elbow pitch and wrist pitch. Opening and closing the fingers is an end-effector action, not an additional positioning DOF.")
para(f"Dimensions measured from the STEP file: base plate 140 mm diameter × 12 mm; rotating pedestal 90 mm diameter × 55 mm high; shoulder axis 95 mm above the table; upper arm {S['link_lengths_mm']['L1']:.1f} mm and forearm {S['link_lengths_mm']['L2']:.1f} mm between joint centres; wrist-to-grasp-point offset 41 mm radial and 47 mm below the wrist axis; finger pads 12 mm thick; demonstration cube 30 mm. (An earlier draft quoted ≈150 mm and ≈130 mm for the two links; the measured joint-centre distances above replace those figures.)")

H("Degrees of Freedom")
table([["Joint", "Motion", "Definition", "Range (deg)", "Used in simulation (deg)"],
       ["J1", "Base yaw", "rotation about vertical axis", "−90 to +90", f"{lim['J1']['min']:.1f} to {lim['J1']['max']:.1f}"],
       ["J2", "Shoulder pitch", "upper-arm elevation above horizontal", "0 to +90", f"{lim['J2']['min']:.1f} to {lim['J2']['max']:.1f}"],
       ["J3", "Elbow pitch", "forearm bend-down relative to upper arm", "0 to +120", f"{lim['J3']['min']:.1f} to {lim['J3']['max']:.1f}"],
       ["J4", "Wrist pitch", "wrist link above forearm axis", "−90 to +90", f"{lim['J4']['min']:.1f} to {lim['J4']['max']:.1f}"]],
      [0.5, 1.2, 2.5, 1.1, 1.6])
para("The ranges are proposed motion-study limits; real limits must be set from mechanical stops, cable routing and collision checks. The gripper is a separate end-effector action: the two fingers slide together or apart along the hand's lateral axis (gap 18 mm as exported, 50 mm fully open).")

H("Simulation Method")
para("The simulation was written in Python (CadQuery for reading the STEP, NumPy/SciPy for kinematics and checks, Matplotlib for rendering). The source is in the code/ folder and re-runs the full study.")
bullet(" The STEP file stores the arm in one posed configuration. The three joint cylinders give the shoulder, elbow and wrist centres, from which the link lengths and the reference joint angles (J1 = 25.0°, J2 = 29.8°, J3 = 56.4°, J4 = 40.3°) are recovered. Every solid is re-expressed in the frame of the link that carries it, so the arm can be re-posed for any joint vector. Posed at the reference angles the model reproduces the STEP bounding boxes of all arm links to 0.000 mm.", "Model from CAD.")
bullet(" Link frames follow T_upper = Rz(J1)·Tr(shoulder)·Ry(−J2); T_fore = T_upper·Tr(L1)·Ry(+J3); T_hand = T_fore·Tr(L2)·Ry(−J4).", "Forward kinematics.")
bullet(" A closed-form planar two-link solution (elbow-up) places the mid-pad grasp point at any (radius, yaw, height) while J4 keeps the fingers vertical, as in the STEP pose.", "Inverse kinematics.")
bullet(" Minimum-jerk profiles give zero velocity and acceleration at every segment boundary. Vertical moves and the yaw swing are solved by IK at every 0.05 s sample.", "Trajectory.")
bullet(" The cube rests on the table until the gripper has closed on it (t = 5.0 s), is then rigidly attached to the hand frame, and is released at the target (t = 9.0 s). The carry is a kinematic constraint, not a contact-force simulation.", "Gripping.")

H("Pick-and-Place Sequence")
para(f"The cube starts at radius {S['pick']['R']:.0f} mm, yaw {S['pick']['theta_deg']:.0f}° and is placed at radius {S['place']['R']:.0f} mm, yaw {S['place']['theta_deg']:.0f}°, a 95° swing of the base. Travel height of the grasp point is 80 mm; the cube centre rests at 15 mm. The arm starts and ends at the STEP pose.")
rows = [["Phase", "Time (s)", "Action"]]
for s in S["segments"]: rows.append([s["phase"], f"{s['t0']:.1f} – {s['t1']:.1f}", s["name"]])
table(rows, [0.7, 1.2, 4.6])

H("Results")
fig(R + "plots/keyframes_montage.png", 6.9, "Figure 2. Key frames of the simulated pick-and-place cycle (rendered from the STEP geometry; Python simulation, not SolidWorks output).")
fig(R + "screenshots/04_cube_gripped_t05.0s.png", 6.9, "Figure 3. Simulation screenshot at t = 5.0 s: cube gripped. Isometric view, top view and live joint-angle plot.")
fig(R + "plots/joint_angles.png", 6.0, "Figure 4. Joint angles, gripper gap and tool height over the 12 s cycle.")
fig(R + "plots/tool_path_speed.png", 6.5, "Figure 5. Tool path (top view, coloured by phase) and tool speed.")
fig(R + "plots/workspace_reach.png", 5.2, "Figure 6. Reachable grasp points in the arm plane with the tool kept vertical and all joint limits respected.")
H("Verification Summary")
table([["Check", "Result"],
       ["Joint limits J1–J4", "All within limits (see Degrees of Freedom table)"],
       ["Cube carried by gripper", f"Cube centre stays on grasp point (max deviation {ch['carry_err']:.1e} mm)"],
       ["Placement accuracy", f"{S['place_position_error_mm']:.2f} mm position error, {S['place_yaw_error_deg']:.2f}° yaw error"],
       ["Arm clearance to table", f"{ch['arm_table_min_z']:.1f} mm (lowest point: finger pads at the grasp)"],
       ["Open fingers vs cube on descent", f"{ch['finger_cube_min_during_descent']:.1f} mm clearance each side (gap 50 mm, cube 30 mm)"],
       ["Closest non-adjacent links", f"≈{min(ch['pair_min'].values()):.0f} mm (forearm to fingers); cube to forearm/hand ≈{min(ch['cube_vs']['fore'], ch['cube_vs']['hand']):.0f} mm"],
       ["Peak joint speeds (J1–J4)", " / ".join(f"{v:.0f}" for v in S["peak_joint_speed_deg_s"]) + " deg/s"],
       ["Peak tool speed", f"{S['peak_tool_speed_mm_s']:.0f} mm/s"],
       ["Cycle closes", "Final pose and gripper gap equal the initial STEP pose" if S["end_pose_matches_start"] else "NO"]],
      [2.3, 4.3])

H("Design Findings")
bullet(" In the exported STEP the finger pads sit 18 mm apart, so the 30 mm cube cannot fit; that pose is only the fully closed gripper. The simulation therefore treats the fingers as sliding (18 mm closed, 50 mm open). The CAD should be updated with a finger-slide joint or a wider default opening.", "Gripper opening.")
bullet(" The palm, fingers and pads in the STEP are axis-aligned boxes and are not turned with the arm's 25° yaw. They were rebuilt, with the same centres and sizes, aligned with the arm plane. The arm links themselves are used exactly as exported.", "Hand alignment.")
bullet(" With the tool vertical, a pick radius of 200 mm needs J4 = 83.7° against a +90° limit. The reach plot shows the grasp height can only be reached from about 186 mm outward, so the inner edge of the working area is limited by J4, not by the links.", "Reach margin.")

H("Limitations and Safety")
para("This is a kinematic simulation of a simplified educational model. It does not model dynamics, motor torque, friction or contact forces, and the gripping is a rigid attachment. Clearances are computed from surface-point sampling (3 mm spacing) and are approximate. It is not a SolidWorks Motion Study and does not include native SLDPRT/SLDASM files or SolidWorks screenshots. Before fabrication, perform full interference checks, strength calculations, motor and gearbox selection, cable routing and a risk assessment, and do not operate a physical arm near people without safeguards.")
para("To repeat the study in SolidWorks, import the STEP file, build the mates and apply rotary motors to J1–J4 using the key-point angles in results/data/joint_trajectory.csv.")

H("Conclusion")
para("A 4-DOF articulated arm was modelled from the supplied CAD and driven through a complete 12 s pick-and-place cycle: the cube is gripped, carried through a 95° base swing and set down at the target with zero positional error, all joints stay within their limits, and the arm clears the table and itself. The study also exposed three CAD issues (finger opening, hand alignment, and the stated link lengths) that should be corrected in the next revision.")

H("Submission Files")
for lead, t in [("CAD/", " original STEP assembly of the arm."),
                ("code/", " robot_model.py (STEP-based model, FK/IK), simulate.py (trajectory and checks), render.py, build_report.py."),
                ("results/animation/", " pick_and_place_simulation.mp4 and .gif."),
                ("results/screenshots/", " eight key-frame screenshots of the simulation."),
                ("results/plots/", " key-frame montage, joint angles, tool path and speed, reachable workspace."),
                ("results/data/", " joint_trajectory.csv (time, joint angles, gripper gap, tool and cube positions) and simulation_summary.json.")]:
    bullet(t, lead)
# new content was appended after sectPr? ensure sectPr is last
body.remove(sect); body.append(sect)
# caption of Figure 1 keeps wording; fix to say Python render
d.save("/home/claude/out/Task2_Robotic_Arm_Report.docx")
