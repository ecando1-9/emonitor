"""
Small helper to convert/resize an image into `icon.png` for the project.
Usage:
    python tools/convert_icon.py "C:\path\to\your-image.jpg" --size 64 --output ..\icon.png
By default it writes `icon.png` to the project root (one level up from tools/).
"""
import sys
import os
from PIL import Image
import argparse

def convert(input_path, output_path, size):
    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}")
        return 2
    try:
        img = Image.open(input_path)
        img = img.convert("RGBA")
        img = img.resize((size, size), Image.LANCZOS)
        img.save(output_path, format="PNG")
        print(f"Saved icon to: {output_path}")
        return 0
    except Exception as e:
        print(f"Error converting image: {e}")
        return 3

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Convert image to icon.png for eMonitor")
    parser.add_argument('input', help='Path to input image file')
    parser.add_argument('--size', type=int, default=64, help='Pixel size (square) for icon, default 64')
    parser.add_argument('--output', default=os.path.join(os.path.dirname(__file__), '..', 'icon.png'), help='Output path (default: project root icon.png)')
    args = parser.parse_args()
    out = os.path.abspath(args.output)
    code = convert(args.input, out, args.size)
    sys.exit(code)
