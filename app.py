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
</style>
""", unsafe_allow_html=True)

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])

# ===============================
# 2. Функція Синьої Крапки з підписом
# ===============================
def get_custom_marker_html(value_text, date_text):
    icon_html = f"""
    <div style="position: relative; display: flex; align-items: center; width: 220px;">
        <div style="
            width: 10px; 
            height: 10px; 
            background-color: blue; 
            border-radius: 50%; 
            border: 1px solid white;
            flex-shrink: 0;">
        </div>
        <div style="
            margin-left: 8px;
            color: blue; 
            font-family: 'Segoe UI', Tahoma, sans-serif; 
            font-size: 10pt; 
            font-weight: bold; 
            line-height: 1.2;
            white-space: nowrap;
            text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white;">
            <div>{value_text}</div>
            <div style="border-top: 1px solid blue; margin: 1px 0;"></div>
            <div>{date_text}</div>
        </div>
    </div>
    """
    return icon_html

# Функція для створення карти (використовується і для екрану, і для експорту)
def create_map(df_data, start_lat, start_lon, zoom_val):
    m = folium.Map(location=[start_lat, start_lon], zoom_start=zoom_val, tiles=None, control_scale=True)
    
    # Додавання шарів
    folium.TileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', name='Схема (OSM)', attr='OpenStreetMap').add_to(m)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', name='Супутник (Гібрид)', attr='Google').add_to(m)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}', name='Рельєф', attr='Google').add_to(m)

    if not df_data.empty:
        df = df_data.copy()
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna(subset=['lat', 'lon', 'value'])

        for day_val in sorted(df['time'].unique(), reverse=True):
            gp = folium.FeatureGroup(name=f"📅 {day_val}")
            for _, r in df[df['time'] == day_val].iterrows():
                v_s = f"{float(r['value']):.3f}".rstrip('0').rstrip('.')
                val_label = f"{v_s} {r['unit']}"
                date_label = str(r['time'])
                
                folium.Marker(
                    [r.lat, r.lon],
                    icon=folium.DivIcon(
                        icon_anchor=(5, 12),
                        html=get_custom_marker_html(val_label, date_label)
                    )
                ).add_to(gp)
            gp.add_to(m)
    
    folium.LayerControl(collapsed=False).add_to(m)
    return m

# ===============================
# 3. Інтерфейс (Управління)
# ===============================
st.header("☢️ КАРТА РАДІАЦІЙНОЇ ОБСТАНОВКИ")

col_map, col_gui = st.columns([4, 1])

with col_gui:
    st.subheader("⚙️ Управління")
    
    up_file = st.file_uploader("📁 CSV файл", type=["csv"])
    if up_file:
        if st.button("Імпортувати дані", use_container_width=True):
            try:
                df_new = pd.read_csv(up_file, sep=None, engine='python')
                if 'time' in df_new.columns:
                    df_new['time'] = pd.to_datetime(df_new['time'], dayfirst=True, errors='coerce').dt.strftime('%d.%m.%Y')
                st.session_state.data = pd.concat([st.session_state.data, df_new], ignore_index=True)
                st.success("Дані додано!")
                st.rerun()
            except Exception as e:
                st.error(f"Помилка: {e}")

    with st.expander("➕ Додати точку вручну"):
        l1 = st.number_input("Широта", format="%.6f", value=50.4501)
        l2 = st.number_input("Довгота", format="%.6f", value=30.5234)
        val = st.number_input("Значення", step=0.001, format="%.3f")
        uni = st.selectbox("Одиниця", ["мкЗв/год", "мЗв/год"])
        tim = st.date_input("Дата", value=datetime.now()).strftime("%d.%m.%Y")
        
        if st.button("Додати на карту"):
            row = pd.DataFrame([{"lat": l1, "lon": l2, "value": val, "unit": uni, "time": tim}])
            st.session_state.data = pd.concat([st.session_state.data, row], ignore_index=True)
            st.rerun()

    st.divider()

    # --- ПОВЕРНЕНИЙ БЛОК ЗБЕРЕЖЕННЯ ТА ОЧИЩЕННЯ ---
    if not st.session_state.data.empty:
        st.subheader("💾 Збереження")
        
        # Визначаємо параметри для експортної карти
        df_exp = st.session_state.data.copy()
        df_exp['lat'] = pd.to_numeric(df_exp['lat'], errors='coerce')
        df_exp['lon'] = pd.to_numeric(df_exp['lon'], errors='coerce')
        df_exp = df_exp.dropna(subset=['lat', 'lon'])
        
        if not df_exp.empty:
            e_lat, e_lon, e_zoom = df_exp.lat.mean(), df_exp.lon.mean(), 9
            # Створюємо об'єкт карти для експорту
            m_export = create_map(st.session_state.data, e_lat, e_lon, e_zoom)
            
            st.download_button(
                "🌐 Завантажити HTML карту", 
                data=m_export._repr_html_(), 
                file_name=f"radiation_map_{datetime.now().strftime('%Y%m%d')}.html", 
                mime="text/html", 
                use_container_width=True
            )

        if st.button("🧹 Очистити карту", use_container_width=True):
            st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
            st.rerun()

# ===============================
# 4. Візуалізація Карти
# ===============================
with col_map:
    if st.session_state.data.empty:
        s_lat, s_lon, s_zoom = 49.0, 31.0, 6
    else:
        df_c = st.session_state.data.copy()
        df_c['lat'] = pd.to_numeric(df_c['lat'], errors='coerce')
        df_c['lon'] = pd.to_numeric(df_c['lon'], errors='coerce')
        df_c = df_c.dropna(subset=['lat', 'lon'])
        s_lat, s_lon, s_zoom = (df_c.lat.mean(), df_c.lon.mean(), 9) if not df_c.empty else (49.0, 31.0, 6)

    # Виклик функції створення карти
    final_map = create_map(st.session_state.data, s_lat, s_lon, s_zoom)
    
    st_folium(final_map, width="100%", height=750, key="rad_map_final_v3")
