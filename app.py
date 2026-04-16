import streamlit as st
import google.generativeai as genai
from docx import Document
import PyPDF2

# --- 1. SAYFA VE ARAYÜZ YAPILANDIRMASI ---
# Uygulamanın tarayıcı sekme adını ve sayfa genişliğini ayarlıyoruz.
st.set_page_config(page_title="Gereksinim Analiz Asistanı v3.0", layout="wide")

# --- 2. GÜVENLİK VE API YÖNETİMİ (SOL MENÜ) ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    # type="password" parametresi ile API anahtarının ekranda okunmasını engelliyor, güvenliği sağlıyoruz.
    api_key = st.text_input("Gemini API Anahtarınızı girin:", type="password")
    st.divider() 
    
    secilen_model = None
    # Kullanıcı API anahtarı girdiyse, Google Gemini sunucularına bağlanmayı deniyoruz.
    if api_key: 
        try:
            # API anahtarını sisteme tanıtıyoruz (Kimlik Doğrulama / Authentication).
            genai.configure(api_key=api_key.strip())
            # Sadece metin üretme (generateContent) yeteneğine sahip güncel modelleri filtreleyip listeliyoruz.
            modeller = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            secilen_model = st.selectbox("🤖 Model Seçin:", modeller)
        except Exception as e:
            # API bağlantısı koparsa sistemin çökmesini engelliyor, kontrollü uyarı veriyoruz (Hata Toleransı).
            st.error("⚠️ API Hatası.")

# --- 3. ANA EKRAN VE BİLGİLENDİRME ---
st.title("🎯 Gereksinim & Kalite Analiz Asistanı")
st.info("""
**📖 Referans Alınan Temel Standartlar ve Mevzuatlar:**
* **IEEE 29148:** Sistem ve Yazılım Mühendisliği - Gereksinim Mühendisliği Süreçleri
* **ISO/IEC 25010:** Yazılım Kalite Modelleri ve Değerlendirmesi
* **ISO/IEC 27001 & CBDDO BİG:** Bilgi Güvenliği Yönetim Sistemi ve Ulusal Standartlar
* **KVKK:** 6698 Sayılı Kişisel Verilerin Korunması Kanunu
""")
st.divider()

# --- 4. VERİ GİRİŞİ (STATELESS / DURUMSUZ MİMARİ) ---
# Yüklenen dosyalar sunucuya kaydedilmez, sadece anlık bellek (RAM) üzerinde tutulur.
st.subheader("📁 Veri Girişi")
yuklenen_dosya = st.file_uploader("Analiz edilecek dosyayı seçin (.docx, .pdf)", type=["docx", "pdf"])
metin_alani = st.text_area("Veya analiz edilecek metni buraya yapıştırın:", height=150)

# Dosya okuma mekanizmasını modüler bir fonksiyon (Kapsülleme) olarak tanımlıyoruz.
def dosya_oku(dosya):
    try:
        if dosya.name.endswith('.docx'):
            doc = Document(dosya)
            # Word belgesindeki paragrafları okuyup tek bir metin bloğunda birleştiriyoruz.
            return "\n".join([p.text for p in doc.paragraphs])
        elif dosya.name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(dosya)
            metin = ""
            # PDF sayfalarını döngüye sokarak metinleri çıkartıyoruz.
            for sayfa in range(len(pdf_reader.pages)):
                metin += pdf_reader.pages[sayfa].extract_text() + "\n"
            return metin
    except Exception as e:
        st.error(f"Dosya okuma sırasında bir hata oluştu: {e}")
        return ""
    return ""

