import streamlit as st
import google.generativeai as genai
from docx import Document
import PyPDF2
import time


# ---------------------------------------------------------
# 1. SAYFA VE ARAYÜZ YAPILANDIRMASI
# ---------------------------------------------------------

st.set_page_config(
    page_title="Gereksinim Analiz Asistanı v3.9",
    layout="wide"
)


# ---------------------------------------------------------
# 2. SABİT DEĞERLER
# ---------------------------------------------------------

UYGULAMA_BASLIGI = "🎯 Gereksinim & Kalite Analiz Asistanı"

CHUNK_KARAKTER_LIMITI = 9000

BASARILI_ORNEK_LIMITI = 5

KRITIK_CEZA = 10
YUKSEK_CEZA = 6
ORTA_CEZA = 3


# ---------------------------------------------------------
# 3. API VE MODEL YÖNETİMİ
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
                tercih_edilen_modeller = [
                    "gemini-2.5-flash",
                    "gemini-2.0-flash",
                    "gemini-1.5-flash",
                    "gemini-1.5-pro"
                ]

                varsayilan_index = 0

                for tercih in tercih_edilen_modeller:
                    if tercih in modeller:
                        varsayilan_index = modeller.index(tercih)
                        break

                secilen_model = st.selectbox(
                    "🤖 Model Seçin:",
                    modeller,
                    index=varsayilan_index
                )

                st.caption("Öneri: Büyük PDF ve DOCX dosyaları için Flash modelleri daha hızlı çalışır.")

            else:
                st.warning("⚠️ Kullanılabilir model bulunamadı.")

        except Exception as e:
            st.error("⚠️ API Hatası: Bağlantı kurulamadı.")
            st.caption(f"Teknik detay: {e}")


# ---------------------------------------------------------
# 4. ANA EKRAN
# ---------------------------------------------------------

st.title(UYGULAMA_BASLIGI)

st.info("""
**📖 Analiz Kapsamı ve Referans Standartlar**

Bu sistem, gereksinim metinlerini aşağıdaki standartlar ve mevzuatlar kapsamında değerlendirir:

* **IEEE 29148:** Yazılım ve Sistem Mühendisliği — Gereksinim Mühendisliği Standartları
* **ISO/IEC 25010:** Yazılım Ürün Kalitesi ve Sistem Kalite Modelleri
* **ISO/IEC 27001:** Bilgi Güvenliği Yönetim Sistemi Gereksinimleri
* **KVKK:** 6698 Sayılı Kişisel Verilerin Korunması Kanunu
* **ISTQB Risk Temelli Yaklaşım:** Kritik, yüksek ve orta risk ağırlıklandırması
""")

st.divider()


# ---------------------------------------------------------
# 5. YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------

def dosya_oku(dosya):
    """
    Kullanıcı tarafından yüklenen PDF veya DOCX dosyasından metin çıkarır.
    """

    if dosya is None:
        return ""

    try:
        dosya_adi = dosya.name.lower()

        if dosya_adi.endswith(".docx"):
            doc = Document(dosya)

            paragraflar = [
                p.text.strip()
                for p in doc.paragraphs
                if p.text and p.text.strip()
            ]

            tablo_metinleri = []

            for tablo in doc.tables:
                for satir in tablo.rows:
                    hucreler = [
                        hucre.text.strip()
                        for hucre in satir.cells
                        if hucre.text and hucre.text.strip()
                    ]

                    if hucreler:
                        tablo_metinleri.append(" | ".join(hucreler))

            tum_metin = "\n".join(paragraflar + tablo_metinleri)

            return tum_metin.strip()

        elif dosya_adi.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(dosya)
            metinler = []

            for sayfa_no, sayfa in enumerate(pdf_reader.pages, start=1):
                try:
                    sayfa_metni = sayfa.extract_text()

                    if sayfa_metni and sayfa_metni.strip():
                        metinler.append(f"\n--- Sayfa {sayfa_no} ---\n{sayfa_metni.strip()}")

                except Exception:
                    metinler.append(f"\n--- Sayfa {sayfa_no} okunamadı ---\n")

            return "\n".join(metinler).strip()

        else:
            st.warning("⚠️ Desteklenmeyen dosya türü.")
            return ""

    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        return ""


