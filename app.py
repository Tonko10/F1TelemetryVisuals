import streamlit as st
import fastf1
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import time
import os

st.set_page_config(layout="wide", page_title="Singapore Quali 2026", page_icon="🏎️")

os.makedirs('f1_cache', exist_ok=True)
fastf1.Cache.enable_cache('f1_cache') 

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

    # TRUE GHOST CAR: Calculate Leclerc's distance at VER's live time 
    lec_dist_at_ver_time = np.interp(ver_time_sync, lec_time_sync, dist_arr)
    
    # Project Leclerc onto VER's GPS line to eliminate sensor drift illusions
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

def get_commentary(dist):
    if dist < 500:
        return "### The Start\nBoth drivers launch into Turn 1. Watch how they drag race down the pit straight."
    elif 1000 <= dist < 2000:
        return "### Sector 1: The Braking Zones\nLeclerc brakes slightly later into the heavy traction zones, trusting the front end of his Ferrari to rotate."
    elif 3000 <= dist < 4000:
        return "### Sector 2: The Twisty Stuff\nThrough the Marina Bay street circuit complexes, see how their speed traces cross as they take different racing lines."
    elif 4500 <= dist <= track_length - 50:
        return "### Turn 18: The 0.054s Decider\nVerstappen wins pole here. He carries ~4km/h more apex speed and gets on the throttle earlier, erasing Leclerc's advantage."
    else:
        return "### Finish Line\nLap completed."

if 'dist' not in st.session_state:
    st.session_state.dist = 0.0
if 'playing' not in st.session_state:
    st.session_state.playing = False

st.title("The 0.054s Margin: Verstappen vs Leclerc")

col_btn, col_slider = st.columns([1, 6])
with col_btn:
    st.write("")
    if st.button("⏯️ Play / Pause", use_container_width=True):
        if st.session_state.dist >= track_length:
            st.session_state.dist = 0.0
        st.session_state.playing = not st.session_state.playing

with col_slider:
    selected_dist = st.slider("Scrub Lap Distance", 0.0, track_length, float(st.session_state.dist), label_visibility="collapsed")

if selected_dist != float(st.session_state.dist) and not st.session_state.playing:
    st.session_state.dist = selected_dist

idx = (np.abs(df['Distance'] - st.session_state.dist)).argmin()
row = df.iloc[idx]
current_dist = row['Distance']

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Track Position")
    fig_track = go.Figure()
    
    fig_track.add_trace(go.Scatter(x=df['VER_X'], y=df['VER_Y'], 
                                   mode='lines', line=dict(color='rgba(255,255,255,0.2)', width=3), 
                                   hoverinfo='none'))
    
    fig_track.add_trace(go.Scatter(x=[row['VER_X']], y=[row['VER_Y']],
                                   mode='markers', marker=dict(color='#0600ef', size=7, line=dict(color='white', width=1)),
                                   name='Verstappen'))
    
    fig_track.add_trace(go.Scatter(x=[row['MAP_LEC_X']], y=[row['MAP_LEC_Y']],
                                   mode='markers', marker=dict(color='#dc0000', size=7, line=dict(color='white', width=1)),
                                   name='Leclerc'))
    
    fig_track.update_layout(plot_bgcolor='rgb(14,17,23)', paper_bgcolor='rgb(14,17,23)',
                            font=dict(color='white'), showlegend=True,
                            xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
                            margin=dict(l=0, r=0, t=30, b=0), height=500, uirevision='constant')
    
    st.plotly_chart(fig_track, use_container_width=True)

with col2:
    st.subheader("Speed Telemetry (km/h)")
    fig_speed = go.Figure()
    
    fig_speed.add_trace(go.Scatter(x=df['Distance'], y=df['VER_Speed'],
                                   mode='lines', line=dict(color='#0600ef', width=2), name='VER'))
    
    fig_speed.add_trace(go.Scatter(x=df['Distance'], y=df['LEC_Speed'],
                                   mode='lines', line=dict(color='#dc0000', width=2), name='LEC'))
    
    fig_speed.add_vline(x=current_dist, line_width=2, line_dash="dash", line_color="white")
    
    fig_speed.update_layout(plot_bgcolor='rgb(14,17,23)', paper_bgcolor='rgb(14,17,23)',
                            font=dict(color='white'), hovermode="x unified",
                            xaxis=dict(title="Distance (m)", gridcolor='rgba(255,255,255,0.1)'),
                            yaxis=dict(title="Speed (km/h)", gridcolor='rgba(255,255,255,0.1)'),
                            margin=dict(l=0, r=0, t=30, b=0), height=300, uirevision='constant')
    
    st.plotly_chart(fig_speed, use_container_width=True)

    st.markdown("### Metrics")
    c1, c2, c3 = st.columns(3)
    c1.metric("VER Speed", f"{int(row['VER_Speed'])} km/h")
    c2.metric("LEC Speed", f"{int(row['LEC_Speed'])} km/h")
    c3.metric("Gap (VER - LEC)", f"{row['Delta']:+.3f}s", delta_color="inverse")

    c4, c5, c6 = st.columns(3)
    c4.metric("VER Live Time", f"{row['VER_Time']:.3f}s")
    c5.metric("LEC Live Time", f"{row['LEC_Time']:.3f}s")

st.markdown(get_commentary(current_dist))

if current_dist >= track_length - 0.1:
    st.success("🏁 **Lap Summary:** While Leclerc was faster through the heavy braking zones of Sectors 1 and 2, Verstappen's execution of Turn 18 was decisive. Carrying roughly 4km/h more speed through the apex allowed Max to get to 100% throttle earlier. Down the final straight, that momentum translated directly into the 54 thousandths of a second that secured pole position.")

if st.session_state.playing:
    time.sleep(0.05) 
    next_dist = st.session_state.dist + 20.0 
    if next_dist >= track_length:
        st.session_state.dist = track_length 
        st.session_state.playing = False 
    else:
        st.session_state.dist = next_dist
    st.rerun()
