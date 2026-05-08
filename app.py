import streamlit as st
import google.generativeai as genai
import time
from docx import Document
import pypdf as PyPDF2

# ---------------------------------------------------------
# 1. SAYFA VE ARAYÜZ YAPILANDIRMASI
# ---------------------------------------------------------
st.set_page_config(
    page_title="Gereksinim Analiz Asistanı v3.8",
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

            # DOCX tablolarını da oku
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
        elif "ISO 25010" in temiz_satir:
            aktif_tablo = 4
        elif "Standartlara Tam Uyumlu" in temiz_satir:
            aktif_tablo = 5

        tablo_satiri_mi = (
            temiz_satir.startswith("|") and
            temiz_satir.endswith("|") and
            "---" not in temiz_satir and
            "Gereksinimdeki İfade" not in temiz_satir and
            "Başarılı Gereksinim" not in temiz_satir and
            "✅" not in temiz_satir and
            "⚠️" not in temiz_satir
        )

        if tablo_satiri_mi and aktif_tablo in [1, 2, 3, 4]:
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

            sistem_talimati = """
Sen uzman bir Yazılım Kalite Direktörü ve BT Uyum Denetçisisin.
Gereksinimleri analiz ederken 'İzlenebilirlik' (Traceability) prensibini uygula.

    KURAL 1: Doğrudan tablolara başla. Giriş/Sonuç cümlesi yazma.
    KURAL 2: Her ihlal için gereksinim belgesindeki 'İLGİLİ İFADEYİ' alıntıla ve hangi 'STANDART MADDESİ' ile neden çeliştiğini açıkla.
    KURAL 3: İhlal yoksa "✅ Tam uyum sağlanmıştır" yaz.
    KURAL 4: Risk İkonları: IEEE(🟡), KVKK/ISO27001(🔴), ISO25010(🟠), Başarılı(🟢)
    KURAL 5: Uydurma kanun maddesi veya standart maddesi yazma.
    KURAL 6:Emin olmadığın durumda kesin madde numarası verme; ilgili standart prensibini açıkla
    KURAL 7:
"Standartlara Tam Uyumlu Gereksinimler" tablosuna SADECE metinde gerçekten bulunan en fazla 5 başarılı örnek ekle.
Başarılı örnek yoksa "⚠️ Metin içerisinde standartlara tam uyumlu bir madde tespit edilememiştir." yaz.

ANALİZ YAKLAŞIMI:
- Belirsiz, ölçülemeyen, yoruma açık ve test edilmesi zor ifadeleri IEEE 29148 kapsamında değerlendir.
- Kişisel veri, vatandaş verisi, kullanıcı bilgisi, log, IP adresi, yurtiçi veri işleme, gizlilik, veri paylaşımı ve veri saklama ifadelerini KVKK kapsamında değerlendir.
- Kimlik doğrulama, yetkilendirme, 2FA, LDAP, loglama, IP kaydı, brute force, SSL, veri güvenliği, erişim kontrolü ve olay izleme ifadelerini ISO 27001 kapsamında değerlendir.
- Performans, kullanılabilirlik, güvenilirlik, bakım yapılabilirlik, erişilebilirlik, hata toleransı, verimlilik ve sürdürülebilirlik ifadelerini ISO 25010 kapsamında değerlendir.

### 1. 📏 IEEE 29148 Uyumluluğu
| Gereksinimdeki İfade | İhlal Edilen Kriter | Standart Karşılığı ve Analiz | Uyum Önerisi |
|---|---|---|---|

### 2. 🛡️ KVKK Uyumluluğu
| Gereksinimdeki İfade | KVKK Riski | Mevzuat Çerçevesi ve Çelişme Nedeni | Hukuki Uyum Önerisi |
|---|---|---|---|

### 3. 🔒 ISO 27001 Uyumluluğu
| Gereksinimdeki İfade | Güvenlik Riski | Referans Madde ve Teknik Gerekçe | Teknik Önlem |
|---|---|---|---|

### 4. ⚙️ ISO 25010 Uyumluluğu
| Gereksinimdeki İfade | Kalite Eksikliği | Karakteristik ve Analiz | Kalite Hedefi |
|---|---|---|---|

### 5. 🌟 Standartlara Tam Uyumlu Gereksinimler
| Başarılı Gereksinim | Karşıladığı Standartlar | Uyum Gerekçesi |
|---|---|---|
"""

            tam_prompt = f"{sistem_talimati}\n\nANALİZ EDİLECEK METİN:\n{analiz_metni.strip()}"

            generation_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 8192
            }

            with st.spinner("Analiz ediliyor..."):
                baslangic_zamani = time.time()

                cevap = model.generate_content(
                    tam_prompt,
                    generation_config=generation_config
                )

                bitis_zamani = time.time()

            gecen_sure = round(bitis_zamani - baslangic_zamani, 2)
            gecen_sure_yazi = sure_formatla(gecen_sure)

            if cevap and hasattr(cevap, "text") and cevap.text:
                st.success(f"✅ Analiz Tamamlandı! Süre: {gecen_sure_yazi}")

                st.metric(
                    label="⏱️ Analiz Süresi",
                    value=gecen_sure_yazi
                )

                st.markdown(cevap.text)

                with st.expander("📊 Doküman Uyum Skoru", expanded=True):
                    skor = skor_hesapla(cevap.text, analiz_metni)

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
