"""Areas used to classify earthquakes, read from the Atlas BNA files in vector/."""
from functools import cache
from pathlib import Path

from django.conf import settings

from .feeds import parse_coordinate

NTWC_BNA = Path(settings.BASE_DIR) / 'vector' / 'NTWC1.bna'


def load_bna(path):
    """Polygons of a BNA file: per record a '"name","type",count' line, then count 'lon,lat' lines."""
    lines = iter([line.strip() for line in Path(path).read_text().splitlines() if line.strip()])
    polygons = []
    for header in lines:
        count = abs(int(header.rsplit(',', 1)[1]))
        polygons.append([tuple(float(value) for value in next(lines).split(',')[:2]) for _ in range(count)])
    return polygons


@cache
def ntwc_polygons():
    """The NTWC area, the boundary between "Event Indonesia" and "Event Luar"."""
    return load_bna(NTWC_BNA)


def inside(polygon, lon, lat):
    """Ray casting: whether (lon, lat) lies inside the polygon (its last point joins the first)."""
    result = False
    previous_lon, previous_lat = polygon[-1]
    for vertex_lon, vertex_lat in polygon:
        if (vertex_lat > lat) != (previous_lat > lat):
            crossing = vertex_lon + (lat - vertex_lat) * (previous_lon - vertex_lon) / (previous_lat - vertex_lat)
            if lon < crossing:
                result = not result
        previous_lon, previous_lat = vertex_lon, vertex_lat
    return result


def in_indonesia(lon, lat):
    return any(inside(polygon, lon, lat) for polygon in ntwc_polygons())


def count_indonesia(table):
    """(events inside the NTWC area, events outside it) of a table with 'Lat'/'Long' columns such as '8.1 S'."""
    indonesia = sum(in_indonesia(parse_coordinate(lon), parse_coordinate(lat)) for lat, lon in zip(table['Lat'], table['Long']))
    return indonesia, len(table) - indonesia
