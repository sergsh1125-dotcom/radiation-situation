import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime

# ===============================
# 1. Налаштування сторінки
# ===============================
st.set_page_config(page_title="КАРТА РАДІАЦІЙНОЇ ОБСТАНОВКИ", page_icon="☢️", layout="wide")
st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
.stButton button {font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# ===============================
# 2. Стан програми
# ===============================
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
if "clicked_coords" not in st.session_state:
    st.session_state.clicked_coords = None

# ===============================
# 3. Підпис маркеру
# ===============================
def get_custom_marker_html(value_text, date_text):
    return f"""
<div style="display: inline-block; font-family: Arial; font-size: 10pt; color: blue; font-weight: bold; text-align: center;
            background-color: transparent; text-shadow: -1px -1px 0 #fff,1px -1px 0 #fff,-1px 1px 0 #fff,1px 1px 0 #fff,2px 2px 3px rgba(255,255,255,0.8);">
    <div style="white-space: nowrap; border-bottom: 2px solid blue; padding-bottom: 2px; margin-bottom: 2px;">
        {value_text}
    </div>
    <div style="font-weight: normal;">{date_text}</div>
</div>
"""

# ===============================
# 4. Створення карти
# ===============================
def create_map(df_data, start_lat, start_lon, zoom_val):
    m = folium.Map(location=[start_lat, start_lon], zoom_start=zoom_val, tiles=None, control_scale=True)
    folium.TileLayer('OpenStreetMap', name='Стандартна карта', show=True).add_to(m)
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google Satellite', name='Супутник', show=False
    ).add_to(m)

    if st.session_state.clicked_coords:
        folium.Marker(
            [st.session_state.clicked_coords['lat'], st.session_state.clicked_coords['lng']],
            icon=folium.Icon(color="red")
        ).add_to(m)

    if not df_data.empty:
        for day_val in sorted(df_data['time'].unique(), reverse=True):
            group = folium.FeatureGroup(name=f"📅 {day_val}")
            for _, r in df_data[df_data['time'] == day_val].iterrows():
                val_label = f"{float(r['value']):.2f} {r['unit']}"
                date_label = str(r['time'])
                folium.CircleMarker([r.lat, r.lon], radius=6, color="blue", fill=True).add_to(group)
                folium.Marker(
                    [r.lat, r.lon],
                    icon=folium.DivIcon(
                        icon_anchor=(70, 45),
                        html=get_custom_marker_html(val_label, date_label)
                    )
                ).add_to(group)
            group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m

# ===============================
# 5. Інтерфейс ПУЛЬТУ УПРАВЛІННЯ
# ===============================
st.header("☢️ КАРТА РАДІАЦІЙНОЇ ОБСТАНОВКИ")
col_map, col_gui = st.columns([3, 1])

with col_gui:
    st.subheader("ПУЛЬТ УПРАВЛІННЯ")

    # Координати кліку та кнопки
    if st.session_state.clicked_coords:
        c_lat, c_lon = st.session_state.clicked_coords['lat'], st.session_state.clicked_coords['lng']
        st.write(f"Вибрано: {c_lat:.6f}, {c_lon:.6f}")
        row1, row2 = st.columns(2)
        if row1.button("Вставити координати у форму", use_container_width=True):
            st.session_state.manual_lat, st.session_state.manual_lon = c_lat, c_lon
            st.rerun()
        if row2.button("Виключити маркер на карті", use_container_width=True):
            st.session_state.clicked_coords = None
            st.rerun()

    st.divider()
    st.markdown("### НАНЕСЕННЯ ТОЧКИ ВИМІРЮВАННЯ ВРУЧНУ")
    l1 = st.number_input("Широта", format="%.6f", value=st.session_state.get('manual_lat', 50.4501))
    l2 = st.number_input("Довгота", format="%.6f", value=st.session_state.get('manual_lon', 30.5234))
    val = st.number_input("Значення", step=0.01, format="%.2f")
    uni = st.selectbox("Одиниця", ["мкЗв/год", "мЗв/год"])
    tim = st.date_input("Дата", value=datetime.now()).strftime("%d.%m.%Y")

    if st.button("Нанести на карту", use_container_width=True):
        new_row = pd.DataFrame([{"lat": l1, "lon": l2, "value": val, "unit": uni, "time": tim}])
        st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
        st.rerun()

    st.divider()
    st.markdown("### НАНЕСЕННЯ ТОЧОК ВИМІРЮВАННЯ З ТАБЛИЦІ")
    uploaded_file = st.file_uploader("Виберіть CSV", type=["csv"], label_visibility="collapsed")
    if uploaded_file and st.button("Імпортувати з файлу", use_container_width=True):
        try:
            df_new = pd.read_csv(uploaded_file)
            if 'time' in df_new.columns:
                df_new['time'] = pd.to_datetime(df_new['time'], dayfirst=True, errors='coerce').dt.strftime('%d.%m.%Y')
            st.session_state.data = pd.concat([st.session_state.data, df_new], ignore_index=True)
            st.rerun()
        except Exception as e:
            st.error(f"Помилка файлу: {e}")

# ===============================
# 6. Візуалізація карти
# ===============================
with col_map:
    if st.session_state.data.empty:
        s_lat, s_lon, s_zoom = 49.0, 31.0, 6
    else:
        df_c = st.session_state.data.copy()
        df_c = df_c.dropna(subset=['lat','lon'])
        s_lat, s_lon = df_c.lat.mean(), df_c.lon.mean()
        s_zoom = 9

    m = create_map(st.session_state.data, s_lat, s_lon, s_zoom)
    map_output = st_folium(m, width="100%", height=750, key="rad_map_mobile", returned_objects=[])

    # Кліки та дотики на карті
    if map_output.get("last_clicked") and st.session_state.clicked_coords != map_output["last_clicked"]:
        st.session_state.clicked_coords = map_output["last_clicked"]
        st.rerun()

    # Кнопка очистки карти
    if st.button("Очистити карту", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.session_state.clicked_coords = None
        st.rerun()

    # Таблиця під картою
    if not st.session_state.data.empty:
        st.subheader("Список нанесених точок вимірювання")
        st.dataframe(
            st.session_state.data[['lat','lon','value','unit','time']].rename(columns={
                'lat':'Широта', 'lon':'Довгота', 'value':'Значення', 'unit':'Одиниця', 'time':'Дата'
            }),
            use_container_width=True
        )
