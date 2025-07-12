import imageio.v2 as imageio
import os
import re



def extract_number(fname):
    match = re.search(r'_(\d+)', fname)
    return int(match.group(1)) if match else -1

def build_gif_from_images(folder, output_name, prefix, fps = 1):
    files = sorted(
        [f for f in os.listdir(folder) if f.endswith('.png') and f.startswith(prefix)],
        key=extract_number
    )
    
    if not files:
        print(f"[❌] Не найдено подходящих .png файлов в {folder} с префиксом '{prefix}'")
        return

    print(f"[✔] Найдено {len(files)} файлов. Собираем GIF: {output_name}")
    images = [imageio.imread(os.path.join(folder, f)) for f in files]
    imageio.mimsave(output_name, images, fps=fps, loop=0)
    print(f"[✅] GIF сохранён: {output_name}")


if __name__ == "__main__":
        # Папка с изображениями
    ptype = "Halo"
    build_gif_from_images(
        folder="run_test/graph",
        output_name= f"run_test/graph/{ptype}_dens3D.gif",
        prefix=f"{ptype}_density_yt3D"
    )