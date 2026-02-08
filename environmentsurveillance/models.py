from django.db import models
from django.utils import timezone


class Device(models.Model):
    """
    Représente le matériel physique (Drone, LoRa32U4).
    """
    device_eui = models.CharField(max_length=16, unique=True, verbose_name="Identifiant LoRa (EUI)")
    name = models.CharField(max_length=100, verbose_name="Nom de l'appareil")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.device_eui})"

    class Meta:
        verbose_name = "Appareil"
        verbose_name_plural = "Appareils"


class TTNUplink(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='ttn_uplinks')
    application_id = models.CharField(max_length=128)

    # Full webhook payload
    raw_payload = models.JSONField()

    # Only the useful extracted data
    decoded_payload = models.JSONField(null=True, blank=True)

    # Metadata (optional but useful)
    rssi = models.FloatField(null=True, blank=True)
    snr = models.FloatField(null=True, blank=True)
    f_port = models.IntegerField(null=True, blank=True)

    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device.device_eui} @ {self.received_at}"


class TelemetryPoint(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="telemetry")
    ts = models.DateTimeField(default=timezone.now)

    lat = models.FloatField()
    lng = models.FloatField()

    temp = models.FloatField(null=True, blank=True)
    battery = models.FloatField(null=True, blank=True)
    rssi = models.FloatField(null=True, blank=True)
    snr = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ts"]

    def __str__(self):
        return f"{self.device.device_eui} @ {self.ts}"
