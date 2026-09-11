"""Epicenter map of a daily report, drawn on the server with PIL over tiles.gempa.de (Web Mercator tiles)."""
import math
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

from core.feeds import parse_coordinate, parse_depth
from core.regions import ntwc_polygons

TILE_URL = 'https://tiles.gempa.de/{z}/{x}/{y}.png'
TILE_SIZE = 256
MAX_ZOOM = 10
TILE_TIMEOUT = 15
TILE_WORKERS = 8
MAP_SIZE = (1600, 1000)      # Map area in pixels.
FRAME = 64                   # White border around the map holding the degree labels.
MIN_LON_SPAN = 15.0          # Smallest area shown, in degrees.
MIN_LAT_SPAN = 9.0
PADDING = 0.12               # Margin around the events, as a fraction of the area.
MAX_LATITUDE = 80.0
DEFAULT_BOUNDS = (90.0, -35.0, 180.0, 20.0)  # West, south, east, north of the paper map, for days without events.
MISSING_TILE_COLOR = (215, 225, 235)
GRID_STEPS = (1, 2, 5, 10, 20, 30, 45, 60)
MAX_GRID_LINES = 7
FONT_DIRECTORY = Path('/usr/share/fonts/truetype/liberation')
NTWC_COLOR = (255, 120, 0)   # Outline of the NTWC area (core.regions).
NTWC_WIDTH = 3

# Legend of the paper map: color by depth (km), size by magnitude.
DEPTH_CLASSES = ((60, (230, 0, 0)), (300, (255, 235, 0)), (math.inf, (0, 205, 0)))
MAGNITUDE_CLASSES = ((4.0, 7), (5.0, 10), (math.inf, 14))
DEPTH_LABELS = ('D ≤ 60 km', '60 < D ≤ 300 km', 'D > 300 km')
MAGNITUDE_LABELS = ('M ≤ 4.0 SR', '4.0 < M ≤ 5.0 SR', 'M > 5.0 SR')


def font(size, bold=False):
    name = 'LiberationSans-Bold.ttf' if bold else 'LiberationSans-Regular.ttf'
    try:
        return ImageFont.truetype(str(FONT_DIRECTORY / name), size)
    except OSError:
        return ImageFont.load_default(size)


def depth_color(depth):
    return next(color for limit, color in DEPTH_CLASSES if depth <= limit)


def marker_radius(magnitude):
    return next(radius for limit, radius in MAGNITUDE_CLASSES if magnitude <= limit)


def event_points(table):
    """(longitude, latitude, depth, magnitude) of each event of a daily report table."""
    points = []
    for event in table.to_dict(orient='records'):
        magnitude = event['Mag']
        magnitude = 0.0 if magnitude is None or magnitude != magnitude else float(magnitude)  # NaN -> 0
        points.append((parse_coordinate(event['Long']), parse_coordinate(event['Lat']), parse_depth(event['D(Km)']), magnitude))
    return points


def crosses_antimeridian(longitudes):
    return bool(longitudes) and max(longitudes) - min(longitudes) > 180


def map_bounds(points):
    """(west, south, east, north) around the events, with a margin and a minimum size.

    When the events straddle the antimeridian, western longitudes are shifted by +360 so the area stays
    continuous (east is then above 180)."""
    if not points:
        return DEFAULT_BOUNDS
    longitudes = [lon for lon, *_ in points]
    latitudes = [lat for _, lat, *_ in points]
    if crosses_antimeridian(longitudes):
        longitudes = [lon + 360 if lon < 0 else lon for lon in longitudes]
    lon_span = max(max(longitudes) - min(longitudes), MIN_LON_SPAN) * (1 + 2 * PADDING)
    lat_span = max(max(latitudes) - min(latitudes), MIN_LAT_SPAN) * (1 + 2 * PADDING)
    lon_center = (max(longitudes) + min(longitudes)) / 2
    lat_center = (max(latitudes) + min(latitudes)) / 2
    return (lon_center - lon_span / 2, max(lat_center - lat_span / 2, -MAX_LATITUDE),
            lon_center + lon_span / 2, min(lat_center + lat_span / 2, MAX_LATITUDE))


