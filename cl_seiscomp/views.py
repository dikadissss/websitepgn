import csv
import datetime
import json
import logging
from collections import defaultdict
from io import StringIO

import plotly.graph_objects as go
import plotly.utils
from django.contrib import messages
from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from slmon.models import SlmonSnapshot
from slmon.services import ensure_map

from .models import WAKTU, CsRecordModel, StationListModel

logger = logging.getLogger(__name__)

GAPS_COLOR = 'rgb(75, 192, 192)'
SPIKES_COLOR = 'rgb(54, 162, 235)'
BLANKS_COLOR = 'rgb(255, 99, 132)'
SLMON_COLOR = 'rgb(255, 205, 86)'


##### Station List Views
class StationListView(ListView):
    model = StationListModel
    template_name = 'cl_seiscomp/station_list.html'
    context_object_name = 'station_list'


class StationCreateView(CreateView):
    model = StationListModel
    template_name = 'cl_seiscomp/sl_form.html'
    fields = '__all__'
    success_url = reverse_lazy('cl_seiscomp:station_list')


class StationUpdateView(UpdateView):
    model = StationListModel
    template_name = 'cl_seiscomp/sl_form.html'
    fields = '__all__'
    success_url = reverse_lazy('cl_seiscomp:station_list')


class StationDeleteView(DeleteView):
    model = StationListModel
    template_name = 'cl_seiscomp/sl_confirm_delete.html'
    success_url = reverse_lazy('cl_seiscomp:station_list')


class StationBulkCreateView(View):
    template_name = 'cl_seiscomp/sl_bulk_create.html'
    expected_headers = ['network', 'code', 'province', 'location', 'digitizer_type', 'UPT', 'longitude', 'latitude']

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        csv_file = request.FILES.get('csv_file')
        csv_data = request.POST.get('csv_data')
        remove_existing = request.POST.get('remove_existing')

        if not csv_file and not csv_data:
            messages.error(request, 'Please upload a CSV file or provide CSV data')
            return redirect('cl_seiscomp:sl_bulk_create')

        try:
            if csv_file:
                if not csv_file.name.endswith('.csv'):
                    messages.error(request, 'This is not a CSV file')
                    return redirect('cl_seiscomp:sl_bulk_create')
                csv_reader = csv.reader(StringIO(csv_file.read().decode('utf-8')))
                # Uploaded files always start with a header row.
                if next(csv_reader, None) is None:
                    messages.error(request, 'CSV file is empty')
                    return redirect('cl_seiscomp:sl_bulk_create')
            else:
                if not csv_data.strip():
                    messages.error(request, 'CSV data is empty')
                    return redirect('cl_seiscomp:sl_bulk_create')
                csv_reader = csv.reader(StringIO(csv_data))
                first_row = [cell.lower() for cell in next(csv_reader)]
                # Pasted data may or may not start with a header row.
                if not any(header.lower() in first_row for header in self.expected_headers):
                    csv_reader = csv.reader(StringIO(csv_data))

            stations, errors = self.parse_rows(csv_reader)

            with transaction.atomic():
                stations_deleted = 0
                if remove_existing:
                    stations_deleted, _ = StationListModel.objects.all().delete()
                    logger.info(f"Deleted {stations_deleted} existing stations as requested")
                StationListModel.objects.bulk_create(stations)

            if remove_existing and stations_deleted > 0:
                messages.warning(request, f'{stations_deleted} existing stations were removed as requested')
            if stations:
                messages.success(request, f'{len(stations)} stations added successfully')
            if len(errors) <= 5:
                for error in errors:
                    messages.error(request, error)
            else:
                messages.error(request, f'{len(errors)} rows had errors. First few errors:')
                for error in errors[:3]:
                    messages.error(request, error)
                messages.warning(request, f'... and {len(errors) - 3} more errors')
            return redirect('cl_seiscomp:station_list')

        except UnicodeDecodeError:
            messages.error(request, 'Error reading CSV file. Please ensure the file is encoded in UTF-8')
            logger.error(f"Unicode decode error while processing CSV file: {csv_file.name if csv_file else 'pasted data'}")
            return redirect('cl_seiscomp:sl_bulk_create')
        except Exception as e:
            messages.error(request, f'An unexpected error occurred while processing the CSV data: {str(e)}')
            logger.error(f"Unexpected error in StationBulkCreateView: {str(e)}", exc_info=True)
            return redirect('cl_seiscomp:sl_bulk_create')

    @staticmethod
    def parse_rows(csv_reader):
        """Stations to create from the data rows, and one message per invalid row."""
        stations, errors = [], []
        for row_number, row in enumerate(csv_reader, start=2):
            if not row or all(cell.strip() == '' for cell in row):
                continue
            if len(row) < 8:
                errors.append(f"Row {row_number}: Expected 8 columns, got {len(row)}. Row data: {row}")
                continue

            coordinates = {}
            for name, value in (('longitude', row[6].strip()), ('latitude', row[7].strip())):
                try:
                    coordinates[name] = float(value) if value else None
                except ValueError:
                    errors.append(f"Row {row_number}: Invalid {name} value '{value}'")
                    break
            else:
                stations.append(StationListModel(
                    network=row[0].strip(),
                    code=row[1].strip(),
                    province=row[2].strip(),
                    location=row[3].strip(),
                    digitizer_type=row[4].strip(),
                    UPT=row[5].strip(),
                    **coordinates,
                ))
        return stations, errors


