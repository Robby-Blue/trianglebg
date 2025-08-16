import argparse
import numpy as np
import numba
import random
import cv2

def create_mask(colors):
    image = np.zeros((256, 144, 3), np.uint8)

    rows_per_color = 256 // len(colors) + 1

    for y in numba.prange(0, 256):
        for x in numba.prange(144):
            color_idx = (y-256)//rows_per_color
            color = colors[color_idx]
            image[y, x] = color

    for _ in range(10):
        image = cv2.GaussianBlur(image, (101, 101), cv2.BORDER_DEFAULT)
    
    return image

def create_points():
    points = []

    y = -2*size
    while y < height:
        x = -2*size
        y += size
        while x < width:
            x += size
            dot = get_dot(x, y)
            points.append(dot)

    points = np.array(points, dtype=np.int32)
    return points

def get_dot(x, y):
    new_x = x+random.randint(-size//2, size//2)
    new_y = y+random.randint(-size//2, size//2)

    return [new_x, new_y]

@numba.njit(parallel=True)
def render_image(points, mask):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for y in numba.prange(height):
        for x in numba.prange(width):
            img[y,x] = get_color((x, y), points, mask)
    return img

@numba.njit
def get_color(pos, points, mask):
    x, y = pos
    
    mask_height, mask_width, _ = mask.shape
    closest_point = None
    smallest_dist = 999999
    
    for point in points:
        dist = (point[0] - x)**2 + (point[1] - y)**2

        if dist < smallest_dist:
            smallest_dist = dist
            closest_point = point

    px, py = closest_point[0], closest_point[1]

    mask_x = int(px / width * (mask_width-1))
    mask_y = int(py / height * (mask_height-1))

    if mask_y < 0:
        mask_y = 0
    if mask_y > mask_height-1:
        mask_y = mask_height-1
    if mask_x < 0:
        mask_x = 0
    if mask_x > mask_width-1:
        mask_x = mask_width-1

    color = mask[mask_y, mask_x]
    y_diff = abs(y - py) / size * 0.8 * color_offset
    color = desaturate_bgr(color, y_diff)
    return color

@numba.njit
def desaturate_bgr(bgr, percentage):
    b, g, r = bgr
    l = int(0.11 * b + 0.59 * g + 0.30 * r)
    
    b = int(b + (l - b) * percentage)
    g = int(g + (l - g) * percentage)
    r = int(r + (l - r) * percentage)
    
    return [b, g, r]

def parse_size(value):
    try:
        parts = value.split("x")
        return int(parts[0].strip()), int(parts[1].strip())
    except:
        raise argparse.ArgumentTypeError("Size must be in Width x Height format, like 1280x720")

def parse_colors(value):
    try:
        parts = value.split(",")
        return [rgb_hex_to_bgr_tuple(int(part, 16)) for part in parts]
    except:
        raise argparse.ArgumentTypeError("Colors must be hex codes, seperated by commas, like 5BCEFA,F5A9B8,FFFFF,F5A9B8,5BCEFA")

def rgb_hex_to_bgr_tuple(rgb_int):
    r = (rgb_int >> 16) & 0xFF
    g = (rgb_int >> 8) & 0xFF
    b = rgb_int & 0xFF

    return (b, g, r)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="trianglesbg")
    
    parser.add_argument("-r", "--resolution", default="1280x720", type=parse_size, help="Width x Height")
    parser.add_argument("-c", "--colors", default=None, type=parse_colors, help="Colors used in the image. Hex codes seperates by commas", required=True)
    parser.add_argument("-s", "--size", type=int, default=None, help="Size of Triangles")
    parser.add_argument("-m", "--color-offset", type=float, default=1, help="Multiplier for the color offset")
    
    args = parser.parse_args()

    resolution = args.resolution
    width, height = resolution
    if args.size:
        size = args.size
    else:
        size = height // 8
    color_offset = args.color_offset

    mask = create_mask(args.colors)
    points = create_points()
    image_data = render_image(points, mask)
    cv2.imwrite("output.png", image_data)