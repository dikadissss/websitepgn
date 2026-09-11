"""Registry of the jobs done in every duty, used by the recap page and the duty summary API."""
from dataclasses import dataclass
from importlib import import_module

from django.apps import apps


@dataclass(frozen=True)
class Job:
    key: str             # URL segment under /api/v1/
    label: str
    model_label: str
    api_namespace: str   # URL namespace of the job's API, under 'api:'
    update_url_name: str
    reports_module: str  # Module whose export_documents(record) lists the record's printed documents.

    @property
    def model(self):
        return apps.get_model(self.model_label)

    def export_documents(self, record):
        """The record's documents in print order: PDF bytes, or workbooks still to be converted."""
        return import_module(self.reports_module).export_documents(record)


# In the order of the duty's printed forms (Rekap Dinas PDF export).
JOBS = (
    Job('bast', 'BAST', 'bast.BastRecordModel', 'bast', 'bast:bastrecord_update', 'bast.reports'),
    Job('daily-report', 'Daily Report', 'daily_report.DailyReport', 'daily_report',
        'daily_report:dailyreport_update', 'daily_report.reports'),
    Job('qc', 'QC Parameter Gempa', 'qc.QcRecord', 'qc', 'qc:qcrecord_update', 'qc.reports'),
    Job('qcfm', 'QC Focal Mechanism', 'qcfm.QcFmRecord', 'qcfm', 'qcfm:qcfmrecord_update', 'qcfm.reports'),
    Job('seiscomp-checklist', 'Checklist SeisComP', 'cl_seiscomp.CsRecordModel', 'seiscomp_checklist',
        'cl_seiscomp:cs_update', 'cl_seiscomp.reports'),
    Job('email-web', 'Monitoring Email & Web', 'monitoring.EmailWebRecord', 'email_web',
        'monitoring:email_web_update', 'monitoring.reports'),
    Job('device-checklist', 'Checklist SeisComP & Aplikasi', 'monitoring.DeviceRecord', 'device_checklist',
        'monitoring:device_update', 'monitoring.reports'),
)
