const ctx = document.getElementById('trafficChart');

new Chart(ctx, {
    type: 'line',
    data: {
        labels: [
            '00h','02h','04h','06h','08h','10h',
            '12h','14h','16h','18h','20h','22h'
        ],
        datasets: [{
            label: 'Vehículos detectados',
            data: [120, 180, 300, 600, 900, 1100, 950, 870, 1020, 1400, 1300, 700],
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37,99,235,0.1)',
            tension: 0.4,
            fill: true,
            pointRadius: 4
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: {
                display: false
            }
        },
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});