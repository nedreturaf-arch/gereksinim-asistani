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
            
            # --- PROMPT: İkonlar, Tablo Yapısı ve Kanıt Sunma Zorunlu Tutuldu ---
            sistem_talimati = """
            Sen uzman bir Bt uyum denetçisi ve uzman bir Gereksinim Mühendisi olarak metni şu kriterlere göre analiz et:
                1. Belirsizlikler (Ölçülemeyen ifadeler)
                2. Mantıksal Çelişkiler
                3. Eksiklikler (Edge Cases)Sadece Markdown tabloları kullan.
            
            KRİTİK KURALLAR:
            1. İlk 3 tabloda (IEEE 29148, KVKK & ISO 27001, ISO 25010) SADECE eksiklikleri ve zafiyetleri (hataları) listele. Uyumlu maddeleri buralara ekleme.
            2. IEEE 29148 tablosundaki her hata satırı 🟡 ile başlamalı.
            3. KVKK ve ISO 27001 tablosundaki her hata satırı 🔴 ile başlamalı.
            4. ISO 25010 tablosundaki her hata satırı 🟠 ile başlamalı.
            5. Başarılı olan VE hiçbir ihlal içermeyen tüm gereksinimleri SADECE "4. 🌟 Başarılı Gereksinimler" tablosunda topla ve her satırı 🟢 ile başlat.
            6. KANIT SUNMA ZORUNLULUĞU: Tüm tablolarda "Orijinal Metin" sütununu doldur. Tablolara SADECE dokümanda var olan ancak hatalı, eksik tanımlanmış veya belirsiz olan ifadeleri ekle ve bu hatalı cümleyi "tırnak içinde" birebir alıntıla. Dokümanda HİÇ GEÇMEYEN (tamamen unutulmuş) konuları tablolara KESİNLİKLE EKLEME.
            7.Halisülasyon uydurma, sadece dökümandaki metin ile sana verilen standart ve mevzuat ile eşleştirme yap. 
            8. Dokümanda tamamen unutulmuş, hiç değinilmemiş ama projenin doğası gereği standartlar açısından mutlaka olması gereken kritik gereksinimleri, tablolardan sonra "⚠️ Gözden Kaçan Kritik Gereksinimler" başlığı altında bir paragraf veya madde imleri ile özetle.
            9. Başarılı Gereksinimler tablosunda en iyi uyum sağlayan en fazla 5 örnek ver. 
            
            ### 1. 📏 IEEE 29148 Analizi
            | Durum | Gereksinim | Orijinal Metin (Kanıt) | İhlal Nedeni | Öneri |
            |---|---|---|---|---|

            ### 2. 🛡️ KVKK ve 🔒 ISO 27001 Analizi
            | Durum | Gereksinim | Orijinal Metin (Kanıt) | Risk/Zafiyet | Uyum Şartı |
            |---|---|---|---|---|

            ### 3. ⚙️ ISO 25010 Analizi
            | Durum | Gereksinim | Orijinal Metin (Kanıt) | Kalite Eksikliği | Hedef |
            |---|---|---|---|---|

            ### 4. 🌟 Başarılı Gereksinimler
            | Durum | Başarılı Gereksinim | Orijinal Metin (Kanıt) | Standart Karşılığı | Neden Başarılı? |
            |---|---|---|---|---|
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
