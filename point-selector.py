import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import xml.etree.ElementTree as ET
import xml.dom.minidom
import math
import json
from datetime import datetime
import io
import os
import sumolib

# Sayfa konfigürasyonu
st.set_page_config(
    page_title="SUMO Point Mapper",
    page_icon="🗺️",
    layout="wide"
)

# Session state başlatma
if 'points' not in st.session_state:
    st.session_state.points = []
if 'bounds' not in st.session_state:
    st.session_state.bounds = None
if 'map_center' not in st.session_state:
    st.session_state.map_center = [39.7767, 30.5206]  # Eskişehir koordinatları
if 'last_clicked_coords' not in st.session_state:
    st.session_state.last_clicked_coords = None
if 'show_add_form' not in st.session_state:
    st.session_state.show_add_form = False
if 'net_file_path' not in st.session_state:
    st.session_state.net_file_path = None

def calculate_distance(lat1, lon1, lat2, lon2):
    """İki nokta arasındaki mesafeyi hesaplar (Haversine formülü)"""
    R = 6371000  # Dünya yarıçapı (metre)
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def get_nearest_edge_from_sumo(lat, lon, net_file_path):
    """SUMO ağ dosyasından en yakın edge'i bulur"""
    try:
        if not os.path.exists(net_file_path):
            return None
            
        # SUMO ağını yükle
        net = sumolib.net.readNet(net_file_path)
        
        # Lat/Lon'u UTM koordinatlarına dönüştür
        x, y = net.convertLonLat2XY(lon, lat)
        
        # En yakın edge'i bul
        edges = net.getNeighboringEdges(x, y, r=100)  # 100 metre yarıçap
        
        if not edges:
            # Daha geniş arama yap
            edges = net.getNeighboringEdges(x, y, r=500)
        
        if edges:
            # En yakın edge'i seç
            closest_edge = min(edges, key=lambda edge_dist: edge_dist[1])
            edge = closest_edge[0]
            
            # Lane ID oluştur (ilk lane'i seç)
            lane_id = edge.getID() + "_0"
            
            # Edge üzerindeki pozisyonu hesapla
            edge_shape = edge.getShape()
            min_dist = float('inf')
            best_pos = 0.0
            
            for i, point in enumerate(edge_shape):
                dist = math.sqrt((point[0] - x)**2 + (point[1] - y)**2)
                if dist < min_dist:
                    min_dist = dist
                    # Pozisyonu edge başlangıcından mesafe olarak hesapla
                    if i == 0:
                        best_pos = 0.0
                    else:
                        # Edge başlangıcından bu noktaya kadar olan mesafe
                        total_dist = 0.0
                        for j in range(i):
                            p1 = edge_shape[j]
                            p2 = edge_shape[j + 1]
                            total_dist += math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                        best_pos = total_dist
            
            # StartPos ve EndPos hesapla
            start_pos = max(0.0, best_pos - 5.0)  # 5 metre öncesinden
            end_pos = min(edge.getLength(), best_pos + 5.0)  # 5 metre sonrasına kadar
            
            return {
                'lane': lane_id,
                'edge_id': edge.getID(),
                'startPos': round(start_pos, 2),
                'endPos': round(end_pos, 2),
                'edge_length': edge.getLength(),
                'distance_to_edge': round(min_dist, 2)
            }
        
        return None
        
    except Exception as e:
        st.error(f"SUMO ağ dosyası işlenirken hata: {str(e)}")
        return None

def get_nearest_road(lat, lon):
    """Koordinatlar için en yakın yol bilgisini bulur"""
    # SUMO ağ dosyası yolunu session state'den al
    if 'net_file_path' in st.session_state and st.session_state.net_file_path:
        sumo_result = get_nearest_edge_from_sumo(lat, lon, st.session_state.net_file_path)
        if sumo_result:
            return sumo_result
    
    # SUMO dosyası yoksa varsayılan değerler
    return {
        'lane': f"auto_{abs(hash(str(lat) + str(lon))) % 1000000}_0",
        'edge_id': f"auto_{abs(hash(str(lat) + str(lon))) % 1000000}",
        'startPos': 0.0,
        'endPos': 10.0,
        'edge_length': 100.0,
        'distance_to_edge': 0.0
    }

