import streamlit as st
import google.generativeai as genai
from docx import Document
import PyPDF2

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Gereksinim Analiz Asistanı v3.0", layout="wide")

# 2. SOL MENÜ
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

# 3. ANA EKRAN TASARIMI
st.title("🎯 Gereksinim & Kalite Analiz Asistanı")
st.info("""
**📖 Referans Alınan Temel Standartlar ve Mevzuatlar:**
* **IEEE 29148:** Sistem ve Yazılım Mühendisliği - Gereksinim Mühendisliği Süreçleri
* **ISO/IEC 25010:** Yazılım Kalite Modelleri ve Değerlendirmesi (SQuaRE)
* **ISO/IEC 12207:** Yazılım Yaşam Döngüsü Süreçleri
* **ISO/IEC 29119:** Yazılım Test Standartları
* **ISO/IEC 27001:** Bilgi Güvenliği Yönetim Sistemi
* **KVKK:** 6698 Sayılı Kişisel Verilerin Korunması Kanunu
* **CBDDO BİG Rehberi:** T.C. Cumhurbaşkanlığı Bilgi ve İletişim Güvenliği Rehberi
""")
st.divider()

# VERİ GİRİŞİ
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
        st.error(f"Dosya okuma sırasında bir hata oluştu: {e}")
        return ""
    return ""

