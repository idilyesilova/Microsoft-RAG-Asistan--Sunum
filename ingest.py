import sqlite3

# Asistanın okuyup öğreneceği örnek bilgi bankası metnimiz
sample_text = """
Microsoft Yaz Okulu ve Azure Foundry Local LLM Projesi Notları:
Bu proje, verilerin tamamen yerel (çevrimdışı) ortamda işlenmesini sağlayarak şirketler için yüksek güvenlik sunar.
Foundry Local SDK kullanılarak cihaz içi (on-device) RAG (Retrieval-Augmented Generation) mimarisi kurulmuştur.
Sistem, internet bağlantısına ihtiyaç duymadan SQLite veritabanındaki belgeler içerisinde anlamsal arama yapabilir.
Proje sonunda tüm kaynak kodlar GitHub üzerinden değerlendirilmek üzere paylaşılacaktır.
"""

def insert_documents():
    conn = sqlite3.connect("knowledge_base.db")
    cursor = conn.cursor()
    
    # Metni satır satır bölüyoruz (chunking işlemi)
    chunks = [line.strip() for line in sample_text.strip().split('\n') if line.strip()]
    
    for chunk in chunks:
        # Şimdilik embedding_vector kısmını boş bırakıyoruz, bir sonraki adımda Foundry Local ile vektörleştireceğiz
        cursor.execute("INSERT INTO documents (text_chunk, embedding_vector) VALUES (?, ?)", (chunk, "bekleniyor"))
        
    conn.commit()
    conn.close()
    print(f"Başarıyla {len(chunks)} adet veri parçası (chunk) veritabanına eklendi!")

if __name__ == "__main__":
    insert_documents()