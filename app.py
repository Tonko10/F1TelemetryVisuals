import streamlit as st
import fastf1
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import time
import os

st.set_page_config(layout="wide", page_title="Singapore Quali 2026", page_icon="🏎️")
st.markdown("""
    <style>
        .block-container { padding: 3.5rem 2rem 0rem 2rem; max-width: 100%; }
        div[data-testid="stMetricValue"] { font-size: 1.4rem; padding-bottom: 0; }
        div[data-testid="stMetricLabel"] { font-size: 0.9rem; }
        h3 { margin-top: -1rem; margin-bottom: 0rem; }
        h4 { margin-top: 0rem; margin-bottom: 0.3rem; font-size: 1.1rem; }
        p { font-size: 0.9rem; line-height: 1.4; margin-bottom: 0; }
        hr { margin: 0.5rem 0; }
        div[data-testid="stSlider"] { padding-bottom: 0px; margin-bottom: -10px; }
    </style>
""", unsafe_allow_html=True)

os.makedirs('f1_cache', exist_ok=True)
fastf1.Cache.enable_cache('f1_cache') 

VER_COLOR = '#0600ef'
LEC_COLOR = '#dc0000'

@st.cache_data
def load_data():
    session = fastf1.get_session(2026, 'Singapore', 2)
    session.load(telemetry=True, weather=False, messages=False)

    lap_ver = session.laps.pick_driver('VER').pick_fastest()
    lap_lec = session.laps.pick_driver('LEC').pick_fastest()

    tel_ver = lap_ver.get_telemetry()
    tel_lec = lap_lec.get_telemetry()

    ver_elapsed = (tel_ver['Time'] - tel_ver['Time'].iloc[0]).dt.total_seconds()
    lec_elapsed = (tel_lec['Time'] - tel_lec['Time'].iloc[0]).dt.total_seconds()

    max_dist = float(min(tel_ver['Distance'].max(), tel_lec['Distance'].max()))
    dist_arr = np.append(np.arange(0, max_dist, 2.0), max_dist)

    ver_speed = np.interp(dist_arr, tel_ver['Distance'], tel_ver['Speed'])
    ver_x = np.interp(dist_arr, tel_ver['Distance'], tel_ver['X'])
    ver_y = np.interp(dist_arr, tel_ver['Distance'], tel_ver['Y'])
    lec_speed = np.interp(dist_arr, tel_lec['Distance'], tel_lec['Speed'])
    
    ver_time_sync = np.interp(dist_arr, tel_ver['Distance'], ver_elapsed)
    lec_time_sync = np.interp(dist_arr, tel_lec['Distance'], lec_elapsed)

    ver_time_sync -= ver_time_sync[0]
    lec_time_sync -= lec_time_sync[0]

    ver_time_sync = ver_time_sync * (91.373 / ver_time_sync[-1])
    lec_time_sync = lec_time_sync * (91.427 / lec_time_sync[-1])

    delta = ver_time_sync - lec_time_sync
    lec_dist_at_ver_time = np.interp(ver_time_sync, lec_time_sync, dist_arr)
    
    map_lec_x = np.interp(lec_dist_at_ver_time, dist_arr, ver_x)
    map_lec_y = np.interp(lec_dist_at_ver_time, dist_arr, ver_y)

    df = pd.DataFrame({
        'Distance': dist_arr,
        'VER_Speed': ver_speed,
        'LEC_Speed': lec_speed,
        'VER_X': ver_x,
        'VER_Y': ver_y,
        'MAP_LEC_X': map_lec_x,
        'MAP_LEC_Y': map_lec_y,
        'VER_Time': ver_time_sync,
        'LEC_Time': lec_time_sync,
        'Delta': delta
    })
    return df, max_dist

try:
    df, track_length = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

