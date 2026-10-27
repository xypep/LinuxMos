"""Weather from MET Norway (no API key) with the city geocoded via OpenStreetMap.

Requests go through curl (services/http.py), the main loop never waits.
The forecast is refreshed every 30 minutes, as MET Norway's terms ask.
"""

import urllib.parse
from datetime import datetime

from gi.repository import GLib

from island.i18n import _, weekday
from island.services import http

FORECAST_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat:.4f}&lon={lon:.4f}"
GEOCODE_URL = "https://nominatim.openstreetmap.org/search?format=json&limit=1&q={q}"
REFRESH_SECONDS = 30 * 60

# MET symbol code prefix -> (symbolic icon, description as German source string)
SYMBOLS = [
    ("clearsky", "weather-clear", "Klar"),
    ("fair", "weather-few-clouds", "Heiter"),
    ("partlycloudy", "weather-few-clouds", "Teils bewölkt"),
    ("cloudy", "weather-overcast", "Bewölkt"),
    ("fog", "weather-fog", "Nebel"),
    ("lightrainshowers", "weather-showers-scattered", "Leichte Schauer"),
    ("rainshowers", "weather-showers", "Schauer"),
    ("heavyrainshowers", "weather-showers", "Starke Schauer"),
    ("lightrain", "weather-showers-scattered", "Leichter Regen"),
    ("heavyrain", "weather-showers", "Starker Regen"),
    ("rain", "weather-showers", "Regen"),
    ("sleet", "weather-snow", "Schneeregen"),
    ("lightsnow", "weather-snow", "Leichter Schnee"),
    ("heavysnow", "weather-snow", "Starker Schnee"),
    ("snow", "weather-snow", "Schnee"),
]


def describe(symbol_code):
    """MET symbol code -> (icon name, description)."""
    code = symbol_code or ""
    night = code.endswith("_night")
    base = code.split("_")[0]
    if "thunder" in base:
        return "weather-storm-symbolic", _("Gewitter")
    # Longest matching prefix wins (e.g. "lightrainshowers" before "rain")
    for prefix, icon, text in sorted(SYMBOLS, key=lambda s: -len(s[0])):
        if base.startswith(prefix):
            if night and icon in ("weather-clear", "weather-few-clouds"):
                icon += "-night"
            return f"{icon}-symbolic", _(text)
    return "weather-overcast-symbolic", "–"


def _failure(status):
    """Error text for a request that brought no usable answer."""
    if status == 0:
        return _("Keine Verbindung")
    return f"HTTP {status}" if status != 200 else _("Antwort nicht lesbar")


class Weather:
    def __init__(self, config, on_change):
        self.config = config
        self._on_change = on_change
        self.current = None   # dict(temp, icon, text, city)
        self.hourly = []      # [dict(time, temp, icon)]
        self.daily = []       # [dict(day, min, max, icon)]
        self.error = None
        self.rain_soon = False
        self._busy = False
        if self.configured:
            self.refresh()
        GLib.timeout_add_seconds(REFRESH_SECONDS, self._on_timer)

    @property
    def configured(self):
        return bool(self.config.get("city"))

    def _on_timer(self):
        if self.configured:
            self.refresh()
        return GLib.SOURCE_CONTINUE

    def set_city(self, city):
        self.config.update(city=city.strip(), latitude=None, longitude=None)
        self.config.save()
        self.refresh()

    def refresh(self):
        if self._busy or not self.configured:
            return
        self._busy = True
        lat, lon = self.config.get("latitude"), self.config.get("longitude")
        if lat is None or lon is None:
            city = self.config["city"]
            http.get_json(GEOCODE_URL.format(q=urllib.parse.quote(city)), lambda st, d: self._on_geocode(city, st, d))
        else:
            self._fetch(lat, lon)

    def _on_geocode(self, city, status, hits):
        if not isinstance(hits, list):
            self._apply(None, _failure(status))
            return
        try:
            lat, lon = float(hits[0]["lat"]), float(hits[0]["lon"])
        except (IndexError, KeyError, TypeError, ValueError):
            self._apply(None, _("Ort „{city}“ nicht gefunden").format(city=city))
            return
        self.config.update(latitude=lat, longitude=lon)
        self.config.save()
        self._fetch(lat, lon)

    def _fetch(self, lat, lon):
        def done(status, data):
            try:
                result = self._parse(data["properties"]["timeseries"])
            except (KeyError, IndexError, TypeError, ValueError):
                result = None   # no answer, an error page or a changed format: all "unavailable"
            self._apply(result, None if result else _failure(status))

        http.get_json(FORECAST_URL.format(lat=lat, lon=lon), done)

    @staticmethod
    def _parse(series):
        def when(entry):
            return datetime.fromisoformat(entry["time"].replace("Z", "+00:00")).astimezone()

        def symbol(entry):
            data = entry["data"]
            for span in ("next_1_hours", "next_6_hours", "next_12_hours"):
                if span in data:
                    return data[span]["summary"]["symbol_code"]
            return ""

        def rain(entry):
            return entry["data"].get("next_1_hours", {}).get("details", {}).get("precipitation_amount", 0.0)

        def temp(entry):
            return entry["data"]["instant"]["details"]["air_temperature"]

        now = series[0]
        icon, text = describe(symbol(now))
        current = {"temp": round(temp(now)), "icon": icon, "text": text}

        hourly = []
        for entry in series[1:25:3]:
            hourly.append({"time": when(entry).strftime("%H"), "temp": round(temp(entry)),
                           "icon": describe(symbol(entry))[0]})

        days = {}
        for entry in series:
            local = when(entry)
            day = days.setdefault(local.date(), {"temps": [], "symbol": None, "dist": 99})
            day["temps"].append(temp(entry))
            dist = abs(local.hour - 13)  # the symbol around midday describes the day best
            if symbol(entry) and dist < day["dist"]:
                day.update(symbol=symbol(entry), dist=dist)
        daily = []
        for date, day in sorted(days.items())[:7]:
            daily.append({"day": weekday(date.weekday()), "min": round(min(day["temps"])),
                          "max": round(max(day["temps"])), "icon": describe(day["symbol"])[0]})

        rain_soon = rain(now) < 0.1 and len(series) > 1 and rain(series[1]) >= 0.2
        return {"current": current, "hourly": hourly, "daily": daily, "rain_soon": rain_soon}

    # ---- results -----------------------------------------------------------
    def _apply(self, result, error):
        self._busy = False
        self.error = error
        rain_started = False
        if result:
            self.current = dict(result["current"], city=self.config.get("city", ""))
            self.hourly, self.daily = result["hourly"], result["daily"]
            rain_started = result["rain_soon"] and not self.rain_soon
            self.rain_soon = result["rain_soon"]
        self._on_change(self, rain_started)
