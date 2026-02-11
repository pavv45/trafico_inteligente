from django.apps import AppConfig

class TrafficConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'traffic'

    def ready(self):
        """Iniciar procesos en segundo plano al arrancar"""
        import os
        
        # Evitar doble ejecución por el reloader de Django
        if os.environ.get('RUN_MAIN') == 'true':
            from . import controller
            print("\n🚀 INICIANDO CONTROLADOR AUTOMÁTICO...")
            controller.start_auto_cycle()