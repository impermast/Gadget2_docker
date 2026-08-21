import os, sys, numpy as np, h5py, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from PIL import Image

BASE = "/nbody"
RUNS = {
    "CDM": os.path.join(BASE, "runs/cdm_N1e6/output"),
    "SIDM0.1": os.path.join(BASE, "runs/sidm_sigma0.1_N1e6/output"),
    "SIDM5": os.path.join(BASE, "runs/sidm_sigma5_N1e6/output"),
}
OUT = os.path.join(BASE, "analyse/cdm_sidm_comparison")
os.makedirs(OUT, exist_ok=True)

from plot_config import GRAPH3D

Gyr_per_code = 0.9777923542981722

def latest(path):
    files = sorted([f for f in os.listdir(path) if f.endswith(".hdf5")])
    return os.path.join(path, files[-1])

def read_snap(path, ptype=3, nmax=150_000):
    with h5py.File(path, "r") as f:
        g = f[f"PartType{ptype}"]
        pos = g["Coordinates"][:].astype(np.float64)
        t = float(f["Header"].attrs.get("Time", 0.0))
    if nmax and len(pos) > nmax:
        idx = np.random.choice(len(pos), nmax, replace=False)
        pos = pos[idx]
    return pos, t

def draw(ax, pos, label, snap_num, t_gyr):
    if len(pos) > 100_000:
        pos = pos[np.random.choice(len(pos), 100_000, replace=False)]
    com = pos.mean(axis=0)
    pos = pos - com
    r = np.linalg.norm(pos, axis=1)
    col = np.log10(r + 1e-6)
    vmin, vmax = np.percentile(col, 2), np.percentile(col, 98)
    lim = float(np.percentile(np.abs(pos), 99) * GRAPH3D["limits"]["factor"])
    lim = max(lim, GRAPH3D["limits"]["min_lim"])

    ax.set_facecolor(GRAPH3D["facecolor"])
    ax.set_axis_off()
    for p in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
        p.set_facecolor(GRAPH3D["pane_color"])
        p.set_alpha(GRAPH3D["pane_alpha"])

    L = lim
    edges = [
        ([-L, L], [-L, -L], [-L, -L]), ([L, L], [-L, L], [-L, -L]),
        ([L, -L], [L, L], [-L, -L]), ([-L, -L], [L, L], [-L, -L]),
        ([-L, L], [-L, -L], [L, L]), ([L, L], [-L, L], [L, L]),
        ([L, -L], [L, L], [L, L]), ([-L, -L], [L, L], [L, L]),
        ([-L, -L], [-L, -L], [-L, L]), ([L, L], [-L, -L], [-L, L]),
        ([L, L], [L, L], [-L, L]), ([-L, -L], [L, L], [-L, L]),
    ]
    for ex, ey, ez in edges:
        ax.plot(ex, ey, ez,
                color=GRAPH3D["wireframe"]["color"],
                lw=GRAPH3D["wireframe"]["linewidth"],
                alpha=GRAPH3D["wireframe"]["alpha"])

    sc = ax.scatter(pos[:, 0], pos[:, 1], pos[:, 2],
                    c=col, cmap=GRAPH3D["scatter"]["cmap"],
                    vmin=vmin, vmax=vmax,
                    s=GRAPH3D["scatter"]["s"],
                    alpha=GRAPH3D["scatter"]["alpha"],
                    edgecolors=GRAPH3D["scatter"]["edgecolors"])
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_zlim(-lim, lim)
    ax.view_init(**GRAPH3D["view"])

    ax.text2D(0.035, 0.08, label, transform=ax.transAxes,
              color=GRAPH3D["labels"]["color"],
              fontsize=GRAPH3D["labels"]["fontsize"],
              weight=GRAPH3D["labels"]["weight"], va="bottom", ha="left")
    ax.text2D(0.035, 0.02, f"snap {snap_num}   t = {t_gyr:.2f}/5.00 Gyr",
              transform=ax.transAxes,
              color=GRAPH3D["time_label"]["color"],
              fontsize=GRAPH3D["time_label"]["fontsize"], va="bottom", ha="left")

    bar_len = 500 if lim >= 600 else (100 if lim >= 120 else 50)
    x0 = -lim + 0.08 * (2 * lim)
    y0 = -lim + 0.14 * (2 * lim)
    z0 = -lim
    x1 = x0 + bar_len; y1 = y0; z1 = z0
    ax.plot([x0, x1], [y0, y1], [z0, z1],
            color=GRAPH3D["scale_bar"]["color"],
            lw=GRAPH3D["scale_bar"]["linewidth"],
            alpha=GRAPH3D["scale_bar"]["alpha"])
    tick = GRAPH3D["scale_bar"]["tick_length"]
    ax.plot([x0, x0], [y0, y0], [z0, z0 + tick],
            color=GRAPH3D["scale_bar"]["color"],
            lw=GRAPH3D["scale_bar"]["tick_linewidth"],
            alpha=GRAPH3D["scale_bar"]["tick_alpha"])
    ax.plot([x1, x1], [y1, y1], [z1, z1 + tick],
            color=GRAPH3D["scale_bar"]["color"],
            lw=GRAPH3D["scale_bar"]["tick_linewidth"],
            alpha=GRAPH3D["scale_bar"]["tick_alpha"])
    ax.text2D(0.12, 0.32, f"{bar_len} kpc", transform=ax.transAxes,
              color=GRAPH3D["scale_bar"]["color"],
              fontsize=GRAPH3D["scale_bar"]["label_fontsize"],
              ha="center", va="top")
    ax.set_position([0, 0, 1, 1])

