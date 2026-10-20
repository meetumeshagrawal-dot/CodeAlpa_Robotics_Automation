"""Renders frames, animation, screenshots and plots from results/data/trajectory.npz."""
import os, sys, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgb
from robot_model import Arm, COLORS, LIMITS_DEG, GAP_STEP, GAP_OPEN, CUBE, apply, Rz
import simulate as sim

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
D = np.load(os.path.join(ROOT, "data", "trajectory.npz"))
t, Q, GAP, PH, SEG, G, cubeP = (D[k] for k in ("t", "Q", "GAP", "PH", "SEG", "G", "cube_P"))
arm = Arm()
LIGHT = np.array([-0.35, -0.55, 0.76]); LIGHT /= np.linalg.norm(LIGHT)
PHASE_NAMES = {1: "Phase 1 - home, gripper opens", 2: "Phase 2 - approach and grip",
               3: "Phase 3 - lift and transfer", 4: "Phase 4 - lower and release", 5: "Phase 5 - return home"}
XMIN, XMAX, YMIN, YMAX = -100, 300, -220, 300
INK, MUTED, GRID = "#1f2933", "#6b7785", "#d5dae0"


def camera(azim, elev):
    a, e = np.radians(azim), np.radians(elev)
    c = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    right = np.cross([0, 0, 1], c); right /= np.linalg.norm(right)   # screen x
    up = np.cross(c, right)
    return c, right, up


def scene_triangles(i):
    """All world-space triangles (Nx3x3) with colours for sample i."""
    parts, _ = arm.pose(Q[i], GAP[i])
    tris, cols = [], []
    for n, (V, F) in parts.items():
        tris.append(V[F]); cols += [COLORS[n]] * len(F)
    cv, cf = arm.cube_local
    tris.append(apply(cubeP[i], cv)[cf]); cols += [COLORS["Cube"]] * len(cf)
    return np.concatenate(tris), cols


def draw_scene(ax, i, azim, elev, trail=True, labels=True, span=None, shadow=True, lw=0.0):
    c, right, up = camera(azim, elev)
    tris, cols = scene_triangles(i)
    P = lambda X: np.stack([X @ right, X @ up], -1)
    # ground plate + grid
    ground = np.array([[XMIN, YMIN, 0], [XMAX, YMIN, 0], [XMAX, YMAX, 0], [XMIN, YMAX, 0]], float)
    ax.add_collection(PolyCollection([P(ground)], facecolors="#f3f5f7", edgecolors="none", zorder=0))
    for g in range(-250, 351, 50):
        segs = []
        if XMIN <= g <= XMAX: segs.append(([g, YMIN, 0], [g, YMAX, 0]))
        if YMIN <= g <= YMAX: segs.append(([XMIN, g, 0], [XMAX, g, 0]))
        for a, b in segs:
            p = P(np.array([a, b], float)); ax.plot(p[:, 0], p[:, 1], color=GRID, lw=0.6, zorder=1)
    # pick / place markers
    for name, R, th, col in (("PICK", sim.R_PICK, sim.TH_PICK, "#2E7D32"), ("PLACE", sim.R_PLACE, sim.TH_PLACE, "#C62828")):
        s = CUBE / 2 + 4
        sq = np.array([[-s, -s, 0], [s, -s, 0], [s, s, 0], [-s, s, 0], [-s, -s, 0]]) @ Rz(th)[:3, :3].T + [R * np.cos(th), R * np.sin(th), 0]
        p = P(sq); ax.plot(p[:, 0], p[:, 1], color=col, lw=1.6, ls="--", zorder=2)
        if labels:
            q = P(np.array([[R * np.cos(th), R * np.sin(th), 0]]) + [0, 0, 0])[0]
            ax.text(q[0], q[1] - 30 * (1 if elev > 60 else 1.0), name, color=col, fontsize=7.5, ha="center", va="top", zorder=3, fontweight="bold")
    # end-effector trail
    if trail:
        p = P(G[: i + 1]); ax.plot(p[:, 0], p[:, 1], color="#8E24AA", lw=1.3, zorder=4, alpha=0.9)
    # shadows (vertical projection, opaque pale grey)
    if shadow:
        sh = tris.copy(); sh[..., 2] = 0.05
        ax.add_collection(PolyCollection(P(sh.reshape(-1, 3)).reshape(-1, 3, 2), facecolors="#d3d8de", edgecolors="none", zorder=3))
    # shaded, culled, depth-sorted triangles
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    vis = n @ c > 0
    depth = tris.mean(axis=1) @ c
    order = np.argsort(depth[vis]); idx = np.flatnonzero(vis)[order]
    shade = 0.42 + 0.58 * np.clip(n[idx] @ LIGHT, 0, 1)
    rgb = np.array([to_rgb(cols[k]) for k in idx]) * shade[:, None]
    ax.add_collection(PolyCollection(P(tris[idx].reshape(-1, 3)).reshape(-1, 3, 2), facecolors=np.clip(rgb, 0, 1),
                                     edgecolors=np.clip(rgb, 0, 1), linewidths=0.25, zorder=5))
    ax.set_aspect("equal"); ax.axis("off")
    return P


