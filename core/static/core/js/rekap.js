/*
 * Rekap page: every job of one duty slot (Rekap Dinas, with a PDF export of all its forms) and the records of
 * one job type filtered by group, operator and dates, with counts per group and per operator and a PDF export of
 * all their forms (Per Pekerjaan).
 */
(function () {
    'use strict';

    const escape = RecordTable.escapeHtml;
    const jobs = JSON.parse(document.getElementById('rekap-jobs').textContent);
    const config = document.getElementById('rekap-config').dataset;

    function today(offsetDays = 0) {
        const now = new Date();
        now.setDate(now.getDate() + offsetDays);
        return [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-');
    }

    function queryString(params) {
        return new URLSearchParams(Object.entries(params).filter(([, value]) => value)).toString();
    }

    async function fetchJson(url) {
        const response = await fetch(url);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        return data;
    }

    function recordLinks(edit, xlsx, pdf) {
        return `<a class="btn btn-sm btn-warning" href="${edit}" title="Edit"><i class="fas fa-edit"></i></a>
            <a class="btn btn-sm btn-light text-success" href="${xlsx}" title="Export to Excel"><i class="fas fa-file-excel"></i></a>
            <a class="btn btn-sm btn-light text-danger" href="${pdf}" title="Export to PDF"><i class="fas fa-file-pdf"></i></a>`;
    }

    /* Rekap Dinas */

    function dutyQuery() {
        return queryString({
            date: document.getElementById('duty-date').value,
            shift: document.getElementById('duty-shift').value,
            group: document.getElementById('duty-group').value,
        });
    }

    // Fixed widths shared by every slot table, so the columns line up from card to card even when a slot
    // only has "Belum ada" rows (the global th rule of base.css centers headers, so each one sets its alignment).
    const SLOT_COLUMNS = `<colgroup><col style="width: 24%;"><col style="width: 22%;"><col style="width: 10%;">
        <col><col style="width: 130px;"></colgroup>`;

    function renderSlot(slot) {
        const rows = slot.jobs.map((job) => {
            if (!job.records.length) {
                return `<tr><td>${escape(job.label)}</td><td colspan="4"><span class="badge text-bg-warning">Belum ada</span></td></tr>`;
            }
            return job.records.map((record) => `<tr>
                <td>${escape(job.label)}</td>
                <td>${escape(record.code)}</td>
                <td class="text-center">${record.group}</td>
                <td>${escape(record.operator_name || '-')}</td>
                <td class="text-nowrap text-end">${recordLinks(record.edit_url, record.xlsx_url, record.pdf_url)}</td>
            </tr>`).join('');
        }).join('');
        const done = slot.jobs.filter((job) => job.records.length).length;
        return `<div class="card mb-3">
            <div class="card-header d-flex flex-wrap justify-content-between gap-2">
                <strong>${escape(slot.shift_code)} &ndash; ${escape(slot.shift)}</strong>
                <span class="text-muted small">Tanggal record ${escape(slot.record_date)} &middot; ${done}/${slot.jobs.length} pekerjaan</span>
            </div>
            <div class="table-responsive">
                <table class="table table-sm align-middle mb-0" style="table-layout: fixed;">
                    ${SLOT_COLUMNS}
                    <thead><tr>
                        <th class="text-start">Pekerjaan</th><th class="text-start">ID</th><th class="text-center">Kelompok</th>
                        <th class="text-start">Petugas</th><th></th>
                    </tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>`;
    }

    async function loadDutySummary(event) {
        if (event) {
            event.preventDefault();
        }
        const result = document.getElementById('duty-result');
        result.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Sedang memuat...';
        try {
            const data = await fetchJson(`${config.dutySummaryUrl}?${dutyQuery()}`);
            result.innerHTML = data.slots.map(renderSlot).join('');
        } catch (error) {
            result.innerHTML = '';
            RecordTable.showError(`Gagal memuat rekap: ${error.message}`);
        }
    }

    function exportDutyPdf() {
        if (!document.getElementById('duty-date').value) {
            RecordTable.showError('Pilih tanggal terlebih dahulu.');
            return;
        }
        // Converting every form takes a moment; the PDF opens in a new tab when it is ready.
        window.open(`${config.dutySummaryPdfUrl}?${dutyQuery()}`, '_blank');
    }

    /* Per Pekerjaan */

    let jobTable = null;
    // Filters of the last "Tampilkan". Tabulator keeps the URL given to setData but not its params, so the table
    // reads them through ajaxParams on every request: changing page or page size keeps the filters.
    let jobFilters = {};

    function renderCounts(tbody, rows, total) {
        tbody.innerHTML = rows.map(([label, count]) =>
            `<tr><td>${escape(label)}</td><td class="text-end">${count}</td></tr>`).join('')
            + `<tr class="table-light fw-bold"><td>Total</td><td class="text-end">${total}</td></tr>`;
    }

    async function loadStats(job, query) {
        try {
            const [byGroup, byOperator] = await Promise.all(
                ['group', 'operator'].map((by) => fetchJson(`${job.stats_url}?${queryString({ by })}&${query}`)));
            renderCounts(document.getElementById('stats-group'),
                byGroup.data.map((row) => [`Kelompok ${row.group}`, row.count]), byGroup.total);
            renderCounts(document.getElementById('stats-operator'),
                byOperator.data.map((row) => [row.operator_name || 'Tidak tercatat', row.count]), byOperator.total);
        } catch (error) {
            RecordTable.showError(`Gagal memuat jumlah pekerjaan: ${error.message}`);
        }
    }

    function selectedJob() {
        return jobs.find((item) => item.key === document.getElementById('job-type').value);
    }

    function jobParams() {
        const dateFrom = document.getElementById('job-date-from');
        const dateTo = document.getElementById('job-date-to');
        if (!dateFrom.value && !dateTo.value) {
            // Without dates the list falls back to the last 2 days, never to every record.
            dateFrom.value = today(-1);
            dateTo.value = today();
        }
        return {
            group: document.getElementById('job-group').value,
            operator: document.getElementById('job-operator').value,
            date_from: dateFrom.value,
            date_to: dateTo.value,
        };
    }

    function exportJobPdf() {
        // Every form of the filtered records, merged; the PDF opens in a new tab when it is ready.
        window.open(`${selectedJob().pdf_export_url}?${queryString(jobParams())}`, '_blank');
    }

    function loadJob(event) {
        if (event) {
            event.preventDefault();
        }
        const job = selectedJob();
        const params = jobParams();
        const query = queryString(params);
        loadStats(job, query);

        jobFilters = Object.fromEntries(Object.entries(params).filter(([, value]) => value));
        if (jobTable) {
            jobTable.setData(job.list_url);
            return;
        }
        jobTable = RecordTable.create({
            element: '#job-table',
            url: job.list_url,
            params: () => jobFilters,
            columns: [
                { title: 'ID', field: 'code', minWidth: 180 },
                { title: 'Tanggal', field: 'date', width: 120 },
                { title: 'Dinas', field: 'shift', width: 110 },
                { title: 'Kelompok', field: 'group', width: 100, hozAlign: 'center' },
                { title: 'Petugas', field: 'operator_name', formatter: (cell) => escape(cell.getValue() || '-') },
                {
                    title: '', headerSort: false, hozAlign: 'right', width: 140,
                    formatter: (cell) => {
                        const id = cell.getRow().getData().id;
                        const current = selectedJob();
                        return recordLinks(RecordTable.recordUrl(current.edit_url, id),
                            RecordTable.recordUrl(current.xlsx_url, id), RecordTable.recordUrl(current.pdf_url, id));
                    },
                },
            ],
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.getElementById('duty-date').value = today();
        // Per Pekerjaan lists the last 2 days (yesterday and today) until the officer picks other dates.
        document.getElementById('job-date-from').value = today(-1);
        document.getElementById('job-date-to').value = today();
        document.getElementById('duty-form').addEventListener('submit', loadDutySummary);
        document.getElementById('duty-pdf').addEventListener('click', exportDutyPdf);
        document.getElementById('job-form').addEventListener('submit', loadJob);
        document.getElementById('job-pdf').addEventListener('click', exportJobPdf);
        loadDutySummary();
        // The job table is built when its tab is first shown, so Tabulator can measure the visible container.
        document.querySelector('[data-bs-target="#tab-job"]').addEventListener('shown.bs.tab', () => {
            if (!jobTable) {
                loadJob();
            }
        }, { once: true });
    });
})();
