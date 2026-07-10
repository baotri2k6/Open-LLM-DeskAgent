import os
from PIL import Image
from pathlib import Path

texture_dir = Path(r"d:\Open LLM DeskAgent\assets\live2d\huohuo2\huohuo\huohuo.8192")

for i in range(4):
    img_name = f"texture_0{i}.png"
    img_path = texture_dir / img_name
    backup_path = texture_dir / f"texture_0{i}_backup.png"
    
    # If the file is already renamed or doesn't exist
    if not img_path.exists() and not backup_path.exists():
        continue
        
    if not backup_path.exists():
        print(f"Backing up {img_path.name}...")
        img_path.rename(backup_path)
        
    with Image.open(backup_path) as img:
        width, height = img.size
        if width > 2048 or height > 2048:
            print(f"Resizing {backup_path.name} from {width}x{height} to 2048x2048...")
            resized_img = img.resize((2048, 2048), Image.Resampling.LANCZOS)
            resized_img.save(img_path, "PNG", optimize=True)
        else:
            print(f"Image {backup_path.name} is already {width}x{height}, restoring...")
            img.save(img_path, "PNG", optimize=True)
            
print("Texture compression completed successfully!")
