"""The two maps of an SLMON snapshot, with a triangle per station colored by its status (the best of its channels,
as on the slmon2 page):

- the Peta: gempa.de tiles, NTWC outline and graticule, like the Peta Harian (daily_report.maps);
- the slmon2 view: OpenStreetMap HOT tiles with the "SUMMARY STATUS" box and pie chart of the slmon2 page.

Both are 1728 x 832 (about 2.08:1), the shape of the SLMON box of the checklist workbook (8.6 x 4.14 in)."""
import math
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

from daily_report.maps import FRAME, TileSource, base_map, draw_attribution, font, frame_map, save_png

BOUNDS = (93.0, -12.0, 142.0, 8.0)  # West, south, east, north: Indonesia.
MAP_SIZE = (1600, 704)  # Map area of the Peta; with its frame 1728 x 832.
MONITOR_SIZE = (MAP_SIZE[0] + 2 * FRAME, MAP_SIZE[1] + 2 * FRAME)  # The slmon2 view, as large as the framed Peta.
OSM_HOT_TILES = TileSource('https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', 'osm-hot',
                           '© OpenStreetMap contributors, tiles OSM France')
LOGO_PATH = Path(__file__).resolve().parent / 'static' / 'slmon' / 'inatews_ina.png'  # From inatews.bmkg.go.id.
LOGO_WIDTH = 320
MARKER = 9  # Half the width of a station triangle, in pixels.
COLORS = {
    'green': (56, 229, 77), 'yellow': (255, 230, 0), 'orange': (255, 150, 0), 'red': (230, 0, 0),
    'black': (27, 36, 48),
}
DRAW_ORDER = ('black', 'red', 'orange', 'yellow', 'green')  # Live stations are drawn last, on top.
LEGEND = (
    ('green', '< 10 detik'), ('yellow', '< 1 menit'), ('orange', '< 3 menit'), ('red', '< 30 menit'),
    ('black', '> 30 menit'),
)

# The slmon2 summary box: latency badges (text, background, text color), then the pie chart, whose slices use the
# CSS color names of the slmon2 Highcharts chart, clockwise from the top in the order that page shows them.
DARK = (33, 37, 41)
BADGES = (
    ('green', '<10s', (56, 229, 77), 'white'), ('yellow', '<1m', (255, 255, 0), DARK),
    ('orange', '<3m', (255, 165, 0), DARK), ('red', '<30m', (255, 0, 0), DARK), ('black', '>30m', (27, 36, 48), 'white'),
)
PIE_COLORS = {'green': (0, 128, 0), 'yellow': (255, 255, 0), 'orange': (255, 165, 0), 'red': (255, 0, 0), 'black': (0, 0, 0)}
PIE_ORDER = ('black', 'green', 'orange', 'red', 'yellow')
SUMMARY_BOX = (1170, 40, 1690, 500)  # Left, top, right, bottom in the slmon2 view.
SUMMARY_FILL = (247, 249, 252, 190)  # Translucent, as on the page.


def triangle(x, y, half=MARKER):
    return [(x, y - half), (x + half, y + half * 0.8), (x - half, y + half * 0.8)]


def draw_station_map(stations):
    """The Peta of [network, code, lon, lat, color1, status] stations, and the number of missing map tiles."""
    image, to_pixel, window, missing = base_map(BOUNDS, MAP_SIZE)
    _draw_stations(ImageDraw.Draw(image), stations, to_pixel)
    framed = frame_map(image, to_pixel, window)
    counts = Counter(station[5] for station in stations)
    _draw_legend(ImageDraw.Draw(framed), counts)  # After the frame, so the graticule does not cross it.
    return framed, missing


def draw_monitor_map(stations, counts):
    """The slmon2 view of the stations with the summary of counts ({status: stations}), and the missing tiles."""
    image, to_pixel, _, missing = base_map(BOUNDS, MONITOR_SIZE, source=OSM_HOT_TILES, outline=False)
    _draw_stations(ImageDraw.Draw(image), stations, to_pixel)
    image = _draw_summary(image, counts)
    _paste_logo(image)
    draw_attribution(ImageDraw.Draw(image), image.size, OSM_HOT_TILES.attribution)
    return image, missing


def _paste_logo(image):
    """The INATEWS-BMKG logo in the lower right corner, above the tile credit, as on the slmon2 page."""
    with Image.open(LOGO_PATH) as logo:
        logo = logo.convert('RGBA')
        logo = logo.resize((LOGO_WIDTH, round(LOGO_WIDTH * logo.height / logo.width)), Image.LANCZOS)
    image.paste(logo, (image.width - LOGO_WIDTH - 24, image.height - logo.height - 40), logo)


def render_station_map(stations, path):
    """Draw the Peta into a PNG at path; returns the number of missing map tiles."""
    image, missing = draw_station_map(stations)
    save_png(image, path)
    return missing


def render_monitor_map(stations, counts, path):
    """Draw the slmon2 view into a PNG at path; returns the number of missing map tiles."""
    image, missing = draw_monitor_map(stations, counts)
    save_png(image, path)
    return missing


