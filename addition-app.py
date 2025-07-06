import streamlit as st
import folium
from streamlit_folium import st_folium
import sumolib
import json
import os
import numpy as np

# Sayfa konfigürasyonu
st.set_page_config(page_title="SUMO Ağ Haritası", layout="wide")

# CSS ile sidebar genişliğini ayarla
st.markdown("""
<style>
    .sidebar .sidebar-content {
        width: 300px;
    }
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Başlık
st.title("🗺️ SUMO Ağ Haritası ve Nokta Seçici")

# SUMO ağ dosyasını yükle (session state'de sakla)
@st.cache_resource
def load_sumo_network():
    try:
        return sumolib.net.readNet("sumo_configs_emek/osm.net.xml.gz")
    except Exception as e:
        st.error(f"SUMO ağ dosyası yüklenemedi: {e}")
        return None

# SUMO ağının sınırlarını hesapla
@st.cache_data
def get_network_bounds():
    """SUMO ağının coğrafi sınırlarını hesapla"""
    try:
        net = load_sumo_network()
        if net is None:
            return None
        
        all_lats = []
        all_lons = []
        
        # Tüm kenarların koordinatlarını topla
        for edge in net.getEdges():
            try:
                shape = edge.getShape()
                for coord in shape:
                    lon, lat = net.convertXY2LonLat(coord[0], coord[1])
                    all_lats.append(lat)
                    all_lons.append(lon)
            except:
                continue
        
        if all_lats and all_lons:
            bounds = {
                'min_lat': min(all_lats),
                'max_lat': max(all_lats),
                'min_lon': min(all_lons),
                'max_lon': max(all_lons),
                'center_lat': (min(all_lats) + max(all_lats)) / 2,
                'center_lon': (min(all_lons) + max(all_lons)) / 2
            }
            return bounds
        return None
    except Exception as e:
        st.error(f"Ağ sınırları hesaplanamadı: {e}")
        return None

# Session state başlatma
if "selected_points" not in st.session_state:
    st.session_state.selected_points = []
if "clicked_history" not in st.session_state:
    st.session_state.clicked_history = []
if "point_counter" not in st.session_state:
    st.session_state.point_counter = 0
if "map_key" not in st.session_state:
    st.session_state.map_key = 0
if "last_clicked_coords" not in st.session_state:
    st.session_state.last_clicked_coords = None
if "map_center" not in st.session_state:
    # Ağ sınırlarını al ve merkezi ayarla
    bounds = get_network_bounds()
    if bounds:
        st.session_state.map_center = [bounds['center_lat'], bounds['center_lon']]
    else:
        st.session_state.map_center = [39.7667, 30.5256]
if "zoom_level" not in st.session_state:
    st.session_state.zoom_level = 16

# Ağ yükleme
net = load_sumo_network()
if net is None:
    st.stop()

# Ağ sınırlarını al
network_bounds = get_network_bounds()

# Sidebar kontrolleri
st.sidebar.header("⚙️ Kontroller")

# Ağ bilgileri
if network_bounds:
    st.sidebar.subheader("🗺️ Ağ Bilgileri")
    st.sidebar.write(f"**Merkez:** {network_bounds['center_lat']:.4f}, {network_bounds['center_lon']:.4f}")
    st.sidebar.write(f"**Enlem:** {network_bounds['min_lat']:.4f} - {network_bounds['max_lat']:.4f}")
    st.sidebar.write(f"**Boylam:** {network_bounds['min_lon']:.4f} - {network_bounds['max_lon']:.4f}")
    st.sidebar.markdown("---")

# Harita yenileme butonu
if st.sidebar.button("🔄 Haritayı Yenile"):
    st.session_state.map_key += 1
    st.rerun()

# Seçilen noktaları temizle
if st.sidebar.button("🗑️ Tüm Noktaları Temizle"):
    st.session_state.selected_points = []
    st.session_state.point_counter = 0
    st.session_state.map_key += 1
    st.rerun()

# Tıklama geçmişini temizle
if st.sidebar.button("🧹 Tıklama Geçmişini Temizle"):
    st.session_state.clicked_history = []
    st.session_state.last_clicked_coords = None
    st.session_state.map_key += 1
    st.rerun()

# Nokta türü seçimi
point_type = st.sidebar.selectbox(
    "Nokta Türü Seç:",
    ["containerStop", "chargingStation"],
    key="point_type"
)

# Zoom kontrolü
new_zoom = st.sidebar.slider("🔍 Zoom Seviyesi", min_value=12, max_value=18, value=st.session_state.zoom_level)
if new_zoom != st.session_state.zoom_level:
    st.session_state.zoom_level = new_zoom
    st.session_state.map_key += 1
    st.rerun()

# Harita sınırlandırma seçeneği
restrict_bounds = st.sidebar.checkbox("🗺️ Haritayı Ağ Sınırları ile Sınırla", value=True)

# Harita istatistikleri
if st.session_state.selected_points:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Seçilen Noktalar")
    container_count = len([p for p in st.session_state.selected_points if p['type'] == 'containerStop'])
    charging_count = len([p for p in st.session_state.selected_points if p['type'] == 'chargingStation'])
    
    st.sidebar.metric("🚚 Container Stops", container_count)
    st.sidebar.metric("⚡ Charging Stations", charging_count)
    st.sidebar.metric("📍 Toplam", len(st.session_state.selected_points))

# Tıklama geçmişi bilgisi
if st.session_state.clicked_history:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Tıklama Geçmişi")
    st.sidebar.metric("Toplam Tıklama", len(st.session_state.clicked_history))

# Harita oluşturma fonksiyonu - cache'li
@st.cache_data
def get_sumo_edges():
    """SUMO kenarlarını cache'le"""
    edges_data = []
    for edge in net.getEdges():
        try:
            shape = edge.getShape()
            if len(shape) > 1:
                coords = []
                for coord in shape:
                    lat, lon = net.convertXY2LonLat(coord[0], coord[1])
                    coords.append([lat, lon])
                if coords:
                    edges_data.append({
                        'id': edge.getID(),
                        'coords': coords
                    })
        except Exception:
            continue
    return edges_data

# Harita oluşturma fonksiyonu - Seçilen noktaları ekle
@st.cache_data
def create_map_with_points():
    m = folium.Map(
        location=st.session_state.map_center, 
        zoom_start=st.session_state.zoom_level,
        tiles="OpenStreetMap",
        prefer_canvas=True  # Performans için
    )

    # Harita sınırlarını kısıtla
    if restrict_bounds and network_bounds:
        # Ağ sınırlarının dışına çıkılmasını engelle
        bounds = [
            [network_bounds['min_lat'] - 0.005, network_bounds['min_lon'] - 0.005],  # SW
            [network_bounds['max_lat'] + 0.005, network_bounds['max_lon'] + 0.005]   # NE
        ]
        m.fit_bounds(bounds)
        
        # Sınır çizgisi çiz
        folium.Rectangle(
            bounds=bounds,
            color='red',
            fill=False,
            weight=2,
            opacity=0.8,
            popup="SUMO Ağ Sınırları"
        ).add_to(m)
    
    # SUMO kenarlarını haritaya ekle
    edges_data = get_sumo_edges()
    for edge_data in edges_data:
        folium.PolyLine(
            edge_data['coords'], 
            color="blue", 
            weight=1.5,
            opacity=0.6,
            popup=f"Edge ID: {edge_data['id']}"
        ).add_to(m)

    # Seçilen noktaları haritaya ekle
    for i, point in enumerate(st.session_state.selected_points):
        lat, lon = net.convertXY2LonLat(point['x'], point['y'])
        color = "red" if point['type'] == "containerStop" else "green"
        icon = "truck" if point['type'] == "containerStop" else "bolt"

        folium.Marker(
            [lat, lon],
            popup=f"{point['type']} #{i+1}: Edge ID: {point['edge_id']}, Position: {point['position']:.2f}",
            tooltip=f"{point['type']} #{i+1}",
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(m)

    return m

def create_map():
    # Harita merkezi ve zoom seviyesi
    m = folium.Map(
        location=st.session_state.map_center, 
        zoom_start=st.session_state.zoom_level,
        tiles="OpenStreetMap",
        prefer_canvas=True  # Performans için
    )
    
    # Harita sınırlarını kısıtla
    if restrict_bounds and network_bounds:
        # Ağ sınırlarının dışına çıkılmasını engelle
        bounds = [
            [network_bounds['min_lat'] - 0.005, network_bounds['min_lon'] - 0.005],  # SW
            [network_bounds['max_lat'] + 0.005, network_bounds['max_lon'] + 0.005]   # NE
        ]
        m.fit_bounds(bounds)
        
        # Sınır çizgisi çiz
        folium.Rectangle(
            bounds=bounds,
            color='red',
            fill=False,
            weight=2,
            opacity=0.8,
            popup="SUMO Ağ Sınırları"
        ).add_to(m)
    
    # SUMO kenarlarını cache'den al
    edges_data = get_sumo_edges()
    
    # Kenarları haritaya ekle
    for edge_data in edges_data:
        folium.PolyLine(
            edge_data['coords'], 
            color="blue", 
            weight=1.5,
            opacity=0.6,
            popup=f"Edge ID: {edge_data['id']}"
        ).add_to(m)
    
    # Seçilen noktaları haritaya ekle
    for i, point in enumerate(st.session_state.selected_points):
        try:
            lat, lon = net.convertXY2LonLat(point['x'], point['y'])
            
            # Nokta türüne göre renk ve ikon
            if point['type'] == "containerStop":
                color = "red"
                icon = "truck"
            else:
                color = "green"
                icon = "bolt"
            
            # Ana marker
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(
                    f"""
                    <div style="width: 220px; font-family: Arial;">
                        <h4 style="margin: 0; color: {color};">
                            {'🚚' if point['type'] == 'containerStop' else '⚡'} 
                            {point['type']} #{i+1}
                        </h4>
                        <hr style="margin: 5px 0;">
                        <p style="margin: 2px 0;"><b>Edge:</b> {point['edge_id']}</p>
                        <p style="margin: 2px 0;"><b>Position:</b> {point['position']:.2f}m</p>
                        <p style="margin: 2px 0;"><b>Koordinat:</b> ({point['x']:.1f}, {point['y']:.1f})</p>
                    </div>
                    """,
                    max_width=300
                ),
                tooltip=f"{'🚚' if point['type'] == 'containerStop' else '⚡'} {point['type']} #{i+1}",
                icon=folium.Icon(
                    color=color, 
                    icon=icon,
                    prefix='fa'
                )
            ).add_to(m)
            
            # Etki alanı çemberi
            folium.Circle(
                [lat, lon],
                radius=15,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.2,
                weight=2,
                opacity=0.8
            ).add_to(m)
            
        except Exception as e:
            continue
    
    # Tüm tıklanan noktaları göster
    for i, clicked_point in enumerate(st.session_state.clicked_history):
        # Son tıklanan farklı renkte
        if i == len(st.session_state.clicked_history) - 1:
            color = 'orange'
            icon = 'crosshairs'
            tooltip = f"🎯 Son Tıklanan (#{i+1})"
        else:
            color = 'purple'
            icon = 'circle'
            tooltip = f"📍 Tıklama #{i+1}"
        
        folium.Marker(
            [clicked_point['lat'], clicked_point['lon']],
            popup=folium.Popup(
                f"""
                <div style="width: 200px; font-family: Arial;">
                    <h4 style="margin: 0; color: {color};">
                        {tooltip}
                    </h4>
                    <hr style="margin: 5px 0;">
                    <p style="margin: 2px 0;"><b>Koordinat:</b> ({clicked_point['lat']:.6f}, {clicked_point['lon']:.6f})</p>
                    <p style="margin: 2px 0;"><b>Zaman:</b> {clicked_point.get('timestamp', 'N/A')}</p>
                </div>
                """,
                max_width=250
            ),
            tooltip=tooltip,
            icon=folium.Icon(
                color=color, 
                icon=icon,
                prefix='fa'
            )
        ).add_to(m)
        
        # Tıklama sırası için küçük çember
        folium.Circle(
            [clicked_point['lat'], clicked_point['lon']],
            radius=8,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.3,
            weight=1,
            opacity=0.6
        ).add_to(m)
    
    # Tıklama geçmişini çizgi ile bağla
    if len(st.session_state.clicked_history) > 1:
        coords = [[point['lat'], point['lon']] for point in st.session_state.clicked_history]
        folium.PolyLine(
            coords,
            color='purple',
            weight=2,
            opacity=0.5,
            dash_array='5, 5',
            popup="Tıklama Geçmişi Rotası"
        ).add_to(m)
    
    return m

# Ana harita gösterimi
st.subheader("🗺️ SUMO Ağ Haritası")
if restrict_bounds and network_bounds:
    st.info("💡 Mavi çizgiler üzerine tıklayarak nokta ekleyebilirsiniz. Kırmızı çerçeve SUMO ağ sınırlarını gösterir.")
else:
    st.info("💡 Mavi çizgiler üzerine tıklayarak nokta ekleyebilirsiniz. Tıklama geçmişi mor işaretlerle gösterilir.")

# Haritayı oluştur
map_obj = create_map_with_points()

# Haritayı tam ekran boyutunda göster
map_data = st_folium(
    map_obj,
    key=f"map_{st.session_state.map_key}",
    width="100%",
    height=600,
    returned_objects=["last_clicked", "last_object_clicked"],
    use_container_width=True
)

# Seçilen noktaları göster
st.subheader("📍 Seçilen Noktalar")

col1, col2 = st.columns([2, 1])

with col1:
    if st.session_state.selected_points:
        for i, point in enumerate(st.session_state.selected_points):
            with st.expander(f"{'🚚' if point['type'] == 'containerStop' else '⚡'} {point['type']} #{i+1}", expanded=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Edge ID:** {point['edge_id']}")
                    st.write(f"**Position:** {point['position']:.2f}m")
                with col_b:
                    st.write(f"**X:** {point['x']:.2f}")
                    st.write(f"**Y:** {point['y']:.2f}")
                
                if st.button(f"🗑️ Sil", key=f"delete_{i}"):
                    st.session_state.selected_points.pop(i)
                    st.session_state.map_key += 1
                    st.rerun()
    else:
        st.info("Henüz nokta seçilmedi. Harita üzerine tıklayarak nokta ekleyebilirsiniz.")

with col2:
    # Hızlı eylemler
    st.subheader("⚡ Hızlı Eylemler")
    
    if st.button("🎯 Son Noktayı Sil", disabled=len(st.session_state.selected_points) == 0):
        if st.session_state.selected_points:
            st.session_state.selected_points.pop()
            st.session_state.map_key += 1
            st.rerun()
    
    if st.button("📍 Ağ Merkezine Git"):
        if network_bounds:
            st.session_state.map_center = [network_bounds['center_lat'], network_bounds['center_lon']]
            st.session_state.zoom_level = 16
            st.session_state.map_key += 1
            st.rerun()
        else:
            st.error("Ağ sınırları bulunamadı!")
    
    if st.button("🔍 Tüm Ağı Göster"):
        if network_bounds:
            st.session_state.map_center = [network_bounds['center_lat'], network_bounds['center_lon']]
            st.session_state.zoom_level = 14
            st.session_state.map_key += 1
            st.rerun()

# Tıklama kontrolü
if map_data and "last_clicked" in map_data and map_data["last_clicked"]:
    clicked_lat = map_data["last_clicked"]["lat"]
    clicked_lon = map_data["last_clicked"]["lng"]
    
    # Tıklama geçmişine ekle
    import datetime
    click_info = {
        'lat': clicked_lat,
        'lon': clicked_lon,
        'timestamp': datetime.datetime.now().strftime("%H:%M:%S")
    }
    
    # Aynı koordinat değilse ekle
    if (not st.session_state.clicked_history or 
        abs(st.session_state.clicked_history[-1]['lat'] - clicked_lat) > 0.00001 or
        abs(st.session_state.clicked_history[-1]['lon'] - clicked_lon) > 0.00001):
        st.session_state.clicked_history.append(click_info)
        st.session_state.last_clicked_coords = [clicked_lat, clicked_lon]
    
    # Tıklama bilgilerini göster
    st.success(f"🎯 **Tıklanan Koordinat:** {clicked_lat:.6f}, {clicked_lon:.6f}")
    st.info(f"📊 **Toplam Tıklama:** {len(st.session_state.clicked_history)} kez")
    
    # Ağ sınırlarını kontrol et
    if restrict_bounds and network_bounds:
        if (clicked_lat < network_bounds['min_lat'] or clicked_lat > network_bounds['max_lat'] or
            clicked_lon < network_bounds['min_lon'] or clicked_lon > network_bounds['max_lon']):
            st.warning("⚠️ **Bu nokta SUMO ağ sınırlarının dışında!**")
    
    # Koordinat dönüşümünü test et
    try:
        # Folium koordinatlarını SUMO koordinatlarına çevir
        x, y = net.convertLonLat2XY(clicked_lon, clicked_lat)
        
        # En yakın kenarı bul
        edges = net.getNeighboringEdges(x, y, 100)  # 100 metre yarıçap
        
        if edges:
            closest_edge = edges[0][0]
            edge_id = closest_edge.getID()
            distance = edges[0][1]
            
            # Kenardaki en yakın pozisyonu hesapla
            closest_pos = closest_edge.getClosestLanePosDist((x, y))[1]
            
            # Bilgileri göster
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                st.info(f"**Edge ID:** {edge_id}")
            with col2:
                st.info(f"**Mesafe:** {distance:.1f}m")
            with col3:
                st.info(f"**Pozisyon:** {closest_pos:.2f}m")
            
            # Yeni nokta oluştur
            new_point = {
                "type": point_type,
                "edge_id": edge_id,
                "position": closest_pos,
                "x": x,
                "y": y,
                "lat": clicked_lat,
                "lon": clicked_lon
            }
            
            # Duplikat kontrolü
            duplicate = False
            for existing_point in st.session_state.selected_points:
                if (existing_point["edge_id"] == edge_id and 
                    abs(existing_point["position"] - closest_pos) < 10):
                    duplicate = True
                    break
            
            # Ekleme butonu
            col1, col2 = st.columns([1, 1])
            with col1:
                if not duplicate:
                    if st.button(f"➕ **{point_type}** Ekle", key=f"add_point_{st.session_state.map_key}", type="primary"):
                        st.session_state.selected_points.append(new_point)
                        st.session_state.point_counter += 1
                        st.session_state.map_key += 1
                        st.success(f"✅ {point_type} başarıyla eklendi!")
                        st.rerun()
                else:
                    st.warning("⚠️ Bu konuma zaten bir nokta eklenmiş!")
            
            with col2:
                if st.button("❌ İptal Et", key=f"cancel_{st.session_state.map_key}"):
                    st.session_state.last_clicked_coords = None
                    st.session_state.map_key += 1
                    st.rerun()
        else:
            st.error("❌ **Bu konumda SUMO ağı bulunamadı.** Lütfen mavi çizgiler üzerine tıklayın.")
    
    except Exception as e:
        st.error(f"❌ **Koordinat dönüşümü hatası:** {str(e)}")

# Tıklama geçmişi gösterimi
if st.session_state.clicked_history:
    st.markdown("---")
    st.subheader("🎯 Tıklama Geçmişi")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        for i, click in enumerate(st.session_state.clicked_history):
            is_last = i == len(st.session_state.clicked_history) - 1
            icon = "🎯" if is_last else "📍"
            st.write(f"{icon} **#{i+1}** - {click['lat']:.6f}, {click['lon']:.6f} - {click['timestamp']}")
    
    with col2:
        if st.button("🗑️ Geçmişi Temizle"):
            st.session_state.clicked_history = []
            st.session_state.last_clicked_coords = None
            st.session_state.map_key += 1
            st.rerun()

# Alternatif: Manuel koordinat girişi
st.markdown("---")
st.subheader("🎯 Manuel Koordinat Girişi")
manual_col1, manual_col2, manual_col3 = st.columns(3)

with manual_col1:
    default_lat = network_bounds['center_lat'] if network_bounds else 39.7667
    manual_lat = st.number_input("Latitude", value=default_lat, format="%.6f")
    
with manual_col2:
    default_lon = network_bounds['center_lon'] if network_bounds else 30.5256
    manual_lon = st.number_input("Longitude", value=default_lon, format="%.6f")
    
with manual_col3:
    if st.button("📍 Bu Koordinata Nokta Ekle"):
        try:
            x, y = net.convertLonLat2XY(manual_lon, manual_lat)
            edges = net.getNeighboringEdges(x, y, 100)
            
            if edges:
                closest_edge = edges[0][0]
                edge_id = closest_edge.getID()
                closest_pos = closest_edge.getClosestLanePosDist((x, y))[1]
                
                new_point = {
                    "type": point_type,
                    "edge_id": edge_id,
                    "position": closest_pos,
                    "x": x,
                    "y": y,
                    "lat": manual_lat,
                    "lon": manual_lon
                }
                
                st.session_state.selected_points.append(new_point)
                st.session_state.map_key += 1
                st.success(f"✅ {point_type} eklendi!")
                st.rerun()
            else:
                st.error("❌ Bu konumda SUMO ağı bulunamadı.")
        except Exception as e:
            st.error(f"❌ Hata: {e}")

# Alt kısım - Dosya oluşturma
st.markdown("---")
st.subheader("📁 Dosya Oluşturma")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("💾 cs.add.xml Oluştur", disabled=len(st.session_state.selected_points) == 0):
        try:
            with open("cs.add.xml", "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<additional xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/additional_file.xsd">\n')
                
                for i, point in enumerate(st.session_state.selected_points, start=1):
                    if point['type'] == 'containerStop':
                        f.write(f'    <containerStop id="cs_{i}" lane="{point["edge_id"]}_0" startPos="{point["position"]:.2f}" endPos="{point["position"] + 5:.2f}"/>\n')
                    elif point['type'] == 'chargingStation':
                        f.write(f'    <chargingStation id="cs_{i}" lane="{point["edge_id"]}_0" startPos="{point["position"]:.2f}" endPos="{point["position"] + 5:.2f}" power="50000"/>\n')
                
                f.write('</additional>\n')
            
            st.success("✅ cs.add.xml dosyası başarıyla oluşturuldu!")
            
        except Exception as e:
            st.error(f"❌ Dosya oluşturma hatası: {e}")

with col2:
    if st.button("📄 JSON Dışa Aktar", disabled=len(st.session_state.selected_points) == 0):
        try:
            export_data = {
                "selected_points": st.session_state.selected_points,
                "clicked_history": st.session_state.clicked_history,
                "network_bounds": network_bounds
            }
            with open("selected_points.json", "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            st.success("✅ JSON dosyası oluşturuldu!")
        except Exception as e:
            st.error(f"❌ JSON dışa aktarma hatası: {e}")

with col3:
    uploaded_file = st.file_uploader("📁 JSON İçe Aktar", type="json")
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            if "selected_points" in data:
                st.session_state.selected_points = data["selected_points"]
            if "clicked_history" in data:
                st.session_state.clicked_history = data["clicked_history"]
            st.session_state.map_key += 1
            st.success("✅ JSON dosyası yüklendi!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ JSON yükleme hatası: {e}")

# İstatistikler
if st.session_state.selected_points:
    st.markdown("---")
    st.subheader("📊 İstatistikler")
    
    container_stops = len([p for p in st.session_state.selected_points if p['type'] == 'containerStop'])
    charging_stations = len([p for p in st.session_state.selected_points if p['type'] == 'chargingStation'])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Container Stops", container_stops)
    with col2:
        st.metric("Charging Stations", charging_stations)
    with col3:
        st.metric("Toplam Nokta", len(st.session_state.selected_points))