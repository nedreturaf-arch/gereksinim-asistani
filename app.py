import streamlit as st
import google.generativeai as genai
from docx import Document
import PyPDF2
import time

# --- 1. SAYFA VE ARAYÜZ YAPILANDIRMASI ---
st.set_page_config(page_title="Gereksinim Analiz Asistanı v3.6", layout="wide")

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
            if modeller:
                secilen_model = st.selectbox("🤖 Model Seçin:", modeller)
            else:
                st.error("⚠️ Uygun model bulunamadı.")
        except Exception as e:
            st.error("⚠️ API Hatası: Bağlantı kurulamadı. Anahtarı kontrol edin.")

# --- 3. ANA EKRAN VE GENİŞLETİLMİŞ BİLGİLENDİRME ---
st.title("🎯 Gereksinim & Kalite Analiz Asistanı")
st.info("""
**📖 Analiz Kapsamı ve Referans Standartlar:**
Bu sistem, gereksinim metinlerini aşağıdaki uluslararası standartlar ve yerel mevzuatlar çerçevesinde denetleyerek, spesifik ifadeleri doğrudan ilgili maddeyle eşleştirir:

* **IEEE 29148:** Yazılım ve Sistem Mühendisliği — Gereksinim Mühendisliği Standartları
* **ISO/IEC 25010:** Yazılım Ürün Kalitesi ve Sistem Kalite Modelleri (Sistem Verimliliği)
* **ISO/IEC 27001:** Bilgi Güvenliği Yönetim Sistemi Gereksinimleri
* **KVKK:** 6698 Sayılı Kişisel Verilerin Korunması Kanunu
""")
st.divider()

# --- 4. VERİ GİRİŞİ (STATELESS MİMARİ) ---
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

def sure_formatla(saniye):
    dakika = int(saniye // 60)
    kalan_saniye = round(saniye % 60, 2)
    if dakika > 0:
        return f"{dakika} dk {kalan_saniye} sn"
    return f"{kalan_saniye} sn"

# --- 5. YAPAY ZEKA ANALİZ SÜRECİ ---
if st.button("🚀 Analizi Başlat"):
    analiz_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani

    if not api_key or not secilen_model or not analiz_metni:
        st.warning("⚠️ Lütfen API anahtarını girin, geçerli bir model seçin ve analiz edilecek metni sağlayın.")
    else:
        try:
            model = genai.GenerativeModel(secilen_model)
            
            # --- PROMPT MÜHENDİSLİĞİ ---
            sistem_talimati = """
            Sen uzman bir Yazılım Kalite Direktörü ve BT Uyum Denetçisisin.
            Gereksinimleri analiz ederken 'İzlenebilirlik' (Traceability) prensibini uygula.
            KURAL 1: Doğrudan tablolara başla. Giriş/Sonuç cümlesi yazma.
            KURAL 2: Her ihlal için gereksinim belgesindeki 'İLGİLİ İFADEYİ' alıntıla ve hangi 'STANDART MADDESİ' ile neden çeliştiğini açıkla.
            KURAL 3: İhlal yoksa "✅ Tam uyum sağlanmıştır" yaz.
            KURAL 4: Risk İkonları: IEEE(🟡), KVKK/ISO27001(🔴), ISO25010(🟠), Başarılı(🟢).
            KURAL 5: Tablo 5 (Başarılı Örnekler) kısmına en az 5 adet en iyi pratik örneğini ekle.

            ### 1. 📏 IEEE 29148 Uyumluluğu
            ### 2. 🛡️ KVKK Uyumluluğu
            ### 3. 🔒 ISO 27001 Uyumluluğu
            ### 4. ⚙️ ISO 25010 Uyumluluğu
            ### 5. 🌟 Başarılı Gereksinimler
            """
            
            with st.spinner("Yapay Zeka İzlenebilirlik Analizini Gerçekleştiriyor..."):
                baslangic_zamani = time.time()
                cevap = model.generate_content(f"{sistem_talimati}\n\nAnaliz edilecek metin:\n{analiz_metni}")
                bitis_zamani = time.time()

            gecen_sure = round(bitis_zamani - baslangic_zamani, 2)
            st.success(f"✅ Analiz Tamamlandı! Süre: {sure_formatla(gecen_sure)}")
            
            st.metric(label="⏱️ Analiz Süresi", value=sure_formatla(gecen_sure))
            st.markdown(cevap.text)
            
            # --- 6. PROFESYONEL ORANSAL SKORLAMA ---
            # DİKKAT: Bu blok 'try' içerisinde, st.markdown'ın hemen altında olmalı!
            with st.expander("📊 Doküman Uyum Skoru (ISTQB Risk & Yoğunluk Analizi)", expanded=True):
                satirlar = cevap.text.split('\n')
                kritik_hata, yuksek_hata, orta_hata = 0, 0, 0
                aktif_tablo = 0
                
                for satir in satirlar:
                    if "IEEE 29148" in satir: aktif_tablo = 1
                    elif "KVKK" in satir: aktif_tablo = 2
                    elif "ISO 27001" in satir: aktif_tablo = 3
                    elif "ISO 25010" in satir: aktif_tablo = 4
                    elif "Başarılı" in satir: aktif_tablo = 5
                    
                    if "|" in satir and "---" not in satir and "İfade" not in satir and "✅" not in satir and aktif_tablo != 5:
                        if aktif_tablo in [2, 3]: kritik_hata += 1
                        elif aktif_tablo == 4: yuksek_hata += 1
                        elif aktif_tablo == 1: orta_hata += 1
                
                toplam_madde = len([s for s in analiz_metni.split('\n') if len(s.strip()) > 15])
                toplam_madde = max(1, toplam_madde) # 0'a bölünme hatası engeli
                
                toplam_ceza = (kritik_hata * 10) + (yuksek_hata * 6) + (orta_hata * 3)
                max_potansiyel = toplam_madde * 10
                mevcut_skor = round(max(0, (1 - (toplam_ceza / max_potansiyel)) * 100), 1)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Kalite Endeksi", f"% {mevcut_skor}", f"-{toplam_ceza} Risk Puanı", delta_color="inverse")
                with col2:
                    st.write(f"**🔴 {kritik_hata}** Kritik | **🟠 {yuksek_hata}** Yüksek | **🟡 {orta_hata}** Orta")
                with col3:
                    hata_yogunlugu = round(((kritik_hata + yuksek_hata + orta_hata) / toplam_madde), 2)
                    st.metric("Hata Yoğunluğu", f"{hata_yogunlugu}", "Hata / Madde")

        except Exception as e:
            st.error(f"❌ Analiz Hatası: {e}")
