import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from fpdf import FPDF
import io

# ===============================
# 1. Генератор PDF (з виправленням кодування)
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
    """Конвертує українські одиниці в латиницю для PDF, щоб уникнути помилки кодування"""
    mapping = {
        "мкЗв/год": "uSv/h",
        "мЗв/год": "mSv/h",
        "Інша дата": "Other date"
    }
    return mapping.get(str(text), str(text))

def generate_pdf_report(df):
    pdf = RadiationPDF()
    pdf.add_page()
    
    # Заголовки таблиці
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(230, 230, 250) # Світло-синій підтон
    
    headers = ['Date/Time', 'Lat', 'Lon', 'Value', 'Unit (Safe)']
    widths = [45, 30, 30, 35, 45]
    
    for i in range(len(headers)):
        pdf.cell(widths[i], 10, headers[i], 1, 0, 'C', True)
    pdf.ln()

    # Дані таблиці
    pdf.set_font('Helvetica', '', 9)
    for _, r in df.iterrows():
        val_clean = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
        pdf.cell(widths[0], 10, safe_text(r['time']), 1)
        pdf.cell(widths[1], 10, str(round(r['lat'], 5)), 1)
        pdf.cell(widths[2], 10, str(round(r['lon'], 5)), 1)
        pdf.cell(widths[3], 10, val_clean, 1)
        pdf.cell(widths[4], 10, safe_text(r['unit']), 1)
        pdf.ln()
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# ===============================
# 2. Налаштування та Сесія
# ===============================
st.set_page_config(page_title="Radiation Blue System", layout="wide")
st.markdown("<style>#MainMenu, footer, header {visibility: hidden;}</style>", unsafe_allow_html=True)

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])

# ===============================
# 3. Інтерфейс (Управління)
# ===============================
st.title("🔵 Моніторинг радіаційної обстановки")

col_map, col_gui = st.columns([2.8, 1])

with col_gui:
    st.subheader("⚙️ Вхідні дані")
    
    # --- МЕТОД 1: РУЧНЕ ВВЕДЕННЯ ---
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

    # --- МЕТОД 2: ЗАВАНТАЖЕННЯ ФАЙЛУ (ПК/ТЕЛЕФОН) ---
    uploaded_file = st.file_uploader("📁 Файл CSV з пристрою", type=["csv"])
    if uploaded_file:
        if st.button("Зчитати файл"):
            try:
                df_up = pd.read_csv(uploaded_file, sep=None, engine='python')
                st.session_state.data = pd.concat([st.session_state.data, df_up], ignore_index=True)
                st.success("Дані з файлу додано")
                st.rerun()
            except: st.error("Помилка формату CSV")

    # --- МЕТОД 3: GOOGLE DRIVE ---
    url_input = st.text_input("🔗 Посилання на Google Drive CSV")
    if st.button("Завантажити з хмари"):
        if url_input:
            try:
                file_id = url_input.split('/d/')[1].split('/')[0] if '/d/' in url_input else url_input.split('id=')[1].split('&')[0]
                direct_link = f'https://drive.google.com/uc?export=download&id={file_id}'
                df_cloud = pd.read_csv(direct_link, sep=None, engine='python')
                st.session_state.data = pd.concat([st.session_state.data, df_cloud], ignore_index=True)
                st.success("Дані з хмари додано")
                st.rerun()
            except: st.error("Помилка доступу до Диску")

    st.divider()

    # --- ЕКСПОРТ ---
    st.markdown("### 📄 Звіти")
    if not st.session_state.data.empty:
        # Підготовка даних (чистка перед PDF)
        clean_df = st.session_state.data.copy()
        clean_df['lat'] = pd.to_numeric(clean_df['lat'], errors='coerce')
        clean_df['lon'] = pd.to_numeric(clean_df['lon'], errors='coerce')
        clean_df['value'] = pd.to_numeric(clean_df['value'], errors='coerce')
        clean_df = clean_df.dropna(subset=['lat', 'lon', 'value'])

        if not clean_df.empty:
            pdf_b = generate_pdf_report(clean_df)
            st.download_button("📊 Завантажити PDF", data=pdf_b, file_name="radiation_report.pdf", mime="application/pdf", use_container_width=True)
    
    if st.button("🧹 Очистити карту", use_container_width=True):
        st.session_state.data = pd.DataFrame(columns=["lat", "lon", "value", "unit", "time"])
        st.rerun()

# ===============================
# 4. Карта (СИНЯ ТЕМА)
# ===============================
with col_map:
    if st.session_state.data.empty:
        st.info("Чекаю на завантаження даних...")
    else:
        df = st.session_state.data.copy()
        for c in ['lat', 'lon', 'value']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna(subset=['lat', 'lon', 'value'])
        
        df['time_dt'] = pd.to_datetime(df['time'], dayfirst=True, errors='coerce')
        df['day'] = df['time_dt'].dt.strftime('%d.%m.%Y')
        df.loc[df['day'].isna(), 'day'] = "Інша дата"

        m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=10)
        
        for d in sorted(df['day'].unique()):
            layer = folium.FeatureGroup(name=f"📅 {d}")
            day_data = df[df['day'] == d]

            for _, r in day_data.iterrows():
                val_c = f"{float(r['value']):.5f}".rstrip('0').rstrip('.')
                txt = f"{val_c} {r['unit']} | {r['time']}"
                
                folium.Marker(
                    [r.lat, r.lon],
                    icon=folium.DivIcon(
                        icon_anchor=(-15, 7),
                        html=f'<div style="color:blue; font-family: sans-serif; font-size: 11pt; font-weight: bold; white-space:nowrap;">{txt}</div>'
                    )
                ).add_to(layer)
                
                folium.CircleMarker(
                    [r.lat, r.lon], radius=7, color="blue", fill=True, fill_color="blue", fill_opacity=0.7
                ).add_to(layer)
            
            layer.add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)
        st_folium(m, width="100%", height=700, key="blue_map_final")
