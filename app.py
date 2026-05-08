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
            secilen_model = st.selectbox("🤖 Model Seçin:", modeller)
        except Exception as e:
            st.error("⚠️ API Hatası: Bağlantı kurulamadı.")

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

    if not api_key or not analiz_metni:
        st.warning("⚠️ Lütfen API anahtarını ve analiz edilecek metni sağlayın.")
    else:
        try:
            model = genai.GenerativeModel(secilen_model)
            
            # --- PROMPT MÜHENDİSLİĞİ (GÜNCELLENMİŞ KURAL 5) ---
            sistem_talimati = """
            Sen uzman bir Yazılım Kalite Direktörü ve BT Uyum Denetçisisin.
            Gereksinimleri analiz ederken 'İzlenebilirlik' (Traceability) prensibini uygula.

            KURAL 1: Doğrudan tablolara başla. Giriş/Sonuç cümlesi yazma.
            KURAL 2: Her ihlal için gereksinim belgesindeki 'İLGİLİ İFADEYİ' alıntıla ve hangi 'STANDART MADDESİ' ile neden çeliştiğini açıkla.
            KURAL 3: İhlal yoksa "✅ Tam uyum sağlanmıştır" yaz.
            KURAL 4: Risk İkonları: IEEE(🟡), KVKK/ISO27001(🔴), ISO25010(🟠), Başarılı(🟢).
            KURAL 5 (ÖNEMLİ): Tablo 5 (Başarılı Örnekler) kısmına metindeki tüm maddeler arasından en az 5, en fazla 10 adet en iyi pratik (best practice) örneğini KESİNLİKLE ekle. Özet geçme.

            ### 1. 📏 IEEE 29148 Gereksinim Kalitesi Uyumluluğu
            | Gereksinimdeki İfade | İhlal Edilen Kriter | Standart Karşılığı ve Analiz | Uyum Önerisi |
            |---|---|---|---|

            ### 2. 🛡️ KVKK ve Veri Gizliliği Mevzuatı Uyumluluğu
            | Gereksinimdeki İfade | KVKK Riski | Mevzuat Maddesi ve Çelişme Nedeni | Hukuki Uyum Şartı |
            |---|---|---|---|

            ### 3. 🔒 ISO 27001 Bilgi Güvenliği Uyumluluğu
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
    baslangic_zamani = time.time()

    cevap = model.generate_content(
        f"{sistem_talimati}\n\nAnaliz edilecek metin:\n{analiz_metni}"
    )

    bitis_zamani = time.time()

gecen_sure = round(bitis_zamani - baslangic_zamani, 2)
gecen_sure_yazi = sure_formatla(gecen_sure)

st.success(f"✅ Kapsamlı Uyumluluk Analizi Tamamlanmıştır! Süre: {gecen_sure_yazi}")

st.metric(
    label="⏱️ Analiz Süresi",
    value=gecen_sure_yazi
)

st.markdown(cevap.text)
            
            # --- 6. GÜNCELLENMİŞ POZİTİF SKORLAMA ALGORİTMASI ---
            with st.expander("📊 Doküman Uyum Skoru (ISTQB Risk Temelli Analiz)", expanded=True):
                satirlar = cevap.text.split('\n')
                kritik_hata, yuksek_hata, orta_hata = 0, 0, 0
                aktif_tablo = 0
                
                for satir in satirlar:
                    if "IEEE 29148" in satir: aktif_tablo = 1
                    elif "KVKK" in satir: aktif_tablo = 2
                    elif "ISO 27001" in satir: aktif_tablo = 3
                    elif "ISO 25010" in satir: aktif_tablo = 4
                    elif "Standartlara Tam Uyumlu" in satir: aktif_tablo = 5
                    
                    if "|" in satir and "---" not in satir and "İfade" not in satir and "✅" not in satir and aktif_tablo != 5:
                        if aktif_tablo in [2, 3]: kritik_hata += 1
                        elif aktif_tablo == 4: yuksek_hata += 1
                        elif aktif_tablo == 1: orta_hata += 1
                
                # Matematiksel risk ağırlıklandırma (100 üzerinden Pozitif Skorlama)
                toplam_ceza = (kritik_hata * 10) + (yuksek_hata * 6) + (orta_hata * 3)
                mevcut_skor = max(0, 100 - toplam_ceza)
                
                # Toplam madde sayısını dinamik hesapla (boş olmayan anlamlı satırlar)
                toplam_madde = len([s for s in analiz_metni.split('\n') if len(s.strip()) > 15])
                toplam_hata = kritik_hata + yuksek_hata + orta_hata
                hatasiz_madde = max(0, toplam_madde - toplam_hata)
                
                st.info(f"""
                📊 **Yönetici Özeti:** İnceleme sonucunda döküman içerisindeki **{toplam_madde}** madde taranmıştır. 
                Sistem; **{hatasiz_madde}** maddeyi standartlara tam uyumlu bulurken, **{toplam_hata}** maddede gelişim alanı tespit etmiştir.
                """)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Güncel Uyum Skoru", f"% {mevcut_skor}", f"-{toplam_ceza} Puan", delta_color="inverse")
                with col2:
                    st.write(f"**🔴 {kritik_hata}** Kritik | **🟠 {yuksek_hata}** Yüksek | **🟡 {orta_hata}** Orta")
                with col3:
                    st.metric("Hedeflenen Durum", "% 100", f"+{toplam_ceza} Gelişim")
                
                st.divider()

                with st.expander("🧮 Puanlama Nasıl Hesaplanıyor? (Matematiksel Döküm)"):
                    st.markdown(f"""
