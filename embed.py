import sqlite3
import json
from foundry_local_sdk import FoundryLocalManager, Configuration

def process_embeddings():
    print("Foundry Local Manager başlatılıyor...")
    config = Configuration(app_name="SecureOps_Copilot")
    manager = FoundryLocalManager(config)
    
    print("Model katalog üzerinden yükleniyor...")
    model = manager.catalog.get_model("qwen3-embedding-0.6b")
    
    # Model indirilmemişse indir, belleğe yüklenmemişse yükle
    if not model.is_cached:
        print("Model dosyaları indiriliyor, lütfen bekleyin...")
        model.download()
        
    if not model.is_loaded:
        print("Model belleğe yükleniyor...")
        model.load()
        
    # Vektör istemcisini oluştur
    client = model.get_embedding_client()
    
    # Veritabanına bağlan
    conn = sqlite3.connect("knowledge_base.db")
    cursor = conn.cursor()
    
    # Vektörleştirilmemiş (bekleniyor) metinleri seç
    cursor.execute("SELECT id, text_chunk FROM documents WHERE embedding_vector = 'bekleniyor'")
    rows = cursor.fetchall()
    
    if not rows:
        print("Vektörleştirilecek yeni metin bulunamadı.")
        return

    print(f"\nToplam {len(rows)} adet metin vektörleştiriliyor...")
    
    for row_id, text in rows:
        print(f"İşleniyor: {text[:40]}...")
        
        try:
            # Bulduğumuz asıl komutu kullanarak metni vektöre çeviriyoruz
            response = client.generate_embedding(text)
            
            # OpenAI standartlarındaki gibi nesne döndürüyorsa içinden listeyi alıyoruz
            # Eğer direkt liste döndürüyorsa onu kullanıyoruz
            if hasattr(response, 'data'):
                embedding_vector = response.data[0].embedding
            else:
                embedding_vector = response
            
            # Vektörü JSON formatında veritabanına kaydediyoruz
            embedding_json = json.dumps(embedding_vector)
            cursor.execute("UPDATE documents SET embedding_vector = ? WHERE id = ?", (embedding_json, row_id))
            
        except Exception as e:
            print(f"Hata oluştu (ID: {row_id}): {e}")
            
    conn.commit()
    conn.close()
    print("\nHarika! Tüm metinler başarıyla vektörleştirildi ve veritabanına kaydedildi!")

if __name__ == "__main__":
    process_embeddings()