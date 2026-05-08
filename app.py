import streamlit as st
import google.generativeai as genai
from docx import Document
import PyPDF2
import time
import re

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
                # Varsayılan olarak pro modelini seçmeye çalışalım, yoksa ilkini alalım
                varsayilan_index = modeller.index("gemini-1.5-pro") if "gemini-1.5-pro" in modeller else 0
                secilen_model = st.selectbox("🤖 Model Seçin:", modeller, index=varsayilan_index)
            else:
                st.error("⚠️ Uygun model bulunamadı.")
        except Exception as e:
            st.error("⚠️ API Bağlantı Hatası.")

# --- 3. ANA EKRAN BİLGİLENDİRME ---
st.title("🎯 Gereksinim & Kalite Analiz Asistanı")
st.info("""
**📖 Analiz Kapsamı:** Bu sistem gereksinim metinlerini **IEEE 29148, ISO 25010, ISO 27001 ve KVKK** standartlarına göre denetler.
""")

# --- 4. VERİ GİRİŞİ ---
st.subheader("📁 Veri Girişi")
yuklenen_dosya = st.file_uploader("Dosya seçin (.docx, .pdf)", type=["docx", "pdf"])
metin_alani = st.text_area("Veya metni buraya yapıştırın:", height=150)

def dosya_oku(dosya):
    try:
        if dosya.name.endswith('.docx'):
            doc = Document(dosya)
            return "\n".join([p.text for p in doc.paragraphs])
        elif dosya.name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(dosya)
            return "\n".join([page.extract_text() for page in pdf_reader.pages])
    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
    return ""

def sure_formatla(saniye):
    return f"{int(saniye // 60)} dk {round(saniye % 60, 2)} sn" if saniye > 60 else f"{round(saniye, 2)} sn"

# --- 5. ANALİZ VE HESAPLAMA SÜRECİ ---
if st.button("🚀 Analizi Başlat"):
    analiz_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani

    if not api_key or not secilen_model or not analiz_metni:
        st.warning("⚠️ Eksik bilgi: API anahtarı, model seçimi veya metin gereklidir.")
    else:
        try:
            model = genai.GenerativeModel(secilen_model)
            
            # --- STRICT PROMPT (TABLO GARANTİLİ) ---
            sistem_talimati = """
            Sen uzman bir Yazılım Kalite Direktörüsün. SADECE aşağıda belirtilen 5 tabloyu oluştur. 
            Asla giriş veya açıklama metni yazma. Sadece Markdown tablolarını ver.
            Tablolarda sütunları tam doldur. İhlal yoksa satıra "✅ Tam uyum" yaz.

            ### 1. IEEE 29148 Analizi
            | Gereksinim | İhlal | Standart Madde | Öneri |
            |---|---|---|---|

            ### 2. KVKK Analizi
            | Gereksinim | Risk | Mevzuat Maddesi | Uyum Şartı |
            |---|---|---|---|

            ### 3. ISO 27001 Analizi
            | Gereksinim | Zafiyet | Referans Madde | Teknik Önlem |
            |---|---|---|---|

            ### 4. ISO 25010 Analizi
            | Gereksinim | Kalite Eksikliği | Karakteristik | Hedef |
            |---|---|---|---|

            ### 5. Başarılı Örnekler
            | Başarılı Gereksinim | Standart | Gerekçe |
            |---|---|---|
            """
            
            with st.spinner("Yapay Zeka Analiz Ediyor..."):
                baslangic_zamani = time.time()
                cevap = model.generate_content(f"{sistem_talimati}\n\nMETİN:\n{analiz_metni}")
                bitis_zamani = time.time()

            # --- EKRAN ÇIKTISI ---
            st.success(f"✅ Analiz Tamamlandı! ({sure_formatla(bitis_zamani - baslangic_zamani)})")
            st.markdown(cevap.text)
            
            # --- 6. GELİŞMİŞ RİSK VE SKORLAMA MANTIĞI ---
            with st.expander("📊 Doküman Uyum Skoru (ISTQB & Risk Analizi)", expanded=True):
                # Satırları temizle ve boşlukları at
                satirlar = [s.strip() for s in cevap.text.split('\n') if s.strip()]
                
                kritik, yuksek, orta = 0, 0, 0
                aktif_bolum = ""

                for s in satirlar:
                    # Bölüm tespiti (Daha esnek regex kullanımı)
                    if "IEEE 29148" in s: aktif_bolum = "orta"
                    elif "KVKK" in s or "27001" in s: aktif_bolum = "kritik"
                    elif "25010" in s: aktif_bolum = "yuksek"
                    elif "Başarılı" in s: aktif_bolum = "basarili"

                    # Tablo satırı sayma (İçinde '|' olan ve ayraç '---' olmayan satırlar)
                    if "|" in s and "---" not in s and "Gereksinim" not in s and "✅" not in s:
                        if aktif_bolum == "kritik": kritik += 1
                        elif aktif_bolum == "yuksek": yuksek += 1
                        elif aktif_bolum == "orta": orta += 1

                # Madde Sayısı Hesaplama
                temiz_metin_satirlari = [m for m in analiz_metni.split('\n') if len(m.strip()) > 20]
                toplam_madde = max(len(temiz_metin_satirlari), 1)
                
                # ISTQB Ağırlıklı Ceza Puanı
                toplam_ceza = (kritik * 15) + (yuksek * 8) + (orta * 4)
                # Max potansiyel ceza (Döküman hacmine göre normalize edilmiş)
                max_risk_puani = toplam_madde * 15
                
                # Uyum Skoru (Yüzdesel)
                uyum_skoru = round(max(0, (1 - (toplam_ceza / max_risk_puani)) * 100), 1)
                hata_yogunlugu = round((kritik + yuksek + orta) / toplam_madde, 2)

                # Görsel Metrikler
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Kalite Endeksi", f"% {uyum_skoru}", f"-{toplam_ceza} Risk")
                with c2:
                    st.write(f"**🔴 {kritik}** Kritik (KVKK/Güvenlik)")
                    st.write(f"**🟠 {yuksek}** Yüksek (ISO 25010)")
                    st.write(f"**🟡 {orta}** Orta (IEEE 29148)")
                with c3:
                    st.metric("Hata Yoğunluğu", f"{hata_yogunlugu}", "Hata / Madde")

                st.divider()
                st.caption(f"💡 **Analiz Notu:** Toplam {toplam_madde} ana madde incelendi. Skorlama ISTQB hata yoğunluğu prensibine göre yapılmıştır.")

        except Exception as e:
            st.error(f"❌ Sistem Hatası: {e}")
