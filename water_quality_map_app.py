
import pandas as pd
import folium
import os
import streamlit as st
import matplotlib.colors as mcolors
from streamlit_folium import st_folium

# تنظیمات اولیه استریم‌لیت
st.set_page_config(layout="wide")
st.title("📍 Interactive Water Quality Map with Parameter Selection")

# مسیر پوشه جاری (همان جایی که کد در آن قرار دارد)
data_folder = os.getcwd()

# خواندن فایل‌های CSV
csv_files = [f for f in os.listdir(data_folder) if f.startswith("resultphyschem") and f.endswith(".csv")]
all_data = []
for file in csv_files:
    df = pd.read_csv(os.path.join(data_folder, file), low_memory=False)
    df = df.dropna(subset=["ActivityLocation/LatitudeMeasure", "ActivityLocation/LongitudeMeasure"])
    df["ActivityStartDate"] = pd.to_datetime(df["ActivityStartDate"], errors='coerce')
    all_data.append(df)

combined_df = pd.concat(all_data, ignore_index=True)
combined_df = combined_df.dropna(subset=["ActivityStartDate", "CharacteristicName", "ResultMeasureValue", "MonitoringLocationIdentifier"])
combined_df["ResultMeasureValue"] = pd.to_numeric(combined_df["ResultMeasureValue"], errors='coerce')

# پارامترها برای انتخاب کاربر
available_params = combined_df["CharacteristicName"].dropna().unique()
selected_param = st.selectbox("Select a Water Quality Parameter:", sorted(available_params))

# فیلتر داده‌ها بر اساس پارامتر انتخاب‌شده
filtered_df = combined_df[combined_df["CharacteristicName"] == selected_param]

# رنگ‌ها برای سازمان‌ها
orgs = filtered_df["OrganizationFormalName"].dropna().unique()
color_palette = list(mcolors.TABLEAU_COLORS.values()) + list(mcolors.CSS4_COLORS.values())
org_colors = {org: color_palette[i % len(color_palette)] for i, org in enumerate(orgs)}

# اطلاعات ایستگاه‌ها
station_info = {}
for station_id, group in filtered_df.groupby("MonitoringLocationIdentifier"):
    lat = group["ActivityLocation/LatitudeMeasure"].iloc[0]
    lon = group["ActivityLocation/LongitudeMeasure"].iloc[0]
    orgs = group["OrganizationFormalName"].dropna().unique()
    org_display = orgs[0] if len(orgs) > 0 else "Unknown"
    org_color = org_colors.get(org_display, "gray")

    dates = group["ActivityStartDate"].sort_values()
    start = dates.min()
    end = dates.max()
    gaps = dates.diff().dt.days.dropna()
    gap_count = len(gaps[gaps > 30])

    station_info[station_id] = {
        "lat": lat,
        "lon": lon,
        "organization": org_display,
        "color": org_color,
        "gap_total": gap_count,
        "start": start.strftime("%Y-%m-%d"),
        "end": end.strftime("%Y-%m-%d")
    }

# ساخت نقشه
m = folium.Map(location=[29.5, -97.5], zoom_start=7, tiles="CartoDB positron", control_scale=True)

# راهنمای رنگ‌ها
legend_html = "<div style='position: fixed; bottom: 50px; left: 50px; width: 300px; height: auto; z-index:9999; font-size:14px; background-color:white; padding: 10px; border:2px solid grey; border-radius:6px;'>"
legend_html += "<b>Legend</b><br>"
for org, color in org_colors.items():
    legend_html += f"<i style='background:{color};width:10px;height:10px;float:left;margin-right:5px;'></i>{org}<br>"
legend_html += "<br><i style='color:red;'>* Gap = interval > 30 days</i><br></div>"
m.get_root().html.add_child(folium.Element(legend_html))

# اضافه کردن ایستگاه‌ها به نقشه
for station_id, info in station_info.items():
    popup_html = f"""
    <div style='font-size:13px; max-height:300px; overflow:auto;'>
        <b>Station ID:</b> {station_id}<br>
        <b>Organization:</b> {info["organization"]}<br>
        <b>First Sample:</b> {info["start"]}<br>
        <b>Last Sample:</b> {info["end"]}<br>
        <b>Total Gaps &gt;30d:</b> {info["gap_total"]}
    </div>
    """
    folium.CircleMarker(
        location=[info["lat"], info["lon"]],
        radius=7,
        color=info["color"],
        weight=1,
        fill=True,
        fill_color=info["color"],
        fill_opacity=0.9,
        popup=folium.Popup(popup_html, max_width=500)
    ).add_to(m)

# نمایش نقشه در Streamlit
st_data = st_folium(m, width=1200, height=700)
