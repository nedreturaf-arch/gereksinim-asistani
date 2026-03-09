# GEREKLİ KÜTÜPHANELERİ İÇERİ AKTARIYORUZ
import streamlit as st
import google.generativeai as genai
from docx import Document 
import io

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Gereksinim Analiz Asistanı", layout="wide")

# 2. SOL MENÜ (AYARLAR KISMI)
with st.sidebar:
    st.header("⚙️ Ayarlar")
    api_key = st.text_input("Gemini API Anahtarınızı girin:", type="password")
    st.markdown("*API Anahtarınızı [Google AI Studio](https://aistudio.google.com/) adresinden alabilirsiniz.*")
    
    st.divider() 
    
    secilen_model = None
    if api_key: 
        try:
            genai.configure(api_key=api_key.strip())
            modeller = []
            
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    modeller.append(m.name.replace("models/", ""))
            
            if modeller:
                st.success("✅ Modeller başarıyla çekildi!")
                secilen_model = st.selectbox("🤖 Kullanılacak Modeli Seçin:", modeller)
        except Exception as e:
            st.error("⚠️ API Anahtarı geçersiz veya modellere ulaşılamıyor.")

# 3. ANA EKRAN TASARIMI (VİTRİN)
st.title("🎯 Gereksinim Analiz Asistanı-LLM Tabanlı")
st.markdown("Bu araç, yazılım gereksinim metinlerini veya **Word dokümanlarını** analiz etmek için tasarlanmıştır.")
st.divider()

# DOSYA YÜKLEME ALANI
st.subheader("📁 Doküman Yükle (Opsiyonel)")
yuklenen_dosya = st.file_uploader("Analiz edilecek Word dosyasını seçin (.docx)", type=["docx"])

# METİN GİRİŞ ALANI
st.subheader("📝 Veya Metin Yapıştır")
metin_alani = st.text_area("Analiz edilmesini istediğiniz gereksinim metnini buraya yazın:", height=150)

# 4. WORD DOSYASI OKUMA FONKSİYONU
def word_oku(dosya):
    doc = Document(dosya)
    tam_metin = []
    for paragraf in doc.paragraphs:
        tam_metin.append(paragraf.text)
    return "\n".join(tam_metin) 

# 5. ANALİZİ BAŞLATMA BUTONU
if st.button("🚀 Analizi Başlat"):
    analiz_edilecek_metin = ""
    
    if yuklenen_dosya is not None:
        analiz_edilecek_metin = word_oku(yuklenen_dosya) 
    else:
        analiz_edilecek_metin = metin_alani 

    if not api_key:
        st.error("⚠️ Lütfen önce sol menüden Gemini API Anahtarınızı girin!")
    elif not secilen_model:
        st.error("⚠️ Lütfen sol menüden bir yapay zeka modeli seçin!")
    elif not analiz_edilecek_metin:
        st.warning("⚠️ Lütfen bir dosya yükleyin veya metin girin.")
    else:
        try:
            genai.configure(api_key=api_key.strip())
            model = genai.GenerativeModel(secilen_model) 
            
            with st.spinner(f"Dosya okunuyor ve {secilen_model} tarafından analiz ediliyor... 🧠"):
                
                # MÜHENDİSLİK KOMUTU (PROMPT ENGINEERING) - KIRMIZI VURGU EKLENDİ!
                sistem_komutu = """
                Sen uzman bir Yazılım Gereksinim Mühendisisin. Lütfen şu metni şu kriterlere göre analiz et:
                1. Belirsizlikler (Ölçülemeyen ifadeler)
                2. Mantıksal Çelişkiler
                3. Eksiklikler (Edge Cases)
                
                ÇOK ÖNEMLİ KURAL: 
                Raporunu oluştururken, metnin içinden bulduğun o hatalı, belirsiz veya çelişen kelimeleri/cümleleri MUTLAKA kırmızı ve kalın yazarak vurgula. 
                Bunu yapmak için şu HTML etiketini kullan: <span style='color:red'>**hatalı kelime buraya**</span>
                
                Cevabını profesyonel, net ve yapılandırılmış bir dille raporla.
                """
                cevap = model.generate_content(f"{sistem_komutu}\n\n{analiz_edilecek_metin}")
                
            st.success("✅ Analiz Tamamlandı!")
            st.info("💡 **Yapay Zeka Analiz Raporu**")
            
            # STREAMLIT'E HTML ÇALIŞTIRMA İZNİ VERDİK (unsafe_allow_html=True)
            st.markdown(cevap.text, unsafe_allow_html=True)
            
            st.download_button(
                label="💾 Raporu İndir (.txt)",
                data=cevap.text,
                file_name="Gereksinim_Analiz_Raporu.txt",
                mime="text/plain" 
            )
            
        except Exception as e:
            st.error(f"❌ Bir hata oluştu: {e}")