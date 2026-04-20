import streamlit as st
import google.generativeai as genai
from docx import Document
import PyPDF2

# --- 1. SAYFA VE ARAYÜZ YAPILANDIRMASI ---
st.set_page_config(page_title="Gereksinim Analiz Asistanı v3.5", layout="wide")

# --- 2. GÜVENLİK VE API YÖNETİMİ (SOL MENÜ) ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    api_key = st.text_input("Gemini API Anahtarınızı girin:", type="password")
    st.divider() 
    
    secilen_model = None
    if api_key: 
        try:
            genai.configure(api_key=api_key.strip())
            modeller = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            secilen_model = st.selectbox("🤖 Model Seçin:", modeller)
        except Exception as e:
            st.error("⚠️ API Hatası.")

# --- 3. ANA EKRAN VE BİLGİLENDİRME ---
st.title("🎯 Gereksinim & Kalite Analiz Asistanı")
st.info("""
**📖 Analiz Kapsamı ve İzlenebilirlik:**
Bu sistem, gereksinim metinlerini sadece denetlemekle kalmaz; gereksinimdeki **spesifik ifadeyi** ilgili **mevzuat maddesiyle** birebir eşleştirerek teknik gerekçesini sunar.
""")
st.divider()

# --- 4. VERİ GİRİŞİ ---
st.subheader("📁 Veri Girişi")
yuklenen_dosya = st.file_uploader("Analiz edilecek dosyayı seçin (.docx, .pdf)", type=["docx", "pdf"])
metin_alani = st.text_area("Veya analiz edilecek metni buraya yapıştırın:", height=150)

def dosya_oku(dosya):
    try:
        if dosya.name.endswith('.docx'):
            doc = Document(dosya)
            return "\n".join([p.text for p in doc.paragraphs])
        elif dosya.name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(dosya)
            metin = ""
            for sayfa in range(len(pdf_reader.pages)):
                metin += pdf_reader.pages[sayfa].extract_text() + "\n"
            return metin
    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        return ""
    return ""

# --- 5. YAPAY ZEKA ANALİZ SÜRECİ ---
if st.button("🚀 Analizi Başlat"):
    analiz_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani

    if not api_key or not analiz_metni:
        st.warning("⚠️ Lütfen API anahtarını ve analiz edilecek metni sağlayın.")
    else:
        try:
            model = genai.GenerativeModel(secilen_model)
            
            # --- GÜNCELLENMİŞ PROMPT MÜHENDİSLİĞİ (YENİ SÜTUN EKLENDİ) ---
            sistem_talimati = """
            Sen uzman bir Yazılım Kalite Direktörü ve Hukuk-Teknik Denetçisisin.
            Gereksinimleri analiz ederken 'İzlenebilirlik' (Traceability) prensibini uygula.

            KURAL 1: Doğrudan tablolara başla. Giriş/Sonuç cümlesi yazma.
            KURAL 2: Her ihlal için gereksinim belgesindeki 'İLGİLİ İFADEYİ' alıntıla ve hangi 'STANDART MADDESİ' ile çeliştiğini açıkla.
            KURAL 3: İhlal yoksa "✅ Tam uyum sağlanmıştır" yaz.
            KURAL 4: İkonları kullan: IEEE(🟡), KVKK/ISO27001(🔴), ISO25010(🟠), Başarılı(🟢).

            ### 1. 📏 IEEE 29148 Gereksinim Kalitesi Uyumluluğu
            | Gereksinimdeki İfade | İhlal Edilen Kriter | Standart Karşılığı ve Analiz | Uyum Önerisi |
            |---|---|---|---|

            ### 2. 🛡️ KVKK ve Veri Gizliliği Mevzuatı Uyumluluğu
            | Gereksinimdeki İfade | KVKK Riski | Mevzuat Maddesi ve Çelişme Nedeni | Hukuki Uyum Şartı |
            |---|---|---|---|

            ### 3. 🔒 ISO 27001 ve CBDDO Bilgi Güvenliği Uyumluluğu
            | Gereksinimdeki İfade | Güvenlik Zafiyeti | Referans Madde ve Teknik Gerekçe | Teknik Önlem |
            |---|---|---|---|

            ### 4. ⚙️ ISO 25010 Yazılım Kalite Modeli Uyumluluğu
            | Gereksinimdeki İfade | Kalite Eksikliği | Karakteristik ve Analiz | Kalite Hedefi |
            |---|---|---|---|

            ### 5. 🌟 Standartlara Tam Uyumlu Gereksinimler
            | Başarılı Gereksinim | Karşıladığı Standartlar | Uyum Gerekçesi (Neden Başarılı?) |
            |---|---|---|
            """
            
            with st.spinner("Yapay Zeka İzlenebilirlik Analizini Gerçekleştiriyor..."):
                cevap = model.generate_content(f"{sistem_talimati}\n\nMetin:\n{analiz_metni}")
            
            st.success("✅ Analiz Tamamlandı: Gereksinim-Standart Eşleşmesi Sağlandı.")
            st.markdown(cevap.text)
            
            # --- 6. RİSK SKORLAMA VE YÖNETİCİ ÖZETİ ---
            with st.expander("📊 Doküman Uyum Skoru", expanded=True):
                satirlar = cevap.text.split('\n')
                kritik, yuksek, orta = 0, 0, 0
                aktif = 0
                for s in satirlar:
                    if "IEEE 29148" in s: aktif = 1
                    elif "KVKK" in s: aktif = 2
                    elif "ISO 27001" in s: aktif = 3
                    elif "ISO 25010" in s: aktif = 4
                    elif "Standartlara Tam Uyumlu" in s: aktif = 5
                    
                    if "|" in s and "---" not in s and "İfade" not in s and "✅" not in s and aktif != 5:
                        if aktif in [2, 3]: kritik += 1
                        elif aktif == 4: yuksek += 1
                        elif aktif == 1: orta += 1
                
                kesilen = (kritik * 10) + (yuksek * 6) + (orta * 3)
                mevcut_skor = max(0, 100 - kesilen)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Genel Uyum Skoru", f"% {mevcut_skor}", f"-{kesilen} Puan")
                c2.markdown(f"**🔴 {kritik}** Kritik | **🟠 {yuksek}** Yüksek | **🟡 {orta}** Orta")
                c3.metric("Hedef Skor", "% 100", f"+{100 - mevcut_skor}")

        except Exception as e:
            st.error(f"❌ Hata: {e}")
