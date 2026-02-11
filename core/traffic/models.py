from django.db import models
from django.utils import timezone


class TrafficCycle(models.Model):
    """Registro de cada ciclo de semáforos ejecutado"""
    timestamp = models.DateTimeField(default=timezone.now)
    phase = models.CharField(max_length=50)  # AVENIDA_IDA, AVENIDA_VUELTA, etc.
    
    # Conteos de vehículos en el momento del ciclo
    zone_a_count = models.IntegerField(default=0)
    zone_b_count = models.IntegerField(default=0)
    zone_c_count = models.IntegerField(default=0)
    zone_d_count = models.IntegerField(default=0)
    zone_e_count = models.IntegerField(default=0)
    zone_f_count = models.IntegerField(default=0)
    
    # Tiempos calculados (en segundos)
    green_time = models.IntegerField(default=0)
    total_vehicles = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.phase} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class TrafficStats(models.Model):
    """Estadísticas agregadas por día"""
    date = models.DateField(unique=True)
    
    total_cycles = models.IntegerField(default=0)
    total_vehicles = models.IntegerField(default=0)
    avg_green_time = models.FloatField(default=0.0)
    
    # Por fase
    avenida_ida_cycles = models.IntegerField(default=0)
    avenida_vuelta_cycles = models.IntegerField(default=0)
    intersection_a_cycles = models.IntegerField(default=0)
    intersection_d_cycles = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"Stats {self.date}"