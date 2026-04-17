import sys
import matplotlib.pyplot as plt

sys.path.append('/workspace')
import glio

def srez_plot(s, figpath):
    # Настройки стиля
    backcolor = '#2e2e2e'
    linecolor = '#7f7f7f'

    # Данные
    x_dm, y_dm = s.pos[0].T[0], s.pos[0].T[1]
    x_gas, y_gas = s.pos[1].T[0], s.pos[1].T[1]

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_facecolor(backcolor)
    fig.patch.set_facecolor(backcolor)

    ax.plot(x_dm, y_dm, '.', color='blue', markersize=0.2, label='dm')
    ax.plot(x_gas, y_gas, '.', color='#2ca02c', markersize=0.2, label='gas')

    ax.set_aspect('equal')
    ax.set_xticks([]); ax.set_yticks([])
    ax.grid(False)

    ax.legend(
        loc='upper right',
        facecolor='black',
        edgecolor=linecolor,
        labelcolor=linecolor,
        markerscale=4.0
    )

    plt.tight_layout()
    plt.savefig(figpath, dpi=300, facecolor=fig.get_facecolor())
    plt.close()


snapshot_path = '/workspace/run_test/snapshot_000'
s = glio.GadgetSnapshot(snapshot_path)
s.load()
srez_plot(s,"test_graph_gas+dm_in.png")

snapshot_path = '/workspace/run_test/snapshot_005'
s = glio.GadgetSnapshot(snapshot_path)
s.load()
srez_plot(s,"test_graph_gas+dm_end.png")

print("Number of particles by type:", s.header.npart)



