document.addEventListener("DOMContentLoaded", async () => {
    // ================== REVENUE STATS ==================
    try {
        const res = await fetch("/admin/members-statistics");
        const data = await res.json();
        const { stats } = data;

        document.getElementById("dailyRevenueDisplay").textContent = `₱${stats.daily_revenue.toFixed(2)}`;
        document.getElementById("monthlyRevenueDisplay").textContent = `₱${stats.monthly_revenue.toFixed(2)}`;
        document.getElementById("totalRevenueDisplay").textContent = `₱${stats.total_revenue.toFixed(2)}`;
        document.getElementById("revenueTimestamp").textContent = `Last updated: ${new Date().toLocaleString()}`;
    } catch (err) { 
        console.error("Error fetching revenue stats:", err); 
    }

    // ================== MEMBERSHIP LOGS ==================
    try {
        const res = await fetch("/admin/membership-logs");
        const logs = await res.json();
        const logList = document.getElementById("logList");
        logList.innerHTML = "";

        const oneWeekAgo = new Date();
        oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);

        logs.forEach(log => {
            const logDate = new Date(log.action_date);
            if (logDate >= oneWeekAgo) {
                const li = document.createElement("li");
                li.textContent = `[${log.action_date}] ${log.member_name} — ${log.action_type}`;
                logList.appendChild(li);
            }
        });
    } catch (err) { 
        console.error("Error fetching membership logs:", err); 
    }

    // ================== STATISTICS SUMMARY ==================
    const totalEl = document.querySelector(".statistics-summary .summary-card:nth-child(1) p");
    const activeEl = document.querySelector(".statistics-summary .summary-card:nth-child(2) p");
    const mostActiveEl = document.querySelector(".statistics-summary .summary-card:nth-child(3) p");

    // Show placeholders
    [totalEl, activeEl, mostActiveEl].forEach(el => el.textContent = "—");

    let statisticsChart;

    const initStatisticsCharts = (data) => {
        // Update summary cards
        totalEl.textContent = data.summary.total.toLocaleString();
        activeEl.textContent = data.summary.active.toLocaleString();
        mostActiveEl.textContent = data.summary.most_active;

        // Animate cards
        document.querySelectorAll(".statistics-summary .summary-card").forEach((c, i) => {
            c.style.animation = `fadeUp 0.6s ease ${i * 0.1}s forwards`;
        });

        // Membership line chart
        
    };

    // Fetch statistics summary for this page
    try {
        const res = await fetch("/admin/statistics-summary");
        const data = await res.json();
        initStatisticsCharts(data);
    } catch (err) {
        console.error("Error fetching statistics summary:", err);
    }
});