def mercator(lon, lat):
    """Position in the zoom-0 world, which is TILE_SIZE pixels wide (longitudes above 180 continue eastward)."""
    sin = math.sin(math.radians(max(min(lat, MAX_LATITUDE), -MAX_LATITUDE)))
    return (lon + 180) / 360 * TILE_SIZE, (0.5 - math.log((1 + sin) / (1 - sin)) / (4 * math.pi)) * TILE_SIZE


def inverse_mercator(x, y):
    return x / TILE_SIZE * 360 - 180, math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / TILE_SIZE))))


def pixel_window(bounds):
    """(left, top, width, height) of the area in the zoom-0 world, widened to the MAP_SIZE aspect ratio."""
    west, south, east, north = bounds
    left, top = mercator(west, north)
    right, bottom = mercator(east, south)
    width, height = right - left, bottom - top
    aspect = MAP_SIZE[0] / MAP_SIZE[1]
    if width / height < aspect:
        left -= (height * aspect - width) / 2
        width = height * aspect
    else:
        top -= (width / aspect - height) / 2
        height = width / aspect
        world_top, world_bottom = mercator(0, MAX_LATITUDE)[1], mercator(0, -MAX_LATITUDE)[1]
        top = min(max(top, world_top), world_bottom - height)
    return left, top, width, height


def fetch_tile(zoom, x, y):
    """PNG bytes of one tile, or None when tiles.gempa.de does not deliver it."""
    try:
        response = requests.get(TILE_URL.format(z=zoom, x=x, y=y), timeout=TILE_TIMEOUT)
    except requests.RequestException:
        return None
    if response.ok and response.headers.get('Content-Type', '').startswith('image/'):
        return response.content
    return None


def load_tile(zoom, x, y):
    """A tile from the disk cache, downloaded on first use; None when it cannot be fetched."""
    path = Path(settings.TILE_CACHE_DIR) / str(zoom) / str(x) / f'{y}.png'
    if not path.exists():
        content = fetch_tile(zoom, x, y)
        if content is None:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    try:
        with Image.open(path) as tile:
            return tile.convert('RGB')
    except OSError:
        path.unlink(missing_ok=True)
        return None


def stitch_tiles(zoom, left, top, width, height):
    """Image of the given window of the world at a zoom level, and the number of tiles that could not be loaded."""
    count = 2 ** zoom
    columns = range(math.floor(left / TILE_SIZE), math.floor((left + width - 1) / TILE_SIZE) + 1)
    rows = range(max(math.floor(top / TILE_SIZE), 0), min(math.floor((top + height - 1) / TILE_SIZE), count - 1) + 1)
    positions = [(column, row) for column in columns for row in rows]
    canvas = Image.new('RGB', (math.ceil(width), math.ceil(height)), MISSING_TILE_COLOR)
    missing = 0
    with ThreadPoolExecutor(max_workers=TILE_WORKERS) as pool:
        tiles = pool.map(lambda position: load_tile(zoom, position[0] % count, position[1]), positions)
        for (column, row), tile in zip(positions, tiles):
            if tile is None:
                missing += 1
            else:
                canvas.paste(tile, (round(column * TILE_SIZE - left), round(row * TILE_SIZE - top)))
    return canvas, missing


def degree_label(value, positive, negative):
    value = round(value, 6)
    if value == 0:
        return '0°'
    return f'{abs(value):g}°{positive if value > 0 else negative}'


def longitude_label(lon):
    lon = (lon + 180) % 360 - 180
    return '180°' if lon == -180 else degree_label(lon, 'E', 'W')


def grid_values(low, high):
    step = next((step for step in GRID_STEPS if (high - low) / step <= MAX_GRID_LINES), GRID_STEPS[-1])
    value = math.ceil(low / step) * step
    while value <= high:
        yield value
        value += step


