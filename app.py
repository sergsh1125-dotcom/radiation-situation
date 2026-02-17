import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ===============================
# 1. Налаштування та Стилі Друкy
# ===============================
st.set_page_config(page_title="Radiation Map Clean PDF", layout="wide")

# CSS для приховування інтерфейсу під час друку
st.markdown("""
<style>
/* Ховаємо меню, футер та заголовок Streamlit */
#MainMenu, footer, header {visibility: hidden;}

/* Налаштування для друку */
@media print {
    /* Ховаємо праву колонку з кнопками та всі віджети Streamlit */
    [data-testid="stSidebar"], 
    [data-testid="stVerticalBlock"] > div:nth-child(2),
    .stButton, .stMarkdown, .stFileUploader, .stExpander {
        display: none !important;
    }
    
    /* Розтягуємо карту на весь екран при друці */
    [data-testid="stHorizontalBlock"] {
        display: block !important;
    }
    [data-testid="column"]:first-child {
        width: 100% !important;
        flex: none !important;
    }
}
</style>
""", unsafe_allow_html=True)

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])

# ===============================
# 2. Інтерфейс (Управління)
# ===============================
st.title("🔵 Моніторинг радіаційної обстановки")

col_map, col_gui = st.columns([3, 1])

with col_gui:
    st.subheader("⚙️ Вхідні дані")
    
    # Завантаження файлу
    uploaded_file = st.file_uploader("📁 Завантажити CSV", type=["csv"])
    if uploaded_file:
        if st.button("Імпортувати дані", use_container_width=True):
            try:
                df_up = pd.read_csv(uploaded_file, sep=None, engine='python')
                st.session_state.data = pd.concat([st.session_state.data, df_up], ignore_index=True)
                st.rerun()
            except: st.error("Помилка формату")

    # Ручне додавання
    with st.expander("➕ Додати точку вручну"):
        lat_in = st.number_input("Широта", format="%.6f", value=50.4501)
        lon_in = st.number_input("Довгота", format="%.6f", value=30.5234)
        val_in = st.number_input("Потужність", step=0.00001, format="%.5f")
        unit_in = st.selectbox("Одиниця", ["мкЗв/год", "мЗв/год"])
        time_in = st.text_input("Час", value=pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"))
        if st.button("Зберегти точку"):
            new_row = pd.DataFrame([{"lat": lat_in, "lon": lon_in, "value": val_in, "unit": unit_in, "time": time_in}])
            st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
            st.rerun()

    st.divider()

    # --- ЕКСПОРТ ---
    if not st.session_state.data.empty:
        st.subheader("💾 Експорт")
        
        # HTML Експорт
        df_c = st.session_state.data.copy()
        df_c['lat'] = pd.to_numeric(df_c['lat'], errors='coerce')
        df_c['lon'] = pd.to_numeric(df_c['lon'], errors='coerce')
        df_c = df_c.dropna(subset=['lat', 'lon'])
        
        m_save = folium.Map(location=[df_c.lat.mean(), df_c.lon.mean()], zoom_start=10)
        for _, r in df_c.iterrows():
            val = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
            folium.Marker([r.lat, r.lon], icon=folium.DivIcon(html=f'<div style="color:blue; font-weight:bold; white-space:nowrap;">{val} {r["unit"]}</div>')).add_to(m_save)
            folium.CircleMarker([r.lat, r.lon], radius=7, color="blue", fill=True).add_to(m_save)
        
        st.download_button("🌐 Завантажити HTML карту", data=m_save._repr_html_(), file_name="map.html", mime="text/html", use_container_width=True)

        # PDF Експорт (window.print)
        if st.button("📄 Завантажити PDF карту", use_container_width=True):
            st.components.v1.html("<script>window.parent.print();</script>", height=0)
            st.info("💡 У вікні друку оберіть 'Зберегти як PDF' та 'Альбомна орієнтація'")

    if st.button("🧹 Очистити карту", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.rerun()

# ===============================
# 3. Карта
# ===============================
with col_map:
    if st.session_state.data.empty:
        st.info("Завантажте дані для активації карти.")
    else:
        df = st.session_state.data.copy()
        for c in ['lat', 'lon', 'value']: df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna(subset=['lat', 'lon', 'value'])
        
        if not df.empty:
            m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=10)
            
            # Логіка шарів по датах
            df['dt'] = pd.to_datetime(df['time'], dayfirst=True, errors='coerce')
            df['day'] = df['dt'].dt.strftime('%d.%m.%Y')
            df.loc[df['day'].isna(), 'day'] = "Дані"

            for day_val in sorted(df['day'].unique()):
                group = folium.FeatureGroup(name=f"📅 {day_val}")
                for _, r in df[df['day'] == day_val].iterrows():
                    v_str = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
                    txt = f"{v_str} {r['unit']} | {r['time']}"
                    folium.Marker([r.lat, r.lon], icon=folium.DivIcon(icon_anchor=(-15, 7), 
                        html=f'<div style="color:blue; font-family:sans-serif; font-size:11pt; font-weight:bold; white-space:nowrap;">{txt}</div>')).add_to(group)
                    folium.CircleMarker([r.lat, r.lon], radius=7, color="blue", fill=True, fill_opacity=0.6).add_to(group)
                group.add_to(m)

            folium.LayerControl(collapsed=False).add_to(m)
            st_folium(m, width=1200, height=800, key="blue_final_print")
