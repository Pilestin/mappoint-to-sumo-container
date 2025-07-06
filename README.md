# SUMO Nokta Haritalama Projesi

## Proje Genel Bakış
Bu proje, SUMO (Simulation of Urban Mobility) simülasyonlarında kullanılmak üzere harita üzerinde ilgi noktalarını (POI) haritalamak ve yönetmek için araçlar sağlar. Kullanıcılar, harita üzerinde noktalar seçabilir, bunları `containerStop` veya `chargingStation` olarak kategorize edebilir ve verileri SUMO uyumlu XML formatında dışa aktarabilir. Proje iki ana uygulamayı içerir:

1. **Addition App** (`addition-app.py`):
   - Kullanıcıların harita ile etkileşim kurmasını, noktalar seçmesini ve kategorize etmesini sağlar.
   - Seçilen noktalar haritada görüntülenir ve bir listeye kaydedilir.
   - Kullanıcılar, seçilen noktaları SUMO uyumlu formatta bir XML dosyasına (`cs.add.xml`) dışa aktarabilir.

2. **Point Selector** (`point-selector.py`):
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

## Nasıl Kullanılır

### Addition App (`addition-app.py`)
1. Uygulamayı Streamlit kullanarak çalıştırın.
2. Harita ile etkileşim kurarak noktalar seçin.
3. Her noktayı `containerStop` veya `chargingStation` olarak kategorize edin.
4. Seçilen noktaların listesini yan panelde görüntüleyin.
5. "Save to cs.add.xml" butonuna tıklayarak noktaları bir XML dosyasına dışa aktarın.

### Point Selector (`point-selector.py`)
1. Uygulamayı Streamlit kullanarak çalıştırın.
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

## Lisans
Bu proje MIT Lisansı altında lisanslanmıştır.
