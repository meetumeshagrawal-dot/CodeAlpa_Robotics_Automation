"""
Pick-and-place motion simulation for the CodeAlpha 4-DOF arm.

Generates a 12 s trajectory (min-jerk profiles), runs forward kinematics on the
STEP-derived model, grips and carries a 30 mm cube, runs clearance / limit
checks and writes results/data/*.csv|json|npz.
"""
import os, json, csv
import numpy as np
from scipy.spatial import cKDTree
from robot_model import (Arm, LIMITS_DEG, GAP_STEP, GAP_OPEN, CUBE, Rz, Tr, apply, box_mesh)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "data")
os.makedirs(OUT, exist_ok=True)

DT = 0.05                       # s
T_END = 12.0
R_PICK, TH_PICK = 200.0, np.radians(-35.0)     # pick  : polar position of cube centre (mm, rad)
R_PLACE, TH_PLACE = 200.0, np.radians(60.0)    # place
Z_CUBE = CUBE / 2               # cube centre height when resting on the table
Z_HOVER = 80.0                  # grasp-point height while travelling
GAP_GRASP = CUBE                # fingers close to exactly the cube width

# (name, t_start, t_end, phase number as in the report)
SEGMENTS = [
    ("hold at home, gripper opens", 0.0, 2.0, 1),
    ("move above pick point",       2.0, 3.5, 2),
    ("descend to cube",             3.5, 4.3, 2),
    ("close gripper on cube",       4.3, 5.0, 2),
    ("lift cube",                   5.0, 6.0, 3),
    ("transfer (base yaw swing)",   6.0, 8.0, 3),
    ("lower cube to table",         8.0, 9.0, 4),
    ("open gripper, release",       9.0, 10.0, 4),
    ("raise to clear height",      10.0, 10.8, 5),
    ("return to home pose",        10.8, 12.0, 5),
]
T_GRASP, T_RELEASE = 5.0, 9.0   # cube is rigidly carried for T_GRASP <= t < T_RELEASE


def minjerk(tau):
    tau = np.clip(tau, 0, 1)
    return 10 * tau**3 - 15 * tau**4 + 6 * tau**5


def build(arm):
    q_home = arm.q_ref.copy()
    q_hover_pick = arm.ik(R_PICK, TH_PICK, Z_HOVER)
    q_pick = arm.ik(R_PICK, TH_PICK, Z_CUBE)
    q_hover_place = arm.ik(R_PLACE, TH_PLACE, Z_HOVER)
    q_place = arm.ik(R_PLACE, TH_PLACE, Z_CUBE)
    t = np.arange(0, T_END + 1e-9, DT)
    Q = np.zeros((len(t), 4)); GAP = np.zeros(len(t)); PH = np.zeros(len(t), int); SEG = np.zeros(len(t), int)

    def seg(i):
        for k, (_, a, b, ph) in enumerate(SEGMENTS):
            if a - 1e-9 <= t[i] < b - 1e-9 or (k == len(SEGMENTS) - 1 and t[i] >= a):
                return k
    for i in range(len(t)):
        k = seg(i); name, a, b, ph = SEGMENTS[k]
        s = minjerk((t[i] - a) / (b - a)); SEG[i] = k; PH[i] = ph
        lerp = lambda x, y: x + (y - x) * s
        if k == 0:    Q[i], GAP[i] = q_home, GAP_STEP + (GAP_OPEN - GAP_STEP) * minjerk((t[i] - 0.5) / 1.0)
        elif k == 1:  Q[i], GAP[i] = lerp(q_home, q_hover_pick), GAP_OPEN
        elif k == 2:  Q[i], GAP[i] = arm.ik(R_PICK, TH_PICK, lerp(Z_HOVER, Z_CUBE)), GAP_OPEN
        elif k == 3:  Q[i], GAP[i] = q_pick, lerp(GAP_OPEN, GAP_GRASP)
        elif k == 4:  Q[i], GAP[i] = arm.ik(R_PICK, TH_PICK, lerp(Z_CUBE, Z_HOVER)), GAP_GRASP
        elif k == 5:  Q[i], GAP[i] = arm.ik(lerp(R_PICK, R_PLACE), lerp(TH_PICK, TH_PLACE), Z_HOVER), GAP_GRASP
        elif k == 6:  Q[i], GAP[i] = arm.ik(R_PLACE, TH_PLACE, lerp(Z_HOVER, Z_CUBE)), GAP_GRASP
        elif k == 7:  Q[i], GAP[i] = q_place, lerp(GAP_GRASP, GAP_OPEN)
        elif k == 8:  Q[i], GAP[i] = arm.ik(R_PLACE, TH_PLACE, lerp(Z_CUBE, Z_HOVER)), GAP_OPEN
        elif k == 9:  Q[i], GAP[i] = lerp(q_hover_place, q_home), GAP_OPEN + (GAP_STEP - GAP_OPEN) * s
    # joint-space legs: make the hover pose of the place leg exact
    return t, Q, GAP, PH, SEG, dict(home=q_home, hover_pick=q_hover_pick, pick=q_pick,
                                    hover_place=q_hover_place, place=q_place)


