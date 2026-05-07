import streamlit as st
import markdown
from xhtml2pdf import pisa
import io
import base64
import html
import time

import google.generativeai as genai
from docx import Document
import pypdf as PyPDF2


# ---------------------------------------------------------
# 1. SAYFA VE ARAYÜZ YAPILANDIRMASI
# ---------------------------------------------------------

st.set_page_config(
    page_title="Gereksinim Analiz Asistanı v4.0",
    layout="wide"
)

st.markdown(
    """
    <style>
    .report-font {
        font-family: Arial, sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ---------------------------------------------------------
# 2. SABİTLER
# ---------------------------------------------------------

TERCIH_EDILEN_MODEL = "gemini-2.5-flash"

MAX_OUTPUT_TOKENS = 4096

KRITIK_CEZA = 10
YUKSEK_CEZA = 6
ORTA_CEZA = 3


# ---------------------------------------------------------
# 3. MODEL LİSTESİ ÖNBELLEĞİ
# ---------------------------------------------------------

@st.cache_data(show_spinner=False)
def modelleri_getir(api_key: str):
    """
    API anahtarına göre kullanılabilir Gemini modellerini getirir.
    Streamlit yeniden çalıştığında listeyi tekrar tekrar çekmemek için önbelleğe alınır.
    """
    genai.configure(api_key=api_key.strip())

    modeller = [
        m.name.replace("models/", "")
        for m in genai.list_models()
        if "generateContent" in m.supported_generation_methods
    ]

    return modeller


# ---------------------------------------------------------
# 4. SIDEBAR - API VE MODEL YÖNETİMİ
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
                st.warning("Kullanılabilir model bulunamadı.")

        except Exception as e:
            st.error("⚠️ API bağlantısı kurulamadı.")
            st.caption(f"Teknik detay: {e}")


# ---------------------------------------------------------
# 5. YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------

def dosya_oku(dosya):
    """
    PDF veya DOCX dosyasını okur.
    Metni analiz edilebilir düz yazıya dönüştürür.
    """

    if dosya is None:
        return ""

    try:
        dosya_adi = dosya.name.lower()

        if dosya_adi.endswith(".docx"):
            doc = Document(dosya)

            metinler = []

            # Paragraflar
            for p in doc.paragraphs:
                temiz = p.text.strip()
                if temiz:
                    metinler.append(temiz)

            # DOCX içindeki tablolar
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

        else:
            st.warning("Desteklenmeyen dosya türü.")
            return ""

    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        return ""


def sistem_talimati_olustur():
    """
    Kısa, kontrollü ve hızlı analiz için sistem talimatı üretir.
    Çıktı uzunluğu özellikle sınırlandırılmıştır.
    """

    return """
Sen uzman bir BT Uyum Denetçisi ve Gereksinim Mühendisliği Analistisin.
Yanıtlarını SADECE Türkçe üret.

GENEL KURALLAR:
- Giriş paragrafı yazma.
- Sonuç paragrafı yazma.
- Sadece aşağıdaki 5 tabloyu üret.
- Her tabloda en fazla 8 bulgu ver.
- Metinde olmayan gereksinim ifadesi üretme.
- Uydurma standart maddesi yazma.
- Emin olmadığın durumda kesin madde numarası verme.
- Bulguları kısa yaz.
- Her öneriyi tek cümleyle ver.
- Aynı bulguyu gereksiz tekrar etme.
- İhlal yoksa ilgili tabloya "✅ Tam uyum sağlanmıştır" yaz.
- Başarılı örnekler tablosunda en fazla 5 örnek ver.

RİSK SINIFLANDIRMASI:
- KVKK ve ISO 27001 bulguları kritik risk kabul edilir.
- ISO 25010 bulguları yüksek risk kabul edilir.
- IEEE 29148 bulguları orta risk kabul edilir.

ÇIKTI FORMATI:

### 1. 📏 IEEE 29148 Uyumluluğu
| Gereksinimdeki İfade | İhlal Edilen Kriter | Standart Karşılığı ve Analiz | Uyum Önerisi |
|---|---|---|---|

### 2. 🛡️ KVKK Uyumluluğu
| Gereksinimdeki İfade | KVKK Riski | Mevzuat Çerçevesi ve Çelişme Nedeni | Hukuki Uyum Önerisi |
|---|---|---|---|

### 3. 🔒 ISO 27001 Uyumluluğu
| Gereksinimdeki İfade | Güvenlik Riski | Referans Alan ve Teknik Gerekçe | Teknik Önlem |
|---|---|---|---|

### 4. ⚙️ ISO 25010 Uyumluluğu
| Gereksinimdeki İfade | Kalite Eksikliği | Karakteristik ve Analiz | Kalite Hedefi |
|---|---|---|---|

### 5. 🌟 Standartlara Tam Uyumlu Gereksinimler
| Başarılı Gereksinim | Karşıladığı Standartlar | Uyum Gerekçesi |
|---|---|---|
"""


def tablo_veri_satiri_mi(satir):
    """
    Markdown tablo satırının gerçek bulgu satırı olup olmadığını kontrol eder.
    Başlık ve ayırıcı satırları saymaz.
    """

    temiz = satir.strip()

    if not temiz.startswith("|") or not temiz.endswith("|"):
        return False

    if "---" in temiz:
        return False

    baslik_ifadeleri = [
        "Gereksinimdeki İfade",
        "İhlal Edilen Kriter",
        "KVKK Riski",
        "Güvenlik Riski",
        "Kalite Eksikliği",
        "Başarılı Gereksinim"
    ]

    if any(ifade in temiz for ifade in baslik_ifadeleri):
        return False

    uyum_ifadeleri = [
        "✅ Tam uyum sağlanmıştır",
        "Tam uyum sağlanmıştır",
        "Metin içerisinde standartlara tam uyumlu"
    ]

    if any(ifade in temiz for ifade in uyum_ifadeleri):
        return False

    return True


def skor_hesapla(ai_cevabi, analiz_metni):
    """
    AI cevabındaki tablo satırlarına göre risk ve uyum skoru hesaplar.
    """

    satirlar = ai_cevabi.split("\n")

    kritik = 0
    yuksek = 0
    orta = 0

    aktif_tablo = None

    for satir in satirlar:
        s = satir.strip()

        if "IEEE 29148 Uyumluluğu" in s:
            aktif_tablo = "IEEE"

        elif "KVKK Uyumluluğu" in s:
            aktif_tablo = "KVKK"

        elif "ISO 27001 Uyumluluğu" in s:
            aktif_tablo = "ISO27001"

        elif "ISO 25010 Uyumluluğu" in s:
            aktif_tablo = "ISO25010"

        elif "Standartlara Tam Uyumlu" in s:
            aktif_tablo = "BASARILI"

        if tablo_veri_satiri_mi(s):
            if aktif_tablo in ["KVKK", "ISO27001"]:
                kritik += 1
            elif aktif_tablo == "ISO25010":
                yuksek += 1
            elif aktif_tablo == "IEEE":
                orta += 1

    toplam_madde = len(
        [satir for satir in analiz_metni.split("\n") if len(satir.strip()) > 15]
    ) or 1

    toplam_hata = kritik + yuksek + orta

    ceza = (
        kritik * KRITIK_CEZA +
        yuksek * YUKSEK_CEZA +
        orta * ORTA_CEZA
    )

    maksimum_risk = max(1, toplam_madde * KRITIK_CEZA)

    skor = max(
        0,
        round(100 * (1 - (ceza / maksimum_risk)))
    )

    basarili = max(0, toplam_madde - toplam_hata)

    return {
        "kritik": kritik,
        "yuksek": yuksek,
        "orta": orta,
        "toplam_h": toplam_hata,
        "toplam_m": toplam_madde,
        "basarili": basarili,
        "skor": skor,
        "ceza": ceza,
        "maksimum_risk": maksimum_risk
    }


def pdf_olustur(ai_metni, skor_verisi):
    """
    Analiz sonucunu PDF formatına dönüştürür.
    PDF sadece kullanıcı istediğinde hazırlanır.
    """

    html_tablolar = markdown.markdown(ai_metni, extensions=["tables"])

    skor_html = f"""
    <div class="skor">
        <b>Genel Uyum Skoru: %{skor_verisi['skor']}</b><br/>
        Taranan Madde: {skor_verisi['toplam_m']}<br/>
        Uyumlu Madde: {skor_verisi['basarili']}<br/>
        Hatalı Madde: {skor_verisi['toplam_h']}<br/>
        Kritik: {skor_verisi['kritik']} |
        Yüksek: {skor_verisi['yuksek']} |
        Orta: {skor_verisi['orta']}<br/>
        Toplam Risk Cezası: {skor_verisi['ceza']}
    </div>
    """

    html_template = f"""
    <html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
        <style>
            @page {{
                size: A4;
                margin: 1cm;
            }}

            body {{
                font-family: Helvetica, Arial, sans-serif;
                font-size: 9pt;
                color: #222;
            }}

            h1 {{
                color: #2C3E50;
                text-align: center;
                border-bottom: 1px solid #cccccc;
                padding-bottom: 8px;
            }}

            h3 {{
                color: #2C3E50;
                margin-top: 16px;
            }}

            .skor {{
                background-color: #f1f4f9;
                padding: 10px;
                border: 1px solid #cccccc;
                margin-bottom: 18px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 8px;
                margin-bottom: 14px;
            }}

            th, td {{
                border: 1px solid #444444;
                padding: 5px;
                text-align: left;
                vertical-align: top;
            }}

            th {{
                background-color: #2C3E50;
                color: white;
                font-weight: bold;
            }}
        </style>
    </head>

    <body>
        <h1>Gereksinim Analiz Raporu</h1>
        {skor_html}
        {html_tablolar}
    </body>
    </html>
    """

    pdf_buffer = io.BytesIO()

    pisa_status = pisa.CreatePDF(
        html_template,
        dest=pdf_buffer,
        encoding="utf-8"
    )

    if pisa_status.err:
        raise RuntimeError("PDF oluşturulurken hata oluştu.")

    return pdf_buffer.getvalue()


def hata_mesaji_goster(e):
    """
    Gemini API hatalarını kullanıcıya daha anlaşılır gösterir.
    """

    hata_metni = str(e)

    if "403" in hata_metni or "denied access" in hata_metni.lower():
        st.error("❌ API erişim hatası.")
        st.warning(
            "Google Cloud projesinin Gemini API erişimi reddedilmiş olabilir. "
            "Faturalandırma, ödeme doğrulama ve API key kısıtlarını kontrol edin."
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
        st.error("❌ Kota veya kullanım sınırı hatası.")
        st.warning(
            "Kullanım kotanız dolmuş olabilir. Bir süre bekleyin veya "
            "AI Studio üzerinden proje kotanızı kontrol edin."
        )
        st.caption(f"Teknik detay: {e}")

    elif "API key" in hata_metni or "API_KEY" in hata_metni:
        st.error("❌ API anahtarı geçersiz veya yetkisiz görünüyor.")
        st.caption(f"Teknik detay: {e}")

    else:
        st.error(f"❌ Analiz sırasında hata: {e}")


def temizle():
    """
    Eski analiz ve PDF çıktılarını temizler.
    """

    for key in [
        "analiz_sonucu",
        "skorlar",
        "pdf_bytes",
        "analiz_metni",
        "analiz_suresi"
    ]:
        if key in st.session_state:
            del st.session_state[key]


# ---------------------------------------------------------
# 6. ANA ARAYÜZ
# ---------------------------------------------------------

st.title("🎯 Gereksinim & Kalite Analiz Asistanı")

st.info(
    "Bu sistem; IEEE 29148, ISO/IEC 25010, ISO/IEC 27001 ve KVKK "
    "kapsamında gereksinim dokümanlarını ön analizden geçirir."
)

st.subheader("📁 Veri Girişi")

yuklenen_dosya = st.file_uploader(
    "Dosya seçin (.docx, .pdf)",
    type=["docx", "pdf"]
)

metin_alani = st.text_area(
    "Veya metni yapıştırın:",
    height=120
)

col_a, col_b = st.columns([1, 1])

with col_a:
    analiz_baslat = st.button("🚀 Analizi Başlat")

with col_b:
    temizle_buton = st.button("🧹 Sonuçları Temizle")

if temizle_buton:
    temizle()
    st.rerun()


# ---------------------------------------------------------
# 7. ANALİZ
# ---------------------------------------------------------

if analiz_baslat:
    temizle()

    girdi_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani

    if not api_key:
        st.warning("⚠️ Gemini API anahtarı girilmelidir.")

    elif not secilen_model:
        st.warning("⚠️ Model seçimi yapılmalıdır.")

    elif not girdi_metni or not girdi_metni.strip():
        st.warning("⚠️ Analiz edilecek metin veya dosya gereklidir.")

    elif len(girdi_metni.strip()) < 30:
        st.warning("⚠️ Analiz metni çok kısa görünüyor.")

    else:
        try:
            genai.configure(api_key=api_key.strip())

            model = genai.GenerativeModel(secilen_model)

            sistem_talimati = sistem_talimati_olustur()

            generation_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "max_output_tokens": MAX_OUTPUT_TOKENS
            }

            tam_prompt = f"""
{sistem_talimati}

ANALİZ EDİLECEK METİN:
{girdi_metni.strip()}
"""

            with st.spinner("Yapay zeka analiz ediyor..."):
                baslangic = time.time()

                cevap = model.generate_content(
                    tam_prompt,
                    generation_config=generation_config
                )

                bitis = time.time()

            if cevap and hasattr(cevap, "text") and cevap.text:
                analiz_sonucu = cevap.text.strip()
                skorlar = skor_hesapla(analiz_sonucu, girdi_metni)

                st.session_state["analiz_sonucu"] = analiz_sonucu
                st.session_state["skorlar"] = skorlar
                st.session_state["analiz_metni"] = girdi_metni
                st.session_state["analiz_suresi"] = round(bitis - baslangic, 2)

                st.success(
                    f"✅ Analiz tamamlandı. Süre: "
                    f"{st.session_state['analiz_suresi']} saniye"
                )

            else:
                st.error("❌ Modelden geçerli yanıt alınamadı.")

        except Exception as e:
            hata_mesaji_goster(e)


# ---------------------------------------------------------
# 8. SONUÇLARI GÖSTER
# ---------------------------------------------------------

if "analiz_sonucu" in st.session_state:
    st.success("✅ Analiz Sonucu Hazır")

    if "analiz_suresi" in st.session_state:
        st.caption(f"Analiz süresi: {st.session_state['analiz_suresi']} saniye")

    st.markdown(st.session_state["analiz_sonucu"])

    with st.expander("📊 Uyum Skoru Detayları", expanded=True):
        s = st.session_state["skorlar"]

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Uyum Skoru",
            f"% {s['skor']}",
            f"-{s['ceza']} Risk"
        )

        c2.write(
            f"🔴 Kritik: {s['kritik']}\n\n"
            f"🟠 Yüksek: {s['yuksek']}\n\n"
            f"🟡 Orta: {s['orta']}"
        )

        c3.metric(
            "Taranan Madde",
            f"{s['toplam_m']}"
        )

        st.write(
            f"Uyumlu madde: **{s['basarili']}** | "
            f"Hatalı madde: **{s['toplam_h']}** | "
            f"Maksimum risk: **{s['maksimum_risk']}**"
        )

    st.divider()

    st.subheader("📄 Rapor Çıktısı")

    st.write(
        "PDF raporu yalnızca aşağıdaki butona bastığınızda hazırlanır. "
        "Bu işlem, sayfanın her yenilenmesinde tekrar çalışmaz."
    )

    if st.button("📄 PDF Raporu Hazırla"):
        try:
            with st.spinner("PDF raporu hazırlanıyor..."):
                st.session_state["pdf_bytes"] = pdf_olustur(
                    st.session_state["analiz_sonucu"],
                    st.session_state["skorlar"]
                )

            st.success("✅ PDF raporu hazır.")

        except Exception as e:
            st.error(f"PDF oluşturma hatası: {e}")

    if "pdf_bytes" in st.session_state:
        pdf_bytes = st.session_state["pdf_bytes"]

        st.download_button(
            label="📥 Raporu PDF Olarak İndir",
            data=pdf_bytes,
            file_name="Gereksinim_Analiz_Raporu.pdf",
            mime="application/pdf"
        )

        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

        pdf_link = f"""
        <a href="data:application/pdf;base64,{b64_pdf}" target="_blank"
           style="text-decoration:none;">
            <button style="
                background-color:#ff4b4b;
                color:white;
                border:none;
                padding:10px 20px;
                border-radius:5px;
                cursor:pointer;">
                📄 Raporu Yeni Sekmede Aç / Yazdır
            </button>
        </a>
        """

        st.markdown(pdf_link, unsafe_allow_html=True)
