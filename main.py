import tkinter as tk
from tkinter import messagebox, ttk
import pandas as pd
import folium
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
import webbrowser
import os
from fpdf import FPDF
from datetime import datetime

class RadiationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Радіаційний моніторинг v1.0")
        self.root.geometry("450x650")
        
        self.db_file = "radiation_database.csv"
        self.measurements = []
        self.setup_ui()
        self.load_from_csv()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        # Поля введення
        frame_input = tk.Frame(self.root, pady=10)
        frame_input.pack()

        tk.Label(frame_input, text="Широта (Lat):").grid(row=0, column=0)
        self.entry_lat = tk.Entry(frame_input); self.entry_lat.grid(row=0, column=1)

        tk.Label(frame_input, text="Довгота (Lon):").grid(row=1, column=0)
        self.entry_lon = tk.Entry(frame_input); self.entry_lon.grid(row=1, column=1)

        tk.Label(frame_input, text="мЗв/год:").grid(row=2, column=0)
        self.entry_val = tk.Entry(frame_input); self.entry_val.grid(row=2, column=1)

        # Кнопки
        tk.Button(self.root, text="Ввести координати замірів", command=self.add_measurement, bg="#e1f5fe", width=35).pack(pady=5)
        tk.Button(self.root, text="Показати карту з ізолініями", command=self.show_map, bg="#c8e6c9", width=35).pack(pady=5)
        tk.Button(self.root, text="Створити аналітичний PDF-звіт", command=self.generate_pdf, bg="#fff9c4", width=35).pack(pady=5)
        tk.Button(self.root, text="Стерти всю базу даних", command=self.clear_data, bg="#ffcdd2", width=35).pack(pady=5)

        # Таблиця
        self.tree = ttk.Treeview(self.root, columns=("Lat", "Lon", "Val"), show='headings', height=10)
        self.tree.heading("Lat", text="Широта"); self.tree.heading("Lon", text="Довгота"); self.tree.heading("Val", text="мЗв/год")
        self.tree.column("Lat", width=100); self.tree.column("Lon", width=100); self.tree.column("Val", width=80)
        self.tree.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    def add_measurement(self):
        try:
            lat = float(self.entry_lat.get().replace(',', '.'))
            lon = float(self.entry_lon.get().replace(',', '.'))
            val = float(self.entry_val.get().replace(',', '.'))
            self.measurements.append([lat, lon, val])
            self.tree.insert("", tk.END, values=(lat, lon, val))
            self.entry_lat.delete(0, tk.END); self.entry_lon.delete(0, tk.END); self.entry_val.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Помилка", "Введіть числові значення (використовуйте крапку)")

    def show_map(self):
        if len(self.measurements) < 3:
            messagebox.showwarning("Мало даних", "Потрібно мінімум 3 точки для інтерполяції")
            return

        df = pd.DataFrame(self.measurements, columns=['lat', 'lon', 'value'])
        m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=13)

        # Нанесення прапорців та цифр
        for _, row in df.iterrows():
            lat, lon, val = row['lat'], row['lon'], row['value']
            f_color = 'blue' if val < 0.03 else 'green' if val < 0.3 else 'orange' if val < 1.0 else 'red'
            
            folium.Marker(location=[lat, lon], icon=folium.Icon(color=f_color, icon='info-sign')).add_to(m)
            folium.map.Marker([lat, lon], icon=folium.features.DivIcon(icon_size=(150,36), icon_anchor=(0,-10),
                html=f'<div style="font-size: 11pt; color: black; font-weight: bold; background: rgba(255,255,255,0.7); border-radius:3px; padding:2px;">{val} mSv/h</div>')).add_to(m)

        # Ізолінії
        try:
            points, values = df[['lat', 'lon']].values, df['value'].values
            grid_x, grid_y = np.mgrid[df['lat'].min()-0.05:df['lat'].max()+0.05:150j, df['lon'].min()-0.05:df['lon'].max()+0.05:150j]
            grid_z = griddata(points, values, (grid_x, grid_y), method='linear')
            levels_config = {0.03: 'blue', 0.3: 'yellow', 1.0: 'orange', 5.0: 'red'}
            
            plt.figure()
            cs = plt.contour(grid_x, grid_y, grid_z, levels=list(levels_config.keys()))
            for i, level in enumerate(cs.levels):
                col = levels_config[level]
                for path in cs.collections[i].get_paths():
                    folium.PolyLine(path.vertices, color=col, weight=4, opacity=0.8, tooltip=f"Рівень {level}").add_to(m)
            plt.close()
        except: pass

        # Кнопка друку
        m.get_root().html.add_child(folium.Element('<div style="position:fixed; top:10px; right:10px; z-index:9999;"><button onclick="window.print()" style="padding:10px; cursor:pointer;">🖨️ Друк</button></div>'))
        m.save("map_output.html")
        webbrowser.open('file://' + os.path.realpath("map_output.html"))

    def generate_pdf(self):
        if not self.measurements: return
        pdf = FPDF()
        pdf.add_page()
        try:
            pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
            pdf.set_font('DejaVu', '', 14)
        except: pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt="Звіт про радіаційну обстановку", ln=True, align='C')
        pdf.set_font('DejaVu' if 'DejaVu' in pdf.fonts else "Arial", '', 10)
        pdf.cell(200, 10, txt=f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True)
        
        pdf.ln(5)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(60, 10, "Широта", 1, 0, 'C', True); pdf.cell(60, 10, "Довгота", 1, 0, 'C', True); pdf.cell(60, 10, "мЗв/год", 1, 1, 'C', True)
        
        for m in self.measurements:
            if m[2] >= 0.3: pdf.set_text_color(200, 0, 0)
            else: pdf.set_text_color(0, 0, 0)
            pdf.cell(60, 10, f"{m[0]:.5f}", 1); pdf.cell(60, 10, f"{m[1]:.5f}", 1); pdf.cell(60, 10, f"{m[2]:.3f}", 1, 1)
        
        pdf.set_text_color(0, 0, 0)
        report_name = f"Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf.output(report_name)
        os.startfile(report_name)

    def load_from_csv(self):
        if os.path.exists(self.db_file):
            df = pd.read_csv(self.db_file)
            for _, r in df.iterrows():
                self.measurements.append([r['lat'], r['lon'], r['value']])
                self.tree.insert("", tk.END, values=(r['lat'], r['lon'], r['value']))

    def on_closing(self):
        if self.measurements:
            pd.DataFrame(self.measurements, columns=['lat', 'lon', 'value']).to_csv(self.db_file, index=False)
        self.root.destroy()

    def clear_data(self):
        if messagebox.askyesno("Видалення", "Очистити всю базу?"):
            self.measurements = []; [self.tree.delete(i) for i in self.tree.get_children()]
            if os.path.exists(self.db_file): os.remove(self.db_file)

if __name__ == "__main__":
    root = tk.Tk(); app = RadiationApp(root); root.mainloop()
