import streamlit as st
import google.generativeai as genai
from docx import Document
import PyPDF2
import time

# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="Gereksinim Analiz Asistanı v3.6", layout="wide")

# --- 2. API YÖNETİMİ ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    api_key = st.text_input("Gemini API Anahtarınızı girin:", type="password")
    st.divider() 
    secilen_model = None
    if api_key: 
        try:
            genai.configure(api_key=api_key.strip())
            modeller = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            secilen_model = st.selectbox("🤖 Model Seçin:", modeller, index=0)
        except:
            st.error("⚠️ API Bağlantı Hatası.")

# --- 3. ANA EKRAN ---
st.title("🎯 Gereksinim & Kalite Analiz Asistanı")
st.info("**Referanslar:** IEEE 29148, ISO 25010, ISO 27001, KVKK")

# --- 4. YARDIMCI FONKSİYONLAR ---
def sure_formatla(saniye):
    if saniye < 60:
        return f"{round(saniye, 2)} sn"
    dakika = int(saniye // 60)
    kalan_saniye = round(saniye % 60, 2)
    return f"{dakika} dk {kalan_saniye} sn"

def dosya_oku(dosya):
    try:
        if dosya.name.endswith('.docx'):
            return "\n".join([p.text for p in Document(dosya).paragraphs])
        elif dosya.name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(dosya)
            return "\n".join([p.extract_text() for p in pdf_reader.pages])
    except: return ""
    return ""

# --- 5. VERİ GİRİŞİ ---
yuklenen_dosya = st.file_uploader("Dosya seçin (.docx, .pdf)", type=["docx", "pdf"])
metin_alani = st.text_area("Veya metni buraya yapıştırın:", height=150)

# --- 6. ANALİZ SÜRECİ ---
if st.button("🚀 Analizi Başlat"):
    analiz_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani

    if not api_key or not analiz_metni:
        st.warning("⚠️ Lütfen gerekli alanları doldurun.")
    else:
        try:
            model = genai.GenerativeModel(secilen_model)
            
            sistem_talimati = """
            Uzman bir denetçi olarak analiz yap. Sadece Markdown tabloları kullan.
            
            KRİTİK KURALLAR:
            1. IEEE 29148 tablosundaki her hata satırı 🟡 ile başlamalı.
            2. KVKK ve ISO 27001 tablosundaki her hata satırı 🔴 ile başlamalı.
            3. ISO 25010 tablosundaki her hata satırı 🟠 ile başlamalı.
            4. Başarılı örnekler 🟢 ile başlamalı.
            5. İhlal yoksa sadece "✅ Tam uyum sağlanmıştır" yaz.

            ### 1. 📏 IEEE 29148 Analizi
            | Durum | Gereksinim | İhlal Nedeni | Öneri |
            |---|---|---|---|

            ### 2. 🛡️ KVKK ve 🔒 ISO 27001 Analizi
            | Durum | Gereksinim | Risk/Zafiyet | Uyum Şartı |
            |---|---|---|---|

            ### 3. ⚙️ ISO 25010 Analizi
            | Durum | Gereksinim | Kalite Eksikliği | Hedef |
            |---|---|---|---|

            ### 4. 🌟 Başarılı Gereksinimler
            | Durum | Başarılı Gereksinim | Standart Karşılığı | Neden Başarılı? |
            |---|---|---|---|
            """
            
            baslangic_zamani = time.time() # Zaman ölçümü başlar
            
            with st.spinner("Yapay Zeka İzlenebilirlik Analizini Gerçekleştiriyor..."):
                cevap = model.generate_content(f"{sistem_talimati}\n\nMETİN:\n{analiz_metni}")
                
            bitis_zamani = time.time() # Zaman ölçümü biter
            gecen_sure = round(bitis_zamani - baslangic_zamani, 2)
            sure_metni = sure_formatla(gecen_sure)

            # Başarı mesajı ve Metrik
            st.success(f"✅ Kapsamlı Uyumluluk Analizi Tamamlanmıştır! Süre: {sure_metni}")
            st.metric(label="⏱️ Analiz Süresi", value=sure_metni)

            st.markdown(cevap.text)
            
            # --- 7. GERÇEK VERİLERLE HESAPLAMA VE ÖZET ---
            with st.expander("📊 Doküman Uyum Skoru (ISTQB Risk Temelli Analiz)", expanded=True):
                satirlar = cevap.text.split('\n')
                kritik, yuksek, orta = 0, 0, 0
                
                for s in satirlar:
                    if "🔴" in s: kritik += 1
                    if "🟠" in s: yuksek += 1
                    if "🟡" in s: orta += 1

                # Dinamik Madde Sayımı
                toplam_madde = len([m for m in analiz_metni.split('\n') if len(m.strip()) > 20])
                toplam_madde = max(toplam_madde, (kritik + yuksek + orta + 5))
                
                toplam_hata = kritik + yuksek + orta
                uyumlu_madde = max(0, toplam_madde - toplam_hata)
                
                # Ceza Puanları
                p_kritik = kritik * 10
                p_yuksek = yuksek * 6
                p_orta = orta * 3
                toplam_ceza = p_kritik + p_yuksek + p_orta
                
                # Skor
                max_risk = toplam_madde * 10
                uyum_skoru = round(max(0, (1 - (toplam_ceza / max_risk)) * 100), 1)

                st.info(f"""
                📊 **Yönetici Özeti:** İnceleme sonucunda döküman içerisindeki **{toplam_madde}** madde taranmıştır. 
                Sistem; **{uyumlu_madde}** maddeyi standartlara tam uyumlu bulurken, **{toplam_hata}** maddede gelişim alanı tespit etmiştir.
                """)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Güncel Uyum Skoru", f"% {uyum_skoru}", f"-{toplam_ceza} Puan", delta_color="inverse")
                with col2:
                    st.write(f"🔴 **{kritik}** Kritik | 🟠 **{yuksek}** Yüksek | 🟡 **{orta}** Orta")
                with col3:
                    st.metric("Hata Yoğunluğu", f"{round(toplam_hata/toplam_madde, 2)}", "Hata / Madde")

                st.divider()
                
                st.subheader("🧮 Puanlama Nasıl Hesaplanıyor? (Matematiksel Döküm)")
                st.markdown(f"""
                Bu rapor için o anki verilerle yapılan hesaplama dökümü:
                
                **1. Risk Seviyelerine Göre Hata Sayıları:**
                * **Kritik Hata (🔴):** {kritik} adet x 10 Puan = **{p_kritik}**
                * **Yüksek Hata (🟠):** {yuksek} adet x 6 Puan = **{p_yuksek}**
                * **Orta Hata (🟡):** {orta} adet x 3 Puan = **{p_orta}**
                * **Toplam Ceza Puanı:** **{toplam_ceza}**

                **2. Uyum Skoru Hesabı:**
                * Toplam Taranan Madde: **{toplam_madde}**
                * Formül: `100 * (1 - ({toplam_ceza} / ({toplam_madde} * 10)))`
                * **Sonuç: %{uyum_skoru}**
                """)

        except Exception as e:
            st.error(f"❌ Analiz Hatası: {e}")
