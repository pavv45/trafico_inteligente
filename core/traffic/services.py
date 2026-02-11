from django.utils.timezone import now
from .models import TrafficRecord
from . import state


def save_traffic_snapshot(intersection_id=1):
    TrafficRecord.objects.create(
        intersection_id=intersection_id,
        vehicle_count=state.vehicle_count,
        timestamp=now()
    )