# 4. ANALİZ SÜRECİ
if st.button("🚀 Analizi Başlat"):
    analiz_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani

    if not api_key or not analiz_metni:
        st.warning("⚠️ Lütfen API anahtarını ve metni sağlayın.")
    else:
        try:
            model = genai.GenerativeModel(secilen_model)
            
            # PROMPT MÜHENDİSLİĞİ: Standart ve Mevzuat Uyum Denetimi
            sistem_talimati = """
            Sen uzman bir Yazılım Kalite Güvence Direktörü ve BT Uyum (Compliance) Denetçisisin.
            Görevin, verilen yazılım gereksinim belgesini (SRS) uluslararası standartlar (IEEE, ISO) ve yasal mevzuatlar (KVKK, CBDDO) açısından denetlemektir.

            KURAL 1: KESİNLİKLE giriş cümlesi, selamlama veya "analiz ettim" gibi açıklamalar YAZMA. Cevabına DOĞRUDAN 1. başlık ile başla.
            KURAL 2: Mimari tasarım kararlarını, proje yönetim süreçlerini veya bütçe/eğitim gibi konuları eleştirme. Sen sadece yazılı gereksinimlerin standartlara uygunluğunu denetleyen bir araçsın. Aşırı mühendislik (overengineering) yapma.
            KURAL 3: Çıktını DOĞRUDAN aşağıdaki 5 TABLO formatında ver. Eğer bir standart açısından ihlal yoksa o başlığın altına "✅ Bu standart açısından tam uyum sağlanmıştır." yaz.

            ### 1. 📏 IEEE 29148 Gereksinim Kalitesi Uyumluluğu
            *(Netlik, Ölçülebilirlik, Çelişmezlik ve İzlenebilirlik denetimi)*
            | Gereksinim | İhlal Edilen Kriter | IEEE 29148 Gerekçesi | Uyumlu Hale Getirme Önerisi |
            |---|---|---|---|

            ### 2. 🛡️ KVKK ve Veri Gizliliği Mevzuatı Uyumluluğu
            *(Privacy by Design, Veri Minimizasyonu, Açık Rıza ve Anonimleştirme denetimi)*
            | Gereksinim | KVKK İhlali / Riski | İlgili Madde veya İlke | Hukuki Uyum İçin Gerekenler |
            |---|---|---|---|

            ### 3. 🔒 ISO 27001 ve CBDDO Bilgi Güvenliği Uyumluluğu
            *(Erişim kontrolleri, Şifreleme, MFA, Loglama ve Veri İmhası denetimi)*
            | Gereksinim | Güvenlik Zafiyeti | Referans (ISO/CBDDO) | Teknik Uyum Önerisi |
            |---|---|---|---|

            ### 4. ⚙️ ISO 25010 Yazılım Kalite Modeli Uyumluluğu
            *(Performans, Kullanılabilirlik, Güvenilirlik ve Hata Toleransı metrikleri denetimi)*
            | Gereksinim | Kalite Özelliği Eksikliği | İlgili Alt Karakteristik | Test Edilebilir Uyum Hedefi |
            |---|---|---|---|

            ### 5. 🌟 Standartlara Tam Uyumlu (Örnek) Gereksinimler
            *(Belgedeki en başarılı, ölçülebilir ve yasalara tam uyumlu 3 gereksinimi seçerek neden başarılı olduklarını açıkla. Bu, sistemin sadece hata aramadığını, doğruları da onayladığını gösterir.)*
            | Örnek Başarılı Gereksinim | Karşıladığı Standartlar | Neden Uyumlu ve Başarılı? |
            |---|---|---|
            """
            
            with st.spinner("Mevzuat ve standartlara göre denetleniyor..."):
                cevap = model.generate_content(f"{sistem_talimati}\n\nAnaliz edilecek metin:\n{analiz_metni}")
            
            st.success("✅ Kapsamlı Uyumluluk Analizi Tamamlanmıştır!")
            st.markdown(cevap.text)
            
            # 5. DİNAMİK DOKÜMAN KALİTE VE UYUM SKORU HESAPLAMASI
            with st.expander("📊 Doküman Kalite ve Uyum Skoru"):
                # Yapay zekanın ürettiği tablolardaki hata satırlarını sayan basit algoritma
                satirlar = cevap.text.split('\n')
                hata_sayisi = 0
                for satir in satirlar:
                    # Tablo satırıysa, başlık veya ayırıcı değilse ve 5. tablo (başarı tablosu) değilse say
                    if "|" in satir and "---" not in satir and "Gereksinim" not in satir and "Örnek Başarılı" not in satir and "✅" not in satir:
                        hata_sayisi += 1
                
                # Skor Hesaplama (100 üzerinden başlar, her hata için ortalama 6 puan kırılır)
                # Puan sıfırın altına düşmesin diye max(0, ...) kullanıyoruz
                mevcut_skor = max(0, 100 - (hata_sayisi * 6))
                
                st.markdown(f"Bu analiz sonucunda dokümanda toplam **{hata_sayisi} adet** standart veya mevzuat ihlali tespit edilmiştir.")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.error("📄 Dokümanın Mevcut Hali")
                    st.caption("Standartlar uygulanmadan önce:")
                    st.metric("Genel Uyum Skoru", f"% {mevcut_skor}", f"-{hata_sayisi} Kritik Bulgu")
                    
                with col2:
                    st.warning("🛠️ Düzeltme Eforu")
                    st.caption("Gereken revizyon miktarı:")
                    st.metric("İncelenmesi Gereken Madde", f"{hata_sayisi} Adet")
                    
                with col3:
                    st.success("🎯 Hedeflenen Durum")
                    st.caption("Önerilen düzeltmeler yapıldığında:")
                    st.metric("Ulaşılan Uyum Skoru", "% 100", f"+{100 - mevcut_skor} Puan Artış")
                
                st.divider()
                st.info("""
                **💡 Puanlama Mantığı:**
                Sisteme yüklediğiniz gereksinim belgesi 100 tam puan üzerinden değerlendirilir. IEEE, ISO ve KVKK standartlarına uymayan, ölçülemeyen veya güvenlik riski taşıyan her bir madde için sistem dinamik olarak puan kırar. Amacımız, yapay zekanın tablolar halinde sunduğu "Uyumlu Hale Getirme Önerileri"ni uygulayarak dokümanınızı %100 uyumlu (Audit-Ready) hale getirmektir.
                """)
        
        except Exception as e:
            st.error(f"❌ Hata: {e}")
