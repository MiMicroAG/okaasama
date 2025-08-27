from PIL import Image
import shutil
import os

tmp_path = os.path.join(os.getcwd(), 'test_image_tmp.jpg')
img = Image.new('RGB', (200,200), color=(255,255,255))
img.save(tmp_path, 'JPEG')

dest_dir = os.path.join(os.getcwd(), 'お母様カレンダー')
os.makedirs(dest_dir, exist_ok=True)
dest_path = os.path.join(dest_dir, 'test_image_for_notify.jpg')
shutil.move(tmp_path, dest_path)
print('created', dest_path)