def create_sumo_xml(points_list):
    """SUMO XML formatında dosya oluşturur"""
    root = ET.Element("additional")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xsi:noNamespaceSchemaLocation", "http://sumo.dlr.de/xsd/additional_file.xsd")
    
    # Yorum ekle
    comment = ET.Comment(f" Generated by SUMO Point Mapper on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ")
    root.insert(0, comment)
    
    container_id = 1
    charging_id = 1
    
    for point in points_list:
        if point['type'] == 'containerStop':
            element = ET.SubElement(root, "containerStop")
            element.set("id", str(container_id))
            if point['name']:
                element.set("name", point['name'])
            element.set("lane", point['lane'])
            element.set("startPos", str(point['startPos']))
            element.set("endPos", str(point['endPos']))
            container_id += 1
            
        elif point['type'] == 'chargingStation':
            element = ET.SubElement(root, "chargingStation")
            element.set("id", f"cs{charging_id}")
            if point['name']:
                element.set("name", point['name'])
            element.set("lane", point['lane'])
            element.set("startPos", str(point['startPos']))
            element.set("endPos", str(point['endPos']))
            element.set("power", "200000.00")
            charging_id += 1
    
    # XML'i güzel formatla
    rough_string = ET.tostring(root, encoding='unicode')
    reparsed = xml.dom.minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")

def create_map():
    """Harita oluşturur"""
    m = folium.Map(
        location=st.session_state.map_center,
        zoom_start=15,
        tiles="OpenStreetMap"
    )
    
    # Sınır çizgisi varsa ekle
    if st.session_state.bounds:
        folium.Rectangle(
            bounds=st.session_state.bounds,
            color='red',
            weight=2,
            fill=False,
            popup="Çalışma Alanı Sınırları"
        ).add_to(m)
    
    # Mevcut noktaları haritaya ekle
    for i, point in enumerate(st.session_state.points):
        color = 'blue' if point['type'] == 'containerStop' else 'green'
        icon = 'bus' if point['type'] == 'containerStop' else 'plug'
        
        folium.Marker(
            location=[point['lat'], point['lon']],
            popup=f"{point['name'] or 'İsimsiz'} ({point['type']})",
            tooltip=f"ID: {i+1}, Type: {point['type']}",
            icon=folium.Icon(color=color, icon=icon)
        ).add_to(m)
    
    return m

