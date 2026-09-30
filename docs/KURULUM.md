# Kaynak dosyalar, imzalama ve telefona kurulum

Bu rehber klasik GTA San Andreas **2.11.311 / ARM64** için hazırlanmıştır. Telefonundan alınan orijinal dosyaları ayrı bir yerde sakla. Oyun verisi ve kayıt dosyaları APK parçalarının içinde değildir; APK yedeği kayıt yedeği sayılmaz.

## 1. Kendi oyun parçalarını edin

Google Play'den satın aldığın oyunun orijinal parçaları gerekir. Daha önce yamalanmış veya yeniden imzalanmış kaynaklar sürüm kontrolünden geçmez.

[Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) içindeki ADB ile, USB hata ayıklamasına izin verdiğin cihazda şu salt okunur komutları kullanabilirsin:

```powershell
adb devices
adb shell pm path com.rockstargames.gtasa
```

İkinci komut her parçanın gerçek cihaz yolunu `package:` önekiyle listeler. Her yol için öneki kaldırıp `adb pull "CIHAZDAKI_TAM_YOL" "BILGISAYARDAKI_HEDEF_DOSYA"` kullan. Dosya adlarını değiştirme. Cihazda görülen gerçek yolları kullan; internetteki örnek APK yollarını kopyalama.

Beklenen yapı:

```text
oyun-dosyalarim/
  base.apk
  split_data_main.apk
  split_config.arm64_v8a.apk
  split_config.tr.apk            (cihazda varsa)
  split_config.xxxhdpi.apk       (cihazının ekran parçası farklı olabilir)
```

Araç temel APK ve ARM64 bileşenini, değiştirilecek oyun varlıklarını ve çeviri/font sürümlerini SHA-256 ile kontrol eder. Bir sürüm uyuşmazlığında orijinal dosyayı değiştirmez. Güncel Play Store sürümü farklıysa bu araç onu destekliyor sayılmaz; sürüm kontrolünü kaldırma.

## 2. Yamayı oluştur

README'deki arayüzü veya komut satırını kullan. Bu aşama yalnızca bilgisayarda çalışır. Çıktıdaki `rapor.json` değişen kayıt sayısını ve APK parmak izlerini gösterir.

## 3. Bütün APK parçalarını aynı anahtarla imzala

APK içeriği değiştiği için eski imza geçerli değildir. `unsigned` klasöründeki **base, yapılandırma ve veri parçalarının tamamı** aynı kişisel anahtarla yeniden imzalanmalıdır. Yalnızca veri parçasını imzalamak yeterli değildir.

Bu projedeki cihaz denemesinde Java ve [uber-apk-signer 1.3.0](https://github.com/patrickfav/uber-apk-signer/releases/tag/v1.3.0) kullanıldı. Araç projeye dahil değildir. Kaynağından edinip ayrıca incele. Kendi anahtarını Java'nın `keytool` aracıyla oluşturabilirsin; komut parolayı etkileşimli olarak sorar:

```powershell
keytool -genkeypair -keystore "C:\GTA-ozel\yama.jks" -alias gta-tr -keyalg RSA -keysize 3072 -validity 3650
```

`C:\GTA-ozel` klasörünü önceden kendin oluştur. Anahtarını ve parolasını koru; sonraki yerel yama güncellemeleri aynı anahtara ihtiyaç duyar. Anahtarı, parolayı veya kişisel telefon yedeğini repoya koyma.

Ardından kendi yollarınla imzala:

```powershell
java -jar "C:\Araclar\uber-apk-signer.jar" -a "C:\GTA-turkce-yeni\unsigned" -o "C:\GTA-turkce-yeni\signed" --allowResign --skipZipAlign --ks "C:\GTA-ozel\yama.jks" --ksAlias gta-tr
```

Parola sorularını terminalde yanıtla. İmzalama aracı her APK için başarılı doğrulama bildirmelidir. `--skipZipAlign`, telefon testinde kullanılan akışla aynıdır; bu projenin değiştirdiği veri APK'sındaki sıkıştırılmamış girdiler 4 bayta hizalanır. Bu, bütün Android sürümlerinde uyumluluk garantisi değildir.

## 4. Kurulumdan önce imza durumunu ayır

**Telefonda daha önce aynı kişisel anahtarla yamalanmış oyun varsa:** `-r` güncellemesi kullanılabilir.

**Telefonda Play Store'un orijinal imzalı oyunu varsa:** kişisel imzayla doğrudan güncelleme normalde imza uyuşmazlığına takılır. Bu araç böyle bir durumda oyunu kaldırmaz. Önce kayıtlarının yedeğini ve geri dönüş yolunu netleştir. Oyunu kaldırmak özel oyun verisini silebilir ve ses paketlerini tekrar indirmeyi gerektirebilir. APK parçalarını yedeklemek bu verileri korumaz.

Yüklenecek parçaları açıkça seç. Aşağıdaki örnekte ekran/dil parçalarını kendi dosyalarınla eşleştir:

```powershell
adb install-multiple -r --no-incremental -i com.android.vending "C:\GTA-turkce-yeni\signed\base-signed.apk" "C:\GTA-turkce-yeni\signed\split_config.arm64_v8a-signed.apk" "C:\GTA-turkce-yeni\signed\split_config.tr-signed.apk" "C:\GTA-turkce-yeni\signed\split_config.xxxhdpi-signed.apk" "C:\GTA-turkce-yeni\signed\split_data_main-signed.apk"
```

`-i com.android.vending` denenen kurulumda mağaza kaynak bilgisini korumak ve oyunun ek ses paketini indirebilmesi için kullanıldı. Oyunu satın alma veya lisans gerekliliğini ortadan kaldırmaz. Başka cihazlarda aynı sonucu garanti etmez.

## 5. Oyunda kontrol et

Rockstar hesap ekranında hesapsız devam etmek için **Skip Sign in** seçilebilir. Bu ekran İngilizce kalır.

Oyun içinde **Görüntü → Altyazılar → Açık** ayarını kontrol et. Ana menüde Türkçe metni, ilk sahnede altyazıyı ve ş/ğ/ı/İ gibi harfleri kontrol et. Seslendirmeler İngilizcedir.

Oyun güncellenirse yama değişebilir. Bir APK veya imza hatasında tekrar tekrar kaldırma/kurma yapmak yerine hata mesajını ve `rapor.json` dosyasını incele; özel anahtarını paylaşma.
