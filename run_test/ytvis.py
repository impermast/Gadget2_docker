import yt
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import numpy as np
from yt.visualization.volume_rendering.api import Scene
from yt.visualization.volume_rendering.transfer_function_helper import ColorTransferFunction
from yt.visualization.volume_rendering.render_source import create_volume_source


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
		
		# ⚙️ Основные параметры визуализации
		self.cmap = "inferno"                        # цветовая карта
		self.color_dm = '#00bfff'
		self.color_gas = '#2ca02c'
		self.color_back = "black"
		self.color_text = 'white'

		self.width = unyt_quantity(20.0,"kpc") 

                 # ширина области обзора
		self.resolution = 1600
		self.dpi = 100                      # разрешение изображения
		self.center = self.ds.domain_center          # центр сцены
		self.dim = 22


		self.redshift = self.ds.current_redshift
		self.cosmtime = self.ds.current_time.to("Gyr")

		
	def print_header_info(self):
		"""
		Выводит краткую сводку из заголовка snapshot'а
		"""
		print("\n=== Snapshot Header Info ===")
		print(f"Файл:                {self.snapshot_path}")
		print(f"Redshift:            {self.ds.current_redshift:.5f}")
		print(f"Domain center:       {self.center.to('kpc')}")
		print(f"Domain width:        {self.ds.domain_width.to('kpc')}")
		print(f"Доступные частицы:   {self.ds.particle_types}")
		
		print("Основные параметры:")
		for key, val in self.ds.parameters.items():
			if isinstance(val, (int, float)):
				print(f"  {key:<25} {val}")
		
		print("Доступные поля:")
		for field in sorted(self.ds.field_list):
			print(f"  {field}")
		print("============================\n")

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
		plt.savefig(output_file, dpi=self.dpi)
		plt.show()

		plt.close()
		print(f"[yt] Сохранено: {output_file}")		

	def plot_volume_render(self, particle_type = "Halo", output_file="volume_yt2D.png"):
		"""
		Объёмный рендеринг частиц Halo.
		"""
		def _x_coord(field, data):
			return data[( particle_type, 'Coordinates')][:, 0]  # Берем X-координату
    
		def _y_coord(field, data):
			return data[( particle_type, 'Coordinates')][:, 1]  # Берем Y-координату
		
		def _z_coord(field, data):
			return data[( particle_type, 'Coordinates')][:, 2]  # Берем Z-координату
		
		# Регистрируем поля в yt
		self.ds.add_field(
			(particle_type, 'particle_position_x'),
			function=_x_coord,
			sampling_type='particle',
			units='kpc'  # или другие единицы, как в вашем snapshot
		)
		
		self.ds.add_field(
			(particle_type, 'particle_position_y'),
			function=_y_coord,
			sampling_type='particle',
			units='kpc'
		)
		
		self.ds.add_field(
			(particle_type, 'particle_position_z'),
			function=_z_coord,
			sampling_type='particle',
			units='kpc'
		)
			
		plot = yt.ParticlePlot(
			self.ds,
			( particle_type, 'particle_position_x'),
			( particle_type, 'particle_position_y'),
			( particle_type, 'particle_position_z'),
			width=self.width,
			depth=self.width,
			color=self.color_dm
		)
		
		plot.save(particle_type+"_"+output_file)
		print(f"[yt] Сохранено: {output_file}")



	def plot_density_yt3d(self, grid, particle_type = "Halo", output_file="_density_yt3D.png"):
		sc = yt.create_scene(grid, field=("stream", "density"))

		
		sc.camera.position = grid.arr([1, 0.5, -0.5 ], "unitary")
		sc.camera.resolution = (1*self.resolution, 1*self.resolution)
		sc.camera.focus = grid.arr([0, 0,0], "unitary")
		sc.camera.zoom(1.5)


		# Добавляет веса разным событиям по массе
		# source = sc[0]
		#mn, mx = int(grid.all_data()["density"].min().to("Msun/kpc**3").value), int(grid.all_data()["density"].max().to("Msun/kpc**3").value)
		# source.set_log(True)
		# bounds = (mn+1,mx*10)
		# tf = yt.ColorTransferFunction(np.log10(bounds))
		# tf.sample_colormap(np.log10(mx)-0.5, w=0.05, colormap="hot")
		# source.tfh.tf = tf
		# source.tfh.bounds = bounds
		# source.tfh.plot("transfer_function.png", profile_field=("stream", "density"))				
		


		text_annot = f"z = {self.redshift:.2f}"+"   "+f"t = {self.cosmtime:.2f}"
		sc.annotate_axes(alpha=0.01)
		sc.annotate_domain(grid, color=[1, 1, 1, 0.05])
		sc.annotate_mesh_lines(grid)
		# sc.save(particle_type+output_file, sigma_clip=1.0)
		sc.save_annotated(particle_type+output_file, sigma_clip=1.0, text_annotate=[[(0.1, 0.95), text_annot]])
		
		print(f"[yt] Сохранено рендер: {particle_type+output_file}")


	def make_density_field(self, particle_type = "Halo"):
		ad = self.ds.all_data()
		coords = ad[(particle_type, 'Coordinates')].to('kpc').value
		masses = ad[(particle_type, 'Mass')].to('Msun').value

		# Центрируем и нормализуем координаты
		resolution = self.resolution
		box_size = self.width.to_value("kpc")
		center = self.ds.domain_center.to('kpc').value
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
		print(f"[yt] Density min={density.min():.2e}, max={density.max():.2e} [Msun/kpc^3]")
		print("[yt] UniformGrid Dataset создан из Halo частиц")
		
		field_name = "density"
		ugrid = yt.load_uniform_grid(
			{field_name: (density, "Msun/kpc**3")},
			domain_dimensions=(self.dim, self.dim, self.dim),
			length_unit="kpc",
		bbox=bounds
		)
		return ugrid


if __name__ == "__main__":
	vis = SnapshotVisualizer("snapshot_007")
	# vis.print_header_info()

	grid_halo = vis.make_density_field(particle_type="Halo")
	# grid_disk = vis.make_density_field(particle_type="Disk")

	vis.plot_density_yt3d(grid_halo,particle_type="Halo")
	# vis.plot_density_yt3d(grid_disk,particle_type="Disk")