def metni_parcalara_bol(metin, limit=CHUNK_KARAKTER_LIMITI):
    """
    Uzun metni Gemini'ye kontrollü göndermek için parçalara böler.
    """

    if len(metin) <= limit:
        return [metin]

    satirlar = metin.splitlines()
    parcalar = []
    aktif_parca = ""

    for satir in satirlar:
        if len(aktif_parca) + len(satir) + 1 <= limit:
            aktif_parca += satir + "\n"
        else:
            if aktif_parca.strip():
                parcalar.append(aktif_parca.strip())

            aktif_parca = satir + "\n"

    if aktif_parca.strip():
        parcalar.append(aktif_parca.strip())

    return parcalar


def gereksinim_sayisini_tahmin_et(metin):
    """
    Toplam taranan madde sayısını yaklaşık olarak hesaplar.
    """

    satirlar = [
        s.strip()
        for s in metin.split("\n")
        if len(s.strip()) > 15
    ]

    return max(1, len(satirlar))


def sistem_talimati_olustur():
    """
    Gemini modeline verilecek ana talimat.
    """

    return f"""
Sen uzman bir BT Uyum Denetçisi ve Gereksinim Mühendisliği Analistisin.
Çıktılarını SADECE Türkçe üret.

ANA GÖREV:
Verilen gereksinim metnindeki ifadeleri IEEE 29148, KVKK, ISO 27001 ve ISO 25010 açısından denetle.
Her ifade için şu mantığı uygula:

1. Bu ifade ilgili standart, kanun veya kalite karakteristiği ile örtüşüyor mu?
2. Örtüşüyorsa başarılı örnek olarak değerlendir.
3. Örtüşmüyorsa hangi risk veya eksiklik oluşuyor?
4. Eksikliği gidermek için somut ve uygulanabilir öneri üret.

KESİN KURALLAR:
- Doğrudan tablolara başla.
- Giriş, sonuç, özet veya açıklama paragrafı yazma.
- Metinde olmayan gereksinim ifadesini uydurma.
- Standart maddesi bilmiyorsan kesin madde numarası uydurma.
- Emin olmadığın durumda "İlgili standart prensibi" ifadesini kullan, ancak sahte madde numarası yazma.
- Başarılı örnekler tablosuna sadece metinde açıkça yer alan ifadeleri ekle.
- Başarılı örnekler tablosunda en fazla {BASARILI_ORNEK_LIMITI} madde göster.
- Aynı ifadeyi birden fazla tabloda gereksiz tekrar etme.
- Boş tablo bırakma.
- İhlal yoksa ilgili tabloya "✅ Tam uyum sağlanmıştır" yaz.
- Başarılı gereksinim bulunmuyorsa 5. tabloya "⚠️ Metin içerisinde standartlara tam uyumlu bir madde tespit edilememiştir." yaz.

RİSK SINIFLANDIRMASI:
- KVKK ve ISO 27001 bulguları kritik risk kabul edilir.
- ISO 25010 bulguları yüksek risk kabul edilir.
- IEEE 29148 bulguları orta risk kabul edilir.
- Bu sınıflandırma ISTQB risk temelli test yaklaşımına göre puanlamada kullanılacaktır.

TABLO FORMATINI AYNEN KORU:

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


def prompt_olustur(analiz_metni, parca_no=None, toplam_parca=None):
    """
    Her analiz için modele gönderilecek tam promptu oluşturur.
    """

    sistem_talimati = sistem_talimati_olustur()

    if parca_no is not None and toplam_parca is not None:
        parca_bilgisi = f"""
BU ANALİZ, UZUN DOKÜMANIN {parca_no}/{toplam_parca} NUMARALI PARÇASIDIR.
Sadece bu parçada açıkça görülen ifadeleri analiz et.
Diğer parçalarda olabilir varsayımı yapma.
"""
    else:
        parca_bilgisi = ""

    return f"""
{sistem_talimati}

{parca_bilgisi}

ANALİZ EDİLECEK METİN:
{analiz_metni.strip()}
"""


def model_cevabi_uret(model, prompt):
    """
    Gemini modelinden cevap üretir.
    """

    generation_config = {
        "temperature": 0.1,
        "top_p": 0.8,
        "top_k": 40,
        "max_output_tokens": 8192
    }

    cevap = model.generate_content(
        prompt,
        generation_config=generation_config
    )

    if cevap and hasattr(cevap, "text") and cevap.text:
        return cevap.text.strip()

    return ""


def tablo_veri_satiri_mi(satir):
    """
    Markdown tablo satırının gerçek veri satırı olup olmadığını kontrol eder.
    Başlık ve ayırıcı satırlar sayılmaz.
    """

    temiz = satir.strip()

    if not temiz.startswith("|") or not temiz.endswith("|"):
        return False

    if "---" in temiz:
        return False

    baslik_kelimeleri = [
        "Gereksinimdeki İfade",
        "İhlal Edilen Kriter",
        "KVKK Riski",
        "Güvenlik Riski",
        "Kalite Eksikliği",
        "Başarılı Gereksinim"
    ]

    if any(kelime in temiz for kelime in baslik_kelimeleri):
        return False

    bos_veya_uyumlu_ifadeler = [
        "✅ Tam uyum sağlanmıştır",
        "⚠️ Metin içerisinde standartlara tam uyumlu bir madde tespit edilememiştir"
    ]

    if any(ifade in temiz for ifade in bos_veya_uyumlu_ifadeler):
        return False

    return True


def skor_hesapla(ai_cevabi, analiz_metni):
    """
    AI cevabındaki tablolara göre risk ve uyum skoru hesaplar.
    """

    satirlar = ai_cevabi.split("\n")

    kritik_hata = 0
    yuksek_hata = 0
    orta_hata = 0

    aktif_tablo = None

    for satir in satirlar:
        temiz_satir = satir.strip()

        if "IEEE 29148 Uyumluluğu" in temiz_satir:
            aktif_tablo = "IEEE"

        elif "KVKK Uyumluluğu" in temiz_satir:
            aktif_tablo = "KVKK"

        elif "ISO 27001 Uyumluluğu" in temiz_satir:
            aktif_tablo = "ISO27001"

        elif "ISO 25010 Uyumluluğu" in temiz_satir:
            aktif_tablo = "ISO25010"

        elif "Standartlara Tam Uyumlu Gereksinimler" in temiz_satir:
            aktif_tablo = "BASARILI"

        if tablo_veri_satiri_mi(temiz_satir):
            if aktif_tablo == "KVKK":
                kritik_hata += 1

            elif aktif_tablo == "ISO27001":
                kritik_hata += 1

            elif aktif_tablo == "ISO25010":
                yuksek_hata += 1

            elif aktif_tablo == "IEEE":
                orta_hata += 1

    toplam_madde = gereksinim_sayisini_tahmin_et(analiz_metni)

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


def tum_analizi_birlestir(cevaplar):
    """
    Parçalı analiz sonuçlarını tek rapor halinde birleştirir.
    """

    if len(cevaplar) == 1:
        return cevaplar[0]

    birlesik = "## 📄 Parçalı Analiz Sonuçları\n\n"

    for index, cevap in enumerate(cevaplar, start=1):
        birlesik += f"\n\n# 🔹 Analiz Parçası {index}\n\n"
        birlesik += cevap
        birlesik += "\n\n---\n"

    return birlesik.strip()


def rapor_indirme_metni_olustur(ai_cevabi, skor):
    """
    Markdown formatında indirilebilir rapor metni üretir.
    """

    return f"""
# Gereksinim ve Kalite Analiz Raporu

## Doküman Uyum Skoru

- Taranan Madde: {skor["toplam_madde"]}
- Uyumlu Madde: {skor["basarili_madde"]}
- Hatalı Madde: {skor["toplam_hata"]}
- Kritik Hata: {skor["kritik_hata"]}
- Yüksek Hata: {skor["yuksek_hata"]}
- Orta Hata: {skor["orta_hata"]}
- Toplam Risk Cezası: {skor["toplam_ceza"]}
- Uyum Skoru: %{skor["mevcut_skor"]}

---

## Analiz Detayı

{ai_cevabi}
"""


def hata_mesaji_goster(e):
    """
    API ve analiz hatalarını kullanıcıya anlaşılır gösterir.
    """

    hata_metni = str(e)

    if "403" in hata_metni or "denied access" in hata_metni.lower():
        st.error("❌ API erişim hatası: Bu Google projesinin Gemini API erişimi reddedilmiş görünüyor.")
        st.warning(
            "Lütfen API anahtarının bağlı olduğu Google Cloud projesinde "
            "faturalandırma, API etkinleştirme, model erişimi ve API key kısıtlarını kontrol edin."
        )
        st.caption(f"Teknik detay: {e}")

    elif "prepayment credits are depleted" in hata_metni.lower():
        st.error("❌ Gemini API ön ödeme krediniz bitmiş görünüyor.")
        st.warning(
            "AI Studio > Projects bölümünden ilgili projenin faturalandırma "
            "ve kredi durumunu kontrol edin."
        )
        st.caption(f"Teknik detay: {e}")

    elif "429" in hata_metni:
        st.error("❌ Kota hatası: API kullanım kotası aşılmış olabilir.")
        st.caption(f"Teknik detay: {e}")

    elif "API key not valid" in hata_metni or "API_KEY_INVALID" in hata_metni:
        st.error("❌ API anahtarı geçersiz. Lütfen yeni bir Gemini API anahtarı girin.")
        st.caption(f"Teknik detay: {e}")

    else:
        st.error(f"❌ Analiz Hatası: {e}")


# ---------------------------------------------------------
# 6. VERİ GİRİŞİ
# ---------------------------------------------------------

st.subheader("📁 Veri Girişi")

yuklenen_dosya = st.file_uploader(
    "Dosya seçin (.docx, .pdf)",
    type=["docx", "pdf"]
)

metin_alani = st.text_area(
    "Veya metni yapıştırın:",
    height=180
)


# ---------------------------------------------------------
# 7. ANALİZ BAŞLATMA
# ---------------------------------------------------------

if st.button("🚀 Analizi Başlat"):
    analiz_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani

    if not api_key:
        st.warning("⚠️ Gemini API anahtarı girilmelidir.")

    elif not secilen_model:
        st.warning("⚠️ Model seçimi yapılmalıdır.")

    elif not analiz_metni or not analiz_metni.strip():
        st.warning("⚠️ Analiz edilecek metin veya dosya gereklidir.")

    elif len(analiz_metni.strip()) < 30:
        st.warning("⚠️ Analiz metni çok kısa görünüyor. Lütfen daha uzun bir gereksinim metni girin.")

    else:
        try:
            model = genai.GenerativeModel(secilen_model)

            parcalar = metni_parcalara_bol(analiz_metni)
            cevaplar = []

            st.info(f"📌 Metin {len(parcalar)} parça halinde analiz edilecek.")

            progress_bar = st.progress(0)
            durum_alani = st.empty()

            baslangic_zamani = time.time()

            for index, parca in enumerate(parcalar, start=1):
                durum_alani.write(f"🔍 {index}/{len(parcalar)} numaralı parça analiz ediliyor...")

                prompt = prompt_olustur(
                    analiz_metni=parca,
                    parca_no=index,
                    toplam_parca=len(parcalar)
                )

                cevap_metni = model_cevabi_uret(model, prompt)

                if cevap_metni:
                    cevaplar.append(cevap_metni)
                else:
                    cevaplar.append(
                        f"### Parça {index}\n\n❌ Bu parça için modelden geçerli yanıt alınamadı."
                    )

                progress_bar.progress(index / len(parcalar))

            bitis_zamani = time.time()
            gecen_sure = round(bitis_zamani - baslangic_zamani, 2)

            ai_cevabi = tum_analizi_birlestir(cevaplar)

            st.success(f"✅ Analiz tamamlandı. Süre: {gecen_sure} saniye")

            st.divider()

            st.markdown(ai_cevabi)

            st.divider()

            # ---------------------------------------------------------
            # 8. SKORLAMA BÖLÜMÜ
            # ---------------------------------------------------------

            with st.expander("📊 Doküman Uyum Skoru", expanded=True):
                skor = skor_hesapla(ai_cevabi, analiz_metni)

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
                    f"🔴 Kritik: {skor['kritik_hata']}\n\n"
                    f"🟠 Yüksek: {skor['yuksek_hata']}\n\n"
                    f"🟡 Orta: {skor['orta_hata']}"
                )

                c3.metric(
                    "Uyumlu Madde",
                    f"{skor['basarili_madde']} Adet"
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

            # ---------------------------------------------------------
            # 9. RAPOR İNDİRME
            # ---------------------------------------------------------

            rapor_metni = rapor_indirme_metni_olustur(ai_cevabi, skor)

            st.download_button(
                label="📥 Analiz Raporunu Markdown Olarak İndir",
                data=rapor_metni,
                file_name="gereksinim_analiz_raporu.md",
                mime="text/markdown"
            )

        except Exception as e:
            hata_mesaji_goster(e)