def fmt_time(seconds):
    if pd.isna(seconds):
        return "0.000s"
    m = int(seconds // 60)
    s = seconds % 60
    if m > 0:
        return f"{m}:{s:06.3f}"
    return f"{s:.3f}s"

def get_commentary(dist):
    if dist < 800:
        return "#### 🚦 Turns 1-3\n**VER S1: 27.002s | LEC S1: 27.025s**<br>Verstappen maximizes entry speed into T1, squaring off T3 perfectly to carry momentum down the straight. He takes an early 0.023s lead."
    elif dist < 1600:
        return "#### 🛑 Turn 7 Braking\nApproaching Memorial corner, Leclerc brakes marginally later. The Ferrari's front-end compliance allows him to rotate sharply without locking up, clawing back time."
    elif dist < 2400:
        return "#### 🐍 Turns 8-12\n**VER S2: 38.531s | LEC S2: 38.401s**<br>Leclerc dominates the twisting mid-lap. Ferrari's superior mechanical grip pulls 0.130s faster than the Red Bull, giving Charles the overall lap lead."
    elif dist < 3200:
        return "#### 🪝 The Hairpin (T13)\nLeclerc uses a slight V-style line, rotating the car instantly at the apex to get on the throttle earlier for the vital bridge crossing."
    elif dist < 4200:
        return "#### 💨 Sector 3 Sweepers\n**VER S3: 25.840s | LEC S3: 26.001s**<br>Verstappen begins his comeback. The Red Bull's aero balance shines through the high-speed Esplanade sweepers, keeping minimum speed extremely high."
    elif dist < 4800:
        return "#### 🎯 Turn 18 (The Decider)\nDown by a tenth, Verstappen carries incredible apex speed through T18. He gets to 100% throttle a fraction of a second earlier than Leclerc, erasing the Ferrari's advantage."
    else:
        return "#### 🏁 Finish Line\n**Pole Margin: 0.054s**<br>Leclerc's phenomenal Sector 2 wasn't quite enough. Verstappen's flawless bookend sectors snatched pole by a microscopic margin."

if 'dist' not in st.session_state:
    st.session_state.dist = 0.0
if 'playing' not in st.session_state:
    st.session_state.playing = False

c_head1, c_head2, c_head3 = st.columns([3.5, 1.5, 6])
with c_head1:
    st.markdown("### 2026 Singapore Quali: VER vs LEC")
with c_head2:
    if st.button("⏯️ Play / Pause", use_container_width=True):
        if st.session_state.dist >= track_length:
            st.session_state.dist = 0.0
        st.session_state.playing = not st.session_state.playing
with c_head3:
    selected_dist = st.slider("Distance", 0.0, track_length, float(st.session_state.dist), format="%.0fm", label_visibility="collapsed")
    st.markdown("""
        <div style="display: flex; justify-content: space-between; width: 100%; font-size: 0.75rem; color: #a1a1aa; padding: 0 5px; margin-top: -5px;">
            <span style="width: 30%;">Start (0m)</span>
            <span style="width: 36%;">Sector 1 (1500m)</span>
            <span style="width: 34%;">Sector 2 (3300m)</span>
            <span style="text-align: right;">Finish</span>
        </div>
    """, unsafe_allow_html=True)

if selected_dist != float(st.session_state.dist) and not st.session_state.playing:
    st.session_state.dist = selected_dist

idx = (np.abs(df['Distance'] - st.session_state.dist)).argmin()
row = df.iloc[idx]
current_dist = row['Distance']
st.divider()

col_track, col_comm, col_tel = st.columns([3.5, 2.5, 4])

with col_track:
    st.markdown("#### 📍 Position &nbsp;&nbsp; 🔵 **VER** &nbsp;|&nbsp; 🔴 **LEC**", unsafe_allow_html=True)
    fig_track = go.Figure()
    fig_track.add_trace(go.Scatter(x=df['VER_X'], y=df['VER_Y'], mode='lines', line=dict(color='rgba(255,255,255,0.1)', width=3), hoverinfo='none'))
    
    # PERFORMANCE FIX: Sub-sample history payload by factor of 6 to stop glitching
    df_hist = df[df['Distance'] <= current_dist].iloc[::6]
    if not df_hist.empty:
        trail_colors = np.where(df_hist['Delta'] < 0, VER_COLOR, LEC_COLOR)
        fig_track.add_trace(go.Scatter(x=df_hist['VER_X'], y=df_hist['VER_Y'], mode='markers', marker=dict(color=trail_colors, size=4), hoverinfo='none'))
    
    turn_marks = {
        300: "1", 370: "2", 450: "3", 800: "4", 900: "5", 1100: "6", 1550: "7", 
        1800: "8", 1900: "9", 2000: "10", 2100: "11", 2250: "12", 2950: "13", 
        3100: "14", 3600: "15", 4200: "16", 4300: "17", 4550: "18", 4700: "19"
    }
    t_x, t_y, t_text = [], [], []
    for d, t in turn_marks.items():
        if d < track_length:
            t_idx = (np.abs(df['Distance'] - d)).argmin()
            t_x.append(df['VER_X'].iloc[t_idx])
            t_y.append(df['VER_Y'].iloc[t_idx])
            t_text.append(t)
        
    fig_track.add_trace(go.Scatter(x=t_x, y=t_y, mode='text', text=t_text, textposition="middle center", textfont=dict(color="rgba(255,255,255,0.7)", size=10), showlegend=False))
    
    fig_track.add_trace(go.Scatter(x=[row['VER_X']], y=[row['VER_Y']], mode='markers', marker=dict(color=VER_COLOR, size=9, line=dict(color='white', width=1)), name='VER'))
    fig_track.add_trace(go.Scatter(x=[row['MAP_LEC_X']], y=[row['MAP_LEC_Y']], mode='markers', marker=dict(color=LEC_COLOR, size=9, line=dict(color='white', width=1)), name='LEC'))
    
    fig_track.update_layout(plot_bgcolor='rgb(14,17,23)', paper_bgcolor='rgb(14,17,23)', showlegend=False,
                            xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
                            margin=dict(l=0, r=0, t=0, b=5), height=230, uirevision='constant')
    st.plotly_chart(fig_track, use_container_width=True)

    zoom_radius = 250
    fig_zoom = go.Figure()
    fig_zoom.add_trace(go.Scatter(x=df['VER_X'], y=df['VER_Y'], mode='lines', line=dict(color='rgba(255,255,255,0.2)', width=5), hoverinfo='none'))
    
    if not df_hist.empty:
        fig_zoom.add_trace(go.Scatter(x=df_hist['VER_X'], y=df_hist['VER_Y'], mode='markers', marker=dict(color=trail_colors, size=6), hoverinfo='none'))

    fig_zoom.add_trace(go.Scatter(x=[row['VER_X']], y=[row['VER_Y']], mode='markers', marker=dict(color=VER_COLOR, size=14, line=dict(color='white', width=2)), name='VER'))
    fig_zoom.add_trace(go.Scatter(x=[row['MAP_LEC_X']], y=[row['MAP_LEC_Y']], mode='markers', marker=dict(color=LEC_COLOR, size=14, line=dict(color='white', width=2)), name='LEC'))
    
    fig_zoom.update_layout(plot_bgcolor='rgb(14,17,23)', paper_bgcolor='rgb(14,17,23)', showlegend=False,
                           xaxis=dict(visible=False, range=[row['VER_X'] - zoom_radius, row['VER_X'] + zoom_radius]), 
                           yaxis=dict(visible=False, range=[row['VER_Y'] - zoom_radius, row['VER_Y'] + zoom_radius]),
                           margin=dict(l=0, r=0, t=0, b=0), height=140,
                           title=dict(text="🔍 Pursuit Camera", font=dict(color="rgba(255,255,255,0.4)", size=11), y=0.9, x=0.02))
    st.plotly_chart(fig_zoom, use_container_width=True)

with col_comm:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(get_commentary(current_dist), unsafe_allow_html=True)

with col_tel:
    fig_speed = go.Figure()
    fig_speed.add_vrect(x0=0, x1=1500, fillcolor="white", opacity=0.02, layer="below", line_width=0)
    fig_speed.add_vrect(x0=1500, x1=3300, fillcolor="white", opacity=0.06, layer="below", line_width=0)
    fig_speed.add_vrect(x0=3300, x1=track_length, fillcolor="white", opacity=0.02, layer="below", line_width=0)
    
    fig_speed.add_annotation(x=750, y=0.05, yref="paper", text="S1", showarrow=False, font=dict(color="rgba(255,255,255,0.3)", size=12))
    fig_speed.add_annotation(x=2400, y=0.05, yref="paper", text="S2", showarrow=False, font=dict(color="rgba(255,255,255,0.3)", size=12))
    fig_speed.add_annotation(x=4100, y=0.05, yref="paper", text="S3", showarrow=False, font=dict(color="rgba(255,255,255,0.3)", size=12))

    fig_speed.add_trace(go.Scatter(x=df['Distance'], y=df['VER_Speed'], mode='lines', line=dict(color=VER_COLOR, width=2), name='VER'))
    fig_speed.add_trace(go.Scatter(x=df['Distance'], y=df['LEC_Speed'], mode='lines', line=dict(color=LEC_COLOR, width=2), name='LEC'))
    fig_speed.add_vline(x=current_dist, line_width=2, line_dash="dash", line_color="white")
    
    fig_speed.update_layout(plot_bgcolor='rgb(14,17,23)', paper_bgcolor='rgb(14,17,23)', font=dict(color='white'), hovermode="x unified",
                            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor='rgba(0,0,0,0)'),
                            xaxis=dict(title="Distance (m)", gridcolor='rgba(255,255,255,0.1)'), yaxis=dict(title="Speed (km/h)", gridcolor='rgba(255,255,255,0.1)'),
                            margin=dict(l=0, r=0, t=0, b=0), height=240, uirevision='constant')
    st.plotly_chart(fig_speed, use_container_width=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("VER Speed", f"{int(row['VER_Speed'])} km/h")
    m2.metric("LEC Speed", f"{int(row['LEC_Speed'])} km/h")
    m3.metric("Gap (VER - LEC)", f"{row['Delta']:+.3f}s", delta_color="inverse")

    m4, m5, m6 = st.columns(3)
    m4.metric("VER Live Time", fmt_time(row['VER_Time']))
    m5.metric("LEC Live Time", fmt_time(row['LEC_Time']))

if st.session_state.playing:
    time.sleep(0.05) 
    next_dist = st.session_state.dist + 20.0 
    if next_dist >= track_length:
        st.session_state.dist = track_length 
        st.session_state.playing = False 
    else:
        st.session_state.dist = next_dist
    st.rerun()
