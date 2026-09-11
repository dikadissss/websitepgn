"""Reading the slmon JSON into a stored snapshot with its maps."""
from .feed import fetch_status, parse_status
from .maps import render_monitor_map, render_station_map
from .models import SlmonSnapshot


def render_maps(snapshot):
    """Draw both maps of the snapshot (the Peta and the slmon2 view); returns the number of missing map tiles."""
    return (render_station_map(snapshot.stations, snapshot.map_path)
            + render_monitor_map(snapshot.stations, snapshot.status_counts, snapshot.monitor_map_path))


def ensure_map(snapshot):
    """Draw the snapshot's maps when a file is missing; returns the number of missing map tiles."""
    if snapshot.map_path.exists() and snapshot.monitor_map_path.exists():
        return 0
    return render_maps(snapshot)


def fetch_snapshot():
    """Read the slmon JSON now, store it (once per data time) and draw its maps: (snapshot, missing map tiles).

    Raises feed.SlmonError when the JSON cannot be read, OSError when a map cannot be written."""
    data_time, stations = parse_status(fetch_status())
    snapshot, _ = SlmonSnapshot.objects.get_or_create(data_time=data_time, defaults={'stations': stations})
    return snapshot, render_maps(snapshot)
