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

# --- 4. VERİ GİRİŞİ ---
yuklenen_dosya = st.file_uploader("Dosya seçin (.docx, .pdf)", type=["docx", "pdf"])
metin_alani = st.text_area("Veya metni buraya yapıştırın:", height=150)

def dosya_oku(dosya):
    try:
        if dosya.name.endswith('.docx'):
            return "\n".join([p.text for p in Document(dosya).paragraphs])
        elif dosya.name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(dosya)
            return "\n".join([p.extract_text() for p in pdf_reader.pages])
    except: return ""
    return ""

# --- 5. ANALİZ SÜRECİ ---
if st.button("🚀 Analizi Başlat"):
    analiz_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani

    if not api_key or not analiz_metni:
        st.warning("⚠️ Lütfen gerekli alanları doldurun.")
    else:
        try:
            model = genai.GenerativeModel(secilen_model)
            
            # --- PROMPT: İkonlar ve Tablo Yapısı Zorunlu Tutuldu ---
            sistem_talimati = """
            Uzman bir denetçi olarak analiz yap. Sadece Markdown tabloları kullan.
            
            KRİTİK KURALLAR:
            1. IEEE 29148 tablosundaki her hata satırı 🟡 ile başlamalı.
            2. KVKK ve ISO 27001 tablolarındaki her hata satırı 🔴 ile başlamalı.
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
            
            with st.spinner("Analiz ediliyor..."):
                baslangic = time.time()
                cevap = model.generate_content(f"{sistem_talimati}\n\nMETİN:\n{analiz_metni}")
                gecen_sure = round(time.time() - baslangic, 2)

            st.success(f"✅ Analiz tamamlandı. Süre: {gecen_sure} saniye")

            st.metric(
                label="⏱️ Analiz Süresi",
                value=f"{gecen_sure} sn"
                )

            st.markdown(cevap.text)
            
            # --- 6. GERÇEK VERİLERLE MATEMATİKSEL HESAPLAMA ---
            with st.expander("📊 Doküman Uyum Skoru ve Detaylı Hesaplama", expanded=True):
                satirlar = cevap.text.split('\n')
                kritik, yuksek, orta = 0, 0, 0
                
                for s in satirlar:
                    if "🔴" in s: kritik += 1
                    if "🟠" in s: yuksek += 1
                    if "🟡" in s: orta += 1

                # Dinamik Madde Sayımı
                toplam_madde = len([m for m in analiz_metni.split('\n') if len(m.strip()) > 20])
                toplam_madde = max(toplam_madde, (kritik + yuksek + orta + 5)) # Güvenlik önlemi
                
                toplam_hata = kritik + yuksek + orta
                uyumlu_madde = max(0, toplam_madde - toplam_hata)
                
                # Ceza Puanları
                p_kritik = kritik * 10
                p_yuksek = yuksek * 6
                p_orta = orta * 3
                toplam_ceza = p_kritik + p_yuksek + p_orta
                
                # Skor (Normalize edilmiş)
                max_risk = toplam_madde * 10
                uyum_skoru = round(max(0, (1 - (toplam_ceza / max_risk)) * 100), 1)

                # Özet Kartları
                st.info(f"📋 **Analiz Özeti:** Toplam **{toplam_madde}** madde incelendi. **{uyumlu_madde}** madde standartlara uyumlu, **{toplam_hata}** madde geliştirilmelidir.")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Güncel Uyum Skoru", f"% {uyum_skoru}", f"-{toplam_ceza} Puan")
                c2.write(f"🔴 **{kritik}** Kritik | 🟠 **{yuksek}** Yüksek | 🟡 **{orta}** Orta")
                c3.metric("Hata Yoğunluğu", f"{round(toplam_hata/toplam_madde, 2)}", "Hata / Madde")

                st.divider()
                
                # Matematiksel Döküm Bölümü
                st.subheader("🧮 Hesaplama Metodolojisi (Gerçek Verilerle)")
                st.markdown(f"""
                Bu döküman için hesaplama aşağıdaki veriler kullanılarak anlık yapılmıştır:
                
                **1. Ceza Puanı Hesabı:**
                * **Kritik Hatalar:** {kritik} adet × 10 Puan = **{p_kritik}**
                * **Yüksek Hatalar:** {yuksek} adet × 6 Puan = **{p_yuksek}**
                * **Orta Hatalar:** {orta} adet × 3 Puan = **{p_orta}**
                * **Toplam Ceza:** **{toplam_ceza} Puan**
                
                **2. Kapasite ve Oran:**
                * Döküman Hacmi: {toplam_madde} Madde
                * Maksimum Risk Barajı ({toplam_madde} × 10): {max_risk} Puan
                
                **3. Final Formül:**
                * `Skor = 100 × (1 - (Toplam Ceza / Maksimum Risk))`
                * `Skor = 100 × (1 - ({toplam_ceza} / {max_risk}))`
                * **Sonuç: %{uyum_skoru}**
                """)

        except Exception as e:
            st.error(f"❌ Hata: {e}")
