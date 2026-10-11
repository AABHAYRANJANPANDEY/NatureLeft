"""
NatureLeft — The Offline Natural Horizon Clock & Biophilic Scavenger
Streamlit Application Edition
Deployable to Streamlit Community Cloud or run locally via `streamlit run app.py`
"""

import streamlit as st
import datetime
import json
import time
import textwrap
from pathlib import Path

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

# Page Configuration
st.set_page_config(
    page_title="NatureLeft — Natural Horizon Clock & Scavenger",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

def render_html(html_str: str):
    """
    Renders custom HTML cleanly without Markdown code-block escaping.
    Uses st.html if available; otherwise uses dedented st.markdown.
    """
    cleaned = textwrap.dedent(html_str).strip()
    if hasattr(st, "html"):
        st.html(cleaned)
    else:
        st.markdown(cleaned, unsafe_allow_html=True)


# Silicon Valley Pro Atelier Custom CSS
render_html("""
<style>
    /* Dark Luxury Atelier Base */
    .stApp {
        background-color: #060911;
        color: #F1F5F9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    }
    
    header[data-testid="stHeader"] {
        background: rgba(6, 9, 17, 0.85);
        backdrop-filter: blur(16px);
    }

    /* Pro Glassmorphic Cards */
    .pro-metric-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.75) 0%, rgba(10, 15, 29, 0.6) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 22px;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1), 0 15px 35px rgba(0, 0, 0, 0.5);
        margin-bottom: 14px;
        backdrop-filter: blur(20px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .pro-metric-card:hover {
        border-color: rgba(255, 255, 255, 0.15);
        transform: translateY(-2px);
    }

    .hero-dial-card {
        background: radial-gradient(circle at 50% 25%, rgba(245, 158, 11, 0.18) 0%, rgba(16, 185, 129, 0.10) 45%, rgba(10, 15, 29, 0.85) 100%);
        border: 1px solid rgba(245, 158, 11, 0.25);
        border-radius: 26px;
        padding: 36px 24px;
        text-align: center;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.15), 0 25px 60px rgba(0, 0, 0, 0.7);
        margin-bottom: 26px;
    }

    .directive-box {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(10, 15, 29, 0.7) 100%);
        border: 1px solid rgba(16, 185, 129, 0.25);
        border-radius: 22px;
        padding: 26px;
        margin-bottom: 20px;
        box-shadow: 0 20px 45px rgba(0, 0, 0, 0.55);
    }

    .tactical-pill {
        background: rgba(2, 6, 23, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 16px;
        padding: 16px;
        margin-top: 12px;
    }

    /* Primary CTA Button */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
        color: white !important;
        font-weight: 800 !important;
        letter-spacing: 0.5px !important;
        border: none !important;
        border-radius: 16px !important;
        padding: 16px 32px !important;
        box-shadow: 0 12px 30px rgba(16, 185, 129, 0.35) !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 18px 40px rgba(16, 185, 129, 0.5) !important;
    }

    div.stButton > button[kind="secondary"] {
        background: rgba(30, 41, 59, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #F1F5F9 !important;
        border-radius: 14px !important;
        font-weight: 600 !important;
    }
</style>
""")

# State initialization
if "streak_days" not in st.session_state:
    st.session_state.streak_days = 4
if "minutes_saved" not in st.session_state:
    st.session_state.minutes_saved = 140
if "escapes_count" not in st.session_state:
    st.session_state.escapes_count = 7
if "active_directive" not in st.session_state:
    st.session_state.active_directive = None
if "escapes_log" not in st.session_state:
    st.session_state.escapes_log = [
        {"time": "Yesterday at Golden Hour", "phase": "The Golden Hour", "min": 25, "badge": "🌅 Golden Hour Witness"},
        {"time": "2 days ago at Blue Hour", "phase": "The Blue Hour & Twilight", "min": 20, "badge": "🌌 Dusk Walker"}
    ]

# SIDEBAR: Location & Controls
with st.sidebar:
    st.markdown("## 🌿 NatureLeft")
    st.caption("The Offline Natural Horizon Clock & Biophilic Scavenger")
    
    st.markdown("---")

    # Location selection
    preset_names = {
        "bengaluru": "☕ Bengaluru, India",
        "san_francisco": "🌉 San Francisco, CA",
        "new_york": "🗽 New York, NY",
        "london": "🎡 London, UK",
        "paris": "🗼 Paris, France",
        "tokyo": "🗾 Tokyo, Japan",
        "sydney": "🦘 Sydney, Australia",
        "reykjavik": "🌋 Reykjavik, Iceland"
    }
    
    selected_city_key = st.selectbox(
        "Observation Horizon",
        options=list(preset_names.keys()),
        format_func=lambda x: preset_names.get(x, x),
        index=0
    )
    city_data = PRESET_LOCATIONS.get(selected_city_key, PRESET_LOCATIONS["bengaluru"])

    st.markdown("---")
    
    # Persona tone selector
    st.markdown("### 🎭 AI Directive Persona")
    tone_options = {
        "witty": "Witty & Poetic Curator",
        "drill_sergeant": "Aggressive Drill Sergeant",
        "zen": "Zen Biophilic Monk",
        "speedrunner": "Speedrun Scavenger"
    }
    selected_tone = st.radio(
        "Persona Voice",
        options=list(tone_options.keys()),
        format_func=lambda x: tone_options[x],
        index=0
    )

    st.markdown("---")

    # Local AI status check
    ai_status = check_ollama_status()
    if ai_status["is_running"] and ai_status["available_models"]:
        st.success(f"🟢 Local Ollama ({ai_status['default_model']})")
    else:
        st.info("⚡ Offline Neural Engine (100% Private, Zero Cloud)")

    st.markdown("---")
    
    # Streak Summary
    st.markdown(f"### 🔥 Outdoor Streak: **{st.session_state.streak_days} Days**")
    st.caption(f"Reclaimed Daylight: **{st.session_state.minutes_saved} minutes**")
    st.caption(f"Total Escapes Logged: **{st.session_state.escapes_count} sessions**")


# TIME-TRAVEL SANDBOX: Scrubbing
st.markdown("### 🎛️ Time-Travel Simulator Sandbox")
col_sim1, col_sim2 = st.columns([1, 3])

with col_sim1:
    enable_simulation = st.checkbox("Enable Time-Travel Scrubbing", value=False)

simulated_time_str = None
if enable_simulation:
    sim_mins = st.slider(
        "Scrub 24 Hours of the Day (00:00 to 23:59)",
        min_value=0,
        max_value=1439,
        value=17 * 60 + 45,
        step=5,
        help="Drag to test any moment of the day (e.g. Dawn, Noon, Golden Hour, Night)"
    )
    sim_h = sim_mins // 60
    sim_m = sim_mins % 60
    simulated_time_str = f"{sim_h:02d}:{sim_m:02d}"
    st.info(f"⏳ Simulating **{simulated_time_str}** for testing.")

# Calculate astronomical metrics
metrics = calculate_daylight_metrics(
    latitude=city_data["latitude"],
    longitude=city_data["longitude"],
    tz_name=city_data["timezone"],
    simulated_time_str=simulated_time_str,
    location_name=city_data["name"]
)

times = metrics["times"]
count = metrics["countdown"]
solar = metrics["solar"]
phase = metrics["phase"]

# MAIN CANVAS: Hero Dial Section
render_html(f"""
<div class="hero-dial-card">
    <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 2.5px; color: #F59E0B; margin-bottom: 8px;">
        {phase['label']}
    </div>
    <div style="font-size: 68px; font-weight: 900; font-family: 'JetBrains Mono', monospace; letter-spacing: -2px; color: #FFFFFF; line-height: 1.1;">
        {count['milestone_formatted']}
    </div>
    <div style="font-size: 15px; font-weight: 700; color: #FCD34D; margin-top: 8px;">
        {count['milestone_label']}
    </div>
    <div style="font-size: 13.5px; color: #CBD5E1; margin-top: 14px; max-width: 680px; margin-left: auto; margin-right: auto; line-height: 1.6;">
        {phase['description']}
    </div>
    <div style="margin-top: 18px; display: flex; justify-content: center; gap: 16px; font-size: 12px; font-family: monospace; color: #38BDF8;">
        <span>☀️ Solar Elevation: {solar['elevation_degrees']}°</span>
        <span>•</span>
        <span>💡 Photometer: {solar.get('lux_label', 'Direct Ambient')}</span>
        <span>•</span>
        <span>🌿 Circadian: {solar.get('circadian_status', 'Natural Cycle')}</span>
    </div>
</div>
""")

# 4 Solar Metrics Columns
c1, c2, c3, c4 = st.columns(4)
with c1:
    render_html(f"""
    <div class="pro-metric-card">
        <div style="font-size: 11px; text-transform: uppercase; color: #94A3B8; font-weight: 700; letter-spacing: 1px;">🌅 Golden Hour</div>
        <div style="font-size: 20px; font-weight: 800; color: #F59E0B; margin-top: 4px; font-family: monospace;">{times['golden_hour_start']}</div>
        <div style="font-size: 11px; color: #64748B;">Soft Amber Lumens</div>
    </div>
    """)
with c2:
    render_html(f"""
    <div class="pro-metric-card">
        <div style="font-size: 11px; text-transform: uppercase; color: #94A3B8; font-weight: 700; letter-spacing: 1px;">🌇 Sunset Horizon</div>
        <div style="font-size: 20px; font-weight: 800; color: #F43F5E; margin-top: 4px; font-family: monospace;">{times['sunset']}</div>
        <div style="font-size: 11px; color: #64748B;">0.0° Solar Horizon</div>
    </div>
    """)
with c3:
    render_html(f"""
    <div class="pro-metric-card">
        <div style="font-size: 11px; text-transform: uppercase; color: #94A3B8; font-weight: 700; letter-spacing: 1px;">🌌 Blue Hour / Dusk</div>
        <div style="font-size: 20px; font-weight: 800; color: #38BDF8; margin-top: 4px; font-family: monospace;">{times['blue_hour_end']}</div>
        <div style="font-size: 11px; color: #64748B;">Cobalt Ozone Scatter</div>
    </div>
    """)
with c4:
    render_html(f"""
    <div class="pro-metric-card">
        <div style="font-size: 11px; text-transform: uppercase; color: #94A3B8; font-weight: 700; letter-spacing: 1px;">☀️ Solar Noon</div>
        <div style="font-size: 20px; font-weight: 800; color: #FCD34D; margin-top: 4px; font-family: monospace;">{times['solar_noon']}</div>
        <div style="font-size: 11px; color: #64748B;">Peak Zenith Intensity</div>
    </div>
    """)

st.markdown("---")

# Main Section: 2 Columns (Left: Scavenger Mission, Right: Touch Grass Action)
col_left, col_right = st.columns([7, 5])

with col_left:
    st.markdown("### 🎯 Outdoor Scavenger Directive")

    # Generate directive if not set or user regenerated
    if st.session_state.active_directive is None or st.button("🔄 Regenerate Scavenger Mission", use_container_width=True):
        with st.spinner("Synthesizing witty anti-screen directive..."):
            st.session_state.active_directive = generate_directive(
                phase_label=phase["label"],
                minutes_left=count["minutes_left_until_sunset"] or 30,
                milestone_label=count["milestone_label"],
                location_name=city_data["name"],
                tone=selected_tone
            )

    d = st.session_state.active_directive
    if d:
        render_html(f"""
        <div class="directive-box">
            <div style="font-size: 11px; font-family: monospace; color: #10B981; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 700;">
                ACTIVE NATURE DIRECTIVE
            </div>
            <div style="font-size: 22px; font-weight: 800; color: #FFFFFF; margin-top: 4px; margin-bottom: 12px; letter-spacing: -0.5px;">
                {d['title']}
            </div>
            <div style="font-size: 15px; line-height: 1.65; color: #E2E8F0; margin-bottom: 18px;">
                {d['directive']}
            </div>
            
            <div class="tactical-pill">
                <div style="font-size: 11.5px; font-weight: 800; color: #F59E0B; text-transform: uppercase; letter-spacing: 0.5px;">
                    🎯 SENSORY TARGET IN NATURE:
                </div>
                <div style="font-size: 13.5px; color: #CBD5E1; margin-top: 4px; font-family: monospace;">
                    {d['sensory_target']}
                </div>
            </div>

            <div class="tactical-pill" style="margin-top: 10px;">
                <div style="font-size: 11.5px; font-weight: 800; color: #F43F5E; text-transform: uppercase; letter-spacing: 0.5px;">
                    ⚡ TACTICAL EGRESS ACTION:
                </div>
                <div style="font-size: 13.5px; color: #CBD5E1; margin-top: 4px; font-family: monospace;">
                    {d['tactical_action']}
                </div>
            </div>

            <div style="margin-top: 18px; font-size: 11px; font-family: monospace; color: #64748B;">
                Inference: <span style="color: #10B981; font-weight: 600;">{d['model_used']}</span> • Latency: {d['latency_ms']}ms • Throughput: {d['tokens_per_sec']} tok/s
            </div>
        </div>
        """)

        with st.expander("🔍 Inspect Local Model JSON Telemetry"):
            st.json(d)

with col_right:
    st.markdown("### 🌿 Biological Escape Protocol")
    st.markdown("Verify departure from fluorescent liquid crystal displays and log outdoor exposure.")

    if st.button("🌿 I Touched Grass — Log Escape", type="primary", use_container_width=True):
        st.session_state.streak_days += 1
        st.session_state.minutes_saved += 25
        st.session_state.escapes_count += 1
        
        st.balloons()
        st.success(f"🎉 Escape Verified! Outdoor streak incremented to {st.session_state.streak_days} Days! +25 mins reclaimed.")

        now_str = datetime.datetime.now().strftime("%I:%M %p — Today")
        st.session_state.escapes_log.insert(0, {
            "time": now_str,
            "phase": phase["label"],
            "min": 25,
            "badge": "🌿 Grass Touched"
        })

    # Stats Summary
    render_html(f"""
    <div class="pro-metric-card" style="margin-top: 20px;">
        <div style="display: flex; justify-content: space-around; text-align: center;">
            <div>
                <div style="font-size: 26px; font-weight: 800; color: #F59E0B; font-family: monospace;">{st.session_state.streak_days} Days</div>
                <div style="font-size: 10px; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Current Streak</div>
            </div>
            <div>
                <div style="font-size: 26px; font-weight: 800; color: #10B981; font-family: monospace;">{st.session_state.minutes_saved}m</div>
                <div style="font-size: 10px; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Daylight Saved</div>
            </div>
            <div>
                <div style="font-size: 26px; font-weight: 800; color: #38BDF8; font-family: monospace;">{st.session_state.escapes_count}</div>
                <div style="font-size: 10px; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Total Escapes</div>
            </div>
        </div>
    </div>
    """)

    # Escape Logs
    st.markdown("#### 📜 Recent Outdoor Escapes")
    for log in st.session_state.escapes_log[:5]:
        render_html(f"""
        <div style="background: rgba(15, 23, 42, 0.6); padding: 12px 16px; border-radius: 14px; margin-bottom: 8px; border: 1px solid rgba(255, 255, 255, 0.06); display: flex; justify-content: space-between; align-items: center; font-size: 12px;">
            <div>
                <span style="color: #10B981; font-weight: 800;">{log['badge']}</span>
                <span style="color: #94A3B8; font-family: monospace; margin-left: 6px;">{log['time']}</span>
            </div>
            <div style="font-weight: 800; color: #F59E0B; font-family: monospace;">
                +{log['min']}m
            </div>
        </div>
        """)

st.markdown("---")
st.caption("NatureLeft • 100% Offline • Touch Grass Edition • Zero Cloud Dependency • Open-Source AI")
