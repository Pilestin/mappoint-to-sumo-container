# SUMO Nokta Haritalama Projesi

## Proje Genel Bakış
SUMO (Simulation of Urban Mobility), şehir içi ulaşım simülasyonları için kullanılan güçlü bir araçtır. Bu proje, SUMO simülasyonlarında kullanılmak üzere harita üzerinde ilgi noktalarını (POI) haritalamak ve yönetmek için kullanıcı dostu bir çözüm sunar. Kullanıcılar, harita üzerinde noktalar seçabilir, bu noktaları `containerStop` veya `chargingStation` olarak kategorize edebilir ve SUMO uyumlu XML formatında dışa aktarabilir. 

Bu proje, özellikle toplu taşıma ve elektrikli araç altyapısı planlaması gibi senaryolarda kullanılabilir.

### SUMO ile Çalışma
SUMO ortamınızı hazırlamak için aşağıdaki adımları izleyebilirsiniz:
1. SUMO’nun kurulu olduğundan emin olun.
2. OSMWebWizard aracını kullanarak çalışma bölgenizi seçin ve çıktı dosyalarını oluşturun.
3. SUMO GUI ile bölgenizi yükleyin ve simülasyonunuzu başlatın.

Daha fazla bilgi için SUMO dökümantasyonuna göz atabilirsiniz:
- [SUMO OSM Import](https://sumo.dlr.de/docs/Networks/Import/OpenStreetMap.html)
- [SUMO OSM Tools](https://sumo.dlr.de/docs/Tools/Import/OSM.html)
- [SUMO OSM Web Wizard](https://sumo.dlr.de/docs/Tutorials/OSMWebWizard.html)
- [SUMO Netconvert](https://sumo.dlr.de/docs/netconvert.html)

## Proje Yapısı

### Ana Konfigürasyon Dosyası
- **osm.sumocfg**: SUMO simülasyonunun ana konfigürasyon dosyası. Bu dosya tüm diğer dosyaları bir araya getirir ve simülasyonun nasıl çalışacağını belirler.

### Çalıştırma Dosyaları
- **run.bat**: Simülasyonu grafik arayüzü (SUMO-GUI) ile başlatan batch dosyası.
- **build.bat**: Simülasyon verilerini oluşturan batch dosyası (OSM verilerinden rota ve trip dosyaları oluşturur).

### Ağ ve Harita Dosyaları
- **osm.net.xml.gz**: SUMO ağ dosyası (yollar, kavşaklar, trafik ışıkları).
- **osm_bbox.osm.xml.gz**: Orijinal OpenStreetMap verisi.
- **osm.poly.xml.gz**: Poligon verileri (binalar, park alanları vb.).
- **osm.netccfg**: Ağ oluşturma konfigürasyonu.
- **osm.polycfg**: Poligon dönüştürme konfigürasyonu.

### Toplu Taşıma Dosyaları
- **osm_pt.rou.xml**: Toplu taşıma araçlarının rotaları (tramvay hatları).
- **osm_ptlines.xml**: Toplu taşıma hat tanımlamaları.
- **osm_stops.add.xml**: Toplu taşıma durakları.
- **stopinfos.xml**: Durak bilgileri ve istatistikleri.

### Trafik ve Seyahat Dosyaları
- **osm.passenger.trips.xml**: Özel araç seyahatleri.
- **trips.trips.xml**: Toplu taşıma seyahatleri.
- **vehroutes.xml**: Araç rotaları ve durak bilgileri.

### Görselleştirme
- **osm.view.xml**: SUMO-GUI görüntü ayarları.

### Hata Dosyaları
- **trips.trips.xml.errorlog**: Hata log dosyası (şu an boş).

## Uygulamalar

### 1. Addition App (`addition-app.py`)
- Kullanıcıların harita ile etkileşim kurmasını, noktalar seçmesini ve kategorize etmesini sağlar.
- Seçilen noktalar haritada görüntülenir ve bir listeye kaydedilir.
- Kullanıcılar, seçilen noktaları SUMO uyumlu formatta bir XML dosyasına (`cs.add.xml`) dışa aktarabilir.

### 2. Point Selector (`point-selector.py`)
- Belirli bir sınır içinde noktalar seçmek için gelişmiş işlevsellik sağlar.
- Kullanıcılar, doğru edge ve lane bilgilerini sağlamak için bir SUMO ağ dosyası (`.net.xml`) yükleyebilir.
- Noktalar manuel olarak veya haritaya tıklanarak eklenebilir.
- Uygulama, her nokta için en yakın edge ve pozisyonu hesaplar.
- Kullanıcılar, noktaları SUMO uyumlu formatta bir XML dosyasına dışa aktarabilir.

## Özellikler
- Noktaları seçmek ve kategorize etmek için etkileşimli harita.
- İki nokta türü için destek: `containerStop` ve `chargingStation`.
- Noktaları SUMO uyumlu XML formatında kaydetme işlevi.
- Nokta seçimini sınırlamak için isteğe bağlı sınır tanımı.
- Doğru edge ve lane bilgileri için SUMO ağ dosyalarıyla entegrasyon.
- Manuel koordinat girişi ve harita tıklama desteği.

## Nasıl Kullanılır

### Addition App (`addition-app.py`)
1. Uygulamayı Streamlit kullanarak çalıştırın:
   ```bash
   streamlit run addition-app.py
   ```
2. Harita ile etkileşim kurarak noktalar seçin.
3. Her noktayı `containerStop` veya `chargingStation` olarak kategorize edin.
4. Seçilen noktaların listesini yan panelde görüntüleyin.
5. "Save to cs.add.xml" butonuna tıklayarak noktaları bir XML dosyasına dışa aktarın.

### Point Selector (`point-selector.py`)
1. Uygulamayı Streamlit kullanarak çalıştırın:
   ```bash
   streamlit run point-selector.py
   ```
2. Doğru edge ve lane bilgileri için isteğe bağlı olarak bir SUMO ağ dosyası (`.net.xml`) yükleyin.
3. Nokta seçimi için bir sınır tanımlayın.
4. Harita ile etkileşim kurarak noktalar seçin veya koordinatları manuel olarak girerek noktalar ekleyin.
5. Her noktayı `containerStop` veya `chargingStation` olarak kategorize edin.
6. Seçilen noktaların listesini yan panelde görüntüleyin.
7. "SUMO XML Oluştur" butonuna tıklayarak noktaları bir XML dosyasına dışa aktarın.

## Gereksinimler
- Python 3.7 veya üzeri
- Streamlit
- Folium
- SUMO Python API (`sumolib`)

## Kurulum
1. Depoyu klonlayın.
2. Gerekli Python paketlerini yükleyin:
   ```bash
   pip install streamlit folium sumolib
   ```
3. İstediğiniz uygulamayı çalıştırın:
   ```bash
   streamlit run addition-app.py
   ```
   veya
   ```bash
   streamlit run point-selector.py
   ```

## Çıktı
Her iki uygulama da SUMO uyumlu formatta seçilen noktaları içeren bir XML dosyası (`cs.add.xml`) oluşturur. Dosya, nokta türü, edge ID, lane ve pozisyon gibi ayrıntıları içerir.

### Örnek Çıktı
```xml
<additional>
    <chargingStation id="cs1" lane="edge1_0" pos="50.0"/>
    <containerStop id="stop1" lane="edge2_1" pos="100.0"/>
</additional>
```

## Lisans
Bu proje MIT Lisansı altında lisanslanmıştır.
