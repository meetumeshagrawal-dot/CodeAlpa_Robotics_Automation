import csv, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
r = list(csv.DictReader(open("scenario1.csv"))); t = np.array([int(x["t_ms"]) for x in r]) / 1000
g = lambda k: np.array([int(x[k]) for x in r])
names = ["IDLE", "RUN", "PROCESS", "CLEARING", "FAULT", "ESTOP"]
fig, ax = plt.subplots(4, 1, figsize=(7.2, 3.9), dpi=200, sharex=True, gridspec_kw=dict(height_ratios=[2.2, 1, 1, 1], hspace=0.25))
ax[0].step(t, g("state"), where="post", color="#16365C", lw=1.6); ax[0].set_yticks(range(6)); ax[0].set_yticklabels(names, fontsize=7); ax[0].set_ylim(-0.4, 3.6)
for a, k, lab, c in zip(ax[1:], ["motor", "object_sensor", "exit_sensor"], ["Motor", "Object sensor", "Exit sensor"], ["#2E7D32", "#EF6C00", "#00838F"]):
    a.fill_between(t, g(k), step="post", color=c, alpha=.75); a.set_yticks([0, 1]); a.set_yticklabels(["off", "on"], fontsize=7); a.set_ylim(0, 1.2)
    a.set_ylabel(lab, fontsize=7, rotation=0, ha="right", va="center")
ax[0].set_ylabel("State", fontsize=7, rotation=0, ha="right", va="center")
ax[-1].set_xlabel("time (s)  -  START pressed at 1.0 s; objects reach the station at about 6, 15 and 24 s", fontsize=7.5); ax[-1].set_xlim(0, 32)
for a in ax:
    a.tick_params(labelsize=7); a.grid(color="#e1e5ea", lw=.5)
    for sp in ("top", "right"): a.spines[sp].set_visible(False)
fig.savefig("scenario1_timeline.png", bbox_inches="tight")
