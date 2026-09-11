// Kelompok form operations
document.addEventListener('DOMContentLoaded', function() {
    const oprInput = document.getElementById('oprInput');
    const suggestionsBox = document.getElementById('suggestions');
    const oprTableBody = document.getElementById('oprTableBody');
    // Use modal and button IDs from base.html
    const confirmationModalElement = document.getElementById('deleteConfirmationModal');
    const confirmDeleteBtn = document.getElementById('confirmDeleteButton');
    let rowToDelete = null; // Variable to store the row targeted for deletion
    let confirmationModal = null;
    if (confirmationModalElement && window.bootstrap) {
        confirmationModal = new bootstrap.Modal(confirmationModalElement);
    }
    let oprCount = 0;
    let operators = [];

    // Fetch operators from the server once
    async function fetchOperators() {
        try {
            const response = await fetch('/api/v1/operators/');
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            const data = await response.json();
            operators = data.data;
            return operators;
        } catch (error) {
            console.error('There was a problem with the fetch operation:', error);
        }
    }

    // Load operators when the page loads
    window.addEventListener('load', () => {
        fetchOperators().then((operators) => {
            // Check for existing members data passed from Django template
            if (typeof existingMemberIds !== 'undefined' && existingMemberIds.length > 0) {
                // Use existing members data for update form
                existingMemberIds.forEach(memberId => {
                    const operator = operators.find(opr => opr.id == memberId.trim());
                    if (operator) {
                        addOprToTable(operator.name);
                    }
                });
            } else {
                // Fallback: check form field value for any other cases
                const memberIdField = document.getElementById('id_member'); // Using Django's default id naming
                if (memberIdField && memberIdField.value) {
                    const memberIds = memberIdField.value.split(',');
                    memberIds.forEach(memberId => {
                        const operator = operators.find(opr => opr.id == memberId);
                        if (operator) {
                            addOprToTable(operator.name);
                        }
                    });
                }
            }
        });
    });

    // Show suggestions when input is focused, even if empty
    oprInput.addEventListener('focus', () => {
        const query = oprInput.value.toLowerCase();
        suggestionsBox.innerHTML = '';
        let matchedOpr;
        if (!query) {
            matchedOpr = operators; // Show all if input is empty
        } else {
            matchedOpr = operators.filter(operator => operator.name.toLowerCase().includes(query));
        }
        if (matchedOpr.length) {
            matchedOpr.forEach(operator => {
                const item = document.createElement('div');
                item.className = 'suggestion-item';
                item.textContent = operator.name;
                item.addEventListener('click', () => {
                    addOprToTable(operator.name);
                    oprInput.value = '';
                    suggestionsBox.classList.add('d-none');
                });
                suggestionsBox.appendChild(item);
            });
            suggestionsBox.classList.remove('d-none');
        } else {
            suggestionsBox.classList.add('d-none');
        }
    });

    // Hide suggestions when input loses focus
    oprInput.addEventListener('blur', () => {
        setTimeout(() => suggestionsBox.classList.add('d-none'), 200);
    });

    // Add operator to the table
    function addOprToTable(operator) {
        oprCount++;
        const operatorData = operators.find(opr => opr.name === operator);

        // Create a new row
        const row = document.createElement('tr');
        row.setAttribute('draggable', 'true');
        row.innerHTML = `
        <td class="drag-handle">☰</td>
        <td>${oprCount}</td>
        <td>${operatorData.id}</td>
        <td class="nama-column">${operatorData.name}</td>
        <td>
          <button class="btn btn-danger btn-sm delete" data-toggle="tooltip" title="Delete Operator" data-pk="${operatorData.id}"><i class="fas fa-trash"></i></button>
        </td>
      `;

        // Add event listener for the delete button to show the modal
        const deleteButton = row.querySelector('.delete');
        deleteButton.addEventListener('click', (e) => {
            e.preventDefault();
            rowToDelete = row; // Store the row to be deleted
            if (confirmationModal) {
                confirmationModal.show(); // Show the confirmation modal
            } else {
                // fallback: delete directly if modal not found
                rowToDelete.remove();
                updateRowNumbers();
                updateMemberInput();
                rowToDelete = null;
            }
        });

        // Initialize tooltip for the new button (using native Bootstrap)
        try {
            if (window.bootstrap && window.bootstrap.Tooltip) {
                new window.bootstrap.Tooltip(deleteButton);
            } else if (typeof $ !== 'undefined' && $.fn.tooltip) {
                $(deleteButton).tooltip();
            }
        } catch (e) {
            // Silently fail if tooltip initialization fails
        }

        // Append row to table
        oprTableBody.appendChild(row);
        updateMemberInput();
    }

    // Add event listener for the modal's confirm delete button
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', () => {
            if (rowToDelete) {
                rowToDelete.remove(); // Remove the stored row
                updateRowNumbers();
                updateMemberInput();
                rowToDelete = null; // Reset the variable
                if (confirmationModal) {
                    confirmationModal.hide(); // Hide the modal
                }
                // Re-initialize tooltips in case any were removed/re-added implicitly
                $('[data-toggle="tooltip"]').tooltip('dispose'); // Remove old tooltips
                $('[data-toggle="tooltip"]').tooltip(); // Initialize new ones
            }
        });
    } else {
        console.error("Confirm delete button with ID 'confirmDeleteButton' not found in base.html");
    }

    // Update row numbers after deletion
    function updateRowNumbers() {
        const rows = oprTableBody.querySelectorAll('tr');
        oprCount = 0;
        rows.forEach((row) => {
            oprCount++;
            row.children[1].textContent = oprCount;
        });
    }

    // Update member input with IDs in comma-separated format
    function updateMemberInput() {
        const rows = oprTableBody.querySelectorAll('tr');
        const ids = Array.from(rows).map(row => row.children[2].textContent);
        document.getElementById('id_member').value = ids.join(',');
    }

    // Add drag-and-drop functionality
    oprTableBody.addEventListener('dragstart', (event) => {
        if (event.target.tagName === 'TR') {
            event.target.classList.add('dragging');
        }
    });

    oprTableBody.addEventListener('dragend', (event) => {
        if (event.target.tagName === 'TR') {
            event.target.classList.remove('dragging');
        }
    });

    oprTableBody.addEventListener('dragover', (event) => {
        event.preventDefault();
        const draggingRow = oprTableBody.querySelector('.dragging');
        const afterElement = getDragAfterElement(oprTableBody, event.clientY);

        // Remove existing drag-over indicators
        oprTableBody.querySelectorAll('tr').forEach(row => row.classList.remove('drag-over'));

        if (afterElement == null) {
            oprTableBody.appendChild(draggingRow);
        } else {
            oprTableBody.insertBefore(draggingRow, afterElement);
            afterElement.classList.add('drag-over');
        }
    });

    oprTableBody.addEventListener('dragleave', () => {
        oprTableBody.querySelectorAll('tr').forEach(row => row.classList.remove('drag-over'));
    });

    oprTableBody.addEventListener('drop', () => {
        oprTableBody.querySelectorAll('tr').forEach(row => row.classList.remove('drag-over'));
        updateRowNumbers();
        updateMemberInput();
    });

    function getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('tr:not(.dragging)')];

        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }

    // Form validation
    (function () {
        'use strict';
        window.addEventListener('load', function () {
            // Fetch all the forms we want to apply custom Bootstrap validation styles to
            var forms = document.getElementsByClassName('needs-validation');
            // Loop over them and prevent submission
            var validation = Array.prototype.filter.call(forms, function (form) {
                form.addEventListener('submit', function (event) {
                    if (form.checkValidity() === false) {
                        event.preventDefault();
                        event.stopPropagation();
                    }
                    form.classList.add('was-validated');
                }, false);
            });
        }, false);
    })();
});