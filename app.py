import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from fpdf import FPDF
import io

# ===============================
# 1. Виправлений Генератор PDF
# ===============================
class RadiationPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, 'Radiation Monitoring Report', ln=True, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def safe_text(text):
    """Конвертація для уникнення помилок кодування в PDF"""
    mapping = {
        "мкЗв/год": "uSv/h",
        "мЗв/год": "mSv/h",
        "Інша дата": "Other date"
    }
    res = mapping.get(str(text), str(text))
    # Видаляємо будь-які не-latin1 символи про всяк випадок
    return str(res).encode('latin-1', 'replace').decode('latin-1')

def generate_pdf_report(df):
    try:
        pdf = RadiationPDF()
        pdf.add_page()
        
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_fill_color(230, 230, 250)
        
        headers = ['Date/Time', 'Lat', 'Lon', 'Value', 'Unit']
        widths = [45, 30, 30, 35, 45]
        
        for i in range(len(headers)):
            pdf.cell(widths[i], 10, headers[i], 1, 0, 'C', True)
        pdf.ln()

        pdf.set_font('Helvetica', '', 9)
        for _, r in df.iterrows():
            val_clean = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
            pdf.cell(widths[0], 10, safe_text(r['time']), 1)
            pdf.cell(widths[1], 10, str(round(r['lat'], 5)), 1)
            pdf.cell(widths[2], 10, str(round(r['lon'], 5)), 1)
            pdf.cell(widths[3], 10, val_clean, 1)
            pdf.cell(widths[4], 10, safe_text(r['unit']), 1)
            pdf.ln()
        
        # У fpdf2 output() без аргументів повертає bytes/bytearray
        return pdf.output()
    except Exception as e:
        return None

# ===============================
# 2. Налаштування та Сесія
# ===============================
st.set_page_config(page_title="Radiation System", layout="wide")
st.markdown("<style>#MainMenu, footer, header {visibility: hidden;}</style>", unsafe_allow_html=True)

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])

# ===============================
# 3. Інтерфейс (Панель управління)
# ===============================
st.title("🔵 Моніторинг радіаційної обстановки")

col_map, col_gui = st.columns([2.8, 1])

with col_gui:
    st.subheader("⚙️ Вхідні дані")
    
    # 1. РУЧНЕ ВВЕДЕННЯ
    with st.expander("➕ Додати вручну"):
        lat_in = st.number_input("Широта", format="%.6f", value=50.4501)
        lon_in = st.number_input("Довгота", format="%.6f", value=30.5234)
        val_in = st.number_input("Значення", step=0.00001, format="%.5f")
        unit_in = st.selectbox("Одиниці", ["мкЗв/год", "мЗв/год"])
        time_in = st.text_input("Час", value=pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"))
        if st.button("Додати точку"):
            new_pt = pd.DataFrame([{"lat": lat_in, "lon": lon_in, "value": val_in, "unit": unit_in, "time": time_in}])
            st.session_state.data = pd.concat([st.session_state.data, new_pt], ignore_index=True)
            st.rerun()

    # 2. ЗАВАНТАЖЕННЯ ФАЙЛУ
    uploaded_file = st.file_uploader("📁 CSV з пристрою", type=["csv"])
    if uploaded_file:
        if st.button("Зчитати файл", use_container_width=True):
            try:
                df_up = pd.read_csv(uploaded_file, sep=None, engine='python')
                st.session_state.data = pd.concat([st.session_state.data, df_up], ignore_index=True)
                st.rerun()
            except: st.error("Помилка файлу")

    # 3. GOOGLE DRIVE
    url_input = st.text_input("🔗 Посилання Google Drive")
    if st.button("Завантажити з хмари", use_container_width=True):
        if url_input:
            try:
                f_id = url_input.split('/d/')[1].split('/')[0] if '/d/' in url_input else url_input.split('id=')[1].split('&')[0]
                direct_link = f'https://drive.google.com/uc?export=download&id={f_id}'
                df_cloud = pd.read_csv(direct_link, sep=None, engine='python')
                st.session_state.data = pd.concat([st.session_state.data, df_cloud], ignore_index=True)
                st.rerun()
            except: st.error("Помилка посилання")

    st.divider()

    # ЕКСПОРТ PDF
    if not st.session_state.data.empty:
        st.markdown("### 📄 Звіти")
        c_df = st.session_state.data.copy()
        c_df['lat'] = pd.to_numeric(c_df['lat'], errors='coerce')
        c_df['lon'] = pd.to_numeric(c_df['lon'], errors='coerce')
        c_df = c_df.dropna(subset=['lat', 'lon'])

        if not c_df.empty:
            pdf_data = generate_pdf_report(c_df)
            if pdf_data:
                st.download_button("📊 Завантажити PDF", data=pdf_data, file_name="report.pdf", mime="application/pdf", use_container_width=True)
            else:
                st.error("Помилка генерації PDF")
    
    if st.button("🧹 Очистити карту", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.rerun()

# ===============================
# 4. Карта (Візуалізація)
# ===============================
with col_map:
    if st.session_state.data.empty:
        st.info("Додайте дані для відображення карти.")
    else:
        df = st.session_state.data.copy()
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna(subset=['lat', 'lon', 'value'])
        
        if not df.empty:
            df['t_dt'] = pd.to_datetime(df['time'], dayfirst=True, errors='coerce')
            df['day'] = df['t_dt'].dt.strftime('%d.%m.%Y')
            df.loc[df['day'].isna(), 'day'] = "Інша дата"

            m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=10)
            
            for d in sorted(df['day'].unique()):
                layer = folium.FeatureGroup(name=f"📅 {d}")
                d_data = df[df['day'] == d]

                for _, r in d_data.iterrows():
                    v_str = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
                    txt = f"{v_str} {r['unit']} | {r['time']}"
                    
                    folium.Marker(
                        [r.lat, r.lon],
                        icon=folium.DivIcon(
                            icon_anchor=(-15, 7),
                            html=f'<div style="color:blue; font-family:sans-serif; font-size:11pt; font-weight:bold; white-space:nowrap;">{txt}</div>'
                        )
                    ).add_to(layer)
                    
                    folium.CircleMarker(
                        [r.lat, r.lon], radius=7, color="blue", fill=True, fill_color="blue", fill_opacity=0.6
                    ).add_to(layer)
                
                layer.add_to(m)

            folium.LayerControl(collapsed=False).add_to(m)
            st_folium(m, width="100%", height=700, key="v4_map")
