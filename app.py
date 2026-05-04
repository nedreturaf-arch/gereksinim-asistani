import streamlit as st
import markdown
from xhtml2pdf import pisa
import io
import google.generativeai as genai
from docx import Document
import PyPDF2

# ---------------------------------------------------------
# 1. SAYFA VE ARAYÜZ YAPILANDIRMASI
# ---------------------------------------------------------
st.set_page_config(
    page_title="Gereksinim Analiz Asistanı v3.8",
    layout="wide"
)

# ---------------------------------------------------------
# 2. GÜVENLİK VE API YÖNETİMİ
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Ayarlar")
    api_key = st.text_input(
        "Gemini API Anahtarınızı girin:",
        type="password"
    )

    st.divider()
    secilen_model = None

    if api_key:
        try:
            genai.configure(api_key=api_key.strip())
            modeller = [
                m.name.replace("models/", "")
                for m in genai.list_models()
                if "generateContent" in m.supported_generation_methods
            ]

            if modeller:
                secilen_model = st.selectbox(
                    "🤖 Model Seçin:",
                    modeller
                )
            else:
                st.warning("⚠️ Kullanılabilir model bulunamadı.")
        except Exception as e:
            st.error("⚠️ API Hatası: Bağlantı kurulamadı.")
            st.caption(f"Teknik detay: {e}")

# ---------------------------------------------------------
# 3. ANA EKRAN VE BİLGİLENDİRME
# ---------------------------------------------------------
# Uygulamanın ana başlığı.
st.title("🎯 Gereksinim & Kalite Analiz Asistanı")

# Kullanıcıya sistemin hangi standartlar kapsamında analiz yaptığı açıklanır.
st.info("""
**📖 Analiz Kapsamı ve Referans Standartlar:**

Bu sistem, gereksinim metinlerini aşağıdaki uluslararası standartlar ve yerel mevzuatlar çerçevesinde denetleyerek, spesifik ifadeleri ilgili standart/prensip ile eşleştirir:

* **IEEE 29148:** Yazılım ve Sistem Mühendisliği — Gereksinim Mühendisliği Standartları
* **ISO/IEC 25010:** Yazılım Ürün Kalitesi ve Sistem Kalite Modelleri
* **ISO/IEC 27001:** Bilgi Güvenliği Yönetim Sistemi Gereksinimleri
* **KVKK:** 6698 Sayılı Kişisel Verilerin Korunması Kanunu
""")

st.divider()

# ---------------------------------------------------------
# 4. YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------
def dosya_oku(dosya):
    if dosya is None:
        return ""
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
                if sayfa_metni:
                    metin += sayfa_metni + "\n"
            return metin.strip()
        return ""
    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        return ""

def skor_hesapla(ai_cevabi, analiz_metni):
    satirlar = ai_cevabi.split("\n")
    kritik_hata, yuksek_hata, orta_hata = 0, 0, 0
    aktif_tablo = 0

    for satir in satirlar:
        temiz_satir = satir.strip()
        if "IEEE 29148" in temiz_satir: aktif_tablo = 1
        elif "KVKK" in temiz_satir: aktif_tablo = 2
        elif "ISO 27001" in temiz_satir: aktif_tablo = 3
        elif "ISO 25010" in temiz_satir: aktif_tablo = 4
        elif "Standartlara Tam Uyumlu" in temiz_satir: aktif_tablo = 5

        tablo_satiri_mi = (
            temiz_satir.startswith("|") and 
            temiz_satir.endswith("|") and 
            "---" not in temiz_satir and
            "Gereksinimdeki İfade" not in temiz_satir and
            "✅" not in temiz_satir and
            "⚠️" not in temiz_satir
        )

        if tablo_satiri_mi and aktif_tablo in [1, 2, 3, 4]:
            if aktif_tablo in [2, 3]: kritik_hata += 1
            elif aktif_tablo == 4: yuksek_hata += 1
            elif aktif_tablo == 1: orta_hata += 1

    toplam_madde = len([s for s in analiz_metni.split("\n") if len(s.strip()) > 15]) or 1
    toplam_hata = kritik_hata + yuksek_hata + orta_hata
    basarili_madde = max(0, toplam_madde - toplam_hata)
    toplam_ceza = (kritik_hata * 10 + yuksek_hata * 6 + orta_hata * 3)
    maksimum_risk = max(1, toplam_madde * 10)
    mevcut_skor = max(0, round(100 * (1 - (toplam_ceza / maksimum_risk))))

    return {
        "kritik_hata": kritik_hata, "yuksek_hata": yuksek_hata, "orta_hata": orta_hata,
        "toplam_hata": toplam_hata, "toplam_madde": toplam_madde,
        "basarili_madde": basarili_madde, "toplam_ceza": toplam_ceza, "mevcut_skor": mevcut_skor
    }

