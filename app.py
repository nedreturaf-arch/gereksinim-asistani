import streamlit as st
import google.generativeai as genai
import time
from docx import Document
import pypdf as PyPDF2


# ---------------------------------------------------------
# 1. SAYFA VE ARAYÜZ YAPILANDIRMASI
# ---------------------------------------------------------
st.set_page_config(
    page_title="Gereksinim Analiz Asistanı v4.1",
    layout="wide"
)


# ---------------------------------------------------------
# 2. MODEL LİSTESİNİ ÖNBELLEĞE ALMA
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def modelleri_getir(api_key):
    genai.configure(api_key=api_key.strip())
    return [
        m.name.replace("models/", "")
        for m in genai.list_models()
        if "generateContent" in m.supported_generation_methods
    ]


# ---------------------------------------------------------
# 3. GÜVENLİK VE API YÖNETİMİ
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Ayarlar")

    api_key = st.text_input(
        "Gemini API Anahtarınızı girin:",
        type="password"
    )

    st.divider()
    secilen_model = None

    if api_key:
        try:
            modeller = modelleri_getir(api_key)

            if modeller:
                tercih_edilen_model = "gemini-2.5-flash"
                varsayilan_index = 0

                if tercih_edilen_model in modeller:
                    varsayilan_index = modeller.index(tercih_edilen_model)

                secilen_model = st.selectbox(
                    "🤖 Model Seçin:",
                    modeller,
                    index=varsayilan_index
                )
            else:
                st.warning("⚠️ Kullanılabilir model bulunamadı.")

        except Exception as e:
            st.error("⚠️ API Hatası: Bağlantı kurulamadı.")
            st.caption(f"Teknik detay: {e}")


# ---------------------------------------------------------
# 4. ANA EKRAN VE BİLGİLENDİRME
# ---------------------------------------------------------
st.title("🎯 Gereksinim & Kalite Analiz Asistanı")

st.info("""
**📖 Analiz Kapsamı ve Referans Standartlar:**

Bu sistem, gereksinim metinlerini aşağıdaki uluslararası standartlar ve yerel mevzuatlar çerçevesinde denetleyerek, spesifik ifadeleri ilgili standart/prensip ile eşleştirir:

* **IEEE 29148:** Yazılım ve Sistem Mühendisliği — Gereksinim Mühendisliği Standartları
* **ISO/IEC 25010:** Yazılım Ürün Kalitesi ve Sistem Kalite Modelleri
* **ISO/IEC 27001:** Bilgi Güvenliği Yönetim Sistemi Gereksinimleri
* **KVKK:** 6698 Sayılı Kişisel Verilerin Korunması Kanunu
""")

st.divider()


# ---------------------------------------------------------
# 5. YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------
def dosya_oku(dosya):
    if dosya is None:
        return ""

    try:
        dosya_adi = dosya.name.lower()

        if dosya_adi.endswith(".docx"):
            doc = Document(dosya)
            metinler = []

            # Paragrafları oku
            for p in doc.paragraphs:
                temiz = p.text.strip()
                if temiz:
                    metinler.append(temiz)

            # DOCX içindeki tabloları da oku
            for tablo in doc.tables:
                for satir in tablo.rows:
                    hucreler = []

                    for hucre in satir.cells:
                        hucre_metni = hucre.text.strip()
                        if hucre_metni:
                            hucreler.append(hucre_metni)

                    if hucreler:
                        metinler.append(" | ".join(hucreler))

            return "\n".join(metinler).strip()

        elif dosya_adi.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(dosya)
            metinler = []

            for sayfa in pdf_reader.pages:
                sayfa_metni = sayfa.extract_text()
                if sayfa_metni and sayfa_metni.strip():
                    metinler.append(sayfa_metni.strip())

            return "\n".join(metinler).strip()

        return ""

    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        return ""


def sure_formatla(saniye):
    dakika = int(saniye // 60)
    kalan_saniye = round(saniye % 60, 2)

    if dakika > 0:
        return f"{dakika} dk {kalan_saniye} sn"

    return f"{kalan_saniye} sn"


def tablo_veri_satiri_mi(satir):
    temiz_satir = satir.strip()

    if not temiz_satir.startswith("|") or not temiz_satir.endswith("|"):
        return False

    if "---" in temiz_satir:
        return False

    baslik_ifadeleri = [
        "Gereksinimdeki İfade",
        "İhlal Edilen Kriter",
        "KVKK Riski",
        "Güvenlik Riski",
        "Kalite Eksikliği",
        "Başarılı Gereksinim",
        "Standart Karşılığı",
        "Mevzuat Çerçevesi",
        "Referans Madde",
        "Karakteristik ve Analiz",
        "Uyum Önerisi",
        "Hukuki Uyum Önerisi",
        "Teknik Önlem",
        "Kalite Hedefi",
        "Karşıladığı Standartlar",
        "Uyum Gerekçesi"
    ]

    if any(ifade in temiz_satir for ifade in baslik_ifadeleri):
        return False

    bos_uyum_ifadeleri = [
        "✅",
        "⚠️"
    ]

    if any(ifade in temiz_satir for ifade in bos_uyum_ifadeleri):
        return False

    return True


def skor_hesapla(ai_cevabi, analiz_metni):
    satirlar = ai_cevabi.split("\n")

    kritik_hata = 0
    yuksek_hata = 0
    orta_hata = 0
    aktif_tablo = 0

    for satir in satirlar:
        temiz_satir = satir.strip()

        if "IEEE 29148" in temiz_satir:
            aktif_tablo = 1
        elif "KVKK" in temiz_satir:
            aktif_tablo = 2
        elif "ISO 27001" in temiz_satir:
            aktif_tablo = 3
        elif "ISO 25010" in temiz_satir or "ISO/IEC 25010" in temiz_satir:
            aktif_tablo = 4
        elif "Standartlara Tam Uyumlu" in temiz_satir:
            aktif_tablo = 5

        if tablo_veri_satiri_mi(temiz_satir) and aktif_tablo in [1, 2, 3, 4]:
            if aktif_tablo in [2, 3]:
                kritik_hata += 1
            elif aktif_tablo == 4:
                yuksek_hata += 1
            elif aktif_tablo == 1:
                orta_hata += 1

    toplam_madde = len(
        [s for s in analiz_metni.split("\n") if len(s.strip()) > 15]
    ) or 1

    toplam_hata = kritik_hata + yuksek_hata + orta_hata
    basarili_madde = max(0, toplam_madde - toplam_hata)

    toplam_ceza = (
        kritik_hata * 10 +
        yuksek_hata * 6 +
        orta_hata * 3
    )

    maksimum_risk = max(1, toplam_madde * 10)

    mevcut_skor = max(
        0,
        round(100 * (1 - (toplam_ceza / maksimum_risk)))
    )

    return {
        "kritik_hata": kritik_hata,
        "yuksek_hata": yuksek_hata,
        "orta_hata": orta_hata,
        "toplam_hata": toplam_hata,
        "toplam_madde": toplam_madde,
        "basarili_madde": basarili_madde,
        "toplam_ceza": toplam_ceza,
        "maksimum_risk": maksimum_risk,
        "mevcut_skor": mevcut_skor
    }


def hata_mesaji_goster(e):
    hata_metni = str(e)

    if "403" in hata_metni or "denied access" in hata_metni.lower():
        st.error("❌ API erişim hatası.")
        st.warning(
            "Google Cloud projenizin Gemini API erişimi reddedilmiş olabilir. "
            "Faturalandırma, ödeme doğrulama ve API key kısıtlarını kontrol edin."
        )
        st.caption(f"Teknik detay: {e}")

    elif "prepayment credits are depleted" in hata_metni.lower():
        st.error("❌ Gemini API ön ödeme krediniz bitmiş görünüyor.")
        st.warning(
            "AI Studio > Projects bölümünden ilgili projenin faturalandırma ve kredi durumunu kontrol edin."
        )
        st.caption(f"Teknik detay: {e}")

    elif "429" in hata_metni:
        st.error("❌ Kota veya kullanım sınırı hatası.")
        st.warning(
            "API kotanız dolmuş olabilir. Bir süre bekleyin veya AI Studio üzerinden proje kotanızı kontrol edin."
        )
        st.caption(f"Teknik detay: {e}")

    elif "API key" in hata_metni or "API_KEY" in hata_metni:
        st.error("❌ API anahtarı geçersiz veya yetkisiz görünüyor.")
        st.caption(f"Teknik detay: {e}")

    else:
        st.error(f"❌ Analiz Hatası: {e}")


def analiz_promptu_olustur(analiz_turu, analiz_metni):
    ortak_kurallar = """
Sen uzman bir Yazılım Kalite Direktörü, Gereksinim Mühendisliği Analisti ve BT Uyum Denetçisisin.
Çıktılarını SADECE Türkçe üret.

GENEL KURALLAR:
- Giriş, sonuç veya özet cümlesi yazma.
- Sadece istenen Markdown tablosunu üret.
- Tablo başlığını ve sütun adlarını aynen koru.
- Metinde olmayan gereksinim ifadesi üretme.
- Her bulguda gereksinim metnindeki ilgili ifadeyi kısa ve doğrudan alıntıla.
- Uydurma kanun maddesi, standart maddesi veya kontrol numarası yazma.
- Kesin madde numarasından emin değilsen madde numarası verme.
- Emin olmadığın durumda ilgili standart prensibini, kalite karakteristiğini, kontrol alanını veya mevzuat ilkesini yaz.
- Açıklama hücrelerinde yalnızca standart adı yazıp bırakma; neden ilgili olduğunu ve gereksinimin neden eksik/riskli olduğunu açıkla.
- Bulgu yoksa ilgili tabloya tek satır olarak "✅ Tam uyum sağlanmıştır" yaz.

TABLO BÜTÜNLÜĞÜ KURALLARI:
- Her tablo satırı, başlıktaki sütun sayısıyla birebir aynı sayıda hücre içermelidir.
- Hiçbir tablo hücresi boş bırakılmamalıdır.
- Bir hücre için bilgi yoksa "Belirtilmemiştir" yaz.
- Her satır mutlaka | işaretiyle başlamalı ve | işaretiyle bitmelidir.
- Markdown tablo yapısını bozacak şekilde hücre içinde | karakteri kullanma.
- Her bulgu satırında tüm sütunları doldur.
- İfade, risk/kriter, standart-mevzuat analizi ve öneri alanı boş kalmamalıdır.
"""

    if analiz_turu == "IEEE":
        gorev = """
YALNIZCA IEEE 29148 açısından analiz yap.

Odaklanılacak noktalar:
- Belirsizlik
- Ölçülemezlik
- Doğrulanamazlık
- Test edilemezlik
- Eksik kabul kriteri
- Yoruma açık ifade
- Kapsam belirsizliği
- Çelişkili veya eksik gereksinim

Özellikle şu tür ifadeleri ara:
"Hızlı", "kolay", "uygun", "tam uyumlu", "verimli", "yüksek performans", "doğru", "güvenli", "sorunsuz", "anında", "yeterli", "çalışır durumda", "bütün veriler".

En fazla 15 bulgu ver.
Bulgu yoksa tabloya "✅ Tam uyum sağlanmıştır" yaz.
Her bulgu satırında dört sütunun tamamını doldur. Boş hücre bırakma.

### 1. 📏 IEEE 29148 Uyumluluğu
| Gereksinimdeki İfade | İhlal Edilen Kriter | Standart Karşılığı ve Analiz | Uyum Önerisi |
|---|---|---|---|
"""

    elif analiz_turu == "KVKK":
        gorev = """
YALNIZCA KVKK açısından analiz yap.

Odaklanılacak noktalar:
- Kişisel veri işleme amacı
- Vatandaş verisi
- Kullanıcı bilgisi
- IP adresi
- Log kaydı
- Açık rıza
- Aydınlatma yükümlülüğü
- Veri minimizasyonu
- Veri saklama süresi
- Veri imha yöntemi
- Yurt içi / yurt dışı veri işleme
- Üçüncü taraflarla veri paylaşımı
- Yetkisiz erişim riski

En fazla 12 bulgu ver.
Bulgu yoksa tabloya "✅ Tam uyum sağlanmıştır" yaz.
Her bulgu satırında dört sütunun tamamını doldur. Boş hücre bırakma.

### 2. 🛡️ KVKK Uyumluluğu
| Gereksinimdeki İfade | KVKK Riski | Mevzuat Çerçevesi ve Çelişme Nedeni | Hukuki Uyum Önerisi |
|---|---|---|---|
"""

    elif analiz_turu == "ISO27001":
        gorev = """
YALNIZCA ISO 27001 bilgi güvenliği açısından analiz yap.

Odaklanılacak noktalar:
- Kimlik doğrulama
- Yetkilendirme
- Rol tabanlı erişim
- 2FA
- LDAP
- Loglama
- IP kaydı
- Brute force koruması
- SSL / şifreli iletişim
- Veri güvenliği
- Erişim kontrolü
- Olay izleme
- Denetim kayıtları
- Log saklama süresi
- Log bütünlüğü
- Yetki matrisi

En fazla 12 bulgu ver.
Bulgu yoksa tabloya "✅ Tam uyum sağlanmıştır" yaz.
Her bulgu satırında dört sütunun tamamını doldur. Boş hücre bırakma.

### 3. 🔒 ISO 27001 Uyumluluğu
| Gereksinimdeki İfade | Güvenlik Riski | Referans Madde ve Teknik Gerekçe | Teknik Önlem |
|---|---|---|---|
"""

    elif analiz_turu == "ISO25010":
        gorev = """
YALNIZCA ISO/IEC 25010 yazılım kalite modeli açısından analiz yap.

Bu tabloyu MUTLAKA üret.

Odaklanılacak kalite karakteristikleri:
- Performans verimliliği
- Kullanılabilirlik
- Güvenilirlik
- Bakım yapılabilirlik
- Uyumluluk
- Güvenlik
- Taşınabilirlik
- Erişilebilirlik

Özellikle şu eksiklikleri ara:
- Yanıt süresi belirtilmemişse
- Eş zamanlı kullanıcı sayısı belirtilmemişse
- İşlem hacmi belirtilmemişse
- Hata oranı belirtilmemişse
- Kullanıcı memnuniyeti veya kullanılabilirlik ölçütü yoksa
- Hata toleransı veya kurtarma süresi yoksa
- Bakım, güncelleme veya sürdürülebilirlik ölçütü yoksa
- Entegrasyon performansı belirsizse
- Sistem erişilebilirlik hedefi yoksa
- Performans ve verimlilik ifadeleri ölçülebilir değilse

En fazla 12 bulgu ver.
Bulgu yoksa tabloya "✅ Tam uyum sağlanmıştır" yaz.
Her bulgu satırında dört sütunun tamamını doldur. Boş hücre bırakma.

### 4. ⚙️ ISO 25010 Uyumluluğu
| Gereksinimdeki İfade | Kalite Eksikliği | Karakteristik ve Analiz | Kalite Hedefi |
|---|---|---|---|
"""

    elif analiz_turu == "BASARILI":
        gorev = """
YALNIZCA standartlara tam veya güçlü biçimde uyumlu görünen başarılı gereksinimleri seç.

Kurallar:
- SADECE metinde gerçekten bulunan ifadeleri kullan.
- En fazla 5 başarılı örnek ver.
- Uydurma örnek oluşturma.
- Başarılı örnek yoksa tabloya "⚠️ Metin içerisinde standartlara tam uyumlu bir madde tespit edilememiştir." yaz.
- Her bulgu satırında üç sütunun tamamını doldur. Boş hücre bırakma.

### 5. 🌟 Standartlara Tam Uyumlu Gereksinimler
| Başarılı Gereksinim | Karşıladığı Standartlar | Uyum Gerekçesi |
|---|---|---|
"""

    return f"""
{ortak_kurallar}

{gorev}

ANALİZ EDİLECEK METİN:
{analiz_metni.strip()}
"""


# ---------------------------------------------------------
# 6. VERİ GİRİŞİ VE ANALİZ
# ---------------------------------------------------------
st.subheader("📁 Veri Girişi")

yuklenen_dosya = st.file_uploader(
    "Dosya seçin (.docx, .pdf)",
    type=["docx", "pdf"]
)

metin_alani = st.text_area(
    "Veya metni yapıştırın:",
    height=150
)


if st.button("🚀 Analizi Başlat"):
    analiz_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani

    if not api_key or not analiz_metni.strip() or not secilen_model:
        st.warning("⚠️ Eksik bilgi: API anahtarı, model seçimi veya metin gereklidir.")

    else:
        try:
            genai.configure(api_key=api_key.strip())
            model = genai.GenerativeModel(secilen_model)

            generation_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 4096
            }

            analiz_turleri = [
                "IEEE",
                "KVKK",
                "ISO27001",
                "ISO25010",
                "BASARILI"
            ]

            cevaplar = []

            with st.spinner("Analiz ediliyor..."):
                baslangic_zamani = time.time()

                progress = st.progress(0)
                durum = st.empty()

                for i, analiz_turu in enumerate(analiz_turleri, start=1):
                    durum.write(f"🔍 {i}/5 analiz yürütülüyor: {analiz_turu}")

                    prompt = analiz_promptu_olustur(
                        analiz_turu=analiz_turu,
                        analiz_metni=analiz_metni
                    )

                    cevap = model.generate_content(
                        prompt,
                        generation_config=generation_config
                    )

                    if cevap and hasattr(cevap, "text") and cevap.text:
                        cevaplar.append(cevap.text.strip())
                    else:
                        cevaplar.append(
                            f"### {analiz_turu}\n\n| Durum | Açıklama |\n|---|---|\n| ✅ | Tam uyum sağlanmıştır |"
                        )

                    progress.progress(i / len(analiz_turleri))

                bitis_zamani = time.time()

            gecen_sure = round(bitis_zamani - baslangic_zamani, 2)
            gecen_sure_yazi = sure_formatla(gecen_sure)

            ai_cevabi = "\n\n".join(cevaplar)

            if ai_cevabi.strip():
                st.success(f"✅ Analiz Tamamlandı! Süre: {gecen_sure_yazi}")

                st.metric(
                    label="⏱️ Analiz Süresi",
                    value=gecen_sure_yazi
                )

                st.markdown(ai_cevabi)

                with st.expander("📊 Doküman Uyum Skoru", expanded=True):
                    skor = skor_hesapla(ai_cevabi, analiz_metni)

                    if skor is None:
                        st.error("Skor hesaplama sonucu boş döndü. Lütfen skor_hesapla fonksiyonunu kontrol edin.")
                        st.stop()

                    st.info(
                        f"Taranan Madde: {skor['toplam_madde']} | "
                        f"Uyumlu: {skor['basarili_madde']} | "
                        f"Hatalı: {skor['toplam_hata']}"
                    )

                    c1, c2, c3 = st.columns(3)

                    c1.metric(
                        "Uyum Skoru",
                        f"% {skor['mevcut_skor']}",
                        f"-{skor['toplam_ceza']} Risk"
                    )

                    c2.write(
                        f"🔴 {skor['kritik_hata']} Kritik\n\n"
                        f"🟠 {skor['yuksek_hata']} Yüksek\n\n"
                        f"🟡 {skor['orta_hata']} Orta"
                    )

                    c3.metric(
                        "Uyumlu Madde",
                        f"{skor['basarili_madde']} Adet"
                    )

                    st.divider()

                    with st.expander("🧮 Puanlama Nasıl Hesaplanıyor? (Matematiksel Döküm)"):
                        st.markdown(f"""
**1. Madde ve Hata Tespiti:**

* **Toplam Taranan Madde:** {skor['toplam_madde']}
* **Tespit Edilen Hatalar:** {skor['kritik_hata']} Kritik + {skor['yuksek_hata']} Yüksek + {skor['orta_hata']} Orta = **{skor['toplam_hata']} Toplam Hata**
* **Başarılı Madde:** {skor['toplam_madde']} (Toplam) - {skor['toplam_hata']} (Hata) = **{skor['basarili_madde']} Adet**

**2. Risk (Ceza) Puanı Hesabı:**

*(Ağırlıklar - Kritik: 10, Yüksek: 6, Orta: 3)*

* Kritik Risk Cezası: {skor['kritik_hata']} x 10 = **{skor['kritik_hata'] * 10} Puan**
* Yüksek Risk Cezası: {skor['yuksek_hata']} x 6 = **{skor['yuksek_hata'] * 6} Puan**
* Orta Risk Cezası: {skor['orta_hata']} x 3 = **{skor['orta_hata'] * 3} Puan**
* **Toplam Risk Puanı:** **{skor['toplam_ceza']} Puan**

**3. Uyum Yüzdesi (%):**

* **Maksimum Olası Risk:** {skor['toplam_madde']} x 10 = **{skor['maksimum_risk']}**
* **Risk Oranı:** {skor['toplam_ceza']} / {skor['maksimum_risk']} = **{skor['toplam_ceza'] / skor['maksimum_risk']:.4f}**
* **Sonuç:** 100 - (Risk Oranı x 100) = **% {skor['mevcut_skor']}**
""")

            else:
                st.error("❌ Modelden yanıt alınamadı.")

        except Exception as e:
            hata_mesaji_goster(e)