def cube_poses(arm, t, Q, GAP):
    """Cube pose (4x4) per sample: on table at pick, rigidly carried by the hand, then resting at place."""
    pick_pose = Rz(TH_PICK) @ Tr(0, 0, 0)
    pick_pose = Tr(R_PICK * np.cos(TH_PICK), R_PICK * np.sin(TH_PICK), Z_CUBE) @ Rz(TH_PICK)
    i_g = int(round(T_GRASP / DT)); i_r = int(round(T_RELEASE / DT))
    Th_g = arm.link_transforms(Q[i_g], GAP[i_g])["hand"]
    rel = np.linalg.inv(Th_g) @ pick_pose                 # cube pose in the hand frame at the grasp instant
    poses = []; place_pose = None
    for i in range(len(t)):
        if i < i_g:      P = pick_pose
        elif i < i_r:    P = arm.link_transforms(Q[i], GAP[i])["hand"] @ rel
        else:
            if place_pose is None:
                place_pose = arm.link_transforms(Q[i_r], GAP[i_r])["hand"] @ rel
            P = place_pose
        poses.append(P)
    return np.array(poses), pick_pose, place_pose


def sample_surface(V, F, spacing=3.0, seed=0):
    rng = np.random.default_rng(seed)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    n = np.maximum(1, np.ceil(area / spacing**2)).astype(int)
    idx = np.repeat(np.arange(len(F)), n)
    u, v = rng.random((2, len(idx))); m = u + v > 1; u[m], v[m] = 1 - u[m], 1 - v[m]
    return a[idx] + u[:, None] * (b[idx] - a[idx]) + v[:, None] * (c[idx] - a[idx])


def run_checks(arm, t, Q, GAP, cube_P):
    groups = {"base": ["01_BasePlate"], "yaw": ["02_RotatingBase", "03_ShoulderJoint"],
              "upper": ["04_UpperArm", "05_ElbowJoint"], "fore": ["06_Forearm", "07_WristJoint"],
              "hand": ["08_WristLink", "09_GripperPalm"],
              "fingL": ["10_GripperFinger_Left", "12_FingerPad_Left"],
              "fingR": ["11_GripperFinger_Right", "13_FingerPad_Right"]}
    pts = {}
    for g, names in groups.items():
        pts[g] = np.vstack([sample_surface(*arm.parts[n][:2], seed=k) for k, n in enumerate(names)])
    cubeV, cubeF = arm.cube_local
    cube_pts = sample_surface(cubeV, cubeF, 3.0)
    adjacent = {frozenset(p) for p in [("base", "yaw"), ("yaw", "upper"), ("upper", "fore"), ("fore", "hand"),
                                       ("hand", "fingL"), ("hand", "fingR"), ("fingL", "fingR")]}
    order = list(groups)
    pairs = [(a, b) for i, a in enumerate(order) for b in order[i + 1:] if frozenset((a, b)) not in adjacent]
    res = {"arm_table_min_z": 1e9, "finger_cube_min_during_descent": 1e9, "cube_table_z": 1e9, "pair_min": {f"{a}-{b}": 1e9 for a, b in pairs},
           "cube_vs": {}, "carry_err": 0.0}
    cube_groups = ["base", "yaw", "upper", "fore", "hand"]
    for g in cube_groups: res["cube_vs"][g] = 1e9
    i_g = int(round(T_GRASP / DT)); i_r = int(round(T_RELEASE / DT))
    for i in range(len(t)):
        T = arm.link_transforms(Q[i], GAP[i]); W = {g: apply(T[g], pts[g]) for g in pts}
        res["arm_table_min_z"] = min(res["arm_table_min_z"], min(w[:, 2].min() for g, w in W.items() if g != "base"))
        for a, b in pairs:
            d = cKDTree(W[a]).query(W[b])[0].min(); k = f"{a}-{b}"
            res["pair_min"][k] = min(res["pair_min"][k], d)
        C = apply(cube_P[i], cube_pts); res["cube_table_z"] = min(res["cube_table_z"], C[:, 2].min())
        tree = cKDTree(C)
        if 3.5 <= t[i] <= 4.3:     # open fingers straddling the cube on the way down
            res["finger_cube_min_during_descent"] = min(res["finger_cube_min_during_descent"],
                                                        min(tree.query(W["fingL"])[0].min(), tree.query(W["fingR"])[0].min()))
        for g in cube_groups:
            res["cube_vs"][g] = min(res["cube_vs"][g], tree.query(W[g])[0].min())
        # while carried, the cube centre must coincide with the grasp point
        if i_g <= i < i_r:
            res["carry_err"] = max(res["carry_err"], float(np.linalg.norm(cube_P[i][:3, 3] - arm.grasp_point(Q[i]))))
    res["grip_contact_gap_mm"] = float(GAP_GRASP - CUBE)     # pad-to-pad gap minus cube width at the grasp instant
    return res


