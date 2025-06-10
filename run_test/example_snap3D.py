 import sys
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

import os

sys.path.append('/workspace')
import glio

def plot_3D(s,figpath,elev,azim):
	backcolor = '#2e2e2e'
	linecolor = '#7f7f7f'
	
	#dm
	x,y,z = s.pos[0].T[0], s.pos[0].T[1], s.pos[0].T[2]
	#gas
	x1,y1,z1 = s.pos[1].T[0], s.pos[1].T[1], s.pos[1].T[2]
	
	
	fig = plt.figure(figsize=(8, 8))

	ax = fig.add_subplot(111, projection='3d')
	ax.view_init(elev=elev,azim=azim)
	ax.scatter(x,y,z, s=1.2, alpha=0.7, c='blue', marker='.', label ='dm')
	ax.scatter(x1,y1,z1, s=1.2, alpha=0.7, c='#2ca02c', marker='.', label ='gas')
	
	#background
	ax.set_facecolor(backcolor)
	fig.patch.set_facecolor(backcolor)
	ax.grid(False)
	
	#axes
	ax.set_title(f'DM + Gas; azim={azim}°', color=linecolor, fontsize=10)
	ax.xaxis.pane.fill = False
	ax.yaxis.pane.fill = False
	ax.zaxis.pane.fill = False
	ax.set_xlabel("x",color=linecolor)
	ax.set_ylabel("y",color=linecolor)
	ax.set_zlabel("z",color=linecolor)
	ax.tick_params(color=linecolor)
	ax.legend(markerscale = 4.0, facecolor="black", edgecolor=linecolor, labelcolor=linecolor)
	
	plt.tight_layout()
	plt.savefig(figpath, dpi=150)
	plt.close()

def prepare_output_dir(path: str, ext: str = '.png'):
    """
    Создаёт папку `path`, если её нет.
    Удаляет все файлы с расширением `ext` в ней.
    """
    os.makedirs(path, exist_ok=True)

    for fname in os.listdir(path):
        full_path = os.path.join(path, fname)
        if os.path.isfile(full_path) and fname.endswith(ext):
            os.remove(full_path)


def gif_generator():
	output_dir = 'gifframes'
	snapshot_path = 'snapshot_005'
	
	prepare_output_dir(output_dir)
	
	s = glio.GadgetSnapshot(snapshot_path)
	s.load()
	start,tot,step = 0,180,15
	for i in range(start,tot,step):
		figpath = os.path.join(output_dir, f'3dgraph_azim{i:03d}.png')
		plot_3D(s,figpath ,30,i)
		if ((i-start) // (step))%3 == 0:
			print(f"[GIF] Генерация кадра {i} из {tot}: azim={i:03d}°")



gif_generator()

