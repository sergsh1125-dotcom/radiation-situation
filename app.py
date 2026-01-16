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

# Стилізація інтерфейсу
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
**Порядок роботи з радіаційною картою:**
1. **Числа:** Потужність дози підтримує точність до 5 знаків. Зайві нулі в кінці (наприклад, 0.100) автоматично приховуються.
2. **Черговість:** Ви можете додавати точки вручну до або після завантаження файлу — шари по датах працюватимуть коректно.
3. **Запобіжник:** При завантаженні CSV система запитає, чи об'єднати нові дані з тими, що вже є на карті.
4. **Візуалізація:** Всі позначення та тексти відображаються **червоним кольором**.
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

    st.markdown("### ➕ Додати точку вручну")
    lat = st.number_input("Широта (lat)", format="%.6f", value=50.4501)
    lon = st.number_input("Довгота (lon)", format="%.6f", value=30.5234)
    
    c1, c2 = st.columns([2, 1])
    with c1:
        value = st.number_input(
            "Потужність дози", 
            min_value=0.0, 
            step=0.00001, 
            format="%.5f"
        )
    with c2:
        unit = st.selectbox("Одиниця", ["мкЗв/год", "мЗв/год"])
        
    time_input = st.text_input("Дата та час", placeholder="2026-01-16 12:00")

    if st.button("➕ Додати на карту", use_container_width=True):
        new_row = pd.DataFrame([{"lat": lat, "lon": lon, "value": value, "unit": unit, "time": time_input}])
        st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
        st.toast("Радіаційну точку додано!")

    st.divider()

    st.markdown("### 📂 Завантажити дані")
    uploaded = st.file_uploader("Виберіть CSV файл", type=["csv"])
    
    if uploaded:
        file_df = pd.read_csv(uploaded)
        if not st.session_state.data.empty:
            st.warning(f"На карті вже є {len(st.session_state.data)} точок. Як вчинити?")
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

    st.divider()
    if st.button("🧹 Очистити карту", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.rerun()

# ===============================
# Візуалізація на карті
# ===============================
with col_map:
    if st.session_state.data.empty:
        st.info("Чекаю на дані для відображення...")
    else:
        df = st.session_state.data.copy()
        
        # Обробка дат для стабільного створення шарів
        df['time_dt'] = pd.to_datetime(df['time'], errors='coerce')
        df['day_label'] = df['time_dt'].dt.date.astype(str)
        df.loc[df['day_label'] == 'NaT', 'day_label'] = "Вказана дата"

        m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=10, control_scale=True)
        
        unique_days = sorted(df['day_label'].unique())

        for day in unique_days:
            # Створюємо групу (шар) для кожної дати
            layer = folium.FeatureGroup(name=f"📅 Дата: {day}")
            day_data = df[df['day_label'] == day]

            for _, r in day_data.iterrows():
                # Динамічне форматування числа (прибираємо нулі в кінці)
                val_formatted = f"{r['value']:.5f}".rstrip('0').rstrip('.')
                
                # Текст підпису червоним кольором
                label_text = f"{val_formatted} {r['unit']} | {r['time']}"
                
                folium.map.Marker(
                    [r.lat, r.lon],
                    icon=folium.DivIcon(
                        icon_anchor=(-15, 7),
                        html=f"""<div style="font-family: sans-serif; font-size: 11pt; color: red; font-weight: bold; white-space: nowrap;">{label_text}</div>"""
                    )
                ).add_to(layer)
                
                # Червона точка вимірювання
                folium.CircleMarker(
                    [r.lat, r.lon],
                    radius=7,
                    color="red",
                    fill=True,
                    fill_color="red",
                    fill_opacity=0.8
                ).add_to(layer)
            
            layer.add_to(m)

        # Додаємо меню керування шарами
        folium.LayerControl(collapsed=False).add_to(m)
        
        st_folium(m, width="100%", height=650, key="rad_map_layers_final")

        # HTML експорт
        m.save("radiation_map.html")
        with open("radiation_map.html", "rb") as f:
            st.download_button("💾 Завантажити HTML карту", f, file_name="radiation_map.html", use_container_width=True)