def render_frame(pos, label, snap_num, t_gyr, out_png):
    fig = plt.figure(figsize=GRAPH3D["figsize"], dpi=GRAPH3D["dpi"])
    fig.patch.set_edgecolor("none")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax = fig.add_subplot(111, projection="3d")
    draw(ax, pos, label, snap_num, t_gyr)
    fig.savefig(out_png, dpi=GRAPH3D["dpi"], bbox_inches="tight", pad_inches=0)
    plt.close(fig)

def make_gif(png_files, out_gif, duration=280):
    imgs = [Image.open(p).convert("P", palette=Image.ADAPTIVE, colors=180) for p in png_files]
    imgs[0].save(out_gif, save_all=True, append_images=imgs[1:], duration=duration, loop=0)

def sample_idxs(n, target=24):
    if n <= target:
        return list(range(n))
    return [int(round(i * (n - 1) / (target - 1))) for i in range(target)]

def animation():
    for label, run_dir in RUNS.items():
        snaps = sorted([f for f in os.listdir(run_dir) if f.endswith(".hdf5")])
        idxs = sample_idxs(len(snaps), 24)
        pngs = []
        for i in idxs:
            path = os.path.join(run_dir, snaps[i])
            pos, t = read_snap(path)
            t_gyr = t * Gyr_per_code
            snap_num = snaps[i].replace("snapshot_", "").replace(".hdf5", "")
            png = os.path.join(OUT, f"tmp_{label}_{i:03d}.png")
            render_frame(pos, label, snap_num, t_gyr, png)
            pngs.append(png)
            print("rendered", label, "snap", snap_num, "t=", round(t_gyr, 2))
        gif = os.path.join(OUT, f"{label}_evolution.gif")
        make_gif(pngs, gif, duration=280)
        print("gif", gif, "size", os.path.getsize(gif))
        for p in pngs:
            os.remove(p)

def preview():
    for label, run_dir in RUNS.items():
        pos, t = read_snap(latest(run_dir))
        t_gyr = t * Gyr_per_code
        out = os.path.join(OUT, f"preview_{label}.png")
        render_frame(pos, label, "latest", t_gyr, out)
        print("preview", label, "->", out)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "anim":
        animation()
    elif len(sys.argv) > 1 and sys.argv[1] == "preview":
        preview()
    else:
        animation()
