from django.contrib import admin
from .models import TrafficCycle, TrafficStats


@admin.register(TrafficCycle)
class TrafficCycleAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'phase', 'total_vehicles', 'green_time']
    list_filter = ['phase', 'timestamp']
    search_fields = ['phase']
    ordering = ['-timestamp']


@admin.register(TrafficStats)
class TrafficStatsAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_cycles', 'total_vehicles', 'avg_green_time']
    ordering = ['-date']