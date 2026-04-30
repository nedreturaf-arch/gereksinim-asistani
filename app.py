import streamlit as st
import google.generativeai as genai
from docx import Document
import PyPDF2

# ---------------------------------------------------------
# 1. SAYFA YAPILANDIRMASI
# ---------------------------------------------------------
st.set_page_config(
    page_title="Gereksinim Analiz Asistanı v4.2",
    layout="wide"
)

# ---------------------------------------------------------
# 2. GÜVENLİK VE SIDEBAR
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Ayarlar")
    api_key = st.text_input("Gemini API Anahtarınızı girin:", type="password")
    st.divider()
    
    secilen_model = None
    if api_key:
        try:
            genai.configure(api_key=api_key.strip())
            modeller = [m.name.replace("models/", "") for m in genai.list_models() 
                       if "generateContent" in m.supported_generation_methods]
            if modeller:
                secilen_model = st.selectbox("🤖 Model Seçin:", modeller)
            else:
                st.warning("⚠️ Kullanılabilir model bulunamadı.")
        except Exception as e:
            st.error("⚠️ API Hatası.")

# ---------------------------------------------------------
# 3. FONKSİYONLAR (METİN OKUMA & AKILLI SKORLAMA)
# ---------------------------------------------------------
def dosya_oku(dosya):
    if dosya is None: return ""
    try:
        dosya_adi = dosya.name.lower()
        if dosya_adi.endswith(".docx"):
            doc = Document(dosya)
            return "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
        elif dosya_adi.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(dosya)
            metin = ""
            for sayfa in pdf_reader.pages:
                sayfa_metni = sayfa.extract_text()
                if sayfa_metni: metin += sayfa_metni + "\n"
            return metin.strip()
        return ""
    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        return ""

def skor_hesapla(ai_cevabi, analiz_metni):
    satirlar = ai_cevabi.split("\n")
    kritik, yuksek, orta = 0, 0, 0
    aktif_tablo = 0
    
    # Gerçekten analiz edilen benzersiz maddeleri takip etmek için
    analiz_edilen_ifadeler = set()

    for satir in satirlar:
        temiz_satir = satir.strip()
        if "IEEE 29148" in temiz_satir: aktif_tablo = 1
        elif "KVKK" in temiz_satir or "ISO 27001" in temiz_satir: aktif_tablo = 2
        elif "ISO 25010" in temiz_satir: aktif_tablo = 3

        if temiz_satir.startswith("|") and "---" not in temiz_satir:
            # Başlıkları ve boş uyum satırlarını eliyoruz
            if any(x in temiz_satir for x in ["Gereksinim", "✅", "Başarılı", "Standart"]):
                continue
            
            # Tablodaki ilk hücreyi (ifadeyi) alıyoruz
            hucreler = temiz_satir.split("|")
            if len(hucreler) > 1:
                ifade = hucreler[1].strip()
                analiz_edilen_ifadeler.add(ifade)

                if aktif_tablo == 2: kritik += 1
                elif aktif_tablo == 3: yuksek += 1
                elif aktif_tablo == 1: orta += 1

    # Kullanıcının girdiği toplam madde sayısını daha hassas hesaplıyoruz
    toplam_madde = len([s for s in analiz_metni.split("\n") if len(s.strip()) > 15]) or 1
    
    # Hata sayısı, toplam madde sayısından fazla görünmemeli (Mapping düzeltmesi)
    toplam_hata = min(len(analiz_edilen_ifadeler), toplam_madde)
    basarili_madde = max(0, toplam_madde - toplam_hata)
    
    toplam_ceza = (kritik * 10) + (yuksek * 6) + (orta * 3)
    maksimum_risk = toplam_madde * 10
    mevcut_skor = max(0, round(100 * (1 - (toplam_ceza / maksimum_risk))))

    return {
        "kritik": kritik, "yuksek": yuksek, "orta": orta,
        "toplam_hata": toplam_hata, "toplam_madde": toplam_madde,
        "basarili_madde": basarili_madde, "mevcut_skor": mevcut_skor,
        "toplam_ceza": toplam_ceza
    }

# ---------------------------------------------------------
# 4. ANA EKRAN
# ---------------------------------------------------------
st.title("🎯 Gereksinim & Kalite Analiz Asistanı")
st.info("""
**📖 Analiz Kapsamı:** IEEE 29148, ISO 25010, ISO 27001 ve KVKK standartlarında otomatik denetim.
""")

st.divider()

col1, col2 = st.columns([1, 1])
with col1:
    yuklenen_dosya = st.file_uploader("Dosya seçin (.docx, .pdf)", type=["docx", "pdf"])
with col2:
    metin_alani = st.text_area("Veya metni yapıştırın:", height=100)

if st.button("🚀 Analizi Başlat"):
    # Veri kaynağı seçimi
    analiz_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani

    if not api_key or not analiz_metni.strip() or not secilen_model:
        st.warning("⚠️ Lütfen gerekli alanları doldurun.")
    else:
        try:
            model = genai.GenerativeModel(secilen_model)
            
            # GÜNCELLENMİŞ SİSTEM TALİMATI (Hallucination Korumalı)
            sistem_talimati = """Sen uzman bir Yazılım Kalite Denetçisisin.
KURAL 1: SADECE sana verilen metindeki maddeleri analiz et. Dışarıdan madde uydurma.
KURAL 2: Eğer bir madde standartlara uygunsa onu sadece Tablo 5'e ekle.
KURAL 3: Tablo 5 (Başarılı Örnekler) kısmına metinde olmayan hiçbir şeyi yazma. Eğer başarılı örnek yoksa 'Uyumlu madde bulunamadı' yaz.
KURAL 4: Tüm çıktıyı Türkçe üret.

### 1. 📏 IEEE 29148 Uyumluluğu
| Gereksinimdeki İfade | İhlal Edilen Kriter | Standart Karşılığı | Öneri |
|---|---|---|---|

### 2. 🛡️ KVKK ve ISO 27001 Uyumluluğu
| Gereksinimdeki İfade | Risk | Mevzuat/Standart Karşılığı | Öneri |
|---|---|---|---|

### 4. ⚙️ ISO 25010 Uyumluluğu
| Gereksinimdeki İfade | Kalite Eksikliği | Karakteristik | İyileştirme |
|---|---|---|---|

### 5. 🌟 Standartlara Tam Uyumlu Gereksinimler
| Başarılı Gereksinim | Standartlar | Gerekçe |
|---|---|---|
"""
            with st.spinner("İzlenebilirlik Analizi Yapılıyor..."):
                cevap = model.generate_content(f"{sistem_talimati}\n\nMETİN:\n{analiz_metni}")
            
            if cevap.text:
                st.markdown(cevap.text)
                st.divider()
                
                # SKORLAMA BÖLÜMÜ
                skor = skor_hesapla(cevap.text, analiz_metni)
                with st.expander("📊 Doküman Uyum Skoru", expanded=True):
                    st.info(f"İnceleme sonucunda **{skor['toplam_madde']}** madde taranmıştır.")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Uyum Skoru", f"%{skor['mevcut_skor']}", f"-{skor['toplam_ceza']} Risk", delta_color="inverse")
                    m2.write(f"🔴 {skor['kritik']} Kritik\n\n🟠 {skor['yuksek']} Yüksek\n\n🟡 {skor['orta']} Orta")
                    m3.metric("Uyumlu Madde", f"{skor['basarili_madde']} Adet")

        except Exception as e:
            st.error(f"Analiz Hatası: {e}")
