from django.conf import settings
from django.conf.urls.static import static

from django.contrib import admin
from django.urls import path
from .views import *
urlpatterns = [
    path('admin/', admin.site.urls),
    path('v1/uplink', ttn_uplink, name='iot_uplink'),
    path('v1/join', join, name='iot_join'),
    path('divace', device_list, name='device_list'),
    path('delete_device/<str:device_eui>/', delete_device, name='delete_device'),
    path('ajouter_device', ajouter_device, name='ajouter_device'),
    path('modifier_device/<str:device_eui>/', modifier_device, name='modifier_device'),
    path('list_ttn_uplinks', list_ttn_uplinks, name='list_ttn_uplinks'),
    path('surprimer_uplink/<int:uplink_id>/', supprimer_uplink, name='supprimer_uplink'),
    


]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
