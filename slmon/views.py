import datetime
import json

import plotly.graph_objects as go
import plotly.utils
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from .feed import SLMON_PAGE_URL, SlmonError
from .models import SlmonSnapshot
from .services import ensure_map, fetch_snapshot

RECENT_SNAPSHOTS = 20
CHART_DAYS = (7, 30, 90)
DEFAULT_CHART_DAYS = 30
NOT_BLANK_COLOR = 'rgb(40, 167, 69)'
BLANK_COLOR = 'rgb(220, 53, 69)'
MISSING_TILES_MESSAGE = '{} potongan peta tidak bisa diunduh dari tiles.gempa.de. Coba ambil data lagi.'


def status_chart(snapshots, days):
    """Plotly figure (JSON) of the Not Blank and Blank stations of the snapshots over time (WIB)."""
    times, not_blank, blank = [], [], []
    for snapshot in snapshots:
        times.append(snapshot.local_time.replace(tzinfo=None))
        not_blank.append(snapshot.not_blank)
        blank.append(snapshot.blank)
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=times, y=not_blank, name='Not Blank', mode='lines+markers',
                                line=dict(color=NOT_BLANK_COLOR)))
    figure.add_trace(go.Scatter(x=times, y=blank, name='Blank', mode='lines+markers', line=dict(color=BLANK_COLOR)))
    figure.update_layout(
        title=f'Kondisi sensor seismik, {days} hari terakhir',
        xaxis_title='Waktu (WIB)', yaxis_title='Jumlah sensor', yaxis_rangemode='tozero',
        hovermode='x unified', legend=dict(orientation='h', y=-0.25), margin=dict(l=60, r=20, t=50, b=40),
        template='plotly_white',
    )
    return json.dumps(figure, cls=plotly.utils.PlotlyJSONEncoder)


class SlmonView(TemplateView):
    """Maps and caption of a snapshot (the latest one by default), the chart of the last days and the recent
    snapshots."""
    template_name = 'slmon/slmon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        snapshots = SlmonSnapshot.objects.all()
        if 'pk' in self.kwargs:
            snapshot = get_object_or_404(SlmonSnapshot, pk=self.kwargs['pk'])
        else:
            snapshot = snapshots.first()
        if snapshot is not None:
            try:
                ensure_map(snapshot)
            except OSError as error:
                messages.warning(self.request, f'Peta SLMON belum bisa dibuat ({error}).')

        days = self.chart_days()
        since = timezone.now() - datetime.timedelta(days=days)
        chart_snapshots = snapshots.filter(data_time__gte=since).order_by('data_time')
        context.update(
            snapshot=snapshot, snapshots=snapshots[:RECENT_SNAPSHOTS], source_url=SLMON_PAGE_URL,
            chart_json=status_chart(chart_snapshots, days), chart_days=days, chart_day_choices=CHART_DAYS,
        )
        return context

    def chart_days(self):
        try:
            days = int(self.request.GET.get('days', DEFAULT_CHART_DAYS))
        except ValueError:
            return DEFAULT_CHART_DAYS
        return days if days in CHART_DAYS else DEFAULT_CHART_DAYS


@require_POST
def fetch(request):
    """"Ambil data SLMON": read the JSON now and show its snapshot."""
    try:
        snapshot, missing = fetch_snapshot()
    except SlmonError as error:
        messages.error(request, str(error))
        return redirect('slmon:index')
    except OSError as error:
        messages.warning(request, f'Peta SLMON belum bisa dibuat ({error}).')
        return redirect('slmon:index')
    if missing:
        messages.warning(request, MISSING_TILES_MESSAGE.format(missing))
    return redirect('slmon:detail', pk=snapshot.pk)
