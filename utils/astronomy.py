"""
Astronomical Engine for DaylightLeft
High-precision offline computation of solar coordinates, sunset countdowns,
golden hour, blue hour, and daylight phases using the astral library.
"""

from datetime import datetime, date, time, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
import math

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

try:
    import tzlocal
    LOCAL_TZ_NAME = tzlocal.get_localzone_name()
except Exception:
    LOCAL_TZ_NAME = "UTC"

from astral import LocationInfo, SunDirection
from astral.sun import sun, golden_hour, blue_hour, elevation

# Curated presets for judges and quick testing
PRESET_LOCATIONS: Dict[str, Dict[str, Any]] = {
    "current": {
        "name": "Local Device Location",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "timezone": LOCAL_TZ_NAME,
    },
    "san_francisco": {
        "name": "San Francisco, CA",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "timezone": "America/Los_Angeles",
    },
    "new_york": {
        "name": "New York, NY",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timezone": "America/New_York",
    },
    "london": {
        "name": "London, UK",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "timezone": "Europe/London",
    },
    "paris": {
        "name": "Paris, France",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "timezone": "Europe/Paris",
    },
    "tokyo": {
        "name": "Tokyo, Japan",
        "latitude": 35.6762,
        "longitude": 139.6503,
        "timezone": "Asia/Tokyo",
    },
    "sydney": {
        "name": "Sydney, Australia",
        "latitude": -33.8688,
        "longitude": 151.2093,
        "timezone": "Australia/Sydney",
    },
    "bengaluru": {
        "name": "Bengaluru, India",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "timezone": "Asia/Kolkata",
    },
    "reykjavik": {
        "name": "Reykjavik, Iceland",
        "latitude": 64.1466,
        "longitude": -21.9426,
        "timezone": "Atlantic/Reykjavik",
    },
}


def get_timezone_obj(tz_name: Optional[str] = None):
    """Safely obtain a ZoneInfo object, falling back to local or UTC."""
    if not tz_name:
        tz_name = LOCAL_TZ_NAME
    try:
        return ZoneInfo(tz_name)
    except Exception:
        try:
            return ZoneInfo("UTC")
        except Exception:
            return timezone.utc


