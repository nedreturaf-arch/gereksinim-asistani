import streamlit as st
import google.generativeai as genai
from docx import Document
import PyPDF2

# ---------------------------------------------------------
# 1. AYARLAR VE API YAPILANDIRMASI
# ---------------------------------------------------------
st.set_page_config(page_title="Gereksinim Analiz Asistanı v4.1", layout="wide")

# Sidebar
with st.sidebar:
    st.header("⚙️ Ayarlar")
    api_key = st.text_input("Gemini API Anahtarınızı girin:", type="password")
    secilen_model = None
    if api_key:
        try:
            genai.configure(api_key=api_key.strip())
            modeller = [m.name.replace("models/", "") for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
            if modeller: secilen_model = st.selectbox("🤖 Model Seçin:", modeller)
        except: st.error("Bağlantı kurulamadı.")

# ---------------------------------------------------------
# 2. SKORLAMA VE ANALİZ FONKSİYONLARI
# ---------------------------------------------------------

def skor_hesapla(ai_cevabi, orijinal_metin):
    satirlar = ai_cevabi.split("\n")
    # Set kullanarak aynı ifadenin birden fazla kez sayılmasını engelliyoruz
    hatali_ifadeler = set()
    kritik, yuksek, orta = 0, 0, 0
    aktif_tablo = 0

    for satir in satirlar:
        s = satir.strip()
        if "IEEE 29148" in s: aktif_tablo = 1
        elif "KVKK" in s or "ISO 27001" in s: aktif_tablo = 2
        elif "ISO 25010" in s: aktif_tablo = 3
        
        if s.startswith("|") and "|" in s[1:] and "---" not in s:
            if any(x in s for x in ["Gereksinim", "✅", "Başarılı"]): continue
            
            # Satırdaki ilk sütunu (ifadeyi) alıp kaydediyoruz
            ifade = s.split("|")[1].strip()
            hatali_ifadeler.add(ifade)
            
            if aktif_tablo == 2: kritik += 1
            elif aktif_tablo == 3: yuksek += 1
            elif aktif_tablo == 1: orta += 1

    # Orijinal metindeki gerçek madde sayısı
    toplam_madde = len([m for m in orijinal_metin.split("\n") if len(m.strip()) > 10]) or 1
    
    # Skorlama (Cezaların toplam maddeye oranı)
    ceza = (kritik * 10) + (yuksek * 6) + (orta * 3)
    max_risk = toplam_madde * 10
    skor = max(0, round(100 * (1 - (ceza / max_risk))))

    return {"kritik": kritik, "yuksek": yuksek, "orta": orta, "toplam_madde": toplam_madde, "skor": skor}

# ---------------------------------------------------------
# 3. ANA ARAYÜZ VE PROMPT
# ---------------------------------------------------------
st.title("🎯 Gereksinim & Kalite Analiz Asistanı")
metin_alani = st.text_area("Analiz edilecek metni buraya yapıştırın:", height=150)

if st.button("🚀 Analizi Başlat"):
    if not api_key or not metin_alani.strip():
        st.warning("Lütfen API anahtarını ve metni girin.")
    else:
        model = genai.GenerativeModel(secilen_model)
        
        # GÜNCELLENMİŞ SİSTEM TALİMATI (KURAL 5 DÜZELTİLDİ)
        sistem_talimati = """Sen uzman bir denetçisin. 
        KURAL: Sadece sana verilen metindeki maddeleri analiz et. 
        KURAL: Kesinlikle dışarıdan örnek uydurma.
        KURAL: Eğer metinde başarılı örnek yoksa Tablo 5'e 'Analiz edilen metinde standartlara tam uyumlu madde bulunamadı' yaz.
        
        ### 1. 📏 IEEE 29148 Uyumluluğu (Sadece metindeki maddeler)
        ### 2. 🛡️ KVKK / ISO 27001 Uyumluluğu (Sadece metindeki maddeler)
        ### 3. ⚙️ ISO 25010 Uyumluluğu (Sadece metindeki maddeler)
        ### 5. 🌟 Standartlara Tam Uyumlu Gereksinimler (Sadece metinde gerçekten varsa)
        """
        
        with st.spinner("Analiz ediliyor..."):
            response = model.generate_content(f"{sistem_talimati}\n\nAnaliz Edilecek Metin:\n{metin_alani}")
            
            if response.text:
                st.markdown(response.text)
                stats = skor_hesapla(response.text, metin_alani)
                
                with st.expander("📊 Analiz Özet Skoru", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Genel Uyum Skoru", f"%{stats['skor']}")
                    c2.metric("İncelenen Madde", stats['toplam_madde'])
                    c3.write(f"🔴 {stats['kritik']} Kritik | 🟠 {stats['yuksek']} Yüksek | 🟡 {stats['orta']} Orta")