def frame(i, size=(12.8, 7.2), dpi=100, panels="full"):
    fig = plt.figure(figsize=size, dpi=dpi, facecolor="white")
    if panels == "full":
        gs = fig.add_gridspec(2, 2, width_ratios=[1.6, 1], height_ratios=[1, 1], left=0.01, right=0.985, top=0.9, bottom=0.07,
                              wspace=0.06, hspace=0.22)
        a3 = fig.add_subplot(gs[:, 0]); at = fig.add_subplot(gs[0, 1]); aj = fig.add_subplot(gs[1, 1])
    else:
        a3 = fig.add_axes([0.0, 0.0, 1, 0.93]); at = aj = None
    draw_scene(a3, i, azim=-58, elev=24)
    a3.set_xlim(-250, 360); a3.set_ylim(-60, 260) if False else None
    # fixed framing: use projection of the work volume
    c, right, up = camera(-58, 24)
    pts = np.array([[x, y, z] for x in (XMIN, XMAX) for y in (YMIN, YMAX) for z in (0, 185)], float)
    px, py = pts @ right, pts @ up
    pad = 8; a3.set_xlim(px.min() - pad, px.max() + pad); a3.set_ylim(py.min() - pad, py.max() + pad)
    a3.set_title("Isometric view", loc="left", fontsize=9, color=MUTED, pad=2)
    if at is not None:
        draw_scene(at, i, azim=-90, elev=90, labels=True)
        at.set_xlim(-110, 330); at.set_ylim(-190, 290) if False else None
        # top view: screen x = world y? use camera basis to set limits
        c2, r2, u2 = camera(-90, 90)
        pts2 = np.array([[x, y, 0] for x in (XMIN, XMAX) for y in (YMIN, YMAX)], float)
        at.set_xlim((pts2 @ r2).min() - 6, (pts2 @ r2).max() + 6); at.set_ylim((pts2 @ u2).min() - 6, (pts2 @ u2).max() + 6)
        at.set_title("Top view (plan)", loc="left", fontsize=9, color=MUTED, pad=2)
        # joint-angle strip
        deg = np.degrees(Q)
        for k, col in zip(range(4), ["#1565C0", "#2E7D32", "#EF6C00", "#8E24AA"]):
            aj.plot(t, deg[:, k], color=col, lw=1.6, label=["J1 yaw", "J2 shoulder", "J3 elbow", "J4 wrist"][k])
        aj.axvline(t[i], color=INK, lw=1.2)
        aj.set_xlim(0, 12); aj.set_ylim(-50, 115)
        aj.set_xlabel("time (s)", fontsize=8, color=MUTED); aj.set_ylabel("joint angle (deg)", fontsize=8, color=MUTED)
        aj.tick_params(labelsize=7.5, colors=MUTED); aj.grid(color="#e8ebee", lw=0.6)
        for sp in ("top", "right"): aj.spines[sp].set_visible(False)
        aj.legend(fontsize=7, ncol=4, loc="upper center", frameon=False, bbox_to_anchor=(0.5, 1.13), handlelength=1.2, columnspacing=0.9)
    seg = sim.SEGMENTS[SEG[i]][0]
    fig.text(0.015, 0.955, "4-DOF Robotic Arm - pick-and-place simulation", fontsize=14, color=INK, fontweight="bold", va="center")
    fig.text(0.985, 0.955, f"t = {t[i]:5.2f} s   |   {PHASE_NAMES[PH[i]]}   |   {seg}", fontsize=9.5, color=MUTED, ha="right", va="center")
    deg = np.degrees(Q[i])
    fig.text(0.015, 0.02, f"J1 {deg[0]:6.1f}°   J2 {deg[1]:5.1f}°   J3 {deg[2]:5.1f}°   J4 {deg[3]:5.1f}°   gripper gap {GAP[i]:4.1f} mm"
             f"   {'cube: GRIPPED' if sim.T_GRASP <= t[i] < sim.T_RELEASE else 'cube: on table'}",
             fontsize=9, color=INK, family="monospace")
    return fig