# --- 5. YAPAY ZEKA ANALİZ SÜRECİ ---
if st.button("🚀 Analizi Başlat"):
    # Dosya yüklendiyse onu, yüklenmediyse metin kutusundaki veriyi alıyoruz.
    analiz_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani

    if not api_key or not analiz_metni:
        st.warning("⚠️ Lütfen API anahtarını ve analiz edilecek metni sağlayın.")
    else:
        try:
            # Seçilen model nesnesini (örneğin Gemini 1.5 Pro) başlatıyoruz.
            model = genai.GenerativeModel(secilen_model)
            
            # --- PROMPT MÜHENDİSLİĞİ (SİSTEM TALİMATI) ---
            # Modelin halüsinasyon görmesini engellemek ve çıktıyı standardize etmek için katı kurallar yazıyoruz.
            sistem_talimati = """
            Sen uzman bir Yazılım Kalite Güvence Direktörü ve BT Uyum (Compliance) Denetçisisin.
            Görevin, verilen yazılım gereksinim belgesini (SRS) uluslararası standartlar (IEEE, ISO) ve yasal mevzuatlar (KVKK, CBDDO) açısından denetlemektir.

            KURAL 1: KESİNLİKLE giriş cümlesi veya "analiz ettim" gibi açıklamalar YAZMA. Doğrudan 1. başlık ile başla.
            KURAL 2: Sadece yazılı gereksinimlerin standartlara uygunluğunu denetle. Aşırı mühendislik (overengineering) yapma.
            KURAL 3: Çıktını DOĞRUDAN aşağıdaki 5 TABLO formatında ver. İhlal yoksa "✅ Tam uyum sağlanmıştır" yaz.
            KURAL 4: RİSK GÖRSELLEŞTİRME: Gereksinimlerin başına şu risk seviyesi ikonlarını KESİNLİKLE ekle:
            - Tablo 1 (IEEE 29148): 🟡 [ORTA RİSK] 
            - Tablo 2 ve 3 (KVKK, ISO 27001): 🔴 [KRİTİK RİSK] 
            - Tablo 4 (ISO 25010): 🟠 [YÜKSEK RİSK] 
            - Tablo 5 (Başarılı Örnekler): 🟢 [KUSURSUZ] 
            
            KURAL 5 (ÇOK KRİTİK): HALÜSİNASYON ÖNLEME: 
            Sırf tablo doldurmak için uydurma hatalar yaratma. Metin kaliteliyse bol bol "✅ Tam uyum" kullan.

            ### 1. 📏 IEEE 29148 Gereksinim Kalitesi Uyumluluğu
            | Gereksinim | İhlal Edilen Kriter | IEEE 29148 Gerekçesi | Uyumlu Hale Getirme Önerisi |
            |---|---|---|---|

            ### 2. 🛡️ KVKK ve Veri Gizliliği Mevzuatı Uyumluluğu
            | Gereksinim | KVKK İhlali / Riski | İlgili Madde veya İlke | Hukuki Uyum İçin Gerekenler |
            |---|---|---|---|

            ### 3. 🔒 ISO 27001 ve CBDDO Bilgi Güvenliği Uyumluluğu
            | Gereksinim | Güvenlik Zafiyeti | Referans (ISO/CBDDO) | Teknik Uyum Önerisi |
            |---|---|---|---|

            ### 4. ⚙️ ISO 25010 Yazılım Kalite Modeli Uyumluluğu
            | Gereksinim | Kalite Özelliği Eksikliği | İlgili Alt Karakteristik | Test Edilebilir Uyum Hedefi |
            |---|---|---|---|

            ### 5. 🌟 Standartlara Tam Uyumlu (Örnek) Gereksinimler
            | Örnek Başarılı Gereksinim | Karşıladığı Standartlar | Neden Uyumlu ve Başarılı? |
            |---|---|---|
            """
            
            with st.spinner("Yapay Zeka Mevzuat ve Standart Denetimini Gerçekleştiriyor..."):
                # Hazırlanan Prompt ve kullanıcının metni API'ye gönderiliyor.
                cevap = model.generate_content(f"{sistem_talimati}\n\nAnaliz edilecek metin:\n{analiz_metni}")
            
            st.success("✅ Kapsamlı Uyumluluk Analizi Tamamlanmıştır!")
            st.markdown(cevap.text)
            
            # --- 6. ISTQB RİSK TEMELLİ SKORLAMA ALGORİTMASI ---
            with st.expander("📊 Doküman Uyum Skoru (ISTQB Risk Temelli Analiz)", expanded=True):
                # Yapay zekadan dönen metni satır satır bölerek içerisindeki riskleri sayıyoruz.
                satirlar = cevap.text.split('\n')
                
                kritik_hata = 0 # KVKK ve Güvenlik (-10 Puan)
                yuksek_hata = 0 # Kalite ve Performans (-6 Puan)
                orta_hata = 0   # Netlik ve Belirsizlik (-3 Puan)
                
                aktif_tablo = 0
                for satir in satirlar:
                    # Okunan satırın hangi tabloya (standarda) ait olduğunu tespit ediyoruz.
                    if "IEEE 29148" in satir: aktif_tablo = 1
                    elif "KVKK" in satir: aktif_tablo = 2
                    elif "ISO 27001" in satir: aktif_tablo = 3
                    elif "ISO 25010" in satir: aktif_tablo = 4
                    elif "Standartlara Tam Uyumlu" in satir: aktif_tablo = 5
                    
                    # Eğer satır bir tablo satırıysa ve içerisinde hata bulunuyorsa (✅ yoksa), risk seviyesine göre sayacı artırıyoruz.
                    if "|" in satir and "---" not in satir and "Gereksinim" not in satir and "✅" not in satir and aktif_tablo != 5:
                        if aktif_tablo in [2, 3]: kritik_hata += 1
                        elif aktif_tablo == 4: yuksek_hata += 1
                        elif aktif_tablo == 1: orta_hata += 1
                
                # Matematiksel risk ağırlıklandırma ve skor hesaplama (Ceza Puanı Sistemi)
                toplam_hata = kritik_hata + yuksek_hata + orta_hata
                kesilen_puan = (kritik_hata * 10) + (yuksek_hata * 6) + (orta_hata * 3)
                mevcut_skor = max(0, 100 - kesilen_puan) # Skorun sıfırın altına düşmesini (negatif skor) engelliyoruz.
                
                # Anlamlı paragraf sayısını bularak (15 karakter üstü) oranlama yapıyoruz.
                toplam_madde = len([s for s in analiz_metni.split('\n') if len(s.strip()) > 15])
                hatasiz_madde = max(0, toplam_madde - toplam_hata)
                
                # --- YÖNETİCİ ÖZETİ (EXECUTIVE SUMMARY) EKRANI ---
                st.info(f"""
                📊 **Yönetici Özeti ve Eylem Planı:**
                Sisteme yüklenen dokümandaki yaklaşık **{toplam_madde}** anlamlı gereksinim maddesi incelenmiştir. 
                Yapılan ISTQB ve ISO uyum denetimi sonucunda; **{hatasiz_madde}** maddenin standartlara uygun olduğu değerlendirilirken, **{toplam_hata}** maddede çeşitli risk seviyelerinde (Kritik/Yüksek/Orta) ihlal tespit edilmiştir. 
                
                **🚀 Sonraki Adım:** Tablolarda sunulan *'Uyumlu Hale Getirme Önerileri'* dikkate alınarak dokümanın revize edilmesi ve **%100 Uyum (Audit-Ready)** onayı almak üzere sisteme tekrar yüklenmesi tavsiye edilmektedir.
                """)
                st.divider()
                
                # Görsel metrik kartları oluşturuyoruz.
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.error("📄 Dokümanın Mevcut Durumu")
                    st.caption("Standartlar uygulanmadan önce:")
                    st.metric("Genel Uyum Skoru", f"% {mevcut_skor}", f"-{kesilen_puan} Ceza Puanı")
                    
                with col2:
                    st.warning("⚠️ Risk Dağılımı")
                    st.caption("ISTQB Risk Temelli Analiz:")
                    st.markdown(f"**🔴 {kritik_hata}** Kritik | **🟠 {yuksek_hata}** Yüksek | **🟡 {orta_hata}** Orta")
                    
                with col3:
                    st.success("🎯 Hedeflenen Durum")
                    st.caption("Önerilen düzeltmeler yapıldığında:")
                    st.metric("Ulaşılan Uyum Skoru", "% 100", f"+{100 - mevcut_skor} Puan Artış")
                
                st.divider()
                st.caption("💡 **Mühendislik Notu:** Bu sistem ISTQB Risk Temelli Test yaklaşımı kullanır. KVKK/Güvenlik ihlalleri -10, Mimari Kalite eksiklikleri -6, Belirsizlikler ise -3 puan ile cezalandırılır.")

        except Exception as e:
            st.error(f"❌ Hata: {e}")
