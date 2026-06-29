import os
from PIL import Image, ImageDraw

def main():
    dest_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    os.makedirs(dest_dir, exist_ok=True)
    
    # Create 512x512 sky blue image
    img = Image.new('RGB', (512, 512), color='#0284c7')
    d = ImageDraw.Draw(img)
    
    # Write text manually by drawing shapes or using basic drawing
    # Just draw a simple cross or a shape since font files might not be present offline
    # Draw simple "M" and "V" outlines in white
    # M
    d.line([(100, 400), (100, 100), (256, 300), (412, 100), (412, 400)], fill="white", width=40)
    
    # Save the icon
    img.save(os.path.join(dest_dir, "icon.png"))
    print("Icon generated successfully.")

if __name__ == "__main__":
    main()
