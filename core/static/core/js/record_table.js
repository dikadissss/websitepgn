/*
 * Record tables of the list pages. Pagination, sorting and the search box are handled by the
 * /api/v1/<job>/records/ endpoints, so the browser only ever holds one page of records.
 *
 * RecordTable.create({url, params, columns, urls: {edit, delete}, csrfToken, pageSize}) binds the page's
 * #globalSearch/#clearSearch box and the delete confirmation modal. Exports are on the Rekap page.
 * URL templates use 0 as the record id placeholder, e.g. "/qc/update/0/". params (extra query parameters) may be a
 * function, called for every request, so filters that change later are kept when paging.
 */
(function () {
    'use strict';

    function escapeHtml(text) {
        const element = document.createElement('div');
        element.textContent = text;
        return element.innerHTML;
    }

    function recordUrl(template, id) {
        return template.replace('/0/', `/${id}/`);
    }

    function showMessage(modalId, contentId, message) {
        const content = document.getElementById(contentId);
        if (!content) {
            alert(message);
            return;
        }
        content.textContent = message;
        bootstrap.Modal.getOrCreateInstance(document.getElementById(modalId)).show();
    }

    const showError = (message) => showMessage('errorModal', 'errorModalContent', message);
    const showSuccess = (message) => showMessage('successModal', 'successModalContent', message);

    function bindSearch(table, input, clearButton) {
        let timer;
        const apply = () => {
            const value = input.value.trim();
            if (value) {
                table.setFilter('search', 'like', value);
            } else {
                table.clearFilter();
            }
        };
        input.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(apply, 300);
        });
        input.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                clearTimeout(timer);
                apply();
            } else if (event.key === 'Escape') {
                input.value = '';
                apply();
            }
        });
        if (clearButton) {
            clearButton.addEventListener('click', () => {
                input.value = '';
                apply();
            });
        }
        document.addEventListener('keydown', (event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === 'f') {
                event.preventDefault();
                input.focus();
                input.select();
            }
        });
    }

    function bindDeleteConfirmation(csrfToken) {
        let deleteUrl = null;
        document.addEventListener('click', (event) => {
            const button = event.target.closest('.action-delete');
            if (button) {
                deleteUrl = button.dataset.deleteUrl;
            }
        });
        const confirmButton = document.getElementById('confirmDeleteButton');
        if (!confirmButton) {
            return;
        }
        confirmButton.addEventListener('click', () => {
            if (!deleteUrl) {
                return;
            }
            const form = document.createElement('form');
            form.method = 'post';
            form.action = deleteUrl;
            form.hidden = true;
            const token = document.createElement('input');
            token.type = 'hidden';
            token.name = 'csrfmiddlewaretoken';
            token.value = csrfToken;
            form.appendChild(token);
            document.body.appendChild(form);
            form.submit();
        });
    }

    function create(options) {
        const urls = options.urls || {};
        const table = new Tabulator(options.element || '#tabulator-table', {
            ajaxURL: options.url,
            ajaxParams: options.params || {},
            layout: options.layout || 'fitColumns',
            height: options.height || '100%',
            pagination: true,
            paginationMode: 'remote',
            sortMode: 'remote',
            filterMode: 'remote',
            paginationSize: options.pageSize || 25,
            paginationSizeSelector: options.pageSizes || [10, 25, 50, 100],
            paginationCounter: 'rows',
            movableColumns: true,
            placeholder: 'Tidak ada data',
            dataLoaderLoading: '<span class="spinner-border spinner-border-sm me-2"></span>Sedang memuat data...',
            dataLoaderError: 'Gagal memuat data. Silakan coba lagi.',
            columns: options.columns,
        });

        const searchInput = document.getElementById('globalSearch');
        if (searchInput) {
            bindSearch(table, searchInput, document.getElementById('clearSearch'));
        }
        if (urls.delete) {
            bindDeleteConfirmation(options.csrfToken);
        }
        return table;
    }

    /* Edit and delete buttons of a row, from the #action-buttons-template of base.html. */
    function actionsColumn(urls) {
        return {
            title: 'Actions',
            headerHozAlign: 'center',
            headerSort: false,
            formatter: (cell) => {
                const id = cell.getRow().getData().id;
                const template = document.getElementById('action-buttons-template');
                const container = template.content.cloneNode(true).querySelector('.d-flex');
                container.querySelector('.action-edit').href = recordUrl(urls.edit, id);
                container.querySelector('.action-delete').dataset.deleteUrl = recordUrl(urls.delete, id);
                container.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((element) => new bootstrap.Tooltip(element));
                return container;
            },
        };
    }

    window.RecordTable = { create, actionsColumn, recordUrl, showError, showSuccess, escapeHtml };
})();
