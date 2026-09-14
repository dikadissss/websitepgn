import datetime

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .feed import SlmonError
from .models import SlmonSnapshot
from .services import draw_preview, preview_json

RECENT_DAYS = 7


@require_POST
def preview(request):
    """Read the slmon JSON now and draw its maps for the checklist form, without storing a snapshot."""
    try:
        token, snapshot, missing = draw_preview()
    except SlmonError as error:
        return JsonResponse({'error': str(error)}, status=502)
    except OSError as error:
        return JsonResponse({'error': f'Peta SLMON belum bisa dibuat ({error}).'}, status=500)
    return JsonResponse(preview_json(token, snapshot, missing))


def snapshots(request):
    """Snapshots of the last RECENT_DAYS days, newest first."""
    since = timezone.now() - datetime.timedelta(days=RECENT_DAYS)
    return JsonResponse({
        'snapshots': [snapshot.as_json() for snapshot in SlmonSnapshot.objects.filter(data_time__gte=since)],
    })