**1. Risk Seviyelerine Göre Hata Sayıları**

* **Kritik Hata:** {kritik_hata} adet  
  *KVKK ve ISO 27001 kapsamındaki bulgular kritik risk olarak değerlendirilmiştir.*

* **Yüksek Hata:** {yuksek_hata} adet  
  *ISO 25010 kapsamındaki kalite eksiklikleri yüksek risk olarak değerlendirilmiştir.*

* **Orta Hata:** {orta_hata} adet  
  *IEEE 29148 kapsamındaki gereksinim belirsizlikleri orta risk olarak değerlendirilmiştir.*

---

**2. Risk Ağırlıkları**

* Kritik hata ağırlığı: **10 puan**
* Yüksek hata ağırlığı: **6 puan**
* Orta hata ağırlığı: **3 puan**

---

**3. Toplam Ceza Puanı Hesabı**

* Kritik ceza: {kritik_hata} × 10 = **{kritik_hata * 10}**
* Yüksek ceza: {yuksek_hata} × 6 = **{yuksek_hata * 6}**
* Orta ceza: {orta_hata} × 3 = **{orta_hata * 3}**

**Toplam Ceza Puanı:**  
{kritik_hata * 10} + {yuksek_hata * 6} + {orta_hata * 3} = **{toplam_ceza}**

---

**4. Uyum Skoru Hesabı**

Başlangıç skoru **100** kabul edilmiştir.  
Toplam ceza puanı bu değerden düşülmüştür.

**Formül:**

`Uyum Skoru = 100 - Toplam Ceza Puanı`

**Uygulama:**

`Uyum Skoru = 100 - {toplam_ceza}`

**Sonuç:**

**Uyum Skoru = %{mevcut_skor}**

---

**5. Madde Bazlı Özet**

* Toplam taranan madde: **{toplam_madde}**
* Hatalı / gelişime açık madde: **{toplam_hata}**
* Hatasız kabul edilen madde: **{hatasiz_madde}**
""")

                st.caption("💡 **Mühendislik Notu:** Bu rapor ISTQB Risk Temelli Analiz prensiplerine göre oluşturulmuştur. Başarılı maddelerin tamamı döküman boyutuna göre örneklenerek sunulmaktadır.")

        except Exception as e:
            st.error(f"❌ Analiz Hatası: {e}")
