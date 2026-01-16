import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ===============================
# Налаштування сторінки
# ===============================
st.set_page_config(
    page_title="Radiation Hazard Map",
    layout="wide"
)

# Стилізація для приховування зайвих елементів
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
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
# Інструкція користування (Відкрити/Закрити)
# ===============================
if st.button("ℹ️ Інструкція користування", use_container_width=True):
    st.session_state.show_instructions = not st.session_state.show_instructions

if st.session_state.show_instructions:
    st.info("""
**Призначення:** Веб-додаток для візуалізації радіаційної обставновки на карті.

**Можливості:**
- Вибір одиниць вимірювання: мЗв/год або мкЗв/год.
- Додавання точок вимірювання вручну або через CSV-файл.
- Відображення значень та часу вимірювання на карті червоним кольором.
- Експорт інтерактивної карти у формат HTML.

**Як працювати:**
1. Оберіть одиницю вимірювання.
2. Додайте координати (lat, lon), значення потужності дози та час вручну АБО завантажте CSV-файл (колонки: `lat`, `lon`, `value`, `unit`, `time`).
3. Карта оновиться автоматично. Ви можете завантажити її як окремий файл.
""")

# ===============================
# Розподіл екрану
# ===============================
col_map, col_gui = st.columns([2.5, 1])

# ===============================
# Панель управління (GUI)
# ===============================
with col_gui:
    st.subheader("⚙️ Управління даними")

    st.markdown("### ➕ Додати точку вручну")
    lat = st.number_input("Широта (lat)", format="%.6f", value=50.4501)
    lon = st.number_input("Довгота (lon)", format="%.6f", value=30.5234)
    
    col_val, col_unit = st.columns([2, 1])
    with col_val:
        value = st.number_input("Потужність дози", min_value=0.0, step=0.01, format="%.4f")
    with col_unit:
        unit = st.selectbox("Одиниця", ["мкЗв/год", "мЗв/год"])
        
    time = st.text_input("Час вимірювання", placeholder="2026-01-16 10:00")

    if st.button("➕ Додати на карту", use_container_width=True):
        new_row = pd.DataFrame([{"lat": lat, "lon": lon, "value": value, "unit": unit, "time": time}])
        st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)

    st.divider()

    st.markdown("### 📂 Завантажити CSV")
    uploaded = st.file_uploader("Виберіть файл (lat, lon, value, unit, time)", type=["csv"])
    if uploaded:
        st.session_state.data = pd.read_csv(uploaded)
        st.success(f"Завантажено {len(st.session_state.data)} точок")

    if st.button("🧹 Очистити карту", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.rerun()

# ===============================
# Візуалізація на карті
# ===============================
with col_map:
    if st.session_state.data.empty:
        st.info("Очікування даних для відображення... Додайте точки через панель праворуч.")
    else:
        df = st.session_state.data.copy()
        m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=12, control_scale=True)

        for _, r in df.iterrows():
            # Коричневий колір для тексту та маркерів (SaddleBrown)
            label_html = f"""
            <div style="
                color: #8B4513;
                font-size: 13px;
                font-weight: bold;
                white-space: nowrap;
                background-color: rgba(255,255,255,0.8);
                padding: 4px;
                border: 2px solid #8B4513;
                border-radius: 4px;
            ">
                {r['value']} {r['unit']}
                <hr style="margin:2px 0; border:1px solid #8B4513;">
                {r['time']}
            </div>
            """
            
            folium.CircleMarker(
                [r.lat, r.lon],
                radius=8,
                color="#8B4513",
                fill=True,
                fill_color="#8B4513",
                fill_opacity=0.7
            ).add_to(m)

            folium.Marker(
                [r.lat, r.lon],
                icon=folium.DivIcon(icon_anchor=(-15, 0), html=label_html)
            ).add_to(m)

        st_folium(m, width="100%", height=650, key="rad_map")

        # Експорт у HTML
        m.save("radiation_map.html")
        with open("radiation_map.html", "rb") as f:
            st.download_button(
                "💾 Завантажити карту (HTML)",
                f,
                file_name="radiation_map.html",
                mime="text/html",
                use_container_width=True
            )
