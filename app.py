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

# Приховуємо зайві елементи інтерфейсу Streamlit
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
# Інструкція користування
# ===============================
if st.button("ℹ️ Інструкція користування", use_container_width=True):
    st.session_state.show_instructions = not st.session_state.show_instructions

if st.session_state.show_instructions:
    st.success("""
**Порядок роботи:**
1. **Ручне введення:** Заповніть координати та значення, натисніть "Додати на карту". Точки накопичуються.
2. **Завантаження файлу:** Виберіть CSV. Якщо на карті вже є точки, система запитає: додати нові дані до старих чи повністю замінити їх.
3. **Візуалізація:** Всі дані (і ручні, і з файлу) відображаються червоним кольором без зайвих рамок.
4. **Очищення:** Кнопка "Очистити карту" видаляє всі дані безповоротно.
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

    # --- СЕКЦІЯ 1: Ручне додавання ---
    st.markdown("### ➕ Додати точку вручну")
    lat = st.number_input("Широта (lat)", format="%.6f", value=50.4501)
    lon = st.number_input("Довгота (lon)", format="%.6f", value=30.5234)
    
    c1, c2 = st.columns([2, 1])
    with c1:
        value = st.number_input("Потужність дози", min_value=0.0, step=0.0001, format="%.4f")
    with c2:
        unit = st.selectbox("Одиниця", ["мкЗв/год", "мЗв/год"])
        
    time = st.text_input("Час вимірювання", placeholder="12:00")

    if st.button("➕ Додати на карту", use_container_width=True):
        new_row = pd.DataFrame([{"lat": lat, "lon": lon, "value": value, "unit": unit, "time": time}])
        st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
        st.toast("Точку додано!")

    st.divider()

    # --- СЕКЦІЯ 2: Завантаження CSV із ЗАПОБІЖНИКОМ ---
    st.markdown("### 📂 Завантажити дані")
    uploaded = st.file_uploader("Виберіть CSV файл", type=["csv"])
    
    if uploaded:
        file_df = pd.read_csv(uploaded)
        
        # Перевірка наявності існуючих даних
        if not st.session_state.data.empty:
            st.warning(f"Увага! На карті вже є {len(st.session_state.data)} точок. Як вчинити?")
            col_b1, col_b2 = st.columns(2)
            
            if col_b1.button("➕ Додати до існуючих"):
                st.session_state.data = pd.concat([st.session_state.data, file_df], ignore_index=True)
                st.success("Дані об'єднано!")
                st.rerun()
                
            if col_b2.button("🔄 Замінити всі дані"):
                st.session_state.data = file_df
                st.success("Дані замінено!")
                st.rerun()
        else:
            if st.button("📥 Завантажити на карту"):
                st.session_state.data = file_df
                st.success(f"Завантажено {len(file_df)} точок")
                st.rerun()

    st.divider()

    if st.button("🧹 Очистити карту", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.rerun()

# ===============================
# Візуалізація на карті
# ===============================
with col_map:
    if st.session_state.data.empty:
        st.info("Очікування даних...")
    else:
        df = st.session_state.data.copy()
        m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=10, control_scale=True)

        for _, r in df.iterrows():
            label_text = f"{r['value']} {r['unit']} | {r['time']}"
            
            # Чистий червоний текст без полів
            folium.map.Marker(
                [r.lat, r.lon],
                icon=folium.DivIcon(
                    icon_anchor=(-15, 7),
                    html=f"""<div style="font-family: sans-serif; font-size: 12pt; color: red; font-weight: bold; white-space: nowrap;">{label_text}</div>"""
                )
            ).add_to(m)
            
            # Червона точка
            folium.CircleMarker(
                [r.lat, r.lon],
                radius=7,
                color="red",
                fill=True,
                fill_color="red",
                fill_opacity=0.9
            ).add_to(m)

        st_folium(m, width="100%", height=650, key="rad_map")

        # HTML експорт
        m.save("radiation_map.html")
        with open("radiation_map.html", "rb") as f:
            st.download_button("💾 Завантажити карту (HTML)", f, file_name="radiation_map.html", use_container_width=True)