##### Stats View
def _chart_layout(title, x_title, annotation_position, **extra):
    return dict(
        title={'text': title, 'font': {'size': 24, 'color': '#333'}, 'x': 0.5, 'xanchor': 'center'},
        xaxis_title={'text': x_title, 'font': {'size': 16, 'color': '#666'}},
        yaxis_title={'text': 'Count', 'font': {'size': 16, 'color': '#666'}},
        xaxis={'showgrid': True, 'gridcolor': '#eee', 'tickfont': {'size': 12}, 'tickangle': -45},
        yaxis={'showgrid': True, 'gridcolor': '#eee', 'tickfont': {'size': 12}},
        hovermode='x unified',
        hoverlabel={'font_size': 14, 'font_family': 'Arial'},
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': 1.02, 'xanchor': 'right', 'x': 1,
                'font': {'size': 14}, 'title': {'font': {'size': 16}}},
        margin={'t': 80, 'b': 80, 'l': 80, 'r': 80},
        plot_bgcolor='#fff',
        paper_bgcolor='#fff',
        annotations=[{
            'text': 'Click and drag to zoom, double-click to reset zoom',
            'x': annotation_position[0], 'y': annotation_position[1], 'xref': 'paper', 'yref': 'paper',
            'showarrow': False, 'font': {'size': 12, 'color': '#999'},
            'bgcolor': 'rgba(255, 255, 255, 0.8)', 'align': 'right',
        }],
        **extra,
    )


