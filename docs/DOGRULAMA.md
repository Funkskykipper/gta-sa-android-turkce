# Yerel inceleme notu — 30 Eylül 2026

## Tamamlanan kontroller

- 12 otomatik test geçti. Testler uzun çevirilerde sonraki GXT tablolarının korunmasını, bozuk dosyaların reddedilmesini, tuş/sayı alanlarını, font adreslerini, APK hizalamasını ve kaynakların üzerine yazılmamasını kapsar.
- Araç gerçek 2.11.311 kaynak parçaları ve çevirmenin standart PC paketiyle komut satırından çalıştırıldı. 12.950 değişmiş kayıt içeren yeni APK paketi üretildi.
- Oluşturulan 11 metin/font varlığı, 26 Eylül'de telefonda kontrol edilen yama varlıklarıyla **bayt bayt aynı** bulundu.
- Kaynak oyun parçaları, ana PC çevirisi, fontlar, APK çıktıları ve imzalama anahtarı yerel reponun dışında tutuldu.
- Yerel paylaşım taraması, izlenen dosyalarda yasak dosya türü, bilinen erişim belirteci kalıbı veya kişisel bilgisayar yolu bulmadı. Bu tarama kapsamlı bir güvenlik veya lisans incelemesi değildir.

## Sınırlar

- Paket oluşturma komut satırından test edildi. Dosya seçim penceresi bu çalışma ortamının Tcl/Tk başlatma hatası nedeniyle görsel olarak test edilemedi. Normal Python kurulumunda Tkinter bileşeni gerekir; pencere açılamazsa komut satırı kullanılabilir.
- Bu incelemede telefona yeni kurulum yapılmadı. Cihazdaki önceki Türkçe yama değiştirilmedi.
- Önceki cihaz denemesi menüler ve giriş sahnesi altyazılarıyla sınırlıdır; bütün görevlerin oynanması anlamına gelmez.
- Bu rapor yayımlama öncesi yerel doğrulamayı kaydeder.
