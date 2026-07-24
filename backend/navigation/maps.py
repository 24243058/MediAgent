"""
MediAgent — Navigation Tool

Finds nearby hospitals when the Safety Agent detects an emergency, or
when the patient explicitly asks for the nearest hospital.

Three providers, selected via settings.MAPS_PROVIDER:
  - "mock" (default): static placeholder data, no setup required,
    clearly flagged with "is_mock": True.
  - "osm": OpenStreetMap's Overpass API — real hospital data, entirely
    free, no API key or billing needed. Good default for a student
    project. Coverage/data quality varies by region since it's
    crowdsourced.
  - "google": Google Maps Places API (Nearby Search) — best data
    quality and includes live "open now" status, but requires
    GOOGLE_MAPS_API_KEY and a billing-enabled project.

Both real providers compute distance via the haversine formula (a
straight-line "as the crow flies" distance, not driving distance) and
a rough ETA from that; neither Places Nearby Search nor Overpass
returns travel time directly. Any failure in a real provider — bad
key, network error, zero results, unreachable endpoint — degrades to
mock data rather than crashing the workflow; a maps outage shouldn't
break emergency handling.
"""

import math
from typing import Any, Dict, List

import requests

from backend.config import settings

PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
AVERAGE_CITY_SPEED_KMPH = 30  # rough estimate for the ETA fallback

# Placeholder names only — not real institutions, not tied to any
# actual coordinates. Distances/ETAs are illustrative demo values.
MOCK_HOSPITALS: List[Dict[str, Any]] = [
    {
        "name": "Kovilpatti General Hospital",
        "distance_km": 2.3,
        "eta_minutes": 7,
        "emergency_available": True,
        "open_now": True,
        "is_mock": True,
    },
    {
        "name": "Sri Ranga Multispeciality Hospital",
        "distance_km": 4.1,
        "eta_minutes": 12,
        "emergency_available": True,
        "open_now": True,
        "is_mock": True,
    },
    {
        "name": "St. Antony's Community Hospital",
        "distance_km": 5.8,
        "eta_minutes": 16,
        "emergency_available": False,
        "open_now": True,
        "is_mock": True,
    },
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lng points, in kilometers."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _eta_minutes(distance_km: float) -> int:
    return max(round(distance_km / AVERAGE_CITY_SPEED_KMPH * 60), 1)


# ---------------------------------------------------------------- Google ----

def _fetch_google_hospitals(latitude: float, longitude: float, radius_m: int = 5000) -> List[Dict[str, Any]]:
    params = {
        "location": f"{latitude},{longitude}",
        "radius": radius_m,
        "type": "hospital",
        "keyword": "hospital",
        "key": settings.GOOGLE_MAPS_API_KEY,
    }
    response = requests.get(PLACES_NEARBY_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(f"Google Maps API error: {status} — {data.get('error_message', '')}")

    hospitals = []
    for place in data.get("results", [])[:5]:
        loc = place.get("geometry", {}).get("location", {})
        if "lat" not in loc or "lng" not in loc:
            continue
        distance_km = round(_haversine_km(latitude, longitude, loc["lat"], loc["lng"]), 1)
        hospitals.append({
            "name": place.get("name", "Unknown Hospital"),
            "distance_km": distance_km,
            "eta_minutes": _eta_minutes(distance_km),
            # Places API doesn't expose real-time ER availability — treated as an approximation
            "emergency_available": True,
            "open_now": place.get("opening_hours", {}).get("open_now", True),
            "is_mock": False,
            "place_id": place.get("place_id"),
        })

    hospitals.sort(key=lambda h: h["distance_km"])
    return hospitals


# -------------------------------------------------------------------- OSM ----

# Overpass's usage policy requires a descriptive User-Agent identifying the
# calling app; the public instance returns 406/429 for generic/default
# request headers as an anti-abuse measure. Fallback mirrors are tried in
# order since the primary instance periodically rate-limits or goes down.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
OVERPASS_HEADERS = {"User-Agent": "MediAgent-HospitalCoordinator/1.0 (student project; contact: sweetyfrost22@gmail.com)"}


def _fetch_osm_hospitals(latitude: float, longitude: float, radius_m: int = 5000) -> List[Dict[str, Any]]:
    """Query OpenStreetMap's Overpass API for amenity=hospital nodes/ways near a point. Free, no API key."""
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="hospital"](around:{radius_m},{latitude},{longitude});
      way["amenity"="hospital"](around:{radius_m},{latitude},{longitude});
    );
    out center tags;
    """

    last_error: Exception | None = None
    data = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = requests.post(endpoint, data={"data": query}, headers=OVERPASS_HEADERS, timeout=25)
            response.raise_for_status()
            data = response.json()
            break
        except Exception as e:
            last_error = e
            continue

    if data is None:
        raise RuntimeError(f"All Overpass endpoints failed. Last error: {last_error}")

    hospitals = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue  # skip unnamed hospital nodes, common in OSM data

        if el.get("type") == "node":
            lat, lon = el.get("lat"), el.get("lon")
        else:
            center = el.get("center") or {}
            lat, lon = center.get("lat"), center.get("lon")
        if lat is None or lon is None:
            continue

        distance_km = round(_haversine_km(latitude, longitude, lat, lon), 1)
        emergency_tag = tags.get("emergency", "").lower()
        hospitals.append({
            "name": name,
            "distance_km": distance_km,
            "eta_minutes": _eta_minutes(distance_km),
            # OSM's "emergency" tag is inconsistently set — default True unless explicitly "no"
            "emergency_available": emergency_tag != "no",
            # OSM's opening_hours is a free-text string (e.g. "24/7", "Mo-Fr 08:00-18:00"),
            # not reliably parseable to a live boolean here — treated as an approximation
            "open_now": True,
            "is_mock": False,
            "osm_id": el.get("id"),
        })

    hospitals.sort(key=lambda h: h["distance_km"])

    # De-duplicate by name — OSM sometimes has both a node and a way for the same hospital
    seen = set()
    deduped = []
    for h in hospitals:
        if h["name"] not in seen:
            seen.add(h["name"])
            deduped.append(h)
    return deduped[:5]


# ------------------------------------------------------------------- Entry ----

def find_nearby_hospitals(latitude: float | None = None, longitude: float | None = None) -> List[Dict[str, Any]]:
    """
    Return a list of nearby hospitals with distance, ETA, emergency
    availability, and open status — used for both the Emergency Card
    and general "nearest hospital" queries. Provider is chosen by
    settings.MAPS_PROVIDER; any failure degrades to mock data.
    """
    provider = settings.MAPS_PROVIDER
    lat = latitude if latitude is not None else settings.DEFAULT_LATITUDE
    lng = longitude if longitude is not None else settings.DEFAULT_LONGITUDE

    if provider == "google" and settings.GOOGLE_MAPS_API_KEY:
        try:
            results = _fetch_google_hospitals(lat, lng)
            if results:
                return results
        except Exception:
            pass
        return MOCK_HOSPITALS

    if provider == "osm":
        try:
            results = _fetch_osm_hospitals(lat, lng)
            if results:
                return results
        except Exception:
            pass
        return MOCK_HOSPITALS

    return MOCK_HOSPITALS