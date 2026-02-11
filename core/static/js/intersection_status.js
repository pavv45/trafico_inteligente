setInterval(() => {
    fetch('/traffic_status/')
        .then(res => res.json())
        .then(data => {
            const circle = document.getElementById('status-circle');

            circle.classList.remove('green', 'yellow', 'red');
            circle.classList.add(data.status);

            document.getElementById('vehicle-count').innerText =
                data.vehicles;
        });
}, 1000);