def calculate_daylight_metrics(
    latitude: float = 12.9716,
    longitude: float = 77.5946,
    tz_name: Optional[str] = None,
    simulated_time_str: Optional[str] = None,
    location_name: str = "Local Horizon"
) -> Dict[str, Any]:
    """
    Computes precise astronomical timings and real-time daylight countdown.

    Parameters:
        latitude: Observer latitude (-90 to +90)
        longitude: Observer longitude (-180 to +180)
        tz_name: Timezone identifier (e.g. 'America/Los_Angeles', 'Asia/Kolkata')
        simulated_time_str: Optional time string (HH:MM or ISO) for Sandbox Time-Travel
        location_name: Friendly name of the location
    """
    tz = get_timezone_obj(tz_name)
    now_local = datetime.now(tz)

    is_simulated = False
    if simulated_time_str:
        try:
            # Check if HH:MM format
            if ":" in simulated_time_str and len(simulated_time_str) <= 8:
                parts = simulated_time_str.split(":")
                sim_h = int(parts[0])
                sim_m = int(parts[1])
                sim_s = int(parts[2]) if len(parts) > 2 else 0
                now_local = now_local.replace(hour=sim_h, minute=sim_m, second=sim_s, microsecond=0)
                is_simulated = True
            else:
                # Parse full ISO string
                parsed = datetime.fromisoformat(simulated_time_str)
                if parsed.tzinfo is None:
                    now_local = parsed.replace(tzinfo=tz)
                else:
                    now_local = parsed.astimezone(tz)
                is_simulated = True
        except Exception:
            pass

    today = now_local.date()
    observer_location = LocationInfo(
        name=location_name,
        region="Local",
        timezone=str(tz),
        latitude=latitude,
        longitude=longitude
    )

    # Calculate standard solar events
    try:
        s_data = sun(observer_location.observer, date=today, tzinfo=tz)
        dawn = s_data['dawn']
        sunrise = s_data['sunrise']
        noon = s_data['noon']
        sunset = s_data['sunset']
        dusk = s_data['dusk']
    except Exception:
        # Fallback approximation in case of polar latitude edge-cases
        noon = datetime.combine(today, time(12, 0), tzinfo=tz)
        sunrise = noon - timedelta(hours=6)
        dawn = sunrise - timedelta(minutes=30)
        sunset = noon + timedelta(hours=6)
        dusk = sunset + timedelta(minutes=30)

    # Calculate golden hour (evening)
    try:
        gh_tuple = golden_hour(
            observer_location.observer,
            date=today,
            direction=SunDirection.SETTING,
            tzinfo=tz
        )
        golden_hour_start = gh_tuple[0]
        golden_hour_end = gh_tuple[1]
    except Exception:
        golden_hour_start = sunset - timedelta(minutes=50)
        golden_hour_end = sunset + timedelta(minutes=15)

    # Calculate blue hour (evening)
    try:
        bh_tuple = blue_hour(
            observer_location.observer,
            date=today,
            direction=SunDirection.SETTING,
            tzinfo=tz
        )
        blue_hour_start = bh_tuple[0]
        blue_hour_end = bh_tuple[1]
    except Exception:
        blue_hour_start = sunset
        blue_hour_end = dusk

    # Calculate solar elevation angle (degrees)
    try:
        now_utc = now_local.astimezone(timezone.utc)
        solar_elevation = float(elevation(observer_location.observer, dateandtime=now_utc))
    except Exception:
        solar_elevation = 0.0

    # Remaining minutes
    diff_to_sunset = (sunset - now_local).total_seconds() / 60.0
    minutes_left_until_sunset = max(0, int(round(diff_to_sunset)))
    raw_minutes_until_sunset = round(diff_to_sunset, 1)

    diff_to_golden_hour = (golden_hour_start - now_local).total_seconds() / 60.0
    minutes_until_golden_hour = int(round(diff_to_golden_hour))

    diff_to_dusk = (dusk - now_local).total_seconds() / 60.0
    minutes_until_dusk = max(0, int(round(diff_to_dusk)))

    # Daylight duration and percentage
    total_daylight_seconds = max(1.0, (sunset - sunrise).total_seconds())
    elapsed_daylight_seconds = (now_local - sunrise).total_seconds()

    if now_local < sunrise:
        daylight_percentage = 0.0
    elif now_local > sunset:
        daylight_percentage = 100.0
    else:
        daylight_percentage = round((elapsed_daylight_seconds / total_daylight_seconds) * 100.0, 1)

    # Phase classification & UI Styling tokens
    phase_key, phase_label, phase_desc, phase_accent, urgency = classify_daylight_phase(
        now_local=now_local,
        sunrise=sunrise,
        golden_hour_start=golden_hour_start,
        sunset=sunset,
        dusk=dusk,
        blue_hour_end=blue_hour_end,
        solar_elevation=solar_elevation
    )

    # Calculate time until next solar milestone for countdown badge
    if now_local < sunrise:
        milestone_label = "Until Sunrise"
        milestone_seconds = max(0, int((sunrise - now_local).total_seconds()))
    elif now_local < golden_hour_start:
        milestone_label = "Until Golden Hour"
        milestone_seconds = max(0, int((golden_hour_start - now_local).total_seconds()))
    elif now_local < sunset:
        milestone_label = "Until Sunset"
        milestone_seconds = max(0, int((sunset - now_local).total_seconds()))
    elif now_local < dusk:
        milestone_label = "Until Blue Hour Ends"
        milestone_seconds = max(0, int((dusk - now_local).total_seconds()))
    else:
        # After dusk, count to tomorrow's sunrise
        tomorrow_sunrise = sunrise + timedelta(days=1)
        milestone_label = "Until Tomorrow's Dawn"
        milestone_seconds = max(0, int((tomorrow_sunrise - now_local).total_seconds()))

    milestone_hours = milestone_seconds // 3600
    milestone_minutes = (milestone_seconds % 3600) // 60
    milestone_secs = milestone_seconds % 60
    milestone_formatted = f"{milestone_hours:02d}:{milestone_minutes:02d}:{milestone_secs:02d}"

    # Ambient natural lux estimation based on solar elevation
    if solar_elevation > 35:
        lux_estimate = 75000 + int(solar_elevation * 500)
        lux_label = "Blinding Full Sun (> 75,000 Lux)"
        circadian_status = "Peak Cortisol • Maximum Alertness"
    elif solar_elevation > 15:
        lux_estimate = 35000 + int(solar_elevation * 800)
        lux_label = "Direct Daylight (~ 40,000 Lux)"
        circadian_status = "Active Biological Alertness"
    elif solar_elevation > 5:
        lux_estimate = 8000 + int(solar_elevation * 1000)
        lux_label = "Soft Ambient Solar (~ 12,000 Lux)"
        circadian_status = "Optimal Natural Photon Window"
    elif solar_elevation > 0:
        lux_estimate = int(400 + (solar_elevation / 5.0) * 1600)
        lux_label = "Golden Hour Glow (400 – 2,000 Lux)"
        circadian_status = "Warm Low-Angle Light • Critical Egress Window"
    elif solar_elevation > -6:
        lux_estimate = max(1, int(1 + (solar_elevation + 6) * 15))
        lux_label = "Civil Blue Hour (1 – 90 Lux)"
        circadian_status = "Melatonin Pathway Awakening • Abandon Screens"
    else:
        lux_estimate = 0.05
        lux_label = "Starlight Night (< 0.1 Lux)"
        circadian_status = "Natural Circadian Curfew • High Screen Fatigue"

    dial_angle_degrees = round(((now_local.hour * 60 + now_local.minute + now_local.second / 60.0) / 1440.0) * 360.0, 1)

    # Format all events into friendly 12h/24h strings
    return {
        "app_name": "NatureLeft",
        "location": {
            "name": location_name,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": str(tz)
        },
        "times": {
            "current_time_iso": now_local.isoformat(),
            "current_time_display": now_local.strftime("%I:%M:%S %p"),
            "current_time_24h": now_local.strftime("%H:%M:%S"),
            "dawn": dawn.strftime("%I:%M %p"),
            "sunrise": sunrise.strftime("%I:%M %p"),
            "solar_noon": noon.strftime("%I:%M %p"),
            "golden_hour_start": golden_hour_start.strftime("%I:%M %p"),
            "sunset": sunset.strftime("%I:%M %p"),
            "blue_hour_end": blue_hour_end.strftime("%I:%M %p"),
            "dusk": dusk.strftime("%I:%M %p"),
            "dawn_raw": dawn.isoformat(),
            "sunrise_raw": sunrise.isoformat(),
            "sunset_raw": sunset.isoformat(),
            "golden_hour_start_raw": golden_hour_start.isoformat(),
            "dusk_raw": dusk.isoformat()
        },
        "countdown": {
            "minutes_left_until_sunset": minutes_left_until_sunset,
            "raw_minutes_until_sunset": raw_minutes_until_sunset,
            "minutes_until_golden_hour": minutes_until_golden_hour,
            "minutes_until_dusk": minutes_until_dusk,
            "daylight_percentage": daylight_percentage,
            "milestone_label": milestone_label,
            "milestone_formatted": milestone_formatted,
            "milestone_seconds": milestone_seconds
        },
        "solar": {
            "elevation_degrees": round(solar_elevation, 1),
            "dial_angle_degrees": dial_angle_degrees,
            "lux_estimate": lux_estimate,
            "lux_label": lux_label,
            "circadian_status": circadian_status,
            "is_daylight": sunrise <= now_local <= sunset,
            "is_golden_hour": golden_hour_start <= now_local <= sunset,
            "is_twilight": sunset < now_local <= dusk,
            "is_night": now_local > dusk or now_local < dawn
        },
        "phase": {
            "key": phase_key,
            "label": phase_label,
            "description": phase_desc,
            "accent": phase_accent,
            "urgency": urgency
        },
        "is_simulated": is_simulated,
        "simulated_slider_value": now_local.hour * 60 + now_local.minute
    }