class StatsView(View):
    template_name = 'cl_seiscomp/stats.html'

    def get(self, request):
        start_date, end_date = self.date_range(request.GET)
        selected_time = request.GET.get('time')

        records = CsRecordModel.objects.filter(date__range=[start_date, end_date]).order_by('date', 'id')
        if selected_time and selected_time != 'All':
            records = records.filter(jam_pelaksanaan=selected_time)

        dates, gaps_data, blanks_data, spikes_data, slmon_data = [], [], [], [], []
        station_errors = defaultdict(lambda: {'gaps': 0, 'spikes': 0, 'blanks': 0})
        rows = records.values_list('date', 'jam_pelaksanaan', 'count_gaps', 'count_blanks', 'count_spikes', 'slmon',
                                   'gaps', 'spikes', 'blanks')
        for date, time, gap_count, blank_count, spike_count, slmon, gaps, spikes, blanks in rows:
            dates.append(f"{date:%Y-%m-%d} {time}")
            gaps_data.append(gap_count)
            blanks_data.append(blank_count)
            spikes_data.append(spike_count)
            slmon_data.append(slmon)
            for kind, stations in (('gaps', gaps), ('spikes', spikes), ('blanks', blanks)):
                for station in (stations or '').splitlines():
                    station_errors[station][kind] += 1

        sorted_stations = sorted(station_errors.items(), key=lambda item: sum(item[1].values()), reverse=True)
        period = f'{start_date:%b %Y} - {end_date:%b %Y}'

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=gaps_data, name='Gaps', line=dict(color=GAPS_COLOR)))
        fig.add_trace(go.Scatter(x=dates, y=blanks_data, name='Blanks', line=dict(color=BLANKS_COLOR)))
        fig.add_trace(go.Scatter(x=dates, y=spikes_data, name='Spikes', line=dict(color=SPIKES_COLOR)))
        fig.add_trace(go.Scatter(x=dates, y=slmon_data, name='SLMON', line=dict(color=SLMON_COLOR)))
        fig.update_layout(**_chart_layout(f'Station Statistics ({period})', 'Date and Time', (1.1, -0.7)))

        station_names = [name for name, _ in sorted_stations]
        station_fig = go.Figure()
        for kind, label, color in (('gaps', 'Gaps', GAPS_COLOR), ('spikes', 'Spikes', SPIKES_COLOR),
                                   ('blanks', 'Blanks', BLANKS_COLOR)):
            station_fig.add_trace(go.Bar(
                x=station_names, y=[counts[kind] for _, counts in sorted_stations], name=label, marker_color=color,
            ))
        station_fig.update_layout(**_chart_layout(
            f'Frequency of Errors per Station ({period})', 'Station', (1, -0.3), barmode='stack',
        ))

        return render(request, self.template_name, {
            'plot_json': json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder),
            'station_plot_json': json.dumps(station_fig, cls=plotly.utils.PlotlyJSONEncoder),
            'start_date': start_date,
            'end_date': end_date,
            'times': WAKTU,
            'selected_time': selected_time or 'All',
        })

    @staticmethod
    def date_range(params):
        """The requested start/end dates, or the last 30 days."""
        try:
            return (datetime.date.fromisoformat(params['start_date']),
                    datetime.date.fromisoformat(params['end_date']))
        except (KeyError, ValueError):
            end_date = timezone.localdate()
            return end_date - datetime.timedelta(days=30), end_date


##### Checklist Seiscomp Views
class CsListView(TemplateView):
    template_name = 'cl_seiscomp/cs_list.html'


def take_slmon_image(request, record):
    """Apply the SLMON part of the checklist form to the record: clear its image, or copy a map of the chosen
    snapshot (slmon_snapshot_id) into it, the slmon2 view unless slmon_map_style is 'peta'. It is a copy, so the
    checklist keeps it whatever happens to the snapshot."""
    if 'clear_image' in request.POST and record.slmon_image:
        record.slmon_image.delete(save=False)
    snapshot_id = request.POST.get('slmon_snapshot_id', '')
    snapshot = SlmonSnapshot.objects.filter(pk=snapshot_id).first() if snapshot_id.isdigit() else None
    if snapshot is None:
        return
    try:
        ensure_map(snapshot)
        source = snapshot.map_path if request.POST.get('slmon_map_style') == 'peta' else snapshot.monitor_map_path
        content = ContentFile(source.read_bytes())
    except OSError as error:
        messages.warning(request, f'Peta SLMON tidak bisa disalin ({error}).')
        return
    if record.slmon_image:
        record.slmon_image.delete(save=False)
    record.slmon_image.save(f'slmon_{record.cs_id}.png', content, save=False)


class CsFormMixin:
    model = CsRecordModel
    template_name = 'cl_seiscomp/cs_form.html'
    # slmon_image is not a form field: it is copied from an SLMON snapshot by take_slmon_image.
    fields = ['kelompok', 'date', 'shift', 'jam_pelaksanaan', 'operator', 'cs_id', 'gaps', 'spikes', 'blanks', 'slmon']
    success_url = reverse_lazy('cl_seiscomp:cs_list')

    def form_valid(self, form):
        take_slmon_image(self.request, form.instance)
        return super().form_valid(form)


class CsCreateView(CsFormMixin, CreateView):
    pass


class CsUpdateView(CsFormMixin, UpdateView):
    pass
