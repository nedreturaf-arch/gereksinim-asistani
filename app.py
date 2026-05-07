import streamlit as st
import markdown
from xhtml2pdf import pisa
import io
import base64
import google.generativeai as genai
from docx import Document
import pypdf as PyPDF2
import time

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
                # Flash modelini otomatik seçmeye çalışalım
                flash_index = 0
                for i, m in enumerate(modeller):
                    if "flash" in m.lower():
                        flash_index = i
                        break
                secilen_model = st.selectbox("🤖 Model Seçin:", modeller, index=flash_index)
        except Exception as e:
            st.error(f"⚠️ API Hatası: {e}")

# ---------------------------------------------------------
# 3. YARDIMCI FONKSİYONLAR
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
    html_tablolar = markdown.markdown(ai_metni, extensions=['tables'])
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
# 4. ANA AKIŞ
# ---------------------------------------------------------
st.title("🎯 Gereksinim & Kalite Analiz Asistanı")

yuklenen_dosya = st.file_uploader("Dosya seçin (.docx, .pdf)", type=["docx", "pdf"])
metin_alani = st.text_area("Veya metni yapıştırın:", height=100)

if st.button("🚀 Analizi Başlat"):
    girdi_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani
    
    if not api_key or not girdi_metni.strip() or not secilen_model:
        st.warning("⚠️ Lütfen API anahtarını ve analiz edilecek metni kontrol edin.")
    else:
        # Eski sonuçları temizle
        if 'analiz_sonucu' in st.session_state:
            for key in ['analiz_sonucu', 'skorlar', 'analiz_suresi']:
                if key in st.session_state: del st.session_state[key]
        
        try:
            baslangic = time.time()
            model = genai.GenerativeModel(secilen_model)
            sistem_talimati = "Sen uzman bir BT Uyum Denetçisisin. Yanıtlarını SADECE Türkçe ve markdown tabloları halinde ver."
            
            # Streaming (Akış) başlatılıyor
            response = model.generate_content(f"{sistem_talimati}\n\nMETİN:\n{girdi_metni}", stream=True)
            
            # Ekranda canlı yazdırma için jeneratör fonksiyonu
            def stream_yazdir():
                for chunk in response:
                    yield chunk.text

            # Canlı çıktı alanı
            full_text = st.write_stream(stream_yazdir())
            
            bitis = time.time()
            gecen_sure = round(bitis - baslangic, 2)
            
            # Sonuçları hafızaya kaydet (PDF ve Skorlar için)
            st.session_state['analiz_sonucu'] = full_text
            st.session_state['skorlar'] = skor_hesapla(full_text, girdi_metni)
            st.session_state['analiz_suresi'] = gecen_sure
            
            # Akış bittikten sonra sayfayı sonuçları sabitlemek için tetikle
            st.rerun()

        except Exception as e:
            st.error(f"Analiz sırasında hata: {e}")

# Hafızada sonuç varsa (akış bittikten sonra burası çalışır)
if 'analiz_sonucu' in st.session_state:
    sure = st.session_state.get('analiz_suresi', 0)
    st.success(f"✅ Analiz {sure} saniyede tamamlandı!")
    st.markdown(st.session_state['analiz_sonucu'])
    
    with st.expander("📊 Uyum Skoru Detayları", expanded=True):
        s = st.session_state['skorlar']
        st.metric("Uyum Skoru", f"% {s['skor']}", f"-{s['ceza']} Risk")
        st.write(f"🔴 {s['kritik']} Kritik | 🟠 {s['yuksek']} Yüksek | 🟡 {s['orta']} Orta")

    st.divider()
    pdf_bytes = pdf_olustur(st.session_state['analiz_sonucu'], st.session_state['skorlar'])
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_link = f'<a href="data:application/pdf;base64,{b64_pdf}" target="_blank"><button style="background-color:#ff4b4b; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer;">📄 Raporu Yeni Sekmede Aç / Yazdır</button></a>'
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(pdf_link, unsafe_allow_html=True)
    with col2:
        st.download_button(label="📥 Raporu PDF Olarak İndir", data=pdf_bytes, file_name="Analiz_Raporu.pdf", mime="application/pdf")