def render_map(table, path):
    """Draw the events of a daily report table into a PNG at path; returns the number of missing map tiles."""
    image, missing = draw_map(table)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.png', delete=False) as temporary:
        image.save(temporary, 'PNG')
    os.replace(temporary.name, path)
    return missing


def draw_map(table):
    """Map image of the events of a daily report table, and the number of map tiles that could not be loaded."""
    points = event_points(table)
    bounds = map_bounds(points)
    left, top, width, height = pixel_window(bounds)
    zoom = max(0, min(MAX_ZOOM, round(math.log2(MAP_SIZE[0] / width))))
    scale = 2 ** zoom
    background, missing = stitch_tiles(zoom, left * scale, top * scale, width * scale, height * scale)
    image = background.resize(MAP_SIZE, Image.LANCZOS)

    def to_pixel(lon, lat):
        x, y = mercator(lon, lat)
        return (x - left) / width * MAP_SIZE[0], (y - top) / height * MAP_SIZE[1]

    draw = ImageDraw.Draw(image)
    for polygon in ntwc_polygons():  # Its longitudes are all east of 0, so they need no antimeridian shift.
        outline = [to_pixel(lon, lat) for lon, lat in polygon]
        draw.line(outline + outline[:1], fill=NTWC_COLOR, width=NTWC_WIDTH, joint='curve')
    shift = bounds[2] > 180  # The area continues east of the antimeridian.
    for lon, lat, depth, magnitude in sorted(points, key=lambda point: point[3]):  # Largest events on top.
        x, y = to_pixel(lon + 360 if shift and lon < 0 else lon, lat)
        radius = marker_radius(magnitude)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=depth_color(depth), outline='black', width=2)
    if not points:
        draw.text((MAP_SIZE[0] / 2, MAP_SIZE[1] / 2), 'Tidak ada gempa', fill='black', font=font(40, bold=True), anchor='mm')
    attribution = 'Tiles © gempa GmbH'
    text_box = draw.textbbox((MAP_SIZE[0] - 8, MAP_SIZE[1] - 6), attribution, font=font(16), anchor='rd')
    draw.rectangle((text_box[0] - 4, text_box[1] - 2, text_box[2] + 4, text_box[3] + 2), fill=(255, 255, 255))
    draw.text((MAP_SIZE[0] - 8, MAP_SIZE[1] - 6), attribution, fill=(60, 60, 60), font=font(16), anchor='rd')

    framed = Image.new('RGB', (MAP_SIZE[0] + 2 * FRAME, MAP_SIZE[1] + 2 * FRAME), 'white')
    framed.paste(image, (FRAME, FRAME))
    _draw_grid(ImageDraw.Draw(framed), to_pixel, (left, top, width, height))
    return framed, missing


def _draw_grid(draw, to_pixel, window):
    """Graticule over the map with degree labels in the white frame, and the black map border."""
    left, top, width, height = window
    west, north = inverse_mercator(left, top)
    east, south = inverse_mercator(left + width, top + height)
    label_font = font(20)
    right_edge, bottom_edge = FRAME + MAP_SIZE[0], FRAME + MAP_SIZE[1]
    for lon in grid_values(west, east):
        x = FRAME + to_pixel(lon, 0)[0]
        draw.line((x, FRAME, x, bottom_edge), fill=(40, 40, 40), width=1)
        draw.text((x, FRAME - 8), longitude_label(lon), fill='black', font=label_font, anchor='md')
        draw.text((x, bottom_edge + 8), longitude_label(lon), fill='black', font=label_font, anchor='ma')
    for lat in grid_values(south, north):
        y = FRAME + to_pixel(west, lat)[1]
        draw.line((FRAME, y, right_edge, y), fill=(40, 40, 40), width=1)
        label = degree_label(lat, 'N', 'S')
        draw.text((FRAME - 6, y), label, fill='black', font=label_font, anchor='rm')
        draw.text((right_edge + 6, y), label, fill='black', font=label_font, anchor='lm')
    draw.rectangle((FRAME, FRAME, right_edge, bottom_edge), outline='black', width=4)
