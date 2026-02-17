import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ===============================
# 1. Налаштування сторінки
# ===============================
st.set_page_config(page_title="КАРТА РАДІАЦІЙНОЇ ОБСТАНОВКИ", layout="wide")

st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])

# ===============================
# 2. Функція Спеціального Маркера (SVG)
# ===============================
def get_custom_marker_html(label_text):
    """Створює рівнобедрений перевернутий трикутник з короткою ніжкою"""
    icon_html = f"""
    <div style="position: relative; display: flex; align-items: center; width: 300px;">
        <svg width="40" height="50" viewBox="0 0 40 50" xmlns="http://www.w3.org/2000/svg">
            <line x1="20" y1="35" x2="20" y2="45" stroke="blue" stroke-width="3" />
            <polygon points="2,5 38,5 20,35" fill="blue" stroke="white" stroke-width="1"/>
            <circle cx="20" cy="18" r="8" fill="yellow" />
            <circle cx="20" cy="18" r="1.5" fill="black" />
            <path d="M20,18 L17,13 A7,7 0 0,1 23,13 Z" fill="black" />
            <path d="M20,18 L24,22 A7,7 0 0,1 16,22 Z" fill="black" />
            <path d="M13,18 A7,7 0 0,1 15,13 L20,18 Z" fill="black" />
            <path d="M25,13 A7,7 0 0,1 27,18 L20,18 Z" fill="black" />
        </svg>
        <div style="
            margin-left: 5px;
            margin-top: -15px;
            color: blue; 
            font-family: sans-serif; 
            font-size: 11pt; 
            font-weight: bold; 
            white-space: nowrap;
            text-shadow: 2px 2px 3px white;">
            {label_text}
        </div>
    </div>
    """
    return icon_html

# ===============================
# 3. Інтерфейс (Управління)
# ===============================
st.header("📍 КАРТА РАДІАЦІЙНОЇ ОБСТАНОВКИ")

col_map, col_gui = st.columns([3, 1])

with col_gui:
    st.subheader("⚙️ Вхідні дані")
    
    # Завантаження файлу
    up_file = st.file_uploader("📁 CSV з пристрою", type=["csv"])
    if up_file:
        if st.button("Імпортувати дані", use_container_width=True):
            try:
                df_new = pd.read_csv(up_file, sep=None, engine='python')
                st.session_state.data = pd.concat([st.session_state.data, df_new], ignore_index=True)
                st.rerun()
            except: st.error("Помилка файлу")

    # Ручне додавання
    with st.expander("➕ Додати вручну"):
        l1 = st.number_input("Широта", format="%.6f", value=50.4501)
        l2 = st.number_input("Довгота", format="%.6f", value=30.5234)
        val = st.number_input("Значення", step=0.00001, format="%.5f")
        uni = st.selectbox("Одиниця", ["мкЗв/год", "мЗв/год"])
        tim = st.text_input("Дата/час", value=pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"))
        if st.button("Зберегти"):
            row = pd.DataFrame([{"lat": l1, "lon": l2, "value": val, "unit": uni, "time": tim}])
            st.session_state.data = pd.concat([st.session_state.data, row], ignore_index=True)
            st.rerun()

    st.divider()

    # Експорт тільки в HTML
    if not st.session_state.data.empty:
        st.subheader("💾 Збереження")
        
        d_c = st.session_state.data.copy()
        d_c['lat'] = pd.to_numeric(d_c['lat'], errors='coerce')
        d_c['lon'] = pd.to_numeric(d_c['lon'], errors='coerce')
        d_c = d_c.dropna(subset=['lat', 'lon'])
        
        if not d_c.empty:
            m_h = folium.Map(location=[d_c.lat.mean(), d_c.lon.mean()], zoom_start=10)
            for _, r in d_c.iterrows():
                v_s = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
                txt = f"{v_s} {r['unit']} | {r['time']}"
                folium.Marker([r.lat, r.lon], icon=folium.DivIcon(icon_anchor=(20, 45), html=get_custom_marker_html(txt))).add_to(m_h)
            
            st.download_button("🌐 Завантажити HTML карту", data=m_h._repr_html_(), file_name="radiation_map.html", mime="text/html", use_container_width=True)

    if st.button("🧹 Очистити карту", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.rerun()

# ===============================
# 4. Візуалізація Карти
# ===============================
with col_map:
    if st.session_state.data.empty:
        st.info("Додайте дані для відображення.")
    else:
        df = st.session_state.data.copy()
        for c in ['lat', 'lon', 'value']: df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna(subset=['lat', 'lon', 'value'])
        
        if not df.empty:
            m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=10)
            
            df['dt'] = pd.to_datetime(df['time'], dayfirst=True, errors='coerce')
            df['day'] = df['dt'].dt.strftime('%d.%m.%Y')
            df.loc[df['day'].isna(), 'day'] = "Дані"

            for d_v in sorted(df['day'].unique()):
                gp = folium.FeatureGroup(name=f"📅 {d_v}")
                for _, r in df[df['day'] == d_v].iterrows():
                    v_s = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
                    txt = f"{v_s} {r['unit']} | {r['time']}"
                    
                    folium.Marker(
                        [r.lat, r.lon],
                        icon=folium.DivIcon(
                            icon_anchor=(20, 45),
                            html=get_custom_marker_html(txt)
                        )
                    ).add_to(gp)
                gp.add_to(m)

            folium.LayerControl(collapsed=False).add_to(m)
            st_folium(m, width="100%", height=700, key="final_map_mobile")
