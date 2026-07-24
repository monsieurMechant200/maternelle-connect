import requests
from math import radians, sin, cos, sqrt, asin
from db import get_approved_hospitals

def geocode(place_name: str, country: str = "Cameroun"):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": f"{place_name}, {country}", "format": "json", "limit": 1}
    headers = {"User-Agent": "MaternelleConnect/1.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        data = resp.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print(f"Erreur géocodage: {e}")
    return None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * asin(sqrt(a))

def get_nearest_hospitals(lat: float, lon: float, limit: int = 3):
    hospitals = get_approved_hospitals()
    if not hospitals:
        return []
    for h in hospitals:
        h["distance_km"] = round(haversine(lat, lon, h["lat"], h["lon"]), 1)
    hospitals.sort(key=lambda x: x["distance_km"])
    return hospitals[:limit]