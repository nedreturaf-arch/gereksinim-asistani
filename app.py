import streamlit as st
import google.generativeai as genai
from docx import Document
import PyPDF2
import time


# ---------------------------------------------------------
# 1. SAYFA VE ARAYÜZ YAPILANDIRMASI
# ---------------------------------------------------------

st.set_page_config(
    page_title="Gereksinim Analiz Asistanı v3.7",
    layout="wide"
)


# ---------------------------------------------------------
# 2. SABİT DEĞERLER
# ---------------------------------------------------------

TERCIH_EDILEN_MODEL = "gemini-2.5-flash"

KRITIK_CEZA = 10
YUKSEK_CEZA = 6
ORTA_CEZA = 3


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
            genai.configure(api_key=api_key.strip())

            modeller = [
                m.name.replace("models/", "")
                for m in genai.list_models()
                if "generateContent" in m.supported_generation_methods
            ]

            if modeller:
                varsayilan_index = 0

                if TERCIH_EDILEN_MODEL in modeller:
                    varsayilan_index = modeller.index(TERCIH_EDILEN_MODEL)

                secilen_model = st.selectbox(
                    "🤖 Model Seçin:",
                    modeller,
                    index=varsayilan_index
                )

                st.caption(f"Önerilen model: {TERCIH_EDILEN_MODEL}")

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

Bu sistem, gereksinim metinlerini aşağıdaki uluslararası standartlar ve yerel mevzuatlar çerçevesinde denetleyerek, spesifik ifadeleri doğrudan ilgili maddeyle eşleştirir:

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
    """
    PDF veya DOCX dosyasından analiz edilebilir metin çıkarır.
    DOCX içindeki paragraflar ve tablolar birlikte okunur.
    PDF dosyalarında boş sayfa hatası engellenir.
    """

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

            # DOCX tablolarını oku
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

            for sayfa_no, sayfa in enumerate(pdf_reader.pages, start=1):
                sayfa_metni = sayfa.extract_text()

                if sayfa_metni and sayfa_metni.strip():
                    metinler.append(
                        f"\n--- Sayfa {sayfa_no} ---\n{sayfa_metni.strip()}"
                    )

            return "\n".join(metinler).strip()

        else:
            st.warning("⚠️ Desteklenmeyen dosya türü.")
            return ""

    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        return ""


def sistem_talimati_olustur():
    """
    Kapsamlı analiz için sistem talimatı.
    Ana tablo yapısı korunmuştur.
    Halüsinasyon riskini azaltmak için başarılı örnek zorlaması kaldırılmıştır.
    """

    return """
Sen uzman bir Yazılım Kalite Direktörü ve BT Uyum Denetçisisin.
Gereksinimleri analiz ederken izlenebilirlik prensibini uygula.
Yanıtlarını SADECE Türkçe üret.

KURAL 1: Doğrudan tablolara başla. Giriş veya sonuç cümlesi yazma.

KURAL 2: Her ihlal için gereksinim belgesindeki ilgili ifadeyi alıntıla.
İlgili ifadenin hangi standart, mevzuat, kalite karakteristiği veya güvenlik prensibi ile neden çeliştiğini açıkla.

KURAL 3: İhlal yoksa ilgili tabloya "✅ Tam uyum sağlanmıştır" yaz.

KURAL 4: Risk ikonları:
IEEE 29148 bulguları için 🟡,
KVKK ve ISO 27001 bulguları için 🔴,
ISO 25010 bulguları için 🟠,
Başarılı gereksinimler için 🟢 kullanılabilir.

KURAL 5: Tablo 5'e yalnızca metinde açıkça bulunan başarılı gereksinimleri ekle.
En fazla 5 başarılı örnek ver.
Metinde uygun başarılı örnek yoksa "⚠️ Metin içerisinde standartlara tam uyumlu bir madde tespit edilememiştir." yaz.

KURAL 6: Metinde olmayan gereksinim ifadesi üretme.
Uydurma örnek oluşturma.
Uydurma kanun maddesi veya standart maddesi yazma.
Emin olmadığın durumda kesin madde numarası verme.
Bunun yerine ilgili standart prensibini belirt.

KURAL 7: Aynı bulguyu gereksiz tekrar etme.
Her bulguyu açık, kısa ve uygulanabilir biçimde yaz.

### 1. 📏 IEEE 29148 Gereksinim Kalitesi Uyumluluğu

| Gereksinimdeki İfade | İhlal Edilen Kriter | Standart Karşılığı ve Analiz | Uyum Önerisi |
|---|---|---|---|

### 2. 🛡️ KVKK ve Veri Gizliliği Mevzuatı Uyumluluğu

| Gereksinimdeki İfade | KVKK Riski | Mevzuat Maddesi ve Çelişme Nedeni | Hukuki Uyum Şartı |
|---|---|---|---|

### 3. 🔒 ISO 27001 Bilgi Güvenliği Uyumluluğu

| Gereksinimdeki İfade | Güvenlik Zafiyeti | Referans Madde ve Teknik Gerekçe | Teknik Önlem |
|---|---|---|---|

### 4. ⚙️ ISO 25010 Yazılım Kalite Modeli Uyumluluğu

| Gereksinimdeki İfade | Kalite Eksikliği | Karakteristik ve Analiz | Kalite Hedefi |
|---|---|---|---|

### 5. 🌟 Standartlara Tam Uyumlu Gereksinimler

| Başarılı Gereksinim | Karşıladığı Standartlar | Uyum Gerekçesi (Neden Başarılı?) |
|---|---|---|
"""


def tablo_veri_satiri_mi(satir):
    """
    Markdown tablo satırının gerçek bulgu satırı olup olmadığını kontrol eder.
    Başlık, ayraç ve tam uyum satırlarını saymaz.
    """

    temiz_satir = satir.strip()

    if not temiz_satir.startswith("|") or not temiz_satir.endswith("|"):
        return False

    if "---" in temiz_satir:
        return False

    baslik_ifadeleri = [
        "Gereksinimdeki İfade",
        "İhlal Edilen Kriter",
        "KVKK Riski",
        "Güvenlik Zafiyeti",
        "Kalite Eksikliği",
        "Başarılı Gereksinim"
    ]

    if any(ifade in temiz_satir for ifade in baslik_ifadeleri):
        return False

    bos_uyum_ifadeleri = [
        "✅ Tam uyum sağlanmıştır",
        "Tam uyum sağlanmıştır",
        "⚠️ Metin içerisinde standartlara tam uyumlu"
    ]

    if any(ifade in temiz_satir for ifade in bos_uyum_ifadeleri):
        return False

    return True


def skor_hesapla(ai_cevabi, analiz_metni):
    """
    AI çıktısındaki tablo satırlarına göre risk ve uyum skoru hesaplar.
    Tezde kullanılan normalize 0-100 skorlama mantığı uygulanır.
    """

    satirlar = ai_cevabi.split("\n")

    kritik_hata = 0
    yuksek_hata = 0
    orta_hata = 0

    aktif_tablo = None

    for satir in satirlar:
        temiz_satir = satir.strip()

        # Aktif tabloyu belirle
        if "IEEE 29148" in temiz_satir:
            aktif_tablo = "IEEE"

        elif "KVKK" in temiz_satir:
            aktif_tablo = "KVKK"

        elif "ISO 27001" in temiz_satir:
            aktif_tablo = "ISO27001"

        elif "ISO 25010" in temiz_satir:
            aktif_tablo = "ISO25010"

        elif "Standartlara Tam Uyumlu" in temiz_satir:
            aktif_tablo = "BASARILI"

        # Sadece hata tablolarındaki gerçek veri satırlarını say
        if tablo_veri_satiri_mi(temiz_satir) and aktif_tablo in ["IEEE", "KVKK", "ISO27001", "ISO25010"]:

            if aktif_tablo in ["KVKK", "ISO27001"]:
                kritik_hata += 1

            elif aktif_tablo == "ISO25010":
                yuksek_hata += 1

            elif aktif_tablo == "IEEE":
                orta_hata += 1

    toplam_madde = len(
        [
            s for s in analiz_metni.split("\n")
            if len(s.strip()) > 15
        ]
    )

    if toplam_madde == 0:
        toplam_madde = 1

    toplam_hata = kritik_hata + yuksek_hata + orta_hata

    basarili_madde = max(0, toplam_madde - toplam_hata)

    toplam_ceza = (
        kritik_hata * KRITIK_CEZA +
        yuksek_hata * YUKSEK_CEZA +
        orta_hata * ORTA_CEZA
    )

    maksimum_risk = max(1, toplam_madde * KRITIK_CEZA)

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
    """
    API hatalarını kullanıcıya daha anlaşılır gösterir.
    """

    hata_metni = str(e)

    if "403" in hata_metni or "denied access" in hata_metni.lower():
        st.error("❌ API erişim hatası.")
        st.warning(
            "Google Cloud projenizin Gemini API erişimi reddedilmiş olabilir. "
            "Faturalandırma, ödeme doğrulama, API etkinleştirme ve API key kısıtlarını kontrol edin."
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
# 6. VERİ GİRİŞİ
# ---------------------------------------------------------

st.subheader("📁 Veri Girişi")

yuklenen_dosya = st.file_uploader(
    "Analiz edilecek dosyayı seçin (.docx, .pdf)",
    type=["docx", "pdf"]
)

metin_alani = st.text_area(
    "Veya analiz edilecek metni buraya yapıştırın:",
    height=150
)


# ---------------------------------------------------------
# 7. YAPAY ZEKA ANALİZ SÜRECİ
# ---------------------------------------------------------

if st.button("🚀 Analizi Başlat"):

    analiz_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani

    if not api_key:
        st.warning("⚠️ Gemini API anahtarı girilmelidir.")

    elif not secilen_model:
        st.warning("⚠️ Model seçimi yapılmalıdır.")

    elif not analiz_metni or not analiz_metni.strip():
        st.warning("⚠️ Lütfen analiz edilecek metni veya dosyayı sağlayın.")

    elif len(analiz_metni.strip()) < 30:
        st.warning("⚠️ Analiz metni çok kısa görünüyor.")

    else:
        try:
            genai.configure(api_key=api_key.strip())

            model = genai.GenerativeModel(secilen_model)

            sistem_talimati = sistem_talimati_olustur()

            tam_prompt = f"""
{sistem_talimati}

ANALİZ EDİLECEK METİN:
{analiz_metni.strip()}
"""

            generation_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 8192
            }

            with st.spinner("Yapay Zeka İzlenebilirlik Analizini Gerçekleştiriyor..."):

                baslangic = time.time()

                response = model.generate_content(
                    tam_prompt,
                    generation_config=generation_config,
                    stream=True
                )

                placeholder = st.empty()
                full_text = ""

                for chunk in response:
                    if hasattr(chunk, "text") and chunk.text:
                        full_text += chunk.text
                        placeholder.markdown(full_text)

                bitis = time.time()

            if not full_text.strip():
                st.error("❌ Modelden geçerli yanıt alınamadı.")

            else:
                gecen_sure = round(bitis - baslangic, 2)

                st.success(
                    f"✅ Kapsamlı Uyumluluk Analizi Tamamlanmıştır. Süre: {gecen_sure} saniye"
                )

                # ---------------------------------------------------------
                # 8. SKORLAMA BÖLÜMÜ
                # ---------------------------------------------------------

                with st.expander("📊 Doküman Uyum Skoru (ISTQB Risk Temelli Analiz)", expanded=True):

                    skor = skor_hesapla(full_text, analiz_metni)

                    st.info(f"""
📊 **Yönetici Özeti:** İnceleme sonucunda doküman içerisindeki **{skor['toplam_madde']}** madde/ifade taranmıştır. 
Sistem; **{skor['basarili_madde']}** maddeyi uyumlu kabul ederken, **{skor['toplam_hata']}** maddede gelişim alanı tespit etmiştir.
""")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric(
                            "Güncel Uyum Skoru",
                            f"% {skor['mevcut_skor']}",
                            f"-{skor['toplam_ceza']} Risk",
                            delta_color="inverse"
                        )

                    with col2:
                        st.write(
                            f"**🔴 {skor['kritik_hata']}** Kritik  \n"
                            f"**🟠 {skor['yuksek_hata']}** Yüksek  \n"
                            f"**🟡 {skor['orta_hata']}** Orta"
                        )

                    with col3:
                        st.metric(
                            "Tam Uyumlu Madde",
                            f"{skor['basarili_madde']} Adet",
                            "Standartlara Uygun"
                        )

                    st.divider()

                    with st.expander("🧮 Puanlama Nasıl Hesaplanıyor?"):
                        st.markdown(f"""
### 1. Madde ve Hata Tespiti

- **Toplam Taranan Madde:** {skor['toplam_madde']}
- **Kritik Hata:** {skor['kritik_hata']}
- **Yüksek Hata:** {skor['yuksek_hata']}
- **Orta Hata:** {skor['orta_hata']}
- **Toplam Hata:** {skor['toplam_hata']}
- **Başarılı Madde:** {skor['basarili_madde']}

### 2. ISTQB Risk Temelli Ceza Hesabı

- Kritik Risk Cezası: {skor['kritik_hata']} x {KRITIK_CEZA} = **{skor['kritik_hata'] * KRITIK_CEZA}**
- Yüksek Risk Cezası: {skor['yuksek_hata']} x {YUKSEK_CEZA} = **{skor['yuksek_hata'] * YUKSEK_CEZA}**
- Orta Risk Cezası: {skor['orta_hata']} x {ORTA_CEZA} = **{skor['orta_hata'] * ORTA_CEZA}**

**Toplam Risk Cezası:** {skor['toplam_ceza']}

### 3. Uyum Skoru

- Maksimum Olası Risk: {skor['toplam_madde']} x {KRITIK_CEZA} = **{skor['maksimum_risk']}**
- Risk Oranı: {skor['toplam_ceza']} / {skor['maksimum_risk']} = **{skor['toplam_ceza'] / skor['maksimum_risk']:.4f}**
- Uyum Skoru: 100 x (1 - Risk Oranı) = **% {skor['mevcut_skor']}**
""")

                    st.caption(
                        "💡 Bu rapor ISTQB risk temelli analiz yaklaşımından yararlanılarak oluşturulmuştur. "
                        "AI çıktıları uzman değerlendirmesini destekleyen ön analiz niteliğindedir."
                    )

        except Exception as e:
            hata_mesaji_goster(e)
