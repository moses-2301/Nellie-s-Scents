document.addEventListener('DOMContentLoaded', () => {
    const charts = {
        ordersChart: null,
        revenueChart: null,
        categoryChart: null,
        productsChart: null,
    };

    const sidebar = document.querySelector('.admin-sidebar');
    const toggleButton = document.querySelector('.sidebar-toggle');

    if (toggleButton) {
        toggleButton.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            document.querySelector('.admin-main').classList.toggle('main-expanded');
        });
    }

    const rangeButtons = document.querySelectorAll('.chart-range-group button');
    const customDateFilter = document.getElementById('custom-date-filter');
    const customStart = document.getElementById('customStart');
    const customEnd = document.getElementById('customEnd');
    const applyCustom = document.getElementById('applyCustomDate');

    let activeRange = '7';

    const fetchWithRange = async (endpoint) => {
        const url = new URL(endpoint, window.location.origin);
        url.searchParams.append('range', activeRange);

        if (activeRange === 'custom' && customStart.value && customEnd.value) {
            url.searchParams.append('start', customStart.value);
            url.searchParams.append('end', customEnd.value);
        }

        const res = await fetch(url);
        return res.json();
    };

    const updateSummary = async () => {
        const summary = await fetchWithRange('/dashboard/api/summary/');
        if (!summary) return;

        document.getElementById('summaryOrdersToday').textContent = summary.orders_today;
        document.getElementById('summaryRevenueToday').textContent = new Intl.NumberFormat('en-NG', {style: 'currency', currency: 'NGN'}).format(summary.revenue_today);
        document.getElementById('summaryRevenueOverall').textContent = new Intl.NumberFormat('en-NG', {style: 'currency', currency: 'NGN'}).format(summary.revenue_overall);
    };

    const updateChart = (chartKey, canvasId, data, options) => {
        const ctx = document.getElementById(canvasId).getContext('2d');
        if (charts[chartKey]) charts[chartKey].destroy();
        charts[chartKey] = new Chart(ctx, data, options);
    };

    const renderAllCharts = async () => {
        await updateSummary();

        const orders = await fetchWithRange('/dashboard/api/orders-per-day/');
        const revenue = await fetchWithRange('/dashboard/api/revenue-per-day/');
        const category = await fetchWithRange('/dashboard/api/category-revenue/');
        const topProducts = await fetchWithRange('/dashboard/api/top-products/');

        updateChart('ordersChart', 'ordersPerDayChart', {
            type: 'line',
            data: { labels: orders.labels, datasets: [{ label: 'Confirmed Orders', data: orders.data, borderColor: '#d73585', backgroundColor: 'rgba(215, 53, 133, 0.2)', tension: 0.35, fill: true } ]},
            options: { responsive: true, scales: { x: {grid: { display: false } }, y: { beginAtZero: true } }, plugins: { tooltip: { callbacks: { label: (context) => `${context.dataset.label}: ${context.formattedValue}` } } } }
        });

        updateChart('revenueChart', 'revenuePerDayChart', {
            type: 'bar',
            data: { labels: revenue.labels, datasets: [{ label: 'Daily Revenue', data: revenue.data, backgroundColor: '#7ed0fb', borderColor: '#0f7bd6', borderWidth: 1 }]},
            options: { responsive: true, scales: { y: { beginAtZero: true }, x: { grid: { display: false } } }, plugins: { tooltip: { callbacks: { label: (context) => `₦${parseFloat(context.formattedValue).toLocaleString()}` } } } }
        });

        updateChart('categoryChart', 'categoryRevenueChart', {
            type: 'pie',
            data: { labels: category.labels, datasets: [{ label: 'Revenue by Category', data: category.data, backgroundColor: ['#fda4af', '#93c5fd', '#a7f3d0', '#fcd34d', '#c4b5fd'] }]},
            options: { responsive: true, plugins: { legend: { position: 'bottom' }, tooltip: { callbacks: { label: (context) => `${context.label}: ₦${parseFloat(context.formattedValue).toLocaleString()}` } } } }
        });

        updateChart('productsChart', 'topProductsChart', {
            type: 'bar',
            data: { labels: topProducts.labels, datasets: [{ label: 'Quantity Sold', data: topProducts.data, backgroundColor: '#93c5fd', borderColor: '#1d4ed8', borderWidth: 1 }]},
            options: { responsive: true, indexAxis: 'y', scales: { x: { beginAtZero: true }, y: { ticks: { autoSkip: false } } }, plugins: { tooltip: { callbacks: { label: (context) => `${context.dataset.label}: ${context.formattedValue}` } } } }
        });
    };

    rangeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            rangeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeRange = btn.dataset.range;
            customDateFilter.classList.toggle('d-none', activeRange !== 'custom');
            if (activeRange !== 'custom') renderAllCharts();
        });
    });

    applyCustom.addEventListener('click', renderAllCharts);

    renderAllCharts();
});