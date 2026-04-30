const analyticsBase = '/dashboard/api';

const chartConfig = (ctx, label, color) => new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label,
            data: [],
            fill: true,
            borderColor: color,
            backgroundColor: color.replace('1)', '0.18)') || 'rgba(236,72,153,0.18)',
            tension: 0.35,
            pointRadius: 4,
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { display: false },
        },
        scales: {
            x: { display: true, grid: { display: false } },
            y: { display: true, grid: { color: 'rgba(148,163,184,0.16)' } }
        }
    }
});

const renderBarChart = (ctx, label, color) => new Chart(ctx, {
    type: 'bar',
    data: { labels: [], datasets: [{ label, data: [], backgroundColor: color, borderRadius: 12, maxBarThickness: 32 }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } }
});

const updateChart = async (endpoint, chart) => {
    const response = await fetch(`${analyticsBase}/${endpoint}`);
    const data = await response.json();
    chart.data.labels = data.labels;
    chart.data.datasets[0].data = data.data;
    chart.update();
};

const initAnalytics = () => {
    const ordersChartCtx = document.getElementById('ordersChart');
    const revenueChartCtx = document.getElementById('revenueChart');
    const topProductsCtx = document.getElementById('topProductsChart');

    if (!ordersChartCtx || !revenueChartCtx || !topProductsCtx) {
        return;
    }

    const ordersChart = chartConfig(ordersChartCtx, 'Orders', 'rgba(236, 72, 153, 1)');
    const revenueChart = chartConfig(revenueChartCtx, 'Revenue', 'rgba(37, 99, 235, 1)');
    const topProductsChart = renderBarChart(topProductsCtx, 'Top Selling', 'rgba(232, 121, 249, 0.8)');

    updateChart('orders-per-day/', ordersChart);
    updateChart('revenue-per-day/', revenueChart);
    updateChart('top-products/', topProductsChart);

    const socket = io('http://localhost:3001');
    socket.on('connect', () => console.log('Connected to analytics socket'));
    socket.on('analyticsUpdate', () => {
        updateChart('orders-per-day/', ordersChart);
        updateChart('revenue-per-day/', revenueChart);
        updateChart('top-products/', topProductsChart);
    });
};

window.addEventListener('DOMContentLoaded', initAnalytics);
