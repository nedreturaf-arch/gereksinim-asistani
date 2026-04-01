# 🎯 Gereksinim & Kalite Analiz Asistanı (RAG Destekli v3.0)

Bu proje, yazılım gereksinim analizi aşamasında karşılaşılan belirsizlikleri, mantıksal çelişkileri ve mevzuat uyumsuzluklarını otomatik olarak tespit edebilen **Büyük Dil Modeli (LLM)** ve **RAG (Retrieval-Augmented Generation)** tabanlı bir karar destek aracıdır.

## 📖 Proje Hakkında
Yazılım projelerindeki hataların büyük bir kısmı analiz aşamasındaki belirsizlerden kaynaklanmaktadır. Bu araç, yüklenen gereksinim dokümanlarını sadece yapay zeka bilgisiyle değil; **IEEE, ISO, KVKK ve CBDDO BİG Rehberi** gibi resmi standartları referans alarak denetler.

## ✨ Temel Özellikler
- **Hibrit Analiz:** Standart LLM yanıtlarını, RAG mimarisi ile resmi mevzuatlarla doğrular.
- **Çoklu Format Desteği:** `.pdf` ve `.docx` uzantılı gereksinim belgelerini doğrudan analiz edebilir.
- **6 Kritik Kategori:** Belirsizlikler, Çelişkiler, Eksiklikler, Süreç İhlalleri, Test Edilebilirlik ve Bilgi Güvenliği başlıklarında tablo bazlı raporlama sunar.
- **Karşılaştırmalı Metrik Paneli:** RAG mimarisinin sisteme kattığı performansı anlık olarak görselleştirir.

## 🛠️ Kullanılan Teknolojiler
* **Dil:** Python 3.9+
* **Arayüz:** [Streamlit](https://streamlit.io/)
* **Yapay Zeka Modeli:** Google Gemini Pro
* **RAG Altyapısı:** LangChain & Vector Embeddings
* **Dosya İşleme:** PyPDF2, python-docx

## 🚀 Kurulum ve Çalıştırma

1. **Depoyu klonlayın:**
   ```bash
   git clone [https://github.com/nedreturaf-arch/gereksinim-asistani.git](https://github.com/nedreturaf-arch/gereksinim-asistani.git)
   cd gereksinim-asistani

