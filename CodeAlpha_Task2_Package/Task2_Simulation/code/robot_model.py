"""
Kinematic model of the CodeAlpha 4-DOF robotic arm, built directly from the
supplied STEP file (CAD/CodeAlpha_4DOF_Robotic_Arm.step).

The STEP stores the arm in ONE posed configuration. This module
  1. reads the joint centres of the three joint cylinders from the STEP,
  2. derives link lengths and the reference joint angles of that pose,
  3. tessellates every solid and expresses it in the frame of the link that
     carries it ("un-posing"), so the arm can be re-posed for any joint vector.

Joint convention (all angles in radians internally, degrees in outputs)
  J1  base yaw        rotation about world +Z through the base axis
  J2  shoulder pitch  elevation of the upper arm above horizontal   (+ = up)
  J3  elbow flexion   forearm bends DOWN relative to the upper arm  (+ = down)
  J4  wrist pitch     angle of the wrist link above the forearm axis (+ = up)
Gripper: two fingers slide along the hand's lateral axis (end-effector action,
not a positioning DOF). Gap is measured between the inner pad faces.
"""
import os
import numpy as np
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
STEP_PATH = os.path.join(HERE, "..", "CAD", "CodeAlpha_4DOF_Robotic_Arm.step")

PART_NAMES = ["01_BasePlate", "02_RotatingBase", "03_ShoulderJoint", "04_UpperArm",
              "05_ElbowJoint", "06_Forearm", "07_WristJoint", "08_WristLink",
              "09_GripperPalm", "10_GripperFinger_Left", "11_GripperFinger_Right",
              "12_FingerPad_Left", "13_FingerPad_Right"]

# --- design values of the gripper (mm) -------------------------------------
FINGER_W = 10.0          # finger thickness along the opening direction
PAD_W = 12.0             # pad thickness along the opening direction
GAP_STEP = 18.0          # pad-to-pad gap as exported in the STEP (fingers at +/-15 mm)
GAP_OPEN = 50.0          # fully open
CUBE = 30.0              # demonstration cube edge

# --- joint limits from the report (deg) ------------------------------------
LIMITS_DEG = {"J1": (-90, 90), "J2": (0, 90), "J3": (0, 120), "J4": (-90, 90)}

COLORS = {  # simple palette per part
    "01_BasePlate": "#1E78D6", "02_RotatingBase": "#455A64", "03_ShoulderJoint": "#1E88E5",
    "04_UpperArm": "#1565C0", "05_ElbowJoint": "#1E88E5", "06_Forearm": "#90CAF9",
    "07_WristJoint": "#64B5F6", "08_WristLink": "#90CAF9", "09_GripperPalm": "#37474F",
    "10_GripperFinger_Left": "#546E7A", "11_GripperFinger_Right": "#546E7A",
    "12_FingerPad_Left": "#1E88E5", "13_FingerPad_Right": "#1E88E5", "Cube": "#FF8F00",
}
LINK_OF = {  # which moving frame carries each part
    "01_BasePlate": "base", "02_RotatingBase": "yaw", "03_ShoulderJoint": "yaw",
    "04_UpperArm": "upper", "05_ElbowJoint": "upper", "06_Forearm": "fore",
    "07_WristJoint": "fore", "08_WristLink": "hand", "09_GripperPalm": "hand",
    "10_GripperFinger_Left": "fingL", "12_FingerPad_Left": "fingL",
    "11_GripperFinger_Right": "fingR", "13_FingerPad_Right": "fingR",
}

# ---------------------------------------------------------------- transforms
def Rz(a):
    c, s = np.cos(a), np.sin(a); T = np.eye(4); T[:2, :2] = [[c, -s], [s, c]]; return T
def Ry(a):
    c, s = np.cos(a), np.sin(a); T = np.eye(4); T[0, 0] = c; T[0, 2] = s; T[2, 0] = -s; T[2, 2] = c; return T
def Tr(x, y, z):
    T = np.eye(4); T[:3, 3] = [x, y, z]; return T
def apply(T, P):
    return P @ T[:3, :3].T + T[:3, 3]


