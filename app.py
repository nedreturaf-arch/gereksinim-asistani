import streamlit as st
import markdown
from xhtml2pdf import pisa
import io
import base64
import google.generativeai as genai
from docx import Document
import pypdf as PyPDF2

# ---------------------------------------------------------
# 1. SAYFA VE ARAYÜZ YAPILANDIRMASI
# ---------------------------------------------------------
st.set_page_config(page_title="Gereksinim Analiz Asistanı v3.9", layout="wide")

# CSS ile Türkçe karakter desteği ve görsel iyileştirme
st.markdown("""
    <style>
    .report-font { font-family: 'Arial', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. GÜVENLİK VE API YÖNETİMİ
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Ayarlar")
    api_key = st.text_input("Gemini API Anahtarınızı girin:", type="password")
    st.divider()
    secilen_model = None

    if api_key:
        try:
            genai.configure(api_key=api_key.strip())
            modeller = [m.name.replace("models/", "") for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
            if modeller:
                secilen_model = st.selectbox("🤖 Model Seçin:", modeller, index=0)
        except Exception as e:
            st.error(f"⚠️ API Hatası: {e}")

# ---------------------------------------------------------
# 3. YARDIMCI FONKSİYONLAR (HIZLANDIRILMIŞ)
# ---------------------------------------------------------
def dosya_oku(dosya):
    if dosya is None: return ""
    try:
        if dosya.name.lower().endswith(".docx"):
            doc = Document(dosya)
            return "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
        elif dosya.name.lower().endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(dosya)
            return "\n".join([sayfa.extract_text() for sayfa in pdf_reader.pages if sayfa.extract_text()])
    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
    return ""

def skor_hesapla(ai_cevabi, analiz_metni):
    # (Mevcut matematiksel mantığınız korunmuştur)
    satirlar = ai_cevabi.split("\n")
    k, y, o = 0, 0, 0
    aktif = 0
    for satir in satirlar:
        s = satir.strip()
        if "IEEE 29148" in s: aktif = 1
        elif "KVKK" in s: aktif = 2
        elif "ISO 27001" in s: aktif = 3
        elif "ISO 25010" in s: aktif = 4
        if s.startswith("|") and s.endswith("|") and "---" not in s and "İfade" not in s:
            if aktif in [2, 3]: k += 1
            elif aktif == 4: y += 1
            elif aktif == 1: o += 1
    
    toplam_m = len([s for s in analiz_metni.split("\n") if len(s.strip()) > 15]) or 1
    toplam_h = k + y + o
    ceza = (k * 10 + y * 6 + o * 3)
    skor = max(0, round(100 * (1 - (ceza / (toplam_m * 10)))))
    return {"kritik": k, "yuksek": y, "orta": o, "toplam_h": toplam_h, "toplam_m": toplam_m, "skor": skor, "ceza": ceza}

def pdf_olustur(ai_metni, skor_verisi):
    # ÇÖZÜM 1: TÜRKÇE KARAKTER SORUNU İÇİN ÖZEL HTML ŞABLONU
    html_tablolar = markdown.markdown(ai_metni, extensions=['tables'])
    
    # xhtml2pdf için Unicode (DejaVu Sans) desteği içeren şablon
    html_template = f"""
    <html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <style>
            @page {{ size: a4; margin: 1cm; }}
            body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #333; }}
            h1 {{ color: #2C3E50; text-align: center; border-bottom: 1px solid #ccc; }}
            .skor {{ background-color: #f1f4f9; padding: 10px; border-radius: 5px; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ border: 1px solid #444; padding: 6px; text-align: left; }}
            th {{ background-color: #2C3E50; color: white; }}
        </style>
    </head>
    <body>
        <h1>Gereksinim Analiz Raporu</h1>
        <div class="skor">
            <b>Genel Uyum Skoru: %{skor_verisi['skor']}</b><br>
            Taranan Madde: {skor_verisi['toplam_m']} | Hatalı: {skor_verisi['toplam_h']}<br>
            (Kritik: {skor_verisi['kritik']}, Yuksek: {skor_verisi['yuksek']}, Orta: {skor_verisi['orta']})
        </div>
        {html_tablolar}
    </body>
    </html>
    """
    pdf_buffer = io.BytesIO()
    pisa.CreatePDF(html_template, dest=pdf_buffer, encoding='utf-8')
    return pdf_buffer.getvalue()

# ---------------------------------------------------------
# 4. ANA AKIŞ VE HIZLANDIRMA (SESSION STATE)
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

yuklenen_dosya = st.file_uploader("Dosya seçin (.docx, .pdf)", type=["docx", "pdf"])
metin_alani = st.text_area("Veya metni yapıştırın:", height=100)

# ÇÖZÜM 2: YAVAŞ ÇALIŞMA SORUNU İÇİN HAFIZA YÖNETİMİ
if st.button("🚀 Analizi Başlat"):
    girdi_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani
    
    if not api_key or not girdi_metni.strip() or not secilen_model:
        st.warning("⚠️ Lütfen API anahtarını ve analiz edilecek metni kontrol edin.")
    else:
        with st.spinner("Yapay zeka analiz ediyor..."):
            try:
                model = genai.GenerativeModel(secilen_model)
                sistem_talimati = "Sen uzman bir BT Uyum Denetçisisin. Yanıtlarını Türkçe ve tablolar halinde ver."
                cevap = model.generate_content(f"{sistem_talimati}\n\nMETİN:\n{girdi_metni}")
                
                # Sonuçları hafızaya al (Böylece sayfa her etkileşimde Gemini'ye gitmez)
                st.session_state['analiz_sonucu'] = cevap.text
                st.session_state['skorlar'] = skor_hesapla(cevap.text, girdi_metni)
            except Exception as e:
                st.error(f"Analiz sırasında hata: {e}")

# Hafızada sonuç varsa göster
if 'analiz_sonucu' in st.session_state:
    st.success("✅ Analiz Tamamlandı!")
    st.markdown(st.session_state['analiz_sonucu'])
    
    with st.expander("📊 Uyum Skoru Detayları", expanded=True):
        s = st.session_state['skorlar']
        st.metric("Uyum Skoru", f"% {s['skor']}", f"-{s['ceza']} Risk")
        st.write(f"🔴 {s['kritik']} Kritik | 🟠 {s['yuksek']} Yüksek | 🟡 {s['orta']} Orta")

    # ÇÖZÜM 3: AYRI SEKMEDE AÇMA VE İNDİRME ÇÖZÜMÜ
    st.divider()
    pdf_bytes = pdf_olustur(st.session_state['analiz_sonucu'], st.session_state['skorlar'])
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    
    # HTML ile "Yeni Sekmede Aç" köprüsü
    pdf_link = f'<a href="data:application/pdf;base64,{b64_pdf}" target="_blank" style="text-decoration:none;"><button style="background-color:#ff4b4b; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer;">📄 Raporu Yeni Sekmede Aç / Yazdır</button></a>'
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(pdf_link, unsafe_allow_html=True)
    with col2:
        st.download_button(label="📥 Raporu PDF Olarak İndir", data=pdf_bytes, file_name="Analiz_Raporu.pdf", mime="application/pdf")
