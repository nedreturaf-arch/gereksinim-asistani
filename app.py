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
            KURAL 4: RİSK GÖRSELLEŞTİRME: Tablolardaki 'Gereksinim' sütununda yer alan her maddenin başına, o tablonun risk seviyesine uygun şu emojileri ve etiketleri KESİNLİKLE EKLE:
            - Tablo 1 (IEEE 29148) hataları için: 🟡 [ORTA RİSK] 
            - Tablo 2 ve 3 (KVKK, ISO 27001) hataları için: 🔴 [KRİTİK RİSK] 
            - Tablo 4 (ISO 25010) hataları için: 🟠 [YÜKSEK RİSK] 
            - Tablo 5 (Başarılı Örnekler) için: 🟢 [KUSURSUZ] 
            
            KURAL 5 (ÇOK KRİTİK): HALÜSİNASYON VE AŞIRI DENETİM ÖNLEME: 
            Sırf tabloları doldurmak için "aşırı teknik detay (örn: sunucu zaman aşımı süresi, veritabanı şifreleme algoritmasının bit uzunluğu)" uydurup bunları İHLAL gibi gösterme. Bir gereksinim, temel ISO/KVKK mantığını ve kuralını karşılıyorsa onu DOĞRU kabul et. Ufak geliştirme tavsiyelerini "Güvenlik Zafiyeti" veya "Hata" gibi raporlama. Metin zaten yüksek kaliteliyse bol bol "✅ Bu standart açısından tam uyum sağlanmıştır." ifadesini kullanmaktan çekinme.

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
            *(Belgedeki en başarılı, ölçülebilir ve yasalara tam uyumlu 3 gereksinimi seçerek neden başarılı olduklarını açıkla.)*
            | Örnek Başarılı Gereksinim | Karşıladığı Standartlar | Neden Uyumlu ve Başarılı? |
            |---|---|---|
            """
            
            with st.spinner("Mevzuat ve standartlara göre denetleniyor..."):
                cevap = model.generate_content(f"{sistem_talimati}\n\nAnaliz edilecek metin:\n{analiz_metni}")
            
            st.success("✅ Kapsamlı Uyumluluk Analizi Tamamlanmıştır!")
            st.markdown(cevap.text)
            
            # 5. METRİKLER (KARŞILAŞTIRMALI ANALİZ VE MATEMATİKSEL ALTYAPI)
            with st.expander("📊 Doküman Kalite Skoru ve Yapay Zeka Metrikleri"):
                # Kullanıcıyı boğmamak için iki sekme oluşturuyoruz
                tab1, tab2 = st.tabs(["📝 Dinamik Uyum Skoru (ISTQB)", "🧮 Yapay Zeka Karmaşıklık Matrisi (Akademik)"])
                
                with tab1:
                    # Ağırlıklı Skor Hesaplama Algoritması (ISTQB Risk Temelli)
                    satirlar = cevap.text.split('\n')
                    
                    kritik_hata = 0 # KVKK ve Güvenlik (-10 Puan)
                    yuksek_hata = 0 # Kalite ve Performans (-6 Puan)
                    orta_hata = 0   # Netlik ve Belirsizlik (-3 Puan)
                    
                    aktif_tablo = 0
                    for satir in satirlar:
                        if "IEEE 29148" in satir: aktif_tablo = 1
                        elif "KVKK" in satir: aktif_tablo = 2
                        elif "ISO 27001" in satir: aktif_tablo = 3
                        elif "ISO 25010" in satir: aktif_tablo = 4
                        elif "Standartlara Tam Uyumlu" in satir: aktif_tablo = 5
                        
                        if "|" in satir and "---" not in satir and "Gereksinim" not in satir and "✅" not in satir and aktif_tablo != 5:
                            if aktif_tablo in [2, 3]: kritik_hata += 1
                            elif aktif_tablo == 4: yuksek_hata += 1
                            elif aktif_tablo == 1: orta_hata += 1
                    
                    toplam_hata = kritik_hata + yuksek_hata + orta_hata
                    kesilen_puan = (kritik_hata * 10) + (yuksek_hata * 6) + (orta_hata * 3)
                    mevcut_skor = max(0, 100 - kesilen_puan)
                    
                    st.markdown(f"Bu analiz sonucunda dokümanda toplam **{toplam_hata} adet** standart veya mevzuat ihlali tespit edilmiştir.")
                    
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
                    st.info("""
                    **💡 ISTQB Risk Temelli Puanlama Mantığı:**
                    Sisteme yüklediğiniz belge 100 tam puan üzerinden değerlendirilir. Hatalar önem derecesine göre ağırlıklandırılmıştır:
                    * **Kritik Riskler (-10 Puan):** KVKK ihlalleri ve ISO 27001 bilgi güvenliği zafiyetleri.
                    * **Yüksek Riskler (-6 Puan):** ISO 25010 mimari kalite, performans ve kullanılabilirlik hataları.
                    * **Orta Riskler (-3 Puan):** IEEE 29148 ölçülebilirlik ve belirsizlik ihlalleri.
                    """)

                with tab2:
                    st.markdown("### Karmaşıklık Matrisi (Confusion Matrix) Temelleri")
                    st.info("""
                    Bu sekme, aracın arka planında çalışan Yapay Zeka modelinin hata yakalama performansını ölçen akademik formülleri içerir. Projenin test aşamasında referans (kusursuz) dokümanlar kullanılarak bu metrikler hesaplanır.
                    """)
                    
                    st.markdown("#### 1. Doğruluk (Accuracy)")
                    st.markdown("Sistemin verdiği tüm kararların yüzde kaçının doğru olduğunu gösterir.")
                    st.latex(r"Accuracy = \frac{TP + TN}{TP + TN + FP + FN}")
                    
                    st.markdown("#### 2. Kesinlik (Precision)")
                    st.markdown("Sistemin işaretlediği hataların ne kadarının **gerçekten** hata olduğunu gösterir.")
                    st.latex(r"Precision = \frac{TP}{TP + FP}")
                    
                    st.markdown("#### 3. Duyarlılık (Recall)")
                    st.markdown("Gerçekte var olan hataların ne kadarını sistemin **yakalayabildiğini** gösterir.")
                    st.latex(r"Recall = \frac{TP}{TP + FN}")
                    
                    st.markdown("#### 4. F1 Skoru")
                    st.markdown("Kesinlik ve Duyarlılığın dengeli (harmonik) ortalamasıdır. Sistemin genel güvenilirliğini ifade eder.")
                    st.latex(r"F1 = 2 \times \frac{Precision \times Recall}{Precision + Recall}")
        
        except Exception as e:
            st.error(f"❌ Hata: {e}")
