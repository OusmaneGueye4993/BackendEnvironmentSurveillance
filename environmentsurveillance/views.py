from django.http import JsonResponse

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Device, TTNUplink
from django.views.decorators.http import require_POST

from django.http import JsonResponse
@csrf_exempt
@require_POST
def ttn_uplink(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    

    # ---- Extract identifiers ----
    end_device_ids = payload.get("end_device_ids", {})
    device_eui = end_device_ids.get("dev_eui")
    device_name = end_device_ids.get("device_id")
    device = Device.objects.get_or_create(device_eui=device_eui, name=device_name)[0]
    application_id = end_device_ids.get("application_ids", {}).get("application_id")

    uplink = payload.get("uplink_message", {})

    decoded_payload = uplink.get("decoded_payload")
    f_port = uplink.get("f_port")

    # ---- Extract radio metadata (best gateway) ----
    rssi = None
    snr = None
    rx_metadata = uplink.get("rx_metadata", [])
    if rx_metadata:
        rssi = rx_metadata[0].get("rssi")
        snr = rx_metadata[0].get("snr")

    # ---- Save to DB ----
    TTNUplink.objects.create(
        device=device,
        application_id=application_id,
        raw_payload=payload,
        decoded_payload=decoded_payload,
        rssi=rssi,
        snr=snr,
        f_port=f_port,
    )

    return JsonResponse({"status": "ok"})

def join(request):
    print("Join received")
    print(request.method)
    print(request.body)
    return JsonResponse({"status": "join received"})


def device_list(request):
    devices = Device.objects.all()
    data = [{"device_eui": d.device_eui, "name": d.name, "is_active": d.is_active} for d in devices]
    return JsonResponse({"devices": data})

def delete_device(request, device_eui):
    try:
        device = Device.objects.get(device_eui=device_eui)
        device.delete()
        return JsonResponse({"status": "deleted"})
    except Device.DoesNotExist:
        return JsonResponse({"error": "Device not found"}, status=404)
    

import json
import random
from django.http import JsonResponse
from .models import Device

def generate_device_eui():
    while True:
        eui = ''.join(random.choice('0123456789ABCDEF') for _ in range(16))
        if not Device.objects.filter(device_eui=eui).exists():
            return eui

def ajouter_device(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            
            # Récupère le device_eui ou génère un aléatoire si non fourni
            device_eui = data.get("device_eui") or generate_device_eui()
            name = data.get("name")
            
            if not name:
                return JsonResponse({"error": "Missing name"}, status=400)
            
            # Crée le device ou récupère s’il existe déjà
            device, created = Device.objects.get_or_create(
                device_eui=device_eui,
                defaults={"name": name}
            )
            
            if not created:
                return JsonResponse({"error": "Device already exists"}, status=400)
            
            # Retour JSON incluant l'heure du système
            return JsonResponse({
                "status": "created",
                "device_eui": device.device_eui,
                "name": device.name,
                "created_at": device.created_at.isoformat()
            })
        
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    else:
        return JsonResponse({"error": "Invalid HTTP method"}, status=405)


def modifier_device(request, device_eui):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            name = data.get("name")
            is_active = data.get("is_active")
            
            try:
                device = Device.objects.get(device_eui=device_eui)
            except Device.DoesNotExist:
                return JsonResponse({"error": "Device not found"}, status=404)
            
            if name is not None:
                device.name = name
            if is_active is not None:
                device.is_active = is_active
            
            device.save()
            
            return JsonResponse({
                "status": "updated",
                "device_eui": device.device_eui,
                "name": device.name,
                "is_active": device.is_active
            })
        
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    else:
        return JsonResponse({"error": "Invalid HTTP method"}, status=405)
    



def list_ttn_uplinks(request):
    uplinks = TTNUplink.objects.select_related('device').all()
    
    data = []
    
    for uplink in uplinks:
        data.append({
            "device_eui": uplink.device.device_eui if uplink.device else None,
            "device_name": uplink.device.name if uplink.device else None,
            "application_id": uplink.application_id,
            "decoded_payload": uplink.decoded_payload,
            "rssi": uplink.rssi,
            "snr": uplink.snr,
            "f_port": uplink.f_port,
            "received_at": uplink.received_at.isoformat() if uplink.received_at else None,
        })
    
    return JsonResponse({"ttn_uplinks": data})
def supprimer_uplink(request, uplink_id):

    try:
        uplink = TTNUplink.objects.get(id=uplink_id)
        uplink.delete()
        return JsonResponse({"status": "deleted"})
    except TTNUplink.DoesNotExist:
        return JsonResponse({"error": "Uplink not found"}, status=404)
    