def _render(i):
    out = os.path.join(ROOT, "animation", "frames", f"f_{i:04d}.png")
    fig = frame(i); fig.savefig(out); plt.close(fig); return out


KEYS = [(0.0, "Home pose (as exported in STEP)"), (3.5, "Above pick point"), (4.3, "Gripper straddles cube"),
        (5.0, "Cube gripped"), (7.0, "Transfer (yaw swing)"), (9.0, "Cube lowered at target"),
        (10.0, "Gripper opened, cube released"), (12.0, "Back at home pose")]


def stills():
    d = os.path.join(ROOT, "screenshots"); os.makedirs(d, exist_ok=True)
    names = ["01_home", "02_above_pick", "03_straddle_cube", "04_cube_gripped", "05_transfer", "06_cube_lowered",
             "07_cube_released", "08_back_home"]
    for (tk, _), nm in zip(KEYS, names):
        i = int(round(tk / sim.DT)); fig = frame(i); fig.savefig(os.path.join(d, f"{nm}_t{tk:04.1f}s.png")); plt.close(fig)
    # 2 x 4 montage (isometric only)
    fig, axs = plt.subplots(2, 4, figsize=(13.6, 6.9), dpi=150, facecolor="white")
    c, right, up = camera(-58, 24)
    pts = np.array([[x, y, z] for x in (XMIN, XMAX) for y in (YMIN, YMAX) for z in (0, 185)], float)
    px, py = pts @ right, pts @ up
    for ax, (tk, lab) in zip(axs.ravel(), KEYS):
        i = int(round(tk / sim.DT)); draw_scene(ax, i, -58, 24, labels=False, trail=False)
        ax.set_xlim(px.min() - 8, px.max() + 8); ax.set_ylim(py.min() - 8, py.max() + 8)
        ax.set_title(f"t = {tk:.1f} s\n{lab}", fontsize=9.5, color=INK, pad=3)
    fig.subplots_adjust(left=0.005, right=0.995, top=0.9, bottom=0.005, wspace=0.01, hspace=0.12)
    fig.savefig(os.path.join(ROOT, "plots", "keyframes_montage.png")); plt.close(fig)


