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
    if dist < 750:
        return "#### Sector 1: The Launch & Turns 1-3\nVerstappen attacks the opening left-right-left sequence with maximum commitment. Red Bull's stable front end allows him to square off Turn 3 perfectly, prioritizing exit speed down the following straight to take an early micro-advantage."
    elif dist < 1500:
        return "#### Sector 1: Turns 4-6\nApproaching Turn 5, Leclerc leans heavily on the Ferrari's mechanical grip. He opens up the steering early, utilizing his power unit's aggressive low-end deployment to slowly start reeling in Verstappen as they cross the first sector timing line."
    elif dist < 2400:
        return "#### Sector 2: Memorial Corner (T7)\nThis is where the lap flips. Hurtling into the heavy braking zone of Turn 7, Leclerc brakes several meters later than the Red Bull. The Ferrari rotates sharply without locking the fronts, allowing Charles to level the overall lap time."
    elif dist < 3300:
        return "#### Sector 2: The Anderson Bridge Hairpin\nThrough the claustrophobic 90-degree street corners, Leclerc edges the lead. At the Turn 13 hairpin, he executes a pronounced V-style racing line - rotating the car instantly at the apex to get on the throttle earlier for the critical bridge crossing."
    elif dist < 4100:
        return "#### Sector 3: Esplanade\nVerstappen begins his comeback. The Red Bull's aerodynamic balance comes alive through the high-speed sequence of Turns 14 and 15. Max keeps a much flatter, more aggressive throttle trace, preserving crucial momentum."
    elif dist < 4800:
        return "#### Sector 3: The Turn 18 Decider\nStill trailing by a fraction, Verstappen produces a masterclass through the off-camber Turn 18. Carrying incredible apex speed, he manages to reach 100% throttle earlier than Leclerc, catapulting his car out of the corner."
    else:
        return "#### Finish Line: The 0.054s Margin\n**VER: 1:31.373 | LEC: 1:31.427**<br>Leclerc’s phenomenal middle sector wasn't quite enough. Verstappen secures the 2026 Singapore Grand Prix pole position with a 1:31.373, edging out Leclerc by a mere 0.054s[cite: 3, 4]."

if 'dist' not in st.session_state:
    st.session_state.dist = 0.0
if 'playing' not in st.session_state:
    st.session_state.playing = False

c_head1, c_head2, c_head3 = st.columns([3.5, 1.5, 6])
with c_head1:
    st.markdown("### 2026 Singapore Quali: VER vs LEC")
with c_head2:
    if st.button("Play / Pause", use_container_width=True):
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
    st.markdown("#### &nbsp;&nbsp; 🔵 **VER** &nbsp;|&nbsp; 🔴 **LEC**", unsafe_allow_html=True)
    fig_track = go.Figure()
    fig_track.add_trace(go.Scatter(x=df['VER_X'], y=df['VER_Y'], mode='lines', line=dict(color='rgba(255,255,255,0.1)', width=3), hoverinfo='none'))
    
    # PERFORMANCE FIX: Sub-sample history payload by factor of 6 to stop glitching
    df_hist = df[df['Distance'] <= current_dist].iloc[::6]
    if not df_hist.empty:
        trail_colors = np.where(df_hist['Delta'] < 0, VER_COLOR, LEC_COLOR)
        fig_track.add_trace(go.Scatter(x=df_hist['VER_X'], y=df_hist['VER_Y'], mode='markers', marker=dict(color=trail_colors, size=4), hoverinfo='none'))
    
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
                           title=dict(text="Pursuit Camera", font=dict(color="rgba(255,255,255,0.4)", size=11), y=0.9, x=0.02))
    st.plotly_chart(fig_zoom, use_container_width=True)

with col_comm:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(get_commentary(current_dist), unsafe_allow_html=True)
    
    gap_val = row['Delta']
    gap_color = VER_COLOR if gap_val < 0 else (LEC_COLOR if gap_val > 0 else "white")
    
    metrics_html = f"""
    <div style="margin-top: 25px; padding: 15px; background: rgba(255,255,255,0.03); border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
        <div style="display: flex; justify-content: space-around; margin-bottom: 15px; font-size: 1.4rem;">
            <div style="color: {VER_COLOR}; font-weight: bold;">VER: <span style="color: white; font-weight: normal;">{fmt_time(row['VER_Time'])}</span></div>
            <div style="color: {LEC_COLOR}; font-weight: bold;">LEC: <span style="color: white; font-weight: normal;">{fmt_time(row['LEC_Time'])}</span></div>
        </div>
        <div style="text-align: center;">
            <span style="font-size: 0.9rem; color: #a1a1aa; text-transform: uppercase; letter-spacing: 1px;">Gap (VER - LEC)</span><br>
            <span style="font-size: 2.2rem; font-weight: bold; color: {gap_color};">{gap_val:+.3f}s</span>
        </div>
    </div>
    """
    st.markdown(metrics_html, unsafe_allow_html=True)

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

    speed_html = f"""
    <div style="display: flex; justify-content: space-evenly; text-align: center; margin-top: 15px;">
        <div>
            <span style="font-size: 0.9rem; color: #a1a1aa; text-transform: uppercase; letter-spacing: 1px;">VER Speed</span><br>
            <span style="font-size: 1.8rem; font-weight: bold; color: {VER_COLOR};">{int(row['VER_Speed'])} <span style="font-size: 1.2rem; color: white;">km/h</span></span>
        </div>
        <div>
            <span style="font-size: 0.9rem; color: #a1a1aa; text-transform: uppercase; letter-spacing: 1px;">LEC Speed</span><br>
            <span style="font-size: 1.8rem; font-weight: bold; color: {LEC_COLOR};">{int(row['LEC_Speed'])} <span style="font-size: 1.2rem; color: white;">km/h</span></span>
        </div>
    </div>
    """
    st.markdown(speed_html, unsafe_allow_html=True)

if st.session_state.playing:
    time.sleep(0.05) 
    next_dist = st.session_state.dist + 20.0 
    if next_dist >= track_length:
        st.session_state.dist = track_length 
        st.session_state.playing = False 
    else:
        st.session_state.dist = next_dist
    st.rerun()