def box_mesh(center, dims, yaw):
    """Closed, outward-oriented box (dims = radial, lateral, vertical) turned by yaw about +Z."""
    dx, dy, dz = np.array(dims) / 2
    sg = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float)
    V = sg * [dx, dy, dz]
    V = V @ Rz(yaw)[:3, :3].T + center
    q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    F = []
    for a, b, c, d in q:
        F += [(a, b, c), (a, c, d)]
    F = np.array(F)
    return orient_outward(V, F)


def orient_outward(V, F):
    """Flip any triangle whose normal points toward the (convex) mesh centroid."""
    c = V.mean(axis=0); F = F.copy()
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    m = V[F].mean(axis=1) - c
    flip = (n * m).sum(axis=1) < 0
    F[flip] = F[flip][:, ::-1]
    return V, F


class Arm:
    def __init__(self, step_path=STEP_PATH):
        shape = cq.importers.importStep(step_path)
        solids = shape.solids().vals()
        assert len(solids) == 13, "expected the 13 solids of the CodeAlpha arm"
        cen = {n: np.array(s.Center().toTuple()) for n, s in zip(PART_NAMES, solids)}

        # ---- reference pose recovered from the joint cylinders -------------
        self.S, self.E, self.W = cen["03_ShoulderJoint"], cen["05_ElbowJoint"], cen["07_WristJoint"]
        d = self.E - self.S
        self.yaw_ref = np.arctan2(d[1], d[0])
        u = np.array([np.cos(self.yaw_ref), np.sin(self.yaw_ref), 0])
        rE, rW = d @ u, (self.W - self.S) @ u
        self.L1 = np.linalg.norm(self.E - self.S)
        self.L2 = np.linalg.norm(self.W - self.E)
        self.phi2_ref = np.arctan2(d[2], rE)
        fore_angle = np.arctan2(self.W[2] - self.E[2], rW - rE)
        self.phi3_ref = self.phi2_ref - fore_angle
        # wrist-link long axis (principal axis of its 8 vertices) -> hand axis angle
        wl = np.array([[v.X, v.Y, v.Z] for v in solids[7].Vertices()])
        w, vec = np.linalg.eigh(np.cov((wl - wl.mean(0)).T))
        ax = vec[:, -1]; ax = ax if ax @ u > 0 else -ax
        self.hand_angle_ref = np.arctan2(ax[2], ax @ u)           # absolute, wrist link above horizontal
        self.phi4_ref = self.hand_angle_ref - (self.phi2_ref - self.phi3_ref)
        # grasp point = mid-point between the two finger pads (as exported)
        padL, padR = cen["12_FingerPad_Left"], cen["13_FingerPad_Right"]
        self.G_ref = (padL + padR) / 2
        self.grasp_offset = ((self.G_ref - self.W) @ u, self.G_ref[2] - self.W[2])   # (radial, vertical) from wrist
        self.palm_c = cen["09_GripperPalm"]

        # ---- meshes in link-local frames ------------------------------------
        qref = self.q_ref
        Tref = self.link_transforms(qref, gap=GAP_STEP, ref=True)
        self.parts = {}
        for n, s in zip(PART_NAMES, solids):
            if n in ("09_GripperPalm", "10_GripperFinger_Left", "11_GripperFinger_Right",
                     "12_FingerPad_Left", "13_FingerPad_Right"):
                # STEP hand parts are axis-aligned boxes; rebuild them aligned with the arm plane
                bb = s.BoundingBox(); c = np.array(s.Center().toTuple())
                dims = {"09_GripperPalm": (32, 44, 12), "10_GripperFinger_Left": (10, FINGER_W, 50),
                        "11_GripperFinger_Right": (10, FINGER_W, 50), "12_FingerPad_Left": (12, PAD_W, 8),
                        "13_FingerPad_Right": (12, PAD_W, 8)}[n]
                V, F = box_mesh(c, dims, self.yaw_ref)
            else:
                verts, tris = s.tessellate(0.2, 0.15)
                V = np.array([[p.x, p.y, p.z] for p in verts]); F = np.array(tris)
            link = LINK_OF[n]
            Vl = apply(np.linalg.inv(Tref[link]), V)
            self.parts[n] = (Vl, F, link)
        self.cube_local = box_mesh(np.zeros(3), (CUBE,) * 3, 0.0)

    # reference joint vector (rad): J1..J4
    @property
    def q_ref(self):
        return np.array([self.yaw_ref, self.phi2_ref, self.phi3_ref, self.phi4_ref])

    def link_transforms(self, q, gap=GAP_OPEN, ref=False):
        q1, p2, p3, p4 = q
        T = {"base": np.eye(4)}
        T["yaw"] = Rz(q1)
        T["upper"] = Rz(q1) @ Tr(*self.S) @ Ry(-p2)
        T["fore"] = T["upper"] @ Tr(self.L1, 0, 0) @ Ry(p3)
        T["hand"] = T["fore"] @ Tr(self.L2, 0, 0) @ Ry(-p4)
        # the STEP fingers sit at +/-(GAP_STEP+PAD_W)/2 = +/-15 mm; slide them to the requested gap
        shift = (gap - GAP_STEP) / 2
        T["fingL"] = T["hand"] @ Tr(0, +shift, 0)
        T["fingR"] = T["hand"] @ Tr(0, -shift, 0)
        return T

    # ------------------------------------------------------------- kinematics
    def grasp_point(self, q):
        """World position of the grasp point (mid-pad) for joint vector q."""
        T = self.link_transforms(q)["hand"]
        Tref = self.link_transforms(self.q_ref, GAP_STEP, True)["hand"]
        g_local = np.linalg.inv(Tref) @ np.append(self.G_ref, 1)
        return (T @ g_local)[:3]

    def ik(self, R, theta, zg):
        """Analytic IK (elbow-up) for the grasp point at polar (R, theta, zg), tool kept vertical."""
        a, b = self.grasp_offset
        wr, wz = R - a, zg - b - self.S[2]            # wrist target in the arm plane, relative to shoulder
        d2 = wr * wr + wz * wz
        d = np.sqrt(d2)
        if d > self.L1 + self.L2 - 1e-6 or d < abs(self.L1 - self.L2) + 1e-6:
            raise ValueError(f"target R={R:.1f}, z={zg:.1f} out of reach (d={d:.1f})")
        gamma = np.arccos((self.L1**2 + self.L2**2 - d2) / (2 * self.L1 * self.L2))
        p3 = np.pi - gamma
        beta = np.arccos((d2 + self.L1**2 - self.L2**2) / (2 * d * self.L1))
        p2 = np.arctan2(wz, wr) + beta
        p4 = self.hand_angle_ref - (p2 - p3)          # keep the hand/fingers at their STEP (vertical) attitude
        return np.array([theta, p2, p3, p4])

    # --------------------------------------------------------------- posing
    def pose(self, q, gap):
        T = self.link_transforms(q, gap)
        out = {}
        for n, (Vl, F, link) in self.parts.items():
            out[n] = (apply(T[link], Vl), F)
        return out, T