def plots():
    d = os.path.join(ROOT, "plots"); os.makedirs(d, exist_ok=True)
    deg = np.degrees(Q); cols = ["#1565C0", "#2E7D32", "#EF6C00", "#8E24AA"]
    lab = ["J1 base yaw", "J2 shoulder pitch", "J3 elbow flexion", "J4 wrist pitch"]
    # ---- 1. joint angles + gripper + tool height
    fig, (a, b) = plt.subplots(2, 1, figsize=(9.5, 7.2), dpi=150, sharex=True, gridspec_kw=dict(height_ratios=[2.1, 1]))
    pc = {1: "#EEF2F6", 2: "#E3EBF3", 3: "#EEF2F6", 4: "#E3EBF3", 5: "#EEF2F6"}
    for ph in range(1, 6):
        ts = [x for x in sim.SEGMENTS if x[3] == ph]; t0, t1 = ts[0][1], ts[-1][2]
        for ax in (a, b): ax.axvspan(t0, t1, color=pc[ph], lw=0)
        a.text((t0 + t1) / 2, 128, f"Phase {ph}", ha="center", fontsize=8.5, color=MUTED)
    for k in range(4):
        a.plot(t, deg[:, k], color=cols[k], lw=2, label=lab[k])
        lo, hi = list(LIMITS_DEG.values())[k]
        for v in (lo, hi):
            if -60 <= v <= 120: a.axhline(v, color=cols[k], lw=0.7, ls=":", alpha=0.7)
    a.set_ylim(-60, 135); a.set_ylabel("joint angle (deg)"); a.legend(ncol=4, fontsize=8, loc="lower center", frameon=False, bbox_to_anchor=(0.5, -0.02))
    a.set_title("Joint trajectories (dotted lines = joint limits that fall in view: J2 0°, J3 0°/120°)", fontsize=10, color=INK, loc="left")
    b.plot(t, GAP, color="#37474F", lw=2, label="gripper gap (mm)"); b.plot(t, G[:, 2], color="#C62828", lw=2, label="tool (mid-pad) height z (mm)")
    b.axhline(CUBE, color="#FF8F00", lw=0.9, ls="--"); b.text(0.15, CUBE + 3, "cube width 30 mm", fontsize=8, color="#FF8F00")
    b.set_ylim(10, 100); b.set_ylabel("mm"); b.set_xlabel("time (s)"); b.legend(fontsize=8, ncol=2, frameon=False, loc="upper right"); b.set_xlim(0, 12)
    for ax in (a, b):
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)
        ax.grid(color="#e1e5ea", lw=0.6)
    fig.tight_layout(); fig.savefig(os.path.join(d, "joint_angles.png")); plt.close(fig)
    # ---- 2. tool path + speed
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.6), dpi=150, gridspec_kw=dict(width_ratios=[1, 1.15]))
    ph_col = {1: "#90A4AE", 2: "#1565C0", 3: "#8E24AA", 4: "#EF6C00", 5: "#2E7D32"}
    for i in range(len(t) - 1): a.plot(G[i:i + 2, 0], G[i:i + 2, 1], color=ph_col[PH[i]], lw=2.2)
    a.add_patch(plt.Circle((0, 0), 70, color="#1E78D6", alpha=.25)); a.add_patch(plt.Circle((0, 0), 45, color="#455A64", alpha=.5))
    for nm, R, th, c in (("PICK", sim.R_PICK, sim.TH_PICK, "#2E7D32"), ("PLACE", sim.R_PLACE, sim.TH_PLACE, "#C62828")):
        a.plot(R * np.cos(th), R * np.sin(th), "s", ms=11, mfc="none", mec=c, mew=2); a.annotate(nm, (R * np.cos(th), R * np.sin(th)), (8, -16), textcoords="offset points", color=c, fontweight="bold", fontsize=9)
    a.plot(*G[0, :2], "o", color="#37474F"); a.annotate("home", G[0, :2], (6, 6), textcoords="offset points", fontsize=9, color="#37474F")
    a.set_aspect("equal"); a.set_xlabel("x (mm)"); a.set_ylabel("y (mm)"); a.set_title("Tool (grasp-point) path, top view", fontsize=10, loc="left")
    from matplotlib.lines import Line2D
    a.legend([Line2D([0], [0], color=ph_col[p], lw=2.5) for p in range(1, 6)], [f"Phase {p}" for p in range(1, 6)], fontsize=7.5, frameon=False, loc="lower left")
    spd = np.linalg.norm(np.gradient(G, sim.DT, axis=0), axis=1)
    b.plot(t, spd, color="#C62828", lw=2); b.set_xlabel("time (s)"); b.set_ylabel("tool speed (mm/s)"); b.set_xlim(0, 12)
    b.set_title("Tool speed (min-jerk segments, zero speed at grip and release)", fontsize=10, loc="left")
    b.axvline(sim.T_GRASP, color="#FF8F00", ls="--", lw=1); b.axvline(sim.T_RELEASE, color="#FF8F00", ls="--", lw=1)
    b.text(sim.T_GRASP + .1, spd.max() * .92, "grip", color="#FF8F00", fontsize=8.5); b.text(sim.T_RELEASE + .1, spd.max() * .92, "release", color="#FF8F00", fontsize=8.5)
    for ax in (a, b):
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)
        ax.grid(color="#e1e5ea", lw=0.6)
    fig.tight_layout(); fig.savefig(os.path.join(d, "tool_path_speed.png")); plt.close(fig)
    # ---- 3. reachable workspace (vertical tool, joint limits incl. J4) in the arm plane
    q2 = np.radians(np.linspace(0, 90, 361)); q3 = np.radians(np.linspace(0, 120, 481))
    A2, A3 = np.meshgrid(q2, q3); A4 = arm.hand_angle_ref - (A2 - A3)
    ok = (np.degrees(A4) >= -90) & (np.degrees(A4) <= 90)
    ox, oz = arm.grasp_offset
    Wr = arm.L1 * np.cos(A2) + arm.L2 * np.cos(A2 - A3); Wz = arm.S[2] + arm.L1 * np.sin(A2) + arm.L2 * np.sin(A2 - A3)
    Rr, Zz = Wr + ox, Wz + oz
    fig, a = plt.subplots(figsize=(8.6, 4.8), dpi=150)
    a.scatter(Rr[ok], Zz[ok], s=2, color="#90CAF9", alpha=.5, lw=0, label="reachable with tool vertical and all joint limits met")
    a.axhline(0, color="#455A64", lw=2); a.text(-5, -9, "table (z = 0)", fontsize=8.5, color="#455A64", ha="right")
    a.add_patch(plt.Rectangle((-45, 12), 90, 55, color="#455A64", alpha=.6)); a.add_patch(plt.Rectangle((-70, 0), 140, 12, color="#1E78D6", alpha=.6))
    for nm, z, c in (("grasp height (z = 15)", sim.Z_CUBE, "#2E7D32"), ("travel height (z = 80)", sim.Z_HOVER, "#8E24AA")):
        a.plot(sim.R_PICK, z, "o", color=c, ms=7, label=f"{nm}, R = {sim.R_PICK:.0f} mm")
    a.plot(np.hypot(*G[0, :2]), G[0, 2], "D", color="#37474F", ms=6, label="home pose (STEP)")
    a.set_xlim(-90, 320); a.set_ylim(-20, 260); a.set_aspect("equal"); a.set_xlabel("radial distance from base axis R (mm)"); a.set_ylabel("grasp-point height z (mm)")
    a.set_title("Reachable grasp points in the arm plane (side section)", fontsize=10, loc="left"); a.legend(fontsize=7.5, frameon=False, loc="upper right")
    for sp in ("top", "right"): a.spines[sp].set_visible(False)
    a.grid(color="#e1e5ea", lw=0.6); fig.tight_layout(); fig.savefig(os.path.join(d, "workspace_reach.png")); plt.close(fig)
    zr = Zz[ok]; Rr_ = Rr[ok]
    np.save(os.path.join(ROOT, "data", "_workspace_stats.npy"), np.array([Rr_.min(), Rr_.max(), zr.min(), zr.max(), Rr_[zr <= sim.Z_CUBE + 1].min() if (zr <= sim.Z_CUBE + 1).any() else np.nan, Rr_[zr <= sim.Z_CUBE + 1].max() if (zr <= sim.Z_CUBE + 1).any() else np.nan]))


def animation():
    from multiprocessing import Pool
    os.makedirs(os.path.join(ROOT, "animation", "frames"), exist_ok=True)
    with Pool(2) as p: p.map(_render, range(len(t)))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "test"
    if mode == "test":
        os.makedirs(os.path.join(ROOT, "animation", "frames"), exist_ok=True)
        for i in (0, int(4.3 / sim.DT), int(7.0 / sim.DT)): print(_render(i))
    elif mode == "stills": stills()
    elif mode == "plots": plots()
    elif mode == "anim": animation()
