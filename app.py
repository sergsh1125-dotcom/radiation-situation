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
    """Створює синю крапку та синій дворядковий напис з лінією"""
    icon_html = f"""
    <div style="position: relative; display: flex; align-items: center; width: 200px;">
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
            white-space: nowrap;">
            <div>{value_text}</div>
            <div style="border-top: 1px solid blue; margin: 1px 0;"></div>
            <div>{date_text}</div>
        </div>
    </div>
    """
    return icon_html

# ===============================
# 3. Інтерфейс (Управління)
# ===============================
st.header("☢️ КАРТА РАДІАЦІЙНОЇ ОБСТАНОВКИ")

col_map, col_gui = st.columns([4, 1])

with col_gui:
    st.subheader("⚙️ Управління")
    
    # Завантаження файлу
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

    # Ручне додавання
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

    # --- БЛОК ЕКСПОРТУ ТА ОЧИЩЕННЯ ---
    if not st.session_state.data.empty:
        st.subheader("💾 Збереження")
        
        # Підготовка даних для HTML-файлу
        d_export = st.session_state.data.copy()
        d_export['lat'] = pd.to_numeric(d_export['lat'], errors='coerce')
        d_export['lon'] = pd.to_numeric(d_export['lon'], errors='coerce')
        d_export = d_export.dropna(subset=['lat', 'lon'])
        
        if not d_export.empty:
            m_html = folium.Map(location=[d_export.lat.mean(), d_export.lon.mean()], zoom_start=10)
            for _, r in d_export.iterrows():
                v_s = f"{float(r['value']):.3f}".rstrip('0').rstrip('.')
                val_txt = f"{v_s} {r['unit']}"
                date_txt = str(r['time'])
                folium.Marker(
                    [r.lat, r.lon],
                    icon=folium.DivIcon(
                        icon_anchor=(5, 12),
                        html=get_custom_marker_html(val_txt, date_txt)
                    )
                ).add_to(m_html)
            
            # Кнопка завантаження
            st.download_button(
                "🌐 Завантажити HTML карту", 
                data=m_html._repr_html_(), 
                file_name="radiation_map.html", 
                mime="text/html", 
                use_container_width=True
            )

        # Кнопка очищення
        if st.button("🧹 Очистити карту", use_container_width=True):
            st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
            st.rerun()

# ===============================
# 4. Візуалізація Карти
# ===============================
with col_map:
    # Визначаємо центр карти
    if st.session_state.data.empty:
        start_lat, start_lon, zoom = 49.0, 31.0, 6
    else:
        df_clean = st.session_state.data.copy()
        df_clean['lat'] = pd.to_numeric(df_clean['lat'], errors='coerce')
        df_clean['lon'] = pd.to_numeric(df_clean['lon'], errors='coerce')
        df_clean = df_clean.dropna(subset=['lat', 'lon'])
        if not df_clean.empty:
            start_lat, start_lon, zoom = df_clean.lat.mean(), df_clean.lon.mean(), 9
        else:
            start_lat, start_lon, zoom = 49.0, 31.0, 6

    m = folium.Map(location=[start_lat, start_lon], zoom_start=zoom, control_scale=True)

    if not st.session_state.data.empty:
        df = st.session_state.data.copy()
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

    st_folium(m, width="100%", height=750, key="main_radiation_map")
