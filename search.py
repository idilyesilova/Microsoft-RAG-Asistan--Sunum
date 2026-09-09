import sqlite3
import json
import math
from foundry_local_sdk import FoundryLocalManager, Configuration

# Vektörler arasındaki anlamsal yakınlığı ölçen matematiksel fonksiyonumuz
def cosine_similarity(v1, v2):
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a * a for a in v1))
    magnitude2 = math.sqrt(sum(b * b for b in v2))
    if magnitude1 * magnitude2 == 0:
        return 0
    return dot_product / (magnitude1 * magnitude2)

def search_knowledge_base(query):
    print("Foundry Local Manager başlatılıyor...")
    config = Configuration(app_name="SecureOps_Copilot")
    manager = FoundryLocalManager(config)
    
    print("Vektör modeli yükleniyor...")
    model = manager.catalog.get_model("qwen3-embedding-0.6b")
    if not model.is_loaded:
        model.load()
        
    client = model.get_embedding_client()
    
    print(f"\nSoru vektörleştiriliyor: '{query}'")
    # 1. Kullanıcının sorusunu vektöre (sayı dizisine) çeviriyoruz
    response = client.generate_embedding(query)
    if hasattr(response, 'data'):
        query_vector = response.data[0].embedding
    else:
        query_vector = response
        
    print("Veritabanında anlamsal arama yapılıyor...")
    # 2. Veritabanındaki kayıtlı tüm vektörleri çekiyoruz
    conn = sqlite3.connect("knowledge_base.db")
    cursor = conn.cursor()
    cursor.execute("SELECT text_chunk, embedding_vector FROM documents WHERE embedding_vector != 'bekleniyor'")
    rows = cursor.fetchall()
    conn.close()
    
    # 3. Soru vektörü ile veritabanındaki her metnin vektörünü matematiksel olarak karşılaştırıyoruz
    results = []
    for text, emb_json in rows:
        doc_vector = json.loads(emb_json)
        score = cosine_similarity(query_vector, doc_vector)
        results.append((score, text))
        
    # 4. En yüksek benzerlik skoruna sahip olanları büyükten küçüğe sıralıyoruz
    results.sort(key=lambda x: x[0], reverse=True)
    
    print("-" * 50)
    print("En yakın bulunan sonuçlar:")
    
    # Sistemin bulduğu en iyi 2 sonucu ekrana yazdırıyoruz
    for score, text in results[:2]:
        print(f"[Skor: {score:.4f}] {text}")

if __name__ == "__main__":
    # Test sorumuz
    test_sorusu = "Bu proje ne işe yarıyor ve kodlar nerede paylaşılacak?"
    search_knowledge_base(test_sorusu)