document.addEventListener("DOMContentLoaded", () => {
    const totalEl = document.querySelector(".summary-card:nth-child(1) p");
    const activeEl = document.querySelector(".summary-card:nth-child(2) p");
    const mostActiveEl = document.querySelector(".summary-card:nth-child(3) p");

    // Show loading placeholders
    [totalEl, activeEl, mostActiveEl].forEach(el => (el.textContent = "—"));

    // Cache charts to prevent re-rendering on reload
    let membershipChart, renewalChart, expirationChart;

    const initCharts = (data) => {
        // Summary Cards
        totalEl.textContent = data.summary.total.toLocaleString();
        activeEl.textContent = data.summary.active.toLocaleString();
        mostActiveEl.textContent = data.summary.most_active;
        document.querySelectorAll(".summary-card").forEach((c, i) => {
            c.style.animation = `fadeUp 0.6s ease ${i * 0.1}s forwards`;
        });

        // Helper: Gradient creator
        const makeGradient = (ctx, colorTop, colorBottom) => {
            const g = ctx.createLinearGradient(0, 0, 0, 300);
            g.addColorStop(0, colorTop);
            g.addColorStop(1, colorBottom);
            return g;
        };

        // Membership Line Chart
        const overviewCtx = document.getElementById("membershipChart")?.getContext("2d");
        if (overviewCtx) {
            membershipChart?.destroy(); // clear old instance
            membershipChart = new Chart(overviewCtx, {
                type: "line",
                data: {
                    labels: data.overview_chart.labels,
                    datasets: [
                        {
                            label: "Students",
                            data: data.overview_chart.students,
                            borderColor: "#00c8ff",
                            backgroundColor: makeGradient(overviewCtx, "rgba(0,200,255,0.4)", "rgba(0,200,255,0.05)"),
                            fill: true, tension: 0.35, borderWidth: 2
                        },
                        {
                            label: "Faculty",
                            data: data.overview_chart.faculty,
                            borderColor: "#ffd700",
                            backgroundColor: makeGradient(overviewCtx, "rgba(255,215,0,0.4)", "rgba(255,215,0,0.05)"),
                            fill: true, tension: 0.35, borderWidth: 2
                        },
                        {
                            label: "Outsiders",
                            data: data.overview_chart.outsiders,
                            borderColor: "#ff5078",
                            backgroundColor: makeGradient(overviewCtx, "rgba(255,80,120,0.4)", "rgba(255,80,120,0.05)"),
                            fill: true, tension: 0.35, borderWidth: 2
                        }
                    ]
                },
                options: chartOptions()
            });
        }

        // Member Status Overview
        const renewCtx = document.getElementById("renewalChart")?.getContext("2d");
        if (renewCtx) {
            renewalChart?.destroy();
            renewalChart = new Chart(renewCtx, {
                type: "bar",
                data: {
                    labels: data.status_overview.labels,
                    datasets: [{
                        label: "Members by Status",
                        data: data.status_overview.values,
                        backgroundColor: makeGradient(renewCtx, "rgba(0,255,163,0.8)", "rgba(0,255,234,0.2)"),
                        borderColor: "rgba(0,255,163,0.8)",
                        borderWidth: 2,
                        borderRadius: 8
                    }]
                },
                options: barOptions()
            });
        }

        // Active Members
        const expCtx = document.getElementById("expirationChart")?.getContext("2d");
        if (expCtx) {
            expirationChart?.destroy();
            expirationChart = new Chart(expCtx, {
                type: "doughnut",
                data: {
                    labels: data.status_chart.labels,
                    datasets: [{
                        data: data.status_chart.values,
                        backgroundColor: [
                            "rgba(0,200,255,0.7)",
                            "rgba(255,215,0,0.7)",
                            "rgba(255,80,120,0.7)"
                        ],
                        borderColor: "#00ffe0",
                        borderWidth: 1
                    }]
                },
                options: doughnutOptions()
            });
        }
    };

    // 🎨 Common Chart Options
    const chartOptions = () => ({
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 700 },
        plugins: {
            legend: { labels: { color: "#00ffe0" } },
            tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y}` } }
        },
        scales: {
            x: { ticks: { color: "#00ffe0" }, grid: { color: "rgba(0,255,234,0.05)" } },
            y: { ticks: { color: "#00ffe0" }, grid: { color: "rgba(0,255,234,0.05)" }, beginAtZero: true }
        }
    });

    const barOptions = () => ({
        ...chartOptions(),
        plugins: { legend: { display: false } }
    });

    const doughnutOptions = () => ({
        responsive: true,
        cutout: "70%",
        plugins: {
            legend: { position: "bottom", labels: { color: "#00ffe0" } }
        }
    });

    // Fetch data once, then render all charts
    fetch("/admin/dashboard-summary")
        .then(res => res.json())
        .then(data => initCharts(data))
        .catch(err => console.error("Dashboard load failed:", err));
});
