import json
import random
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone

from .models import Device, TTNUplink, TelemetryPoint



# --------------------------
# Helpers
# --------------------------
import re

def _to_float(v):
    
    if v is None:
        return None

    # Déjà numérique
    if isinstance(v, (int, float)):
        return float(v)

    # String: extraire le 1er nombre valide
    if isinstance(v, str):
        m = re.search(r'[-+]?\d+(\.\d+)?', v)
        if not m:
            return None
        try:
            return float(m.group(0))
        except ValueError:
            return None

    # Autres types
    try:
        return float(v)
    except (TypeError, ValueError):
        return None



def generate_device_eui():
    while True:
        eui = ''.join(random.choice('0123456789ABCDEF') for _ in range(16))
        if not Device.objects.filter(device_eui=eui).exists():
            return eui


def _extract_gps(decoded_payload: dict):
    """
    Accepte plusieurs formats:
      - {"lat": ..., "lng": ...}
      - {"latitude": ..., "longitude": ...}
      - {"gps": {"lat":..., "lng":...}}
    """
    if not isinstance(decoded_payload, dict):
        return None, None

    # direct
    lat = decoded_payload.get("lat")
    lng = decoded_payload.get("lng")

    # alternative keys
    if lat is None:
        lat = decoded_payload.get("latitude")
    if lng is None:
        lng = decoded_payload.get("longitude")

    # nested gps
    gps = decoded_payload.get("gps")
    if (lat is None or lng is None) and isinstance(gps, dict):
        if lat is None:
            lat = gps.get("lat") or gps.get("latitude")
        if lng is None:
            lng = gps.get("lng") or gps.get("lon") or gps.get("longitude")

    return _to_float(lat), _to_float(lng)