if __name__ == "__main__":
    A = Arm()
    r = np.degrees
    print("S", A.S.round(2), "E", A.E.round(2), "W", A.W.round(2))
    print("L1 %.2f  L2 %.2f  yaw_ref %.2f  J2 %.2f  J3 %.2f  J4 %.2f  hand angle %.2f" % (
        A.L1, A.L2, r(A.yaw_ref), r(A.phi2_ref), r(A.phi3_ref), r(A.phi4_ref), r(A.hand_angle_ref)))
    print("grasp offset from wrist (radial, vertical):", np.round(A.grasp_offset, 2))
    print("grasp point @ref:", A.grasp_point(A.q_ref).round(3), " STEP G:", A.G_ref.round(3))
    # round-trip: pose at reference must reproduce the STEP vertices exactly
    shape = cq.importers.importStep(STEP_PATH).solids().vals()
    pp, _ = A.pose(A.q_ref, GAP_STEP)
    for n, s in zip(PART_NAMES, shape):
        bb = s.BoundingBox()
        V = pp[n][0]
        err = max(abs(V.min(0) - [bb.xmin, bb.ymin, bb.zmin]).max(), abs(V.max(0) - [bb.xmax, bb.ymax, bb.zmax]).max())
        print(f"{n:26s} bbox error vs STEP: {err:.3f} mm")
    q = A.ik(*(A.grasp_point(A.q_ref)[[0, 1, 2]] * 0 + [np.hypot(*A.G_ref[:2]), A.yaw_ref, A.G_ref[2]]))
    print("IK(ref grasp) ->", r(q).round(3), " expect", r(A.q_ref).round(3))
