import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import io
import requests

# ===============================
# 1. Налаштування сторінки
# ===============================
st.set_page_config(
    page_title="Radiation Monitoring System",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Приховуємо зайві елементи інтерфейсу
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Ініціалізація бази даних у сесії
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])

# ===============================
# 2. Інтерфейс (Заголовок)
# ===============================
st.title("☢️ Моніторинг радіаційної обстановки")

col_map, col_gui = st.columns([2.8, 1])

# ===============================
# 3. Права панель (Управління)
# ===============================
with col_gui:
    st.subheader("⚙️ Управління даними")

    # БЛОК 1: Ручне додавання
    with st.expander("➕ Додати точку вручну", expanded=False):
        lat_in = st.number_input("Широта (lat)", format="%.6f", value=50.4501)
        lon_in = st.number_input("Довгота (lon)", format="%.6f", value=30.5234)
        c1, c2 = st.columns([2, 1])
        with c1:
            val_in = st.number_input("Потужність", min_value=0.0, step=0.00001, format="%.5f")
        with c2:
            unit_in = st.selectbox("Од.", ["мкЗв/год", "мЗв/год"])
        time_in = st.text_input("Дата та час", value="16.02.2026 12:00")
        
        if st.button("Додати на карту", use_container_width=True):
            new_row = pd.DataFrame([{"lat": lat_in, "lon": lon_in, "value": val_in, "unit": unit_in, "time": time_in}])
            st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
            st.success("Точку додано!")
            st.rerun()

    st.divider()

    # БЛОК 2: Google Drive та посилання
    st.markdown("### 🔗 Завантаження з хмари")
    url_input = st.text_input("Посилання на Google Drive CSV", placeholder="https://drive.google.com/...")
    
    if st.button("📥 Завантажити з Google Drive", use_container_width=True):
        if url_input:
            try:
                # Конвертація посилання Google Drive у Direct Link
                file_id = ""
                if '/d/' in url_input:
                    file_id = url_input.split('/d/')[1].split('/')[0]
                elif 'id=' in url_input:
                    file_id = url_input.split('id=')[1].split('&')[0]
                
                if file_id:
                    direct_link = f'https://drive.google.com/uc?export=download&id={file_id}'
                    # Автовизначення роздільника (кома або крапка з комою)
                    df_cloud = pd.read_csv(direct_link, sep=None, engine='python', on_bad_lines='skip')
                    st.session_state.data = pd.concat([st.session_state.data, df_cloud], ignore_index=True)
                    st.success("Дані з хмари завантажено!")
                    st.rerun()
                else:
                    st.error("Невірний формат посилання. Переконайтеся, що файл відкритий для доступу всім.")
            except Exception as e:
                st.error("Помилка доступу. Перевірте налаштування 'Поділитися' у Google Drive.")
        else:
            st.warning("Вставте посилання.")

    st.divider()

    # БЛОК 3: Локальний файл
    uploaded = st.file_uploader("Або виберіть локальний CSV", type=["csv"])
    if uploaded:
        df_upload = pd.read_csv(uploaded, sep=None, engine='python')
        if st.button("➕ Об'єднати з картою", use_container_width=True):
            st.session_state.data = pd.concat([st.session_state.data, df_upload], ignore_index=True)
            st.success("Файл додано!")
            st.rerun()

    if st.button("🧹 Очистити карту", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.rerun()

# ===============================
# 4. Карта (Візуалізація)
# ===============================
with col_map:
    if st.session_state.data.empty:
        st.info("Додайте дані для формування карти.")
    else:
        df = st.session_state.data.copy()

        # ЗАПОБІЖНИК: Чистка даних
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna(subset=['lat', 'lon', 'value'])

        if df.empty:
            st.error("У завантажених даних немає коректних координат.")
        else:
            # Обробка часових шарів
            df['time_dt'] = pd.to_datetime(df['time'], dayfirst=True, errors='coerce')
            df['day_label'] = df['time_dt'].dt.strftime('%d.%m.%Y')
            df.loc[df['day_label'].isna(), 'day_label'] = "Інші дати"

            # Створення карти
            m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=10, control_scale=True)
            
            # Групування точок по шарах (днях)
            for day in sorted(df['day_label'].unique()):
                layer = folium.FeatureGroup(name=f"📅 {day}", overlay=True, control=True)
                day_data = df[df['day_label'] == day]

                for _, r in day_data.iterrows():
                    val_formatted = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
                    label_text = f"{val_formatted} {r['unit']} | {r['time']}"
                    
                    # Маркер та підпис
                    folium.Marker(
                        [r.lat, r.lon],
                        icon=folium.DivIcon(
                            icon_anchor=(-15, 7),
                            html=f'<div style="font-family: sans-serif; font-size: 11pt; color: red; font-weight: bold; white-space: nowrap;">{label_text}</div>'
                        )
                    ).add_to(layer)
                    
                    folium.CircleMarker(
                        [r.lat, r.lon], radius=7, color="red", fill=True, fill_color="red", fill_opacity=0.8
                    ).add_to(layer)
                
                layer.add_to(m)

            # Легенда завжди розгорнута
            folium.LayerControl(collapsed=False).add_to(m)
            
            # Відображення
            st_folium(m, width="100%", height=700, key="main_map")

            # Кнопка збереження HTML
            m.save("radiation_map.html")
            with open("radiation_map.html", "rb") as f:
                st.download_button("💾 Завантажити автономну карту (HTML)", f, file_name="radiation_map.html", use_container_width=True)