def _draw_stations(draw, stations, to_pixel):
    order = {color: index for index, color in enumerate(DRAW_ORDER)}
    for _, _, lon, lat, _, status in sorted(stations, key=lambda station: order.get(station[5], 0)):
        draw.polygon(triangle(*to_pixel(lon, lat)), fill=COLORS.get(status, COLORS['black']), outline='black', width=2)


def _draw_legend(draw, counts):
    """Color key with the number of stations of each status, and the total, in the lower left corner of the Peta."""
    label_font, total_font = font(18), font(18, bold=True)
    row_height, padding = 26, 10
    width, height = 240, 2 * padding + row_height * (len(LEGEND) + 1)
    left, top = FRAME + 12, FRAME + MAP_SIZE[1] - 12 - height
    right = left + width - padding
    draw.rectangle((left, top, left + width, top + height), fill='white', outline='black', width=2)
    for index, (color, label) in enumerate(LEGEND):
        y = top + padding + (index + 0.5) * row_height
        draw.polygon(triangle(left + padding + MARKER, y), fill=COLORS[color], outline='black', width=1)
        draw.text((left + 2 * padding + 2 * MARKER, y), label, fill='black', font=label_font, anchor='lm')
        draw.text((right, y), str(counts.get(color, 0)), fill='black', font=label_font, anchor='rm')
    y = top + padding + (len(LEGEND) + 0.5) * row_height
    draw.line((left + padding, y - row_height / 2, right, y - row_height / 2), fill=(120, 120, 120), width=1)
    draw.text((left + 2 * padding + 2 * MARKER, y), 'Total', fill='black', font=total_font, anchor='lm')
    draw.text((right, y), str(sum(counts.values())), fill='black', font=total_font, anchor='rm')


def _draw_summary(image, counts):
    """The "SUMMARY STATUS" box of the slmon2 page: latency badges, station counts and the pie chart."""
    left, top, right, _ = SUMMARY_BOX
    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle(SUMMARY_BOX, fill=SUMMARY_FILL, outline=(215, 222, 230, 255), width=2)
    image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(image)
    draw.text(((left + right) / 2, top + 30), 'SUMMARY STATUS', fill=DARK, font=font(26), anchor='mm')

    badge_row, count_row = top + 78, top + 110
    columns = [left + 215 + index * 55 for index in range(len(BADGES) + 1)]  # One per badge, then Total.
    bold, regular = font(17, bold=True), font(17)
    draw.text((left + 14, badge_row), 'LATENCIES', fill=DARK, font=bold, anchor='lm')
    draw.text((left + 14, count_row), 'SEISMIC STATION', fill=DARK, font=regular, anchor='lm')
    for x, (status, text, fill, text_color) in zip(columns, BADGES):
        draw.rounded_rectangle((x - 25, badge_row - 13, x + 25, badge_row + 13), radius=5, fill=fill)
        draw.text((x, badge_row), text, fill=text_color, font=font(15, bold=True), anchor='mm')
        draw.text((x, count_row), str(counts.get(status, 0)), fill=DARK, font=regular, anchor='mm')
    draw.text((columns[-1], badge_row), 'Total', fill=DARK, font=bold, anchor='mm')
    draw.text((columns[-1], count_row), str(sum(counts.values())), fill=DARK, font=regular, anchor='mm')

    _draw_pie(draw, counts, center=((left + right) / 2, top + 290), radius=120)
    return image


def _draw_pie(draw, counts, center, radius):
    """Pie of the station counts with the status names on connector lines, like the slmon2 Highcharts chart."""
    total = sum(counts.values())
    if not total:
        return
    center_x, center_y = center
    slices, angle = [], -90.0  # PIL angles run clockwise from 3 o'clock; the chart starts at the top.
    for status in PIE_ORDER:
        if not counts.get(status):
            continue
        extent = 360 * counts[status] / total
        draw.pieslice((center_x - radius, center_y - radius, center_x + radius, center_y + radius),
                      angle, angle + extent, fill=PIE_COLORS[status], outline='white', width=1)
        slices.append((status, math.radians(angle + extent / 2)))
        angle += extent

    label_font = font(16, bold=True)
    for side in (-1, 1):  # Labels left and right of the pie, spread so the thin slices do not overlap.
        labels = sorted((center_y + (radius + 30) * math.sin(middle), status, middle)
                        for status, middle in slices if (math.cos(middle) >= 0) == (side > 0))
        previous = -math.inf
        for y, status, middle in labels:
            y = previous = max(y, previous + 22)
            label_x = center_x + side * (radius + 45)
            edge = (center_x + radius * math.cos(middle), center_y + radius * math.sin(middle))
            draw.line([edge, (label_x - side * 6, y)], fill=PIE_COLORS[status], width=2)
            draw.text((label_x, y), status, fill='black', font=label_font, anchor='lm' if side > 0 else 'rm')
