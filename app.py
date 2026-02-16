import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ===============================
# 1. Налаштування сторінки
# ===============================
st.set_page_config(page_title="Radiation Map Cloud", layout="wide")

st.markdown("<style>#MainMenu, footer, header {visibility: hidden;}</style>", unsafe_allow_html=True)

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])

# ===============================
# 2. Інтерфейс
# ===============================
st.title("☢️ Радіаційна обстановка (Cloud Ready)")

col_map, col_gui = st.columns([2.8, 1])

with col_gui:
    st.subheader("⚙️ Управління")

    # Ручне введення
    with st.expander("➕ Додати вручну"):
        lat = st.number_input("Широта", format="%.6f", value=50.4501)
        lon = st.number_input("Довгота", format="%.6f", value=30.5234)
        val = st.number_input("Потужність", step=0.00001, format="%.5f")
        unit = st.selectbox("Од.", ["мкЗв/год", "мЗв/год"])
        tm = st.text_input("Дата/Час", placeholder="16.02.2026")
        if st.button("Додати"):
            new = pd.DataFrame([{"lat": lat, "lon": lon, "value": val, "unit": unit, "time": tm}])
            st.session_state.data = pd.concat([st.session_state.data, new], ignore_index=True)
            st.rerun()

    st.divider()

    # Завантаження з Google Drive або посилання
    st.markdown("### 🔗 Посилання на Google Drive")
    url_input = st.text_input("Вставте посилання на CSV файл", placeholder="https://drive.google.com/...")
    if st.button("📥 Завантажити з хмари", use_container_width=True):
        if url_input:
            try:
                if 'drive.google.com' in url_input:
                    # Витягуємо ID файлу
                    if '/d/' in url_input:
                        file_id = url_input.split('/d/')[1].split('/')[0]
                    elif 'id=' in url_input:
                        file_id = url_input.split('id=')[1].split('&')[0]
                    else:
                        file_id = url_input
                    link = f'https://drive.google.com/uc?export=download&id={file_id}'
                else:
                    link = url_input
                
                cloud_df = pd.read_csv(link)
                st.session_state.data = pd.concat([st.session_state.data, cloud_df], ignore_index=True)
                st.success("Дані завантажено!")
                st.rerun()
            except:
                st.error("Доступ заборонено або посилання невірне")

    st.divider()

    # Звичайне завантаження
    uploaded = st.file_uploader("Або виберіть локальний CSV", type=["csv"])
    if uploaded:
        file_df = pd.read_csv(uploaded)
        if st.button("➕ Об'єднати з поточними"):
            st.session_state.data = pd.concat([st.session_state.data, file_df], ignore_index=True)
            st.rerun()

    if st.button("🧹 Очистити карту", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.rerun()

# ===============================
# 3. Карта
# ===============================
with col_map:
    if st.session_state.data.empty:
        st.info("Додайте дані для відображення.")
    else:
        df = st.session_state.data.copy()
        for c in ['lat', 'lon', 'value']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna(subset=['lat', 'lon', 'value'])
        
        df['time_dt'] = pd.to_datetime(df['time'], dayfirst=True, errors='coerce')
        df['day'] = df['time_dt'].dt.strftime('%d.%m.%Y')
        df.loc[df['day'].isna(), 'day'] = "Вказана дата"

        m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=10)
        
        for d in sorted(df['day'].unique()):
            layer = folium.FeatureGroup(name=f"📅 {d}")
            for _, r in df[df['day'] == d].iterrows():
                val_c = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
                txt = f"{val_c} {r['unit']} | {r['time']}"
                folium.Marker([r.lat, r.lon], icon=folium.DivIcon(html=f'<div style="color:red; font-weight:bold; white-space:nowrap;">{txt}</div>')).add_to(layer)
                folium.CircleMarker([r.lat, r.lon], radius=7, color="red", fill=True).add_to(layer)
            layer.add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)
        st_folium(m, width="100%", height=700)