# ---------------------------------------------------------
# 5. VERİ GİRİŞİ VE ANALİZ
# ---------------------------------------------------------
st.subheader("📁 Veri Girişi")
yuklenen_dosya = st.file_uploader("Dosya seçin (.docx, .pdf)", type=["docx", "pdf"])
metin_alani = st.text_area("Veya metni yapıştırın:", height=150)

if st.button("🚀 Analizi Başlat"):
    analiz_metni = dosya_oku(yuklenen_dosya) if yuklenen_dosya else metin_alani

    if not api_key or not analiz_metni.strip() or not secilen_model:
        st.warning("⚠️ Eksik bilgi: API anahtarı, model seçimi veya metin gereklidir.")
    else:
        try:
            model = genai.GenerativeModel(secilen_model)
            
            # Anti-halüsinasyon odaklı sistem talimatı
            sistem_talimati = """
            Sen uzman bir BT Uyum Denetçisisin. Çıktılarını SADECE Türkçe üret.
            KURAL 1: Doğrudan tablolara başla. Giriş/Sonuç cümlesi yazma.
            KURAL 2: İhlal yoksa tabloya "✅ Tam uyum sağlanmıştır" yaz.
            KURAL 3 (ANTİ-HALÜSİNASYON): "5. Başarılı Örnekler" tablosuna SADECE metinde var olan en fazla 5 madde ekle. 
            KURAL 4: Tablolardaki "Standart Karşılığı", "Mevzuat Karşılığı", "Karakteristik", "Kontrol Alanı" ve "Karşıladığı Standartlar" sütunlarına ASLA genel açıklamalar veya yorumlar yazma. Bu sütunlara SADECE ihlal edilen veya karşılanan standardın/mevzuatın TAM KANUN MADDESİNİ, REFERANS NUMARASINI, ALT BAŞLIĞINI veya KONTROL MADDESİNİ yaz (Örnek: "ISO 27001 Ek A.9.2.1", "KVKK Madde 12(1)", "IEEE 29148 Madde 5.2.3", "ISO 25010 - Güvenilirlik / Olgunluk").
            Eğer metinde standartlara tam uyumlu bir madde BULUNMUYORSA, tabloya "⚠️ Metin içerisinde standartlara tam uyumlu bir madde tespit edilememiştir." yaz. 
            Kesinlikle uydurma örnek oluşturma.

            ### 1. 📏 IEEE 29148 Uyumluluğu
            | Gereksinimdeki İfade | İhlal Edilen Kriter | Standart Karşılığı ve Analiz | Uyum Önerisi |

            ### 2. 🛡️ KVKK Uyumluluğu
            | Gereksinimdeki İfade | KVKK Riski | Mevzuat Çerçevesi ve Çelişme Nedeni | Hukuki Uyum Önerisi |

            ### 3. 🔒 ISO 27001 Uyumluluğu
            | Gereksinimdeki İfade | Güvenlik Riski | Refesrans Madde ve Teknik Gerekçe | Teknik Önlem |

            ### 4. ⚙️ ISO 25010 Uyumluluğu
            | Gereksinimdeki İfade | Kalite Eksikliği | Karakteristik ve Analiz | Kalite Hedefi |

            ### 5. 🌟 Standartlara Tam Uyumlu Gereksinimler
            | Başarılı Gereksinim | Karşıladığı Standartlar | Uyum Gerekçesi |
            """

            tam_prompt = f"{sistem_talimati}\n\nANALİZ EDİLECEK METİN:\n{analiz_metni.strip()}"

            with st.spinner("Analiz ediliyor..."):
                cevap = model.generate_content(tam_prompt)

            if cevap and hasattr(cevap, "text"):
                st.success("✅ Analiz Tamamlandı!")
                st.markdown(cevap.text)
                
                # Skorlama
                with st.expander("📊 Doküman Uyum Skoru", expanded=True):
                    skor = skor_hesapla(cevap.text, analiz_metni)
                    st.info(f"Taranan Madde: {skor['toplam_madde']} | Uyumlu: {skor['basarili_madde']} | Hatalı: {skor['toplam_hata']}")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Uyum Skoru", f"% {skor['mevcut_skor']}", f"-{skor['toplam_ceza']} Risk")
                    c2.write(f"🔴 {skor['kritik_hata']} Kritik\n🟠 {skor['yuksek_hata']} Yüksek\n🟡 {skor['orta_hata']} Orta")
                    c3.metric("Uyumlu Madde", f"{skor['basarili_madde']} Adet")

                    st.divider()
                    
                    with st.expander("🧮 Puanlama Nasıl Hesaplanıyor? (Matematiksel Döküm)"):
                        st.markdown(f"""
                        **1. Madde ve Hata Tespiti:**
                        * **Toplam Taranan Madde:** {skor['toplam_madde']}
                        * **Tespit Edilen Hatalar:** {skor['kritik_hata']} Kritik + {skor['yuksek_hata']} Yüksek + {skor['orta_hata']} Orta = **{skor['toplam_hata']} Toplam Hata**
                        * **Başarılı Madde:** {skor['toplam_madde']} (Toplam) - {skor['toplam_hata']} (Hata) = **{skor['basarili_madde']} Adet**

                        **2. Risk (Ceza) Puanı Hesabı:**
                        *(Ağırlıklar - Kritik: 10, Yüksek: 6, Orta: 3)*
                        * Kritik Risk Cezası: {skor['kritik_hata']} x 10 = **{skor['kritik_hata'] * 10} Puan**
                        * Yüksek Risk Cezası: {skor['yuksek_hata']} x 6 = **{skor['yuksek_hata'] * 6} Puan**
                        * Orta Risk Cezası: {skor['orta_hata']} x 3 = **{skor['orta_hata'] * 3} Puan**
                        * **Toplam Risk Puanı:** **{skor['toplam_ceza']} Puan**

                        **3. Uyum Yüzdesi (%):**
                        * **Maksimum Olası Risk:** {skor['toplam_madde']} x 10 = **{skor['toplam_madde'] * 10}**
                        * **Risk Oranı:** {skor['toplam_ceza']} / {max(1, (skor['toplam_madde'] * 10))} = **{skor['toplam_ceza'] / max(1, (skor['toplam_madde'] * 10)):.4f}**
                        * **Sonuç:** 100 - (Risk Oranı x 100) = **% {skor['mevcut_skor']}**
                        """)
                
                # --- İŞTE YENİ EKLENECEK PDF KISMI ---
                st.divider() # Araya ince bir çizgi çeker
                
                # PDF Dönüştürme Fonksiyonu (Sadece ihtiyaç olduğunda çalışır)
                def pdf_olustur(ai_metni, skor_verisi):
                    html_tablolar = markdown.markdown(ai_metni, extensions=['tables'])
                    
                    html_sablon = f"""
                    <!DOCTYPE html>
                    <html lang="tr">
                    <head>
                        <meta charset="UTF-8">
                        <style>
                            @page {{ size: a4 portrait; margin: 2cm; }}
                            body {{ font-family: Helvetica, Arial, sans-serif; font-size: 12px; color: #333; }}
                            h1 {{ color: #2C3E50; border-bottom: 1px solid #2C3E50; padding-bottom: 5px; }}
                            .skor-kutusu {{ background-color: #f8f9fa; padding: 15px; border-left: 3px solid #28a745; margin-bottom: 20px; }}
                            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                            th {{ background-color: #2C3E50; color: white; font-weight: bold; }}
                        </style>
                    </head>
                    <body>
                        <h1>Gereksinim Analiz ve Kalite Raporu</h1>
                        <div class="skor-kutusu">
                            <h2>Genel Uyum Skoru: %{skor_verisi['mevcut_skor']}</h2>
                            <p><strong>Taranan Madde:</strong> {skor_verisi['toplam_madde']} | 
                               <strong>Uyumlu:</strong> {skor_verisi['basarili_madde']} | 
                               <strong>Hatalı:</strong> {skor_verisi['toplam_hata']}</p>
                            <p style="color:red; font-weight:bold;">
                               (Kritik: {skor_verisi['kritik_hata']}, Yüksek: {skor_verisi['yuksek_hata']}, Orta: {skor_verisi['orta_hata']})
                            </p>
                        </div>
                        <h2>Detaylı Analiz Tabloları</h2>
                        {html_tablolar}
                    </body>
                    </html>
                    """
                    # HTML'i PDF bytes verisine çevir (xhtml2pdf ile)
                    pdf_buffer = io.BytesIO()
                    pisa_status = pisa.CreatePDF(html_sablon, dest=pdf_buffer)
                    
                    if pisa_status.err:
                        raise Exception("PDF oluşturulurken teknik bir hata meydana geldi.")
                        
                    return pdf_buffer.getvalue()

                # İndirme Butonu
                try:
                    with st.spinner("PDF Raporu Hazırlanıyor..."):
                        pdf_verisi = pdf_olustur(cevap.text, skor)
                        
                    st.download_button(
                        label="📄 Bu Raporu PDF Olarak İndir",
                        data=pdf_verisi,
                        file_name="Gereksinim_Analiz_Raporu.pdf",
                        mime="application/pdf",
                        type="primary" # Butonu mavi/vurgulu yapar
                    )
                except Exception as e:
                    st.error(f"PDF oluşturulurken bir hata oluştu: {e}")
                # --- PDF KISMI SONU ---

            else:
                st.error("❌ Modelden yanıt alınamadı.")

        except Exception as e:
            st.error(f"❌ Analiz Hatası: {e}")
