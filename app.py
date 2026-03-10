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
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
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
    st.subheader("⚙️ Вхідні дані")
    
    # Завантаження файлу
    up_file = st.file_uploader("📁 CSV з пристрою", type=["csv"])
    if up_file:
        if st.button("Імпортувати дані", use_container_width=True):
            try:
                df_new = pd.read_csv(up_file, sep=None, engine='python')
                # Форматуємо час при імпорті (тільки дата)
                if 'time' in df_new.columns:
                    df_new['time'] = pd.to_datetime(df_new['time'], dayfirst=True, errors='coerce').dt.strftime('%d.%m.%Y')
                st.session_state.data = pd.concat([st.session_state.data, df_new], ignore_index=True)
                st.success("Дані успішно додано!")
                st.rerun()
            except Exception as e:
                st.error(f"Помилка файлу: {e}")

    # Ручне додавання
    with st.expander("➕ Додати вручну"):
        l1 = st.number_input("Широта", format="%.6f", value=50.4501)
        l2 = st.number_input("Довгота", format="%.6f", value=30.5234)
        val = st.number_input("Значення", step=0.00001, format="%.5f")
        uni = st.selectbox("Одиниця", ["мкЗв/год", "мЗв/год"])
        # Тільки дата без годин/хвилин
        tim = st.date_input("Дата", value=datetime.now()).strftime("%d.%m.%Y")
        
        if st.button("Зберегти точку"):
            row = pd.DataFrame([{"lat": l1, "lon": l2, "value": val, "unit": uni, "time": tim}])
            st.session_state.data = pd.concat([st.session_state.data, row], ignore_index=True)
            st.rerun()

    st.divider()

    # Експорт в HTML
    if not st.session_state.data.empty:
        st.subheader("💾 Збереження")
        d_c = st.session_state.data.copy()
        d_c['lat'] = pd.to_numeric(d_c['lat'], errors='coerce')
        d_c['lon'] = pd.to_numeric(d_c['lon'], errors='coerce')
        d_c = d_c.dropna(subset=['lat', 'lon'])
        
        if not d_c.empty:
            m_export = folium.Map(location=[d_c.lat.mean(), d_c.lon.mean()], zoom_start=10)
            for _, r in d_c.iterrows():
                v_s = f"{float(r['value']):.3f}".rstrip('0').rstrip('.')
                val_txt = f"{v_s} {r['unit']}"
                date_txt = str(r['time'])
                
                folium.Marker(
                    [r.lat, r.lon],
                    icon=folium.DivIcon(
                        icon_anchor=(5, 12),
                        html=get_custom_marker_html(val_txt, date_txt)
                    )
                ).add_to(m_export)
            
            st.download_button("🌐 Завантажити HTML карту", data=m_export._repr_html_(), file_name="radiation_map.html", mime="text/html", use_container_width=True)

    if st.button("🧹 Очистити карту", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.rerun()

# ===============================
# 4. Візуалізація Карти
# ===============================
with col_map:
    if st.session_state.data.empty:
        st.info("Використовуйте панель праворуч для додавання даних.")
        # Порожня карта для візуалу
        folium.Map(location=[50.45, 30.52], zoom_start=6)
    else:
        df = st.session_state.data.copy()
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna(subset=['lat', 'lon', 'value'])
        
        if not df.empty:
            m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=10)
            
            # Групування по днях для шарів
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
            st_folium(m, width="100%", height=750, key="rad_map_blue_dots")
