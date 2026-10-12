from core import memory

TOOL = {
    "name": "weather_report",
    "description": "Live weather for a city. If no city is given, uses the remembered city or the user's IP location.",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
}


def handler(params, ctx):
    import requests
    city = (params.get("city") or "").strip()
    if not city:
        hit = memory.search("city location home")
        city = hit[0][1]["value"] if hit else ""
    try:
        d = requests.get(f"https://wttr.in/{city}?format=j1", timeout=8).json()
        c, t = d["current_condition"][0], d["weather"][0]
        where = d.get("nearest_area", [{}])[0].get("areaName", [{"value": city}])[0]["value"]
        return (f"{where}: {c['weatherDesc'][0]['value']}, {c['temp_C']}°C (feels {c['FeelsLikeC']}°C), "
                f"humidity {c['humidity']}%, wind {c['windspeedKmph']} km/h. "
                f"Today {t['mintempC']}–{t['maxtempC']}°C.")
    except Exception as e:
        return f"Could not fetch weather: {e}"