def classify_daylight_phase(
    now_local: datetime,
    sunrise: datetime,
    golden_hour_start: datetime,
    sunset: datetime,
    dusk: datetime,
    blue_hour_end: datetime,
    solar_elevation: float
) -> Tuple[str, str, str, str, str]:
    """
    Returns (phase_key, label, description, accent_theme, urgency)
    """
    if now_local < sunrise - timedelta(minutes=45):
        return (
            "NIGHT_PRE_DAWN",
            "Pre-Dawn Obsidian",
            "The world is still asleep. Photons are at minimum zero. Prepare for morning radiance.",
            "violet",
            "CALM"
        )
    elif now_local < sunrise:
        return (
            "DAWN",
            "Morning Civil Dawn",
            "First horizontal rays cresting the horizon. Crisp, high-contrast awakening light.",
            "amber",
            "WARM"
        )
    elif now_local < golden_hour_start - timedelta(minutes=60):
        return (
            "DAYLIGHT_PEAK",
            "Direct Solar Daylight",
            "Abundant photons overhead. High screen fatigue zone. Plan your outdoor egress.",
            "cyan",
            "NORMAL"
        )
    elif now_local < golden_hour_start:
        return (
            "PRE_GOLDEN_HOUR",
            "The Golden Rush",
            "The sun is descending past 12° elevation. Shadows are stretching across the concrete.",
            "amber-orange",
            "ELEVATED"
        )
    elif now_local <= sunset:
        return (
            "GOLDEN_HOUR",
            "The Golden Hour",
            "CRITICAL WINDOW: Warm, low-angle amber photons. Long cinematic shadows. Drop screens immediately.",
            "coral-amber",
            "CRITICAL"
        )
    elif now_local <= dusk:
        return (
            "BLUE_HOUR",
            "The Blue Hour & Twilight",
            "The sun dipped below horizon. Ethereal royal blue and indigo twilight. 15 minutes of magic left.",
            "electric-blue",
            "LAST_CHANCE"
        )
    else:
        return (
            "NIGHT_CURFEW",
            "Screen Curfew & Total Dark",
            "Natural daylight expired. Blue light from monitors is now poisoning your circadian rhythm. Step outside.",
            "indigo-slate",
            "CURFEW"
        )