# Ana uygulama
def main():
    st.title("🗺️ SUMO Point Mapper")
    st.markdown("Harita üzerinde nokta işaretleyip SUMO XML formatında kaydedin")
    
    # Yan panel
    with st.sidebar:
        st.header("⚙️ Kontroller")
        
        # SUMO ağ dosyası yükleme
        st.subheader("📁 SUMO Ağ Dosyası")
        
        uploaded_net = st.file_uploader(
            "SUMO .net.xml dosyası seçin",
            type=['xml'],
            help="SUMO ağ dosyası yükleyerek doğru edge ID ve pozisyon bilgilerini alın"
        )
        
        if uploaded_net is not None:
            # Geçici dosya oluştur
            temp_net_path = f"temp_net_{uploaded_net.name}"
            with open(temp_net_path, "wb") as f:
                f.write(uploaded_net.getbuffer())
            
            st.session_state.net_file_path = temp_net_path
            st.success(f"Ağ dosyası yüklendi: {uploaded_net.name}")
            
            # Dosya bilgilerini göster
            try:
                net = sumolib.net.readNet(temp_net_path)
                st.info(f"📊 Ağ İstatistikleri:\n- Edge sayısı: {len(net.getEdges())}\n- Intersection sayısı: {len(net.getNodes())}")
            except Exception as e:
                st.error(f"Ağ dosyası okunamadı: {str(e)}")
                st.session_state.net_file_path = None
        
        elif st.session_state.net_file_path:
            st.info("✅ Ağ dosyası yüklü")
            if st.button("🗑️ Ağ Dosyasını Kaldır"):
                if os.path.exists(st.session_state.net_file_path):
                    os.remove(st.session_state.net_file_path)
                st.session_state.net_file_path = None
                st.rerun()
        else:
            st.warning("⚠️ SUMO ağ dosyası yüklenmedi. Varsayılan değerler kullanılacak.")
        
        st.markdown("---")
        
        # Sınır belirleme
        st.subheader("🔲 Çalışma Alanı")
        
        col1, col2 = st.columns(2)
        with col1:
            min_lat = st.number_input("Min Enlem", value=39.770, format="%.6f")
            min_lon = st.number_input("Min Boylam", value=30.515, format="%.6f")
        with col2:
            max_lat = st.number_input("Max Enlem", value=39.783, format="%.6f")
            max_lon = st.number_input("Max Boylam", value=30.525, format="%.6f")
        
        if st.button("Sınırları Ayarla"):
            st.session_state.bounds = [[min_lat, min_lon], [max_lat, max_lon]]
            st.session_state.map_center = [(min_lat + max_lat) / 2, (min_lon + max_lon) / 2]
            st.success("Sınırlar ayarlandı!")
        
        # Nokta ekleme
        st.subheader("📍 Nokta Ekleme")
        
        point_type = st.selectbox(
            "Nokta Tipi",
            ["containerStop", "chargingStation"],
            format_func=lambda x: "🚏 Container Stop" if x == "containerStop" else "🔌 Charging Station"
        )
        
        point_name = st.text_input("Nokta Adı (İsteğe bağlı)")
        
        # Manuel koordinat girişi
        st.subheader("📝 Manuel Koordinat")
        manual_lat = st.number_input("Enlem", value=39.7767, format="%.6f", key="manual_lat")
        manual_lon = st.number_input("Boylam", value=30.5206, format="%.6f", key="manual_lon")
        
        if st.button("Manuel Nokta Ekle"):
            # Sınır kontrolü
            if st.session_state.bounds:
                bounds = st.session_state.bounds
                if not (bounds[0][0] <= manual_lat <= bounds[1][0] and 
                       bounds[0][1] <= manual_lon <= bounds[1][1]):
                    st.error("Nokta belirlenen sınırlar dışında!")
                    return
            
            # Yol bilgisi al
            with st.spinner("SUMO ağından edge bilgisi alınıyor..."):
                road_info = get_nearest_road(manual_lat, manual_lon)
            
            # Nokta ekle
            new_point = {
                'lat': manual_lat,
                'lon': manual_lon,
                'type': point_type,
                'name': point_name or f"{point_type}_{len(st.session_state.points) + 1}",
                'lane': road_info['lane'],
                'edge_id': road_info.get('edge_id', 'unknown'),
                'startPos': road_info['startPos'],
                'endPos': road_info['endPos'],
                'edge_length': road_info.get('edge_length', 0),
                'distance_to_edge': road_info.get('distance_to_edge', 0)
            }
            
            st.session_state.points.append(new_point)
            
            # Detaylı bilgi göster
            if st.session_state.net_file_path:
                st.success(f"✅ Nokta eklendi: {new_point['name']}")
                st.info(f"📍 Edge: {new_point['edge_id']}\n🚩 Lane: {new_point['lane']}\n📏 Pozisyon: {new_point['startPos']:.2f} - {new_point['endPos']:.2f}\n📐 Edge'e mesafe: {new_point['distance_to_edge']:.2f}m")
            else:
                st.success(f"Nokta eklendi: {new_point['name']} (Varsayılan değerlerle)")
        
        # Mevcut noktalar
        st.subheader("📋 Mevcut Noktalar")
        
        if st.session_state.points:
            for i, point in enumerate(st.session_state.points):
                with st.expander(f"{'🚏' if point['type'] == 'containerStop' else '🔌'} {point['name']}"):
                    st.write(f"**Koordinatlar:** {point['lat']:.6f}, {point['lon']:.6f}")
                    st.write(f"**Edge ID:** {point.get('edge_id', 'N/A')}")
                    st.write(f"**Lane:** {point['lane']}")
                    st.write(f"**Pozisyon:** {point['startPos']:.2f} - {point['endPos']:.2f}")
                    if 'distance_to_edge' in point:
                        st.write(f"**Edge'e mesafe:** {point['distance_to_edge']:.2f}m")
                    
                    if st.button("🗑️ Sil", key=f"del_{i}"):
                        st.session_state.points.pop(i)
                        st.rerun()
            
            # Tümünü temizle
            if st.button("🗑️ Tümünü Temizle"):
                st.session_state.points = []
                st.rerun()
            
            # XML oluştur ve indir
            st.subheader("💾 XML Kaydet")
            
            if st.button("SUMO XML Oluştur"):
                try:
                    xml_content = create_sumo_xml(st.session_state.points)
                    
                    # İndirme butonu
                    st.download_button(
                        label="📥 XML Dosyasını İndir",
                        data=xml_content,
                        file_name=f"sumo_points_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml",
                        mime="application/xml"
                    )
                    
                    st.success("XML dosyası hazırlandı!")
                    
                    # Önizleme
                    with st.expander("XML Önizleme"):
                        st.code(xml_content, language="xml")
                
                except Exception as e:
                    st.error(f"XML oluşturulurken hata: {str(e)}")
        
        else:
            st.info("Henüz nokta eklenmedi")
    
    # Ana harita alanı
    st.header("🗺️ Harita")
    
    # Harita oluştur ve göster
    map_obj = create_map()
    
    # Harita etkileşimi
    map_data = st_folium(
        map_obj,
        key="main_map",
        use_container_width=True,
        returned_objects=["last_clicked"]
    )
    
    # Tıklama session state'ini kontrol et
    if 'last_clicked_coords' not in st.session_state:
        st.session_state.last_clicked_coords = None
    if 'show_add_form' not in st.session_state:
        st.session_state.show_add_form = False
    
    # Harita tıklaması ile nokta ekleme
    if map_data['last_clicked'] and map_data['last_clicked'] != st.session_state.last_clicked_coords:
        clicked_lat = map_data['last_clicked']['lat']
        clicked_lon = map_data['last_clicked']['lng']
        
        # Yeni tıklama koordinatlarını kaydet
        st.session_state.last_clicked_coords = map_data['last_clicked']
        
        # Sınır kontrolü
        if st.session_state.bounds:
            bounds = st.session_state.bounds
            if not (bounds[0][0] <= clicked_lat <= bounds[1][0] and 
                   bounds[0][1] <= clicked_lon <= bounds[1][1]):
                st.warning("Tıklanan nokta belirlenen sınırlar dışında!")
                st.session_state.show_add_form = False
            else:
                st.session_state.show_add_form = True
                st.session_state.clicked_lat = clicked_lat
                st.session_state.clicked_lon = clicked_lon
        else:
            st.session_state.show_add_form = True
            st.session_state.clicked_lat = clicked_lat
            st.session_state.clicked_lon = clicked_lon
    
    # Nokta ekleme formu göster
    if st.session_state.show_add_form and hasattr(st.session_state, 'clicked_lat'):
        st.markdown("---")
        st.write(f"📍 **Tıklanan konum:** {st.session_state.clicked_lat:.6f}, {st.session_state.clicked_lon:.6f}")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            form_type = st.selectbox(
                "Nokta Tipi",
                ["containerStop", "chargingStation"],
                format_func=lambda x: "🚏 Container Stop" if x == "containerStop" else "🔌 Charging Station",
                key="click_type"
            )
        
        with col2:
            form_name = st.text_input("Nokta Adı (İsteğe bağlı)", key="click_name")
        
        with col3:
            st.write("")  # Boşluk için
            col3a, col3b = st.columns(2)
            with col3a:
                if st.button("✅ Ekle", key="add_clicked_point"):
                    with st.spinner("SUMO ağından edge bilgisi alınıyor..."):
                        road_info = get_nearest_road(st.session_state.clicked_lat, st.session_state.clicked_lon)
                    
                    new_point = {
                        'lat': st.session_state.clicked_lat,
                        'lon': st.session_state.clicked_lon,
                        'type': form_type,
                        'name': form_name or f"{form_type}_{len(st.session_state.points) + 1}",
                        'lane': road_info['lane'],
                        'edge_id': road_info.get('edge_id', 'unknown'),
                        'startPos': road_info['startPos'],
                        'endPos': road_info['endPos'],
                        'edge_length': road_info.get('edge_length', 0),
                        'distance_to_edge': road_info.get('distance_to_edge', 0)
                    }
                    
                    st.session_state.points.append(new_point)
                    
                    # Detaylı bilgi göster
                    if st.session_state.net_file_path:
                        st.success(f"✅ Nokta eklendi: {new_point['name']}")
                        st.info(f"📍 Edge: {new_point['edge_id']}\n🚩 Lane: {new_point['lane']}\n📏 Pozisyon: {new_point['startPos']:.2f} - {new_point['endPos']:.2f}")
                    else:
                        st.success(f"Nokta eklendi: {new_point['name']} (Varsayılan değerlerle)")
                    
                    # Formu gizle
                    st.session_state.show_add_form = False
                    st.rerun()
            
            with col3b:
                if st.button("❌ İptal", key="cancel_clicked_point"):
                    st.session_state.show_add_form = False
                    st.rerun()
    
    # Durum bilgisi
    st.info(f"Toplam {len(st.session_state.points)} nokta işaretlendi")
    
    # Kullanım talimatları
    with st.expander("📖 Kullanım Talimatları"):
        st.markdown("""
        **SUMO Ağ Dosyası Yükleme:**
        1. Sol panelden SUMO .net.xml dosyasını yükleyin
        2. Dosya yüklendikten sonra doğru edge ID ve pozisyon bilgileri alınır
        3. Ağ dosyası yoksa varsayılan değerler kullanılır
        
        **Harita Üzerinde Nokta Ekleme:**
        1. Harita üzerinde istediğiniz yere tıklayın
        2. Açılan formda nokta tipini seçin
        3. İsterseniz nokta adı verin
        4. "✅ Ekle" butonuna tıklayın
        
        **Manuel Koordinat Girişi:**
        1. Sol panelden enlem ve boylam değerlerini girin
        2. Nokta tipini seçin
        3. "Manuel Nokta Ekle" butonuna tıklayın
        
        **Sınır Belirleme:**
        1. Min/Max enlem ve boylam değerlerini girin
        2. "Sınırları Ayarla" butonuna tıklayın
        3. Kırmızı çerçeve çalışma alanınızı gösterir
        
        **XML Kaydetme:**
        1. Tüm noktaları işaretledikten sonra
        2. "SUMO XML Oluştur" butonuna tıklayın
        3. "XML Dosyasını İndir" ile dosyayı kaydedin
        
        **Nokta Tipleri:**
        - 🚏 **Container Stop**: Mavi işaretçi, otobüs durağı
        - 🔌 **Charging Station**: Yeşil işaretçi, şarj istasyonu
        
        **SUMO Entegrasyonu:**
        - Gerçek edge ID'leri SUMO ağından alınır
        - StartPos ve EndPos edge üzerindeki gerçek pozisyonlar
        - Edge'e olan mesafe bilgisi gösterilir
        - Koordinatlar UTM formatına dönüştürülür
        """)
        
        # Temizlik işlemi
        if st.button("🧹 Geçici Dosyaları Temizle"):
            temp_files = [f for f in os.listdir('.') if f.startswith('temp_net_')]
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass
            st.success("Geçici dosyalar temizlendi!")

if __name__ == "__main__":
    main()