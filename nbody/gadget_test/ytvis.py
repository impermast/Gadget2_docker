import yt
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import numpy as np
import json
import pandas as pd

from yt.visualization.volume_rendering.api import Scene
from yt.visualization.volume_rendering.transfer_function_helper import ColorTransferFunction
from yt.visualization.volume_rendering.render_source import create_volume_source
from mpl_toolkits.axes_grid1 import AxesGrid



import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

from unyt import unyt_quantity

class SnapshotVisualizer:
	def __init__(self, snapshot_path):
		"""
		Загрузка snapshot-а и инициализация сцены
		"""
		self.snapshot_path = snapshot_path
		self.ds = yt.load(snapshot_path)
		self.graph_path = "run_test/graph/"
		
		# ⚙️ Основные параметры визуализации
		self.cmap = "inferno"                        # цветовая карта
		self.color_dm = '#00bfff'
		self.color_gas = '#2ca02c'
		self.color_back = "black"
		self.color_text = 'white'

		self.width = unyt_quantity(400.0,"kpc") 

                 # ширина области обзора
		self.resolution = 1600
		self.dpi = 100                      # разрешение изображения   
		self.dim = 50


		self.redshift = self.ds.current_redshift
		self.cosmtime = self.ds.current_time.to("Gyr")

		
	def print_header_info(self):
		"""
		Выводит краткую сводку из заголовка snapshot'а
		"""
		print("\n=== Snapshot Header Info ===")
		print(f"Файл:                {self.snapshot_path}")
		print(f"Redshift:            {self.ds.current_redshift:.5f}")
		print(f"Domain center:       {self.ds.domain_center.to('kpc')}")
		print(f"Domain width:        {self.ds.domain_width.to('kpc')}")
		
		print("Основные параметры:")
		for key, val in self.ds.parameters.items():
			if isinstance(val, (int, float)):
				print(f"  {key:<25} {val}")
		
		print("Доступные поля:")
		for field in sorted(self.ds.field_list):
			print(f"  {field}")
		print("============================\n")

	def plot_speed_profile(self, ptype = "Halo"):
		field_r = (ptype, f'{ptype}_r')
		field_v = (ptype, f'{ptype}_v')

		profile =[]
		labels = []
		ad = self.ds.all_data()
		profile.append(yt.create_profile(
			ad,
			bin_fields=[field_r],
       		fields=[field_v],
        	weight_field=None,
			n_bins=15))
		profile.append(yt.create_profile(
			ad,
			bin_fields=[field_r],
        	fields=[field_v],
        	weight_field=None,
			n_bins=self.dim))
		
		labels.append(f"Speed in bins")
		labels.append(f"Speed")
		plot = yt.ProfilePlot.from_profiles(profile, labels=labels)
		plot.set_log(field_r, False)
		plot.set_xlabel("R [kpc]")
		plot.save(self.graph_path + f"{ptype}_SpeedProfile1D.png")

	def plot_density_profile(self, ptype1 = "Halo", ptype2 = "Disk"):
		field_name1 = (ptype1, f'{ptype1}_r')
		field_name2 = (ptype2, f'{ptype2}_r')

		profile =[]
		labels = []
		plot_specs = [dict(color="red", linestyle="-"), dict(color="green", linestyle="-")]
		ad = self.ds.all_data()
		profile.append(yt.create_profile(
			ad,
			bin_fields=[field_name1],
       		fields=[field_name1],
        	weight_field=None,
			n_bins=20))
		profile.append(yt.create_profile(
			ad,
			bin_fields=[field_name2],
        	fields=[field_name2],
        	weight_field=None,
			n_bins=20))
			
		labels.append(f"Count in bins")
		labels.append(f"Count particles")
		plot = yt.ProfilePlot.from_profiles(profile, 
									  labels=labels,
									  plot_specs=plot_specs)
		plot.set_log(field_name1, False)
		plot.set_log(field_name2, False)
		plot.set_xlabel("R [kpc]")
		plot.save(self.graph_path + f"PartProfile1D.png")

	def plot_phase_vr(self, ptype = "Halo"):
		field_r = (ptype, f'{ptype}_r')
		field_v = (ptype, f'{ptype}_v')
		ad = self.ds.all_data()
		
		p = yt.PhasePlot(
        ad,
        field_r,         # r
        field_v,     # |v|
        (ptype, "Mass"),      # цветим по массе / количеству
        weight_field=None,
        x_bins=self.dim,
        y_bins=self.dim,
		)
		p.set_xlabel("r [kpc]")
		p.set_ylabel("|v| [km/s]")
		p.set_log(field_r, True)
		p.set_log(field_v, True)
		out = f"{self.graph_path}{ptype}_phase_r_v.png"
		p.save(out)
		print(f"[yt] Сохранено: {out}")

	def plot_inplane2d(self, grid, zaxis=None, ptype = "Halo", output_file="inplane2D.png"):
		fig = plt.figure()
		axesgrid = AxesGrid(
			fig,
			(0.085, 0.085, 0.75, 0.75),
			nrows_ncols=(3, 1),
			axes_pad=0.7,
			label_mode="all",
			share_all=False,
			cbar_location="right",
			cbar_mode="single",
			cbar_size="1%",
			cbar_pad="0%",
			aspect=False,
		)
		if zaxis == None:
			with open(f"analysis/finder/{ptype}_frame.json") as f:
				info = json.load(f)
			zaxis = np.array(info["basis_rows"])[2]		
		field_key = [ field for field in grid.field_list if ptype in field[1] ]
		print(f"[yt] Using field --- {field_key} for inplane graph")
		
		for i, normal in enumerate("xyz"):
			p =	yt.SlicePlot(grid, normal, field_key)
			p.set_cmap(field_key, self.cmap)
			p.set_buff_size(self.resolution)
			p.set_background_color(field_key, self.color_back)

			plot = p.plots[field_key[0][0],field_key[0][1]]
			plot.figure = fig
			plot.axes = axesgrid[i].axes
			plot.cax = axesgrid.cbar_axes[i]
			p.render()
			
		plt.savefig(self.graph_path+ptype+"_"+output_file)

	def plot_radial_distribution(
		self,
		ptype_list=["Halo", "Disk"],
		field_name_template="{ptype}_r", 
		n_bins=40
	):
		"""
		Строит график распределения по радиусу для разных ptype.

		Args:
			ptype_list: список типов частиц, например ["Halo", "Disk"]
			field_name_template: шаблон названия поля радиуса
			plot_styles: dict кастомизации графика для каждого ptype
			n_bins: число бинов
		"""
		import matplotlib.pyplot as plt

		ad = self.ds.all_data()
		fig, ax = plt.subplots()
		plot_styles =dict(
        {"Halo": {"color": self.color_dm, "linestyle": "-", "linewidth": 1.5},
        "Disk": {"color": self.color_gas, "linestyle": "-", "linewidth": 1.5}}
		)
		for ptype in ptype_list:
			radius_field = f"{ptype}_r"

			r = ad[radius_field].to("kpc").ndarray_view()
			
			# Создаём гистограмму
			hist, edges = np.histogram(r, bins=n_bins)
			centers = 0.5 * (edges[1:] + edges[:-1])

			# Настройки стиля
			style = plot_styles.get(ptype, {}) if plot_styles else {}
			label = f"{ptype}"

			ax.plot(centers, hist, label=label, **style)


		ax.spines["top"].set_visible(False)
		ax.spines["right"].set_visible(False)

		ax.set_xlabel("Radius [kpc]")
		ax.set_xscale("log")
		ax.set_ylabel("Particle count")
		ax.legend(loc="best")
		ax.grid(False)

		out_path = self.graph_path + "RadialProfile.png"
		fig.savefig(out_path)
		print(f"[yt] Saved radial profile plot to {out_path}")
		plt.close(fig)


	def plot_rotation_curves(
		self,
		ptype_list=["Halo", "Disk"],
		n_bins=30,
		r_units="kpc",
		v_units="km/s"
	):
		"""
		Вручную строит speed-профили аналогично yt.create_profile(...),
		для каждого ptype в ptype_list.
		"""
		import matplotlib.pyplot as plt
		import numpy as np

		ad = self.ds.all_data()
		fig, ax = plt.subplots()

		plot_styles = {
			"Halo": {"color": self.color_dm, "linestyle": "-", "linewidth": 3},
			"Disk": {"color": self.color_gas, "linestyle": "-", "linewidth": 3},
		}

		for ptype in ptype_list:
			# Радиус и модуль скорости
			r = ad[(ptype, f"{ptype}_r")].to(r_units).ndarray_view()
			v = ad[(ptype, f"{ptype}_v")].to(v_units).ndarray_view()

			bins = np.linspace(r.min(), r.max(), n_bins + 1)
			indices = np.digitize(r, bins)

			v_mean = []
			r_centers = []

			for i in range(1, len(bins)):
				mask = indices == i
				if np.any(mask):
					v_bin = v[mask]
					v_mean.append(np.mean(v_bin))  # аналог weight_field=None
					r_centers.append(0.5 * (bins[i] + bins[i - 1]))
			style = plot_styles.get(ptype, {})

			# 1. Полупрозрачные точки: r-v (сырые данные)
			ax.scatter(r, v, alpha=0.1, color=style.get("color", "gray"), s=1, label=f"{ptype} particles")

			# 2. Жирная линия: средняя скорость по радиусу
			line_style = {
				"color": style.get("color", "black"),
				"linestyle": style.get("linestyle"),
				"linewidth": 3,
			}
			ax.plot(r_centers, v_mean, label=f"{ptype} mean", **line_style)

		ax.set_xlabel(f"R [{r_units}]")
		ax.set_ylabel(f"Mean |v| [{v_units}]")
		ax.set_yscale("log")
		ax.legend()
		ax.grid(False)
		fig.tight_layout()

		out_path = self.graph_path + "rotcurve.png"
		fig.savefig(out_path, dpi=300)
		print(f"[yt] Saved speed profile to {out_path}")
		plt.close(fig)




	def plot_disk_halo_3d(self, elev=30, azim=310, output_file="disk_halo_3d.png"):
		"""
		Строит 3D-график частиц 'Disk' и 'Halo' с заданным углом обзора.
		"""
		
		graph_name = "Disk + Halo (3D)"

		ad = self.ds.all_data()

		# Получаем координаты
		disk = ad[('Disk', 'Coordinates')].to('kpc')
		halo = ad[('Halo', 'Coordinates')].to('kpc')
		
		mass_d = ad[('Disk', 'Mass')]
		mass_h = ad[('Halo', 'Mass')]
		s_d = 10 * (mass_d / mass_d.max())
		s_h = 2 * (mass_h / mass_h.max())
		
		x_d, y_d, z_d = disk[:, 0], disk[:, 1], disk[:, 2]
		x_h, y_h, z_h = halo[:, 0], halo[:, 1], halo[:, 2]

		fig = plt.figure(figsize=(self.resolution/self.dpi, self.resolution/self.dpi))
		ax = fig.add_subplot(111, projection='3d')
		ax.view_init(elev=elev, azim=azim)
		
		
		ax.scatter(x_d, y_d, z_d, s=s_d, alpha=0.5, color=self.color_gas, label='Disk', edgecolors='none')
		ax.scatter(x_h, y_h, z_h, s=s_h, alpha=0.12, color=self.color_dm, label='Halo', edgecolors='none')
		
		ax.set_title(graph_name, loc='left')
		ax.set_xlabel("x [kpc]")
		ax.set_ylabel("y [kpc]")
		ax.set_zlabel("z [kpc]")
		ax.legend(loc='upper left', bbox_to_anchor=(-0.05, 1), frameon=False, fontsize=10, markerscale=4)
		z_text = f"z = {self.ds.current_redshift:.4f}"
		fig.text(0.05, 0.8, z_text, ha='left', fontsize=10)

		# Убираем фон "плиток" и стилизуем сетку
		ax.xaxis.set_pane_color(self.color_back)
		ax.yaxis.set_pane_color(self.color_back)
		ax.zaxis.set_pane_color(self.color_back)


		for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
			axis.pane.fill = True
			axis._axinfo["grid"]['color'] = self.color_text
			axis._axinfo["grid"]['linewidth'] = 0.1
			axis._axinfo["tick"]["color"] = self.color_back
			axis._axinfo["tick"]["inward_factor"] = 0
			axis._axinfo["tick"]["outward_factor"] = 0.2

		plt.tight_layout()
		plt.savefig(self.graph_path+output_file, dpi=self.dpi)
		plt.show()

		plt.close()
		print(f"[yt] Сохранено: {output_file}")		

	def plot_volume_render(self, ptype = "Halo", output_file="volume_yt2D.png"):
		plot = yt.ParticlePlot(
			self.ds,
			( ptype, f'{ptype}_x'),
			( ptype, f'{ptype}_y'),
			( ptype, f'{ptype}_z'),  
			figure_size=(8,8)
			)
		plot.set_xlabel("X [kpc]")
		plot.set_ylabel("Y [kpc]")
		plot.annotate_title(f'ParticlePlot for {ptype}, t={self.cosmtime:.2f}')
		plot.save(self.graph_path+ptype+"_"+output_file)
		print(f"[yt] Сохранено: {output_file}")



	def plot_density_yt3d(self, grid, ptype = "Halo", output_file="_density_yt3D.png"):
		sc = yt.create_scene(grid, field=("stream", f"{ptype}_density"))
		# tf = yt.ColorTransferFunction([-28, -25])
		# tf.clear()
		# tf.add_layers(4, 0.02, alpha=np.logspace(-3, -1, 4), colormap="winter")
		# source.set_transfer_function(tf)
		
		sc.camera.position = grid.arr([+0.5, -0.5, 0.5 ], "unitary")
		sc.camera.resolution = (1*self.resolution, 1*self.resolution)
		sc.camera.focus = grid.arr([0, 0, 0], "unitary")
		sc.camera.zoom(3)

		# Добавляет веса разным событиям по массе
		# source = sc[0]
		# mn, mx = int(grid.all_data()[f"{ptype}_density"].min().to("Msun/kpc**3").value), int(grid.all_data()[f"{ptype}_density"].max().to("Msun/kpc**3").value)
		# source.set_log(True)
		# bounds = (mx/1000,mx*10)
		# tf = yt.ColorTransferFunction(np.log10(bounds))
		# tf.sample_colormap(np.log10(mx)-0.5, w=0.08, colormap=self.cmap)
		# source.tfh.tf = tf
		# source.tfh.bounds = bounds
		# source.tfh.plot("transfer_function.png", profile_field=("stream", f"{ptype}_density"))				
		


		text_annot = f"z = {self.redshift:.2f}"+"   "+f"t = {self.cosmtime:.2f}"
		sc.annotate_axes(alpha=0.03)
		sc.annotate_mesh_lines(grid, alpha = 0.03)
		# sc.save(ptype+output_file, sigma_clip=1.0)
		sc.save_annotated(self.graph_path+ptype+output_file,
					 sigma_clip=2.0, 
					 text_annotate=[[
						 (0.15, 0.95), text_annot,
						 dict(color="y", fontsize="24", horizontalalignment="left")]]
					)
		
		print(f"[yt] Сохранено рендер: {ptype+output_file}")

	def make_coord_fields(self, ptype = "Halo"):
		import field_maker
		field_maker.register_particle_fields(self.ds, ptype)

	def make_density_field(self, ptype = "Halo"):
		ad = self.ds.all_data()
		coords = ad[(ptype, 'Coordinates')].to('kpc').value
		masses = ad[(ptype, 'Mass')].to('Msun').value

		box_size = self.width.to_value("kpc")
		center, __ = self.find_center(ptype=ptype)
		center = center.to("kpc").value
		shifted = coords - center

		# Определяем границы куба
		half_box = box_size / 2
		bounds = np.array([[-half_box, half_box]] * 3)

		# Строим 3D гистограмму плотности (масса в каждой ячейке)
		H, edges = np.histogramdd(shifted, bins=self.dim, range=bounds, weights=masses)

		# Переводим массу в плотность (Msun/kpc^3)
		cell_volume = (box_size / self.dim)**3
		density = H / cell_volume
				
		density = np.nan_to_num(density, nan=0.0, posinf=0.0, neginf=0.0)
		field_key = ptype+"_density"
		ugrid = yt.load_uniform_grid(
			{field_key: (density, "Msun/kpc**3")},
			domain_dimensions=(self.dim, self.dim, self.dim),
			length_unit="kpc",
			bbox=bounds
		)
		print("[yt] fields in ugrid:", ugrid.field_list)
		return ugrid
	


	def find_center(self, ds = None, ptype = "Disk"):
		if ds == None:
			ds = self.ds
		ad = ds.all_data()
		pos = ad[(ptype, "Coordinates")].to("kpc").value #(N 3)
		vel = ad[(ptype, "Velocities")].to("km/s").value
		mass = ad[(ptype, "Mass")].to("Msun").value      # (N,)
		
		vmean   = np.average(vel, weights=mass, axis=0)
		center = np.average(pos,weights=mass, axis = 0)
		
		r_rel = pos - center
		v_rel = vel - vmean
		L = np.sum(np.cross(r_rel, v_rel) * mass[:, np.newaxis], axis=0)
		z_axis = L / np.linalg.norm(L)
		up = np.array([0.0, 0.0, 1.0]) if abs(z_axis[2]) < 0.9 else np.array([1.0, 0.0, 0.0])

		x_axis = np.cross(up, z_axis)
		x_axis /= np.linalg.norm(x_axis)
		y_axis = np.cross(z_axis, x_axis)
		basis = np.array([x_axis, y_axis, z_axis])


		output_file = f"{self.graph_path}/../analysis/finder/{ptype}_frame.json"
		out_data = {
			"center_kpc": center.tolist(),
			"basis_rows": basis.tolist(),  # [x_axis, y_axis, z_axis]
		}
		with open(output_file, "w") as f:
			json.dump(out_data, f, indent=2)

		print(f"[finder] Saved disk frame to {output_file}")
		print(f"[finder] Center: {center}")
		print(f"[finder] z_axis: {z_axis}")

		return ds.arr(center, "kpc"), basis


if __name__ == "__main__":
	
	# for i, snap in enumerate([f"run_test/snaps/snapshot_00{i}" for i in range(7,8)]):
	# 	vis = SnapshotVisualizer(snap)		
	# 	vis.print_header_info()
		# for ptype in ["Disk", "Halo"]:
		# 	# vis.make_coord_fields(ptype)
		# 	grid = vis.make_density_field(ptype=ptype)

		# 	vis.plot_density_yt3d(grid,ptype=ptype, output_file = f"_density_yt3D_{i}.png")
	
	snap = "run_test/snaps/snapshot_007"
	vis = SnapshotVisualizer(snap)
	vis.make_coord_fields("Halo")
	vis.make_coord_fields("Disk")
	# vis.plot_radial_distribution(n_bins=25)
	vis.plot_rotation_curves(n_bins=30)
	
	
	# vis.plot_speed_profile(ptype)
	

	# vis.plot_inplane2d(grid, zaxis="z", ptype =ptype)
	# vis.plot_phase_vr(ptype)
