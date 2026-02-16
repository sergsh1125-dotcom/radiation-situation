import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime

# ===============================
# Налаштування сторінки
# ===============================
st.set_page_config(
    page_title="Radiation Hazard Map",
    layout="wide"
)

# Стилізація інтерфейсу
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stButton>button {border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

# ===============================
# Стан програми (Session State)
# ===============================
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])

if "show_instructions" not in st.session_state:
    st.session_state.show_instructions = False

# ===============================
# Заголовок
# ===============================
st.title("☢️ Карта радіаційної обстановки")

# ===============================
# Інструкція користування
# ===============================
if st.button("ℹ️ Інструкція користування", use_container_width=True):
    st.session_state.show_instructions = not st.session_state.show_instructions

if st.session_state.show_instructions:
    st.info("""
**Порядок роботи з радіаційною картою:**
1. **Числа:** Потужність дози підтримує точність до 5 знаків. Система ігнорує некоректні символи у файлах.
2. **Формат CSV:** Файл повинен мати колонки: `lat`, `lon`, `value`, `unit`, `time`.
3. **Візуалізація:** Всі позначення та тексти відображаються **червоним кольором** для кращої видимості.
4. **Шари:** Ви можете вмикати/вимикати дані за певними датами у верхньому правому куті карти.
""")

# ===============================
# Розподіл екрану
# ===============================
col_map, col_gui = st.columns([2.5, 1])

# ===============================
# Права панель (GUI)
# ===============================
with col_gui:
    st.subheader("⚙️ Управління даними")

    with st.expander("➕ Додати точку вручну", expanded=True):
        lat = st.number_input("Широта (lat)", format="%.6f", value=50.4501)
        lon = st.number_input("Довгота (lon)", format="%.6f", value=30.5234)
        
        c1, c2 = st.columns([2, 1])
        with c1:
            val_input = st.number_input(
                "Потужність дози", 
                min_value=0.0, 
                step=0.00001, 
                format="%.5f"
            )
        with c2:
            unit_choice = st.selectbox("Одиниця", ["мкЗв/год", "мЗв/год"])
            
        time_input = st.text_input("Дата та час", value=datetime.now().strftime("%Y-%m-%d %H:%M"))

        if st.button("Додати на карту", use_container_width=True):
            new_row = pd.DataFrame([{"lat": lat, "lon": lon, "value": val_input, "unit": unit_choice, "time": time_input}])
            st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
            st.toast("Точку додано!")

    st.divider()

    st.markdown("### 📂 Завантажити дані")
    uploaded = st.file_uploader("Виберіть CSV файл", type=["csv"])
    
    if uploaded:
        file_df = pd.read_csv(uploaded)
        # Перевірка наявності необхідних колонок
        required_cols = ["lat", "lon", "value"]
        if all(col in file_df.columns for col in required_cols):
            if not st.session_state.data.empty:
                st.warning(f"На карті вже є {len(st.session_state.data)} точок.")
                cb1, cb2 = st.columns(2)
                if cb1.button("➕ Об'єднати"):
                    st.session_state.data = pd.concat([st.session_state.data, file_df], ignore_index=True)
                    st.rerun()
                if cb2.button("🔄 Замінити"):
                    st.session_state.data = file_df
                    st.rerun()
            else:
                if st.button("📥 Завантажити на карту"):
                    st.session_state.data = file_df
                    st.rerun()
        else:
            st.error(f"Файл повинен містити колонки: {', '.join(required_cols)}")

    st.divider()
    if st.button("🧹 Очистити карту", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.rerun()

# ===============================
# Візуалізація на карті
# ===============================
with col_map:
    if st.session_state.data.empty:
        # Порожня карта, якщо даних немає
        m_empty = folium.Map(location=[50.45, 30.52], zoom_start=6)
        st_folium(m_empty, width="100%", height=650, key="empty_map")
    else:
        df = st.session_state.data.copy()
        
        # --- ФІКС ПОМИЛКИ: Очищення даних ---
        # Перетворюємо в числа, некоректні значення стануть NaN
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        
        # Видаляємо рядки з критичними порожніми значеннями
        df = df.dropna(subset=['value', 'lat', 'lon'])
        # ------------------------------------

        # Обробка дат
        df['time_dt'] = pd.to_datetime(df['time'], errors='coerce')
        df['day_label'] = df['time_dt'].dt.date.astype(str)
        df.loc[df['day_label'] == 'NaT', 'day_label'] = "Невідома дата"

        # Центрування карти
        m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=10, control_scale=True)
        
        unique_days = sorted(df['day_label'].unique())

        for day in unique_days:
            layer = folium.FeatureGroup(name=f"📅 {day}")
            day_data = df[df['day_label'] == day]

            for _, r in day_data.iterrows():
                # Безпечне форматування: якщо раптом потрапив NaN (хоча ми їх видалили), воно не впаде
                try:
                    val_formatted = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
                except:
                    val_formatted = str(r['value'])

                unit_str = str(r['unit']) if pd.notnull(r['unit']) else ""
                time_str = str(r['time']) if pd.notnull(r['time']) else ""
                
                label_text = f"{val_formatted} {unit_str} | {time_str}"
                
                # Червона точка вимірювання
                folium.CircleMarker(
                    [r.lat, r.lon],
                    radius=6,
                    color="red",
                    fill=True,
                    fill_color="red",
                    fill_opacity=0.7,
                    popup=label_text
                ).add_to(layer)

                # Текст підпису
                folium.map.Marker(
                    [r.lat, r.lon],
                    icon=folium.DivIcon(
                        icon_anchor=(-15, 7),
                        html=f"""<div style="font-family: sans-serif; font-size: 10pt; color: red; font-weight: bold; white-space: nowrap; text-shadow: 1px 1px 2px white;">{label_text}</div>"""
                    )
                ).add_to(layer)
            
            layer.add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)
        
        st_folium(m, width="100%", height=700, key="rad_map_final")

        # HTML експорт
        m.save("radiation_map.html")
        with open("radiation_map.html", "rb") as f:
            st.download_button("💾 Скачати карту як HTML файл", f, file_name="radiation_map.html", use_container_width=True)
