"""Reading the slmon JSON into a stored snapshot with its maps, or into a preview for the checklist form."""
import re
import time
import uuid

from .feed import fetch_status, parse_status
from .maps import render_monitor_map, render_station_map
from .models import MAP_DIRECTORY, SlmonSnapshot, media_path, media_src

PREVIEW_DIRECTORY = f'{MAP_DIRECTORY}/preview'
PREVIEW_MAX_AGE = 24 * 3600  # Seconds; older previews were never saved into a checklist.
PREVIEW_TOKEN = re.compile(r'[0-9a-f]{32}')


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


# Previews: the checklist form reads the same JSON and draws the slmon2 view (the only map a checklist takes), but
# stores no snapshot. The map is a temporary file under MEDIA_ROOT (so the browser can show it); saving the checklist
# copies it and deletes it.

def preview_name(token):
    return f'{PREVIEW_DIRECTORY}/{token}_slmon2.png'


def preview_path(token):
    """Path of the preview map of a token, or None when the token is not one draw_preview makes."""
    if not isinstance(token, str) or not PREVIEW_TOKEN.fullmatch(token):
        return None
    return media_path(preview_name(token))


def delete_preview(token):
    path = preview_path(token)
    if path is not None:
        path.unlink(missing_ok=True)


def delete_old_previews(max_age=PREVIEW_MAX_AGE):
    directory = media_path(PREVIEW_DIRECTORY)
    if not directory.is_dir():
        return
    oldest = time.time() - max_age
    for path in directory.glob('*.png'):
        try:
            if path.stat().st_mtime < oldest:
                path.unlink()
        except FileNotFoundError:
            pass


def draw_preview():
    """Read the slmon JSON now and draw its slmon2 view without storing a snapshot: (token, unsaved snapshot, missing
    tiles).

    Raises feed.SlmonError when the JSON cannot be read, OSError when a map cannot be written."""
    data_time, stations = parse_status(fetch_status())
    snapshot = SlmonSnapshot(data_time=data_time, stations=stations)
    delete_old_previews()
    token = uuid.uuid4().hex
    missing = render_monitor_map(stations, snapshot.status_counts, preview_path(token))
    return token, snapshot, missing


def preview_json(token, snapshot, missing):
    """The preview as the checklist form uses a stored snapshot (SlmonSnapshot.as_json), with id preview-<token> and
    no Peta (map_url)."""
    data = {
        **snapshot.as_json(),
        'id': f'preview-{token}',
        'label': f'{snapshot.label} · baru (tidak disimpan)',
        'monitor_map_url': media_src(preview_name(token)),
        'missing_tiles': missing,
    }
    del data['map_url']
    return data
