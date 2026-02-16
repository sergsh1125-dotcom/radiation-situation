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
**Як працювати з шарами та даними:**
1. **Легенда (праворуч на карті)**: Кожна дата автоматично стає окремим шаром. Використовуйте 'галочки', щоб вмикати/вимикати дані за конкретні дні.
2. **Числа**: Потужність дози відображається без зайвих нулів (напр. 0.1 замість 0.10000).
3. **CSV формат**: Файл повинен мати стовпці `lat`, `lon`, `value`, `unit`, `time`.
4. **Запобіжник**: При завантаженні файлу ви можете вибрати — додати нові точки до вже існуючих чи повністю замінити карту.
""")

# Розподіл екрану
col_map, col_gui = st.columns([2.8, 1])

# ===============================
# 3. Права панель (Управління)
# ===============================
with col_gui:
    st.subheader("⚙️ Управління")

    # Ручне введення
    with st.expander("➕ Додати точку вручну", expanded=True):
        lat = st.number_input("Широта (lat)", format="%.6f", value=50.4501)
        lon = st.number_input("Довгота (lon)", format="%.6f", value=30.5234)
        
        c1, c2 = st.columns([2, 1])
        with c1:
            val_input = st.number_input("Потужність", min_value=0.0, step=0.00001, format="%.5f")
        with c2:
            unit_input = st.selectbox("Од.", ["мкЗв/год", "мЗв/год"])
        
        time_input = st.text_input("Дата/Час", placeholder="16.02.2026 12:00")

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
            st.warning(f"На карті вже є дані. Оберіть дію:")
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

    if st.button("🧹 Очистити карту", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.rerun()

# ===============================
# 4. Карта (Візуалізація з шарами по датах)
# ===============================
with col_map:
    if st.session_state.data.empty:
        st.warning("Додайте дані для відображення.")
    else:
        df = st.session_state.data.copy()

        # ЗАПОБІЖНИК: Перетворення в числа
        for col in ['lat', 'lon', 'value']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['lat', 'lon', 'value'])

        # ОБРОБКА ДАТ ДЛЯ ЛЕГЕНДИ
        # Спроба розпізнати дату автоматично
        df['time_dt'] = pd.to_datetime(df['time'], dayfirst=True, errors='coerce')
        # Створюємо текстову мітку дня (якщо дата не розпізнана - пишемо "Інша дата")
        df['day_label'] = df['time_dt'].dt.strftime('%d.%m.%Y')
        df.loc[df['day_label'].isna(), 'day_label'] = "Вказана дата"

        # Ініціалізація карти (центрування по масиву точок)
        m = folium.Map(
            location=[df.lat.mean(), df.lon.mean()], 
            zoom_start=10, 
            control_scale=True
        )
        
        # Отримуємо унікальні дні та сортуємо їх
        unique_days = sorted(df['day_label'].unique())

        # Створюємо шари для кожного дня
        for day in unique_days:
            # FeatureGroup — це окремий шар у меню
            layer = folium.FeatureGroup(name=f"📅 {day}", overlay=True, control=True)
            
            day_data = df[df['day_label'] == day]

            for _, r in day_data.iterrows():
                # Число без зайвих нулів
                val_clean = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
                label_text = f"{val_clean} {r['unit']} | {r['time']}"
                
                # Маркер з червоним підписом
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
            
            # Додаємо шар на карту
            layer.add_to(m)

        # ДОДАЄМО МЕНЮ ШАРІВ (Layer Control)
        # collapsed=False — меню завжди відкрите для зручності
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        
        # Відображення в Streamlit
        st_folium(m, width="100%", height=650, key="rad_map_final_deploy")

        # HTML експорт
        m.save("radiation_map.html")
        with open("radiation_map.html", "rb") as f:
            st.download_button(
                "💾 Завантажити HTML карту", 
                f, 
                file_name="radiation_map.html", 
                use_container_width=True
            )
