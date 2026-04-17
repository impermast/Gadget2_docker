import imageio.v2 as imageio
import os
import re

# Папка с изображениями
image_folder = './gif'
output_gif = 'dm_end.gif'

def extract_number(fname):
    match = re.search(r'azim(\d+)', fname)
    return int(match.group(1)) if match else -1


files = sorted(
    [f for f in os.listdir(image_folder) if f.endswith('.png')],
    key=extract_number
)


images = [imageio.imread(os.path.join(image_folder, f)) for f in files]
imageio.mimsave('dm_rotation.gif', images, fps=2)
