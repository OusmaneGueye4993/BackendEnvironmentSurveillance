from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from .views import (
    # IoT / TTN
    ttn_uplink,
    join,

    # Devices
    device_list,
    ajouter_device,
    modifier_device,
    delete_device,

    # Uplinks
    list_ttn_uplinks,
    supprimer_uplink,

    # Telemetry API (Angular)
    telemetry_latest,
    telemetry_history,
    telemetry_ingest,
)

urlpatterns = [
    # --- IoT ---
    path('v1/uplink', ttn_uplink, name='iot_uplink'),
    path('v1/join', join, name='iot_join'),

    # --- Devices ---
    path('device', device_list, name='device_list'),
    path('ajouter_device', ajouter_device, name='ajouter_device'),
    path('modifier_device/<str:device_eui>/', modifier_device, name='modifier_device'),
    path('delete_device/<str:device_eui>/', delete_device, name='delete_device'),

    # --- Uplinks ---
    path('list_ttn_uplinks', list_ttn_uplinks, name='list_ttn_uplinks'),
    path('surprimer_uplink/<int:uplink_id>/', supprimer_uplink, name='supprimer_uplink'),

    # --- Telemetry API ---
    path('v1/telemetry/latest/<str:device_eui>/', telemetry_latest),
    path('v1/telemetry/history/<str:device_eui>/', telemetry_history),
    path('v1/telemetry/ingest/', telemetry_ingest),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
