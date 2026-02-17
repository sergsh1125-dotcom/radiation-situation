import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import io

# ===============================
# 1. Налаштування сторінки
# ===============================
st.set_page_config(page_title="Radiation Map Blue", layout="wide")

# Приховуємо зайві елементи інтерфейсу Streamlit
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
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
    
    # --- МЕТОД 1: ЗАВАНТАЖЕННЯ ФАЙЛУ (ПК/ТЕЛЕФОН) ---
    uploaded_file = st.file_uploader("📁 Завантажити CSV-файл", type=["csv"])
    if uploaded_file:
        if st.button("Імпортувати дані з файлу", use_container_width=True):
            try:
                df_up = pd.read_csv(uploaded_file, sep=None, engine='python')
                st.session_state.data = pd.concat([st.session_state.data, df_up], ignore_index=True)
                st.rerun()
            except Exception as e:
                st.error("Помилка: перевірте формат CSV")

    # --- МЕТОД 2: РУЧНЕ ВВЕДЕННЯ ---
    with st.expander("➕ Додати точку вручну"):
        lat_in = st.number_input("Широта", format="%.6f", value=50.4501)
        lon_in = st.number_input("Довгота", format="%.6f", value=30.5234)
        val_in = st.number_input("Потужність", step=0.00001, format="%.5f")
        unit_in = st.selectbox("Одиниця", ["мкЗв/год", "мЗв/год"])
        time_in = st.text_input("Час", value=pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"))
        if st.button("Зберегти"):
            new_row = pd.DataFrame([{"lat": lat_in, "lon": lon_in, "value": val_in, "unit": unit_in, "time": time_in}])
            st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
            st.rerun()

    st.divider()

    # --- ЕКСПОРТ ---
    if not st.session_state.data.empty:
        st.subheader("💾 Експорт карти")
        
        # 1. Кнопка HTML
        # Ми створюємо карту заздалегідь для збереження
        tmp_df = st.session_state.data.copy()
        tmp_df['lat'] = pd.to_numeric(tmp_df['lat'], errors='coerce')
        tmp_df['lon'] = pd.to_numeric(tmp_df['lon'], errors='coerce')
        tmp_df = tmp_df.dropna(subset=['lat', 'lon'])
        
        if not tmp_df.empty:
            m_save = folium.Map(location=[tmp_df.lat.mean(), tmp_df.lon.mean()], zoom_start=10)
            for _, r in tmp_df.iterrows():
                val_txt = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
                label = f"{val_txt} {r['unit']} | {r['time']}"
                folium.Marker([r.lat, r.lon], icon=folium.DivIcon(html=f'<div style="color:blue; font-weight:bold; white-space:nowrap;">{label}</div>')).add_to(m_save)
                folium.CircleMarker([r.lat, r.lon], radius=7, color="blue", fill=True).add_to(m_save)
            
            html_data = m_save._repr_html_()
            st.download_button(
                label="🌐 Завантажити карту в HTML",
                data=html_data,
                file_name="radiation_map.html",
                mime="text/html",
                use_container_width=True
            )

            # 2. Кнопка PDF (Через вікно друку браузера)
            if st.button("📄 Завантажити карту в PDF", use_container_width=True):
                st.components.v1.html("""
                    <script>
                        var mapElement = window.parent.document.querySelector('.stExpander');
                        window.parent.print();
                    </script>
                """, height=0)
                st.info("У вікні, що відкрилося, оберіть 'Зберегти як PDF'")

    if st.button("🧹 Очистити карту", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.rerun()

# ===============================
# 3. Візуалізація карти (Синя тема)
# ===============================
with col_map:
    if st.session_state.data.empty:
        st.info("Завантажте файл або додайте точки вручну для перегляду карти.")
    else:
        df = st.session_state.data.copy()
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna(subset=['lat', 'lon', 'value'])
        
        if not df.empty:
            df['dt'] = pd.to_datetime(df['time'], dayfirst=True, errors='coerce')
            df['day'] = df['dt'].dt.strftime('%d.%m.%Y')
            df.loc[df['day'].isna(), 'day'] = "Дані"

            m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=10)
            
            for d_val in sorted(df['day'].unique()):
                group = folium.FeatureGroup(name=f"📅 {d_val}")
                for _, r in df[df['day'] == d_val].iterrows():
                    v_str = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
                    txt = f"{v_str} {r['unit']} | {r['time']}"
                    
                    folium.Marker(
                        [r.lat, r.lon],
                        icon=folium.DivIcon(
                            icon_anchor=(-15, 7),
                            html=f'<div style="color:blue; font-family:sans-serif; font-size:11pt; font-weight:bold; white-space:nowrap;">{txt}</div>'
                        )
                    ).add_to(group)
                    
                    folium.CircleMarker([r.lat, r.lon], radius=7, color="blue", fill=True, fill_opacity=0.6).add_to(group)
                group.add_to(m)

            folium.LayerControl(collapsed=False).add_to(m)
            st_folium(m, width="100%", height=700, key="blue_final_map")
