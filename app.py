import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ===============================
# 1. Налаштування сторінки
# ===============================
st.set_page_config(
    page_title="Radiation Hazard Map",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Приховуємо службові елементи інтерфейсу
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Ініціалізація сховища даних
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])

if "show_instructions" not in st.session_state:
    st.session_state.show_instructions = False

# ===============================
# 2. Інтерфейс (Заголовок та Інструкція)
# ===============================
st.title("☢️ Карта радіаційної обстановки")

if st.button("ℹ️ Інструкція користування", use_container_width=True):
    st.session_state.show_instructions = not st.session_state.show_instructions

if st.session_state.show_instructions:
    st.info("""
**Як працювати з картою:**
1. **Дані**: Можна додавати точки вручну або завантажити CSV-файл.
2. **Формат CSV**: Стовпці `lat`, `lon`, `value`, `unit`, `time`. Використовуйте крапку для десяткових дробів (0.12).
3. **Керування шарами**: У правому верхньому куті карти можна вмикати/вимикати дані за певні дати.
4. **Експорт**: Кнопка внизу дозволяє завантажити готову карту як файл .html.
""")

# Розподіл екрану
col_map, col_gui = st.columns([2.5, 1])

# ===============================
# 3. Права панель (Управління)
# ===============================
with col_gui:
    st.subheader("⚙️ Управління даними")

    # Ручне введення
    with st.expander("➕ Додати точку вручну", expanded=True):
        lat = st.number_input("Широта (lat)", format="%.6f", value=50.4501)
        lon = st.number_input("Довгота (lon)", format="%.6f", value=30.5234)
        
        c1, c2 = st.columns([2, 1])
        with c1:
            val_input = st.number_input("Потужність дози", min_value=0.0, step=0.00001, format="%.5f")
        with c2:
            unit_input = st.selectbox("Одиниця", ["мкЗв/год", "мЗв/год"])
        
        time_input = st.text_input("Дата та час", placeholder="2026-02-16 12:00")

        if st.button("Додати на карту", use_container_width=True):
            new_row = pd.DataFrame([{"lat": lat, "lon": lon, "value": val_input, "unit": unit_input, "time": time_input}])
            st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
            st.toast("Точку додано!")

    st.divider()

    # Завантаження файлу
    st.markdown("### 📂 Завантажити CSV")
    uploaded = st.file_uploader("Виберіть файл", type=["csv"])
    
    if uploaded:
        file_df = pd.read_csv(uploaded)
        
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
            if st.button("📥 Завантажити дані", use_container_width=True):
                st.session_state.data = file_df
                st.rerun()

    if st.button("🧹 Очистити все", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.rerun()

# ===============================
# 4. Карта (Візуалізація)
# ===============================
with col_map:
    if st.session_state.data.empty:
        st.warning("Немає даних для відображення. Додайте точку вручну або завантажте файл.")
    else:
        # Копія даних для обробки
        df = st.session_state.data.copy()

        # ЗАПОБІЖНИК: Конвертація значень у числа
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df = df.dropna(subset=['lat', 'lon', 'value'])

        # Обробка дат для шарів
        df['time_dt'] = pd.to_datetime(df['time'], errors='coerce')
        df['day_label'] = df['time_dt'].dt.date.astype(str)
        df.loc[df['day_label'] == 'NaT', 'day_label'] = "Інша дата"

        # Центрування карти
        m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=10, control_scale=True)
        
        # Створення шарів по днях
        unique_days = sorted(df['day_label'].unique())

        for day in unique_days:
            layer = folium.FeatureGroup(name=f"📅 {day}")
            day_data = df[df['day_label'] == day]

            for _, r in day_data.iterrows():
                # Форматування числа без зайвих нулів
                val_clean = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
                label_text = f"{val_clean} {r['unit']} | {r['time']}"
                
                # Підпис (червоний, без фону)
                folium.map.Marker(
                    [r.lat, r.lon],
                    icon=folium.DivIcon(
                        icon_anchor=(-15, 7),
                        html=f"""<div style="font-family: sans-serif; font-size: 11pt; color: red; font-weight: bold; white-space: nowrap;">{label_text}</div>"""
                    )
                ).add_to(layer)
                
                # Точка
                folium.CircleMarker(
                    [r.lat, r.lon],
                    radius=7,
                    color="red",
                    fill=True,
                    fill_color="red",
                    fill_opacity=0.8
                ).add_to(layer)
            
            layer.add_to(m)

        # Контроль шарів
        folium.LayerControl(collapsed=False).add_to(m)
        
        # Відображення карти в Streamlit
        st_folium(m, width="100%", height=650, key="rad_map_final_v1")

        # Кнопка збереження
        m.save("radiation_map.html")
        with open("radiation_map.html", "rb") as f:
            st.download_button("💾 Завантажити карту в HTML", f, file_name="radiation_map.html", use_container_width=True)
