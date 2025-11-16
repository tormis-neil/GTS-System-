document.addEventListener("DOMContentLoaded", () => {
    const filterID = document.getElementById("filterID");
    const filterType = document.getElementById("filterType");
    const filterPlan = document.getElementById("filterPlan");
    const filterStatus = document.getElementById("filterStatus");
    const tableRows = document.querySelectorAll(".registered-member-table tbody tr");

    const rowsPerPage = 10; // Adjust as needed
    let currentPage = 1;
    let filteredRows = Array.from(tableRows);

    function applyFilters() {
        const idValue = filterID.value.toLowerCase();
        const typeValue = filterType.value;
        const planValue = filterPlan.value;
        const statusValue = filterStatus.value;

        filteredRows = Array.from(tableRows).filter(row => {
            const id = row.cells[0].textContent.toLowerCase();
            const type = row.cells[2].textContent;
            const plan = row.cells[3].textContent;
            const status = row.cells[4].textContent;

            const matchID = id.includes(idValue);
            const matchType = !typeValue || type === typeValue;
            const matchPlan = !planValue || plan === planValue;
            const matchStatus = !statusValue || status === statusValue;

            return matchID && matchType && matchPlan && matchStatus;
        });

        currentPage = 1; // reset to first page when filtering
        updatePagination();
    }

    // Pagination logic
    function updatePagination() {
        const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
        const tableBody = document.getElementById("memberTableBody");

        // Add fade-out animation
        tableBody.classList.add("fade-out");

        // Wait for fade-out before updating rows
        setTimeout(() => {
            tableRows.forEach(row => (row.style.display = "none"));

            const start = (currentPage - 1) * rowsPerPage;
            const end = start + rowsPerPage;
            filteredRows.slice(start, end).forEach(row => (row.style.display = ""));

            renderPageNumbers(totalPages);

            // Switch to fade-in
            tableBody.classList.remove("fade-out");
            tableBody.classList.add("fade-in");

            // Remove fade-in after animation completes
            setTimeout(() => {
                tableBody.classList.remove("fade-in");
            }, 300);
        }, 200);
    }

    function renderPageNumbers(totalPages) {
        const pageNumbersDiv = document.getElementById("pageNumbers");
        pageNumbersDiv.innerHTML = "";

        for (let i = 1; i <= totalPages; i++) {
            const btn = document.createElement("button");
            btn.textContent = i;
            btn.classList.add("page-number");
            if (i === currentPage) btn.classList.add("active");
            btn.addEventListener("click", () => {
                currentPage = i;
                updatePagination();
            });
            pageNumbersDiv.appendChild(btn);
        }

        document.getElementById("prevPage").disabled = currentPage === 1;
        document.getElementById("nextPage").disabled = currentPage === totalPages || totalPages === 0;
    }

    // Button listeners
    document.getElementById("prevPage").addEventListener("click", () => {
        if (currentPage > 1) {
            currentPage--;
            updatePagination();
        }
    });

    document.getElementById("nextPage").addEventListener("click", () => {
        const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
        if (currentPage < totalPages) {
            currentPage++;
            updatePagination();
        }
    });

    // Initial load
    [filterID, filterType, filterPlan, filterStatus].forEach(input => {
        input.addEventListener("input", applyFilters); 
        input.addEventListener("change", applyFilters);
    });

    applyFilters(); // initialize first render
});