# --------------------------
# TTN uplink
# --------------------------
@csrf_exempt
@require_POST
def ttn_uplink(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # ---- Extract identifiers ----
    end_device_ids = payload.get("end_device_ids", {}) or {}
    device_eui = end_device_ids.get("dev_eui")
    device_name = end_device_ids.get("device_id") or "unknown-device"
    application_id = (end_device_ids.get("application_ids", {}) or {}).get("application_id")

    if not device_eui:
        return JsonResponse({"error": "Missing dev_eui in payload"}, status=400)

    device, _ = Device.objects.get_or_create(
        device_eui=device_eui,
        defaults={"name": device_name}
    )
    # si le device existe déjà et qu’il n’a pas de nom correct, tu peux le mettre à jour
    if device.name != device_name and device_name != "unknown-device":
        device.name = device_name
        device.save(update_fields=["name"])

    uplink = payload.get("uplink_message", {}) or {}

    decoded_payload = uplink.get("decoded_payload")
    f_port = uplink.get("f_port")

    # ---- Extract radio metadata (best gateway) ----
    rssi = None
    snr = None
    rx_metadata = uplink.get("rx_metadata", []) or []
    if rx_metadata:
        rssi = rx_metadata[0].get("rssi")
        snr = rx_metadata[0].get("snr")

    # ---- Save uplink to DB ----
    TTNUplink.objects.create(
        device=device,
        application_id=application_id or "",
        raw_payload=payload,
        decoded_payload=decoded_payload,
        rssi=_to_float(rssi),
        snr=_to_float(snr),
        f_port=f_port,
    )

    # ---- Save telemetry point if GPS exists ----
    if isinstance(decoded_payload, dict):
        lat, lng = _extract_gps(decoded_payload)

        if lat is not None and lng is not None:
            TelemetryPoint.objects.create(
                device=device,
                lat=lat,
                lng=lng,
                temp=_to_float(decoded_payload.get("temp")),
                battery=_to_float(decoded_payload.get("battery") or decoded_payload.get("battery_level")),
                rssi=_to_float(rssi),
                snr=_to_float(snr),
                ts=timezone.now()
            )

    return JsonResponse({"status": "ok"})


def join(request):
    return JsonResponse({"status": "join received"})


# --------------------------
# Devices
# --------------------------
@require_GET
def device_list(request):
    devices = Device.objects.all()
    data = [{"device_eui": d.device_eui, "name": d.name, "is_active": d.is_active} for d in devices]
    return JsonResponse({"devices": data})


@csrf_exempt
def ajouter_device(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid HTTP method"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    device_eui = data.get("device_eui") or generate_device_eui()
    name = data.get("name")

    if not name:
        return JsonResponse({"error": "Missing name"}, status=400)

    device, created = Device.objects.get_or_create(
        device_eui=device_eui,
        defaults={"name": name}
    )

    if not created:
        return JsonResponse({"error": "Device already exists"}, status=400)

    return JsonResponse({
        "status": "created",
        "device_eui": device.device_eui,
        "name": device.name,
        "created_at": device.created_at.isoformat()
    })


@csrf_exempt
def modifier_device(request, device_eui):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid HTTP method"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = data.get("name")
    is_active = data.get("is_active")

    try:
        device = Device.objects.get(device_eui=device_eui)
    except Device.DoesNotExist:
        return JsonResponse({"error": "Device not found"}, status=404)

    changed = False
    if name is not None:
        device.name = name
        changed = True
    if is_active is not None:
        device.is_active = bool(is_active)
        changed = True

    if changed:
        device.save()

    return JsonResponse({
        "status": "updated",
        "device_eui": device.device_eui,
        "name": device.name,
        "is_active": device.is_active
    })


@require_GET
def delete_device(request, device_eui):
    try:
        device = Device.objects.get(device_eui=device_eui)
        device.delete()
        return JsonResponse({"status": "deleted"})
    except Device.DoesNotExist:
        return JsonResponse({"error": "Device not found"}, status=404)


# --------------------------
# Uplinks list
# --------------------------
@require_GET
def list_ttn_uplinks(request):
    uplinks = TTNUplink.objects.select_related('device').all().order_by("-received_at")[:500]

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


@require_GET
def supprimer_uplink(request, uplink_id):
    try:
        uplink = TTNUplink.objects.get(id=uplink_id)
        uplink.delete()
        return JsonResponse({"status": "deleted"})
    except TTNUplink.DoesNotExist:
        return JsonResponse({"error": "Uplink not found"}, status=404)


# --------------------------
# Telemetry API for Angular
# --------------------------
@require_GET
def telemetry_latest(request, device_eui):
    try:
        device = Device.objects.get(device_eui=device_eui)
        p = TelemetryPoint.objects.filter(device=device).latest("ts")

        return JsonResponse({
            "device_eui": device.device_eui,
            "ts": int(p.ts.timestamp()),
            "lat": p.lat,
            "lng": p.lng,
            "temp": p.temp,
            "battery": p.battery,
            "rssi": p.rssi,
            "snr": p.snr,
        })
    except (Device.DoesNotExist, TelemetryPoint.DoesNotExist):
        return JsonResponse({"error": "No data"}, status=404)




@csrf_exempt
@require_GET
def telemetry_history(request, device_eui):
    """
    GET /api/v1/telemetry/history/<device_eui>/?limit=300&fromTs=...&toTs=...
    Retour:
      { "device_eui": "...", "count": n, "history": [ {ts,lat,lng,temp,battery,rssi,snr}, ... ] }
    """
    limit = request.GET.get("limit", "300")
    try:
        limit = int(limit)
    except ValueError:
        limit = 300
    limit = max(1, min(limit, 5000))

    # ✅ optionnels
    from_ts = request.GET.get("fromTs")
    to_ts = request.GET.get("toTs")

    try:
        device = Device.objects.get(device_eui=device_eui)
    except Device.DoesNotExist:
        return JsonResponse({"error": "Device not found"}, status=404)

    qs = TelemetryPoint.objects.filter(device=device)

    # ts en DB = DateTimeField (timezone.now())
    # fromTs/toTs = epoch seconds -> convertir en datetime
    if from_ts:
        try:
            from_dt = timezone.datetime.fromtimestamp(int(from_ts), tz=timezone.get_current_timezone())
            qs = qs.filter(ts__gte=from_dt)
        except ValueError:
            pass

    if to_ts:
        try:
            to_dt = timezone.datetime.fromtimestamp(int(to_ts), tz=timezone.get_current_timezone())
            qs = qs.filter(ts__lte=to_dt)
        except ValueError:
            pass

    qs = qs.order_by("-ts")[:limit]
    points = list(qs)
    points.reverse()  # ancien -> récent (polyline)

    return JsonResponse({
        "device_eui": device.device_eui,
        "count": len(points),
        "history": [
            {
                "ts": int(p.ts.timestamp()),
                "lat": p.lat,
                "lng": p.lng,
                "temp": p.temp,
                "battery": p.battery,
                "rssi": p.rssi,
                "snr": p.snr,
            }
            for p in points
        ]
    })



@csrf_exempt
@require_POST
def telemetry_ingest(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    device_eui = str(data.get("device_eui") or "").strip()
    if not device_eui:
        return JsonResponse({"error": "Missing device_eui"}, status=400)

    lat = _to_float(data.get("lat"))
    lng = _to_float(data.get("lng"))
    if lat is None or lng is None:
        return JsonResponse({"error": "Missing lat/lng"}, status=400)

    # ts en secondes (si ms -> conversion)
    ts_raw = data.get("ts")
    if ts_raw is None:
        ts_dt = timezone.now()
    else:
        try:
            ts_int = int(ts_raw)
            if ts_int > 1_000_000_000_000:
                ts_int //= 1000
            ts_dt = timezone.datetime.fromtimestamp(ts_int, tz=timezone.get_current_timezone())
        except Exception:
            ts_dt = timezone.now()

    temp = _to_float(data.get("temp"))
    battery = _to_float(data.get("battery") or data.get("battery_level"))
    rssi = _to_float(data.get("rssi"))
    snr = _to_float(data.get("snr"))

    device, _ = Device.objects.get_or_create(
        device_eui=device_eui,
        defaults={"name": device_eui}
    )

    TelemetryPoint.objects.create(
        device=device,
        ts=ts_dt,
        lat=lat,
        lng=lng,
        temp=temp,
        battery=battery,
        rssi=rssi,
        snr=snr,
    )

    return JsonResponse({"status": "ok"})