def main():
    arm = Arm()
    t, Q, GAP, PH, SEG, key = build(arm)
    cube_P, pick_P, place_P = cube_poses(arm, t, Q, GAP)
    deg = np.degrees(Q)
    # --- end-effector path
    G = np.array([arm.grasp_point(q) for q in Q])
    # --- limits
    lim = {}
    for j, (name, (lo, hi)) in enumerate(LIMITS_DEG.items()):
        lim[name] = dict(min=float(deg[:, j].min()), max=float(deg[:, j].max()), lo=lo, hi=hi,
                         ok=bool(deg[:, j].min() >= lo - 1e-6 and deg[:, j].max() <= hi + 1e-6))
    chk = run_checks(arm, t, Q, GAP, cube_P)
    # --- placement accuracy
    target = np.array([R_PLACE * np.cos(TH_PLACE), R_PLACE * np.sin(TH_PLACE), Z_CUBE])
    place_err = float(np.linalg.norm(place_P[:3, 3] - target))
    yaw_err = float(np.degrees(np.arctan2(place_P[1, 0], place_P[0, 0]) - TH_PLACE))
    # --- velocities
    vel = np.gradient(deg, DT, axis=0)
    spd = np.linalg.norm(np.gradient(G, DT, axis=0), axis=1)
    summary = dict(
        link_lengths_mm=dict(L1=float(arm.L1), L2=float(arm.L2)),
        cube_mm=CUBE, pick=dict(R=R_PICK, theta_deg=float(np.degrees(TH_PICK))),
        place=dict(R=R_PLACE, theta_deg=float(np.degrees(TH_PLACE))),
        key_poses_deg={k: np.degrees(v).round(2).tolist() for k, v in key.items()},
        joint_limits=lim, clearances_mm=chk, place_position_error_mm=place_err, place_yaw_error_deg=yaw_err,
        peak_joint_speed_deg_s=np.abs(vel).max(axis=0).round(1).tolist(), peak_tool_speed_mm_s=float(spd.max()),
        end_pose_matches_start=bool(np.allclose(Q[-1], Q[0], atol=1e-6) and abs(GAP[-1] - GAP[0]) < 1e-6),
        segments=[dict(name=n, t0=a, t1=b, phase=p) for n, a, b, p in SEGMENTS])
    with open(os.path.join(OUT, "simulation_summary.json"), "w") as f: json.dump(summary, f, indent=2)
    with open(os.path.join(OUT, "joint_trajectory.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["t_s", "phase", "segment", "J1_yaw_deg", "J2_shoulder_deg", "J3_elbow_deg",
                                       "J4_wrist_deg", "gripper_gap_mm", "tool_x_mm", "tool_y_mm", "tool_z_mm",
                                       "cube_x_mm", "cube_y_mm", "cube_z_mm"])
        for i in range(len(t)):
            w.writerow([f"{t[i]:.2f}", PH[i], SEGMENTS[SEG[i]][0], *deg[i].round(3), round(GAP[i], 2),
                        *G[i].round(2), *cube_P[i][:3, 3].round(2)])
    np.savez(os.path.join(OUT, "trajectory.npz"), t=t, Q=Q, GAP=GAP, PH=PH, SEG=SEG, G=G, cube_P=cube_P)
    print(json.dumps(summary, indent=1)[:3500])
    return summary


if __name__ == "__main__":
    main()
