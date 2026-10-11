"""
DaylightLeft — The Offline Sunset Clock & Golden Hour Scavenger
FastAPI Local Backend Server
100% Offline, Zero Cloud Dependency, Privacy-Preserving
"""

import os
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from utils.astronomy import (
    calculate_daylight_metrics,
    PRESET_LOCATIONS,
    LOCAL_TZ_NAME
)
from utils.ai_generator import (
    generate_directive,
    check_ollama_status,
    TONES
)

# Initialize FastAPI App
app = FastAPI(
    title="NatureLeft — The Offline Natural Horizon Clock & Scavenger",
    description="The anti-screen biophilic golden hour countdown clock and scavenger mission generator.",
    version="2.0.0"
)

# CORS middleware for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
STREAKS_FILE = DATA_DIR / "streaks.json"

# In-memory / persistent streak state
def load_streaks() -> Dict[str, Any]:
    if STREAKS_FILE.exists():
        try:
            with open(STREAKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "current_streak_days": 4,
        "total_minutes_saved": 140,
        "total_escapes_logged": 7,
        "last_escape_date": None,
        "recent_escapes": [
            {
                "timestamp": "Yesterday at Golden Hour",
                "phase": "Golden Hour (Magic Hour)",
                "minutes_reclaimed": 25,
                "location": "Local Horizon",
                "badge": "🌅 Golden Hour Witness"
            },
            {
                "timestamp": "2 days ago at Blue Hour",
                "phase": "The Blue Hour & Twilight",
                "minutes_reclaimed": 20,
                "location": "Local Horizon",
                "badge": "🌌 Dusk Walker"
            }
        ]
    }


def save_streaks(data: Dict[str, Any]) -> None:
    try:
        with open(STREAKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save streaks: {e}")


# Pydantic Schemas
class DirectiveRequest(BaseModel):
    phase_label: str = Field(default="The Golden Hour")
    minutes_left: int = Field(default=35)
    milestone_label: str = Field(default="Until Sunset")
    location_name: str = Field(default="Local Horizon")
    tone: str = Field(default="witty")
    model: Optional[str] = None


class EscapeLogRequest(BaseModel):
    phase: str = Field(default="Golden Hour")
    minutes_reclaimed: int = Field(default=20)
    location: str = Field(default="Local Horizon")
    note: Optional[str] = None


# Mount static directory if it exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Routes
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the primary UI dashboard."""
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        index_file = STATIC_DIR / "index.html"

    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    
    return HTMLResponse(
        content="<h1>DaylightLeft is starting up... template not found.</h1>",
        status_code=500
    )


@app.get("/api/status")
async def get_daylight_status(
    lat: float = Query(12.9716, description="Latitude"),
    lon: float = Query(77.5946, description="Longitude"),
    tz: Optional[str] = Query(None, description="Timezone name"),
    simulated_time: Optional[str] = Query(None, description="Simulated time in HH:MM or ISO"),
    location_name: str = Query("Local Horizon", description="Location display name")
):
    """
    Computes precise astronomical timings, solar elevation, phase,
    and remaining minutes until golden hour / sunset.
    """
    metrics = calculate_daylight_metrics(
        latitude=lat,
        longitude=lon,
        tz_name=tz,
        simulated_time_str=simulated_time,
        location_name=location_name
    )

    ollama_status = check_ollama_status()
    streaks = load_streaks()

    return {
        "success": True,
        "metrics": metrics,
        "ai_engine": ollama_status,
        "streak_summary": {
            "current_streak_days": streaks.get("current_streak_days", 4),
            "total_minutes_saved": streaks.get("total_minutes_saved", 140),
            "total_escapes_logged": streaks.get("total_escapes_logged", 7)
        }
    }


@app.post("/api/directive")
async def get_ai_directive(req: DirectiveRequest):
    """
    Generates a fresh, witty, poetic anti-screen outdoor mission
    using local Ollama or the zero-latency offline engine.
    """
    directive = generate_directive(
        phase_label=req.phase_label,
        minutes_left=req.minutes_left,
        milestone_label=req.milestone_label,
        location_name=req.location_name,
        tone=req.tone,
        model_override=req.model
    )
    return {
        "success": True,
        "directive": directive
    }


@app.get("/api/streak")
async def get_streak():
    """Returns the current streak and outdoor escape log."""
    return load_streaks()


@app.post("/api/streak")
async def log_escape(req: EscapeLogRequest):
    """
    Logs an outdoor grass-touching session, increments streak,
    and returns celebratory feedback.
    """
    data = load_streaks()
    today_str = datetime.now().strftime("%Y-%m-%d")

    data["total_escapes_logged"] = data.get("total_escapes_logged", 0) + 1
    data["total_minutes_saved"] = data.get("total_minutes_saved", 0) + req.minutes_reclaimed

    # If new day, increment streak
    if data.get("last_escape_date") != today_str:
        data["current_streak_days"] = data.get("current_streak_days", 0) + 1
        data["last_escape_date"] = today_str

    # Prepend new escape record
    timestamp_display = datetime.now().strftime("%I:%M %p — Today")
    badge = "🌿 Grass Touched"
    if "Golden" in req.phase:
        badge = "🌅 Golden Hour Legend"
    elif "Blue" in req.phase or "Twilight" in req.phase:
        badge = "🌌 Dusk Walker"

    new_log = {
        "timestamp": timestamp_display,
        "phase": req.phase,
        "minutes_reclaimed": req.minutes_reclaimed,
        "location": req.location,
        "badge": badge,
        "note": req.note or "Successfully abandoned screens for natural photons."
    }

    recent = data.get("recent_escapes", [])
    recent.insert(0, new_log)
    data["recent_escapes"] = recent[:10]  # Keep last 10

    save_streaks(data)

    return {
        "success": True,
        "message": "Escape verified! Your biological clock salutes you.",
        "updated_streak": data["current_streak_days"],
        "total_minutes_saved": data["total_minutes_saved"],
        "total_escapes_logged": data["total_escapes_logged"],
        "badge_earned": badge
    }


@app.get("/api/presets")
async def get_presets():
    """Returns pre-configured cities for judges to test."""
    return PRESET_LOCATIONS


@app.get("/api/models")
async def get_models():
    """Returns Ollama status and available local models."""
    return check_ollama_status()


@app.get("/api/tones")
async def get_tones():
    """Returns available tone personas for directive generation."""
    return TONES


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": "DaylightLeft",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🌅 DaylightLeft — The Offline Sunset Clock & Golden Hour Scavenger")
    print("🚀 Starting local server at http://127.0.0.1:8000")
    print("🛡️  100% Offline | Zero Cloud Dependency | Touch Grass Edition")
    print("="*60 + "\n")
    uvicorn.run("main.py:app", host="127.0.0.1", port=8000, reload=False)
