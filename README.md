# GTA San Andreas Android Türkçe Yama Oluşturucu

Satın aldığın **klasik GTA San Andreas Android 2.11.311** oyununu, kendi bilgisayarında Türkçe yamaya hazırlayan araç. Menü, görev, altyazı ve dokunmatik yardım metinlerini birleştirir; Türkçe harflerin yazı tiplerini mobil biçime dönüştürür.

**Bu repo oyun veya hazır APK içermez.** Orijinal oyun parçalarını ve CriminaL277'nin PC çeviri ZIP paketini kendin sağlamalısın. Araç dosyaları yerelde işler; indirme, telefona kurulum veya oyun kaldırma işlemi yapmaz.

## Durum

- Desteklenen kaynak: test edilen Google Play **2.11.311 / ARM64** dosyaları. Dosya parmak izleri farklıysa işlem durur.
- İlk cihaz testi: **OPPO Reno14 Pro 5G / ColorOS 16.0.9**. Menüler ve giriş sahnesi altyazıları kontrol edildi.
- **12.950 metin kaydı** değiştirildi; 17.173 kayıt yapısal olarak doğrulandı. 1.043 kayıt için bu projede hazırlanan mobil ek çeviriler kullanılır.
- Konuşmaların sesi İngilizce kalır. Rockstar hesap ekranı ayrı bir bileşendir ve İngilizce kalır.
- Tüm görevler baştan sona oynanarak test edilmedi. Özel isimler ve bazı eski/kullanılmayan metinler değişmez. Bu sayı, her metnin çevrildiği anlamına gelmez.
- Definitive Edition, Netflix sürümü, iOS, PC oyunu veya diğer Android sürümleri için değildir.

## Hızlı başlangıç — Windows

1. [Python](https://www.python.org/downloads/windows/) 3.11 veya üstünü kur. Python kurulumundaki `py` başlatıcısı ve Tkinter bileşeni gerekli.
2. Bu projeyi indirip ayrı bir klasöre çıkar.
3. Proje klasöründe terminal açıp bağımlılıkları kur:

   ```powershell
   py -3 -m pip install -r requirements.txt
   ```

4. `Baslat.cmd` dosyasını aç. Üç alanı seç:
   - Orijinal `base.apk`, `split_data_main.apk` ve `split_config.*.apk` parçalarını içeren klasör.
   - [CriminaL277'nin yayın sayfasından](https://forum.donanimhaber.com/grand-theft-auto-san-andreas-2020-turkce-yama-pc-ps2--144764586) edindiğin **standart PC ZIP paketi**. ZIP'i açmana gerek yok; D.E.P. font seçeneği kullanılmaz.
   - Henüz var olmayan yeni bir çıktı klasörü.
5. **Yamayı Oluştur** düğmesine bas.

Çıktı, `unsigned/` altında APK parçalarını ve `rapor.json` dosyasını içerir. **Bu APK'lar henüz kuruluma hazır değildir:** tüm parçalar aynı anahtarla yeniden imzalanmalıdır. [İmzalama ve telefon kurulumu](docs/KURULUM.md) rehberini izle.

İlk çalıştırma için kaynak dosyalara ek olarak birkaç GB boş disk alanı gerekir. Araç kaynak dosyaları değiştirmez ve var olan çıktı klasörünün üzerine yazmaz. Yarım kalan çıktıda `OLUSTURMA-TAMAMLANMADI.txt` bulunur; bu çıktı kullanılmamalıdır.

## Komut satırı

```powershell
py -3 yama.py --oyun "C:\GTA-dosyalarim" --ceviri "C:\Indirilenler\ceviri-pc.zip" --cikti "C:\GTA-turkce-yeni"
```

Linux/macOS üzerinde aynı komut `python3` ile kullanılabilir. Bu sistemlerde arayüz ayrıca Tkinter kurulumu gerektirebilir; Android cihaz testi Windows üzerinde yapıldı.

## Kaynaklar ve paylaşım kapsamı

Ana PC çevirisi ve Türkçe fontlar **CriminaL277**'ye aittir. Bu proje, kullanıcının sağladığı o paketi Android'e uyarlar. [Kaynaklar ve katkı ayrımı](NOTICE.md) dosyasına bak.

Repoda uyarlama kodu, bu çalışma sırasında hazırlanan mobil ek çeviriler, testler ve rehberler bulunur. Oyunun varlıkları, üçüncü taraf çeviri/font paketi, imzalı APK'lar ve anahtarlar bulunmaz. Kendi oluşturduğun çıktıları GitHub'a ekleme. `.gitignore` yanlışlıkla eklemeye karşı yardımcıdır; zorla eklemeyi engellemez.

Bu proje için henüz açık kaynak lisansı atanmadı. Bu proje Rockstar Games veya çevirmen tarafından onaylanmış resmî bir ürün değildir.

## Geliştirici kontrolü

Aracın [yerel doğrulama sonuçlarını ve sınırlarını](docs/DOGRULAMA.md) inceleyebilirsin.

```powershell
py -3 -m unittest discover -s tests -v
py -3 scripts/check_release.py
```

Testler sentetik veriler kullanır; oyun dosyası gerektirmez. `data/supported.json` dosyasındaki parmak izlerini yalnızca yeni sürüm gerçekten incelenip test edildiğinde güncelle. Araç bilinmeyen dosyaları zorla yamalamak için bir seçenek sunmaz.
