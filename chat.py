import sqlite3
import json
import math
from foundry_local_sdk import FoundryLocalManager, Configuration

# Vektör matematiği (Kosinüs Benzerliği)
def cosine_similarity(v1, v2):
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a * a for a in v1))
    magnitude2 = math.sqrt(sum(b * b for b in v2))
    return dot_product / (magnitude1 * magnitude2) if magnitude1 * magnitude2 != 0 else 0

def ask_copilot(query):
    print("Sistem başlatılıyor...")
    config = Configuration(app_name="SecureOps_Copilot")
    manager = FoundryLocalManager(config)
    
    # --- 1. ARAMA (RETRIEVAL) AŞAMASI ---
    emb_model = manager.catalog.get_model("qwen3-embedding-0.6b")
    if not emb_model.is_loaded: 
        emb_model.load()
    emb_client = emb_model.get_embedding_client()
    
    response = emb_client.generate_embedding(query)
    query_vector = response.data[0].embedding if hasattr(response, 'data') else response
        
    conn = sqlite3.connect("knowledge_base.db")
    cursor = conn.cursor()
    cursor.execute("SELECT text_chunk, embedding_vector FROM documents WHERE embedding_vector != 'bekleniyor'")
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for text, emb_json in rows:
        score = cosine_similarity(query_vector, json.loads(emb_json))
        results.append((score, text))
        
    results.sort(key=lambda x: x[0], reverse=True)
    # En iyi 2 sonucu yan yana birleştirerek bağlam (context) oluşturuyoruz
    context_text = " ".join([text for score, text in results[:2]])
    
    # --- 2. ÜRETİM (GENERATION) AŞAMASI ---
    print("\n[Bilgi] Chat modeli hazırlanıyor...")
    
    # KESİN ÇÖZÜM: İsmi tahmin etmek yerine, modeli doğrudan katalog listesinden çekip alıyoruz
    chat_model = None
    for m in manager.catalog.list_models():
        m_id = getattr(m, 'id', str(m))
        if "qwen2.5-0.5b-instruct" in m_id:
            # Objeyi doğrudan listesinden alıp kullanıyoruz
            chat_model = m if hasattr(m, 'is_cached') else manager.catalog.get_model(m_id)
            print(f"[Başarılı] Chat modeli katalogdan dinamik olarak yakalandı: {m_id}")
            break
            
    if chat_model is None:
        print("Kritik Hata: Model katalogda hiç bulunamadı!")
        return
    
    if not chat_model.is_cached:
        print("Model dosyaları indiriliyor (boyutu küçük olduğu için hızlı inecektir)...")
        chat_model.download()
        
    if not chat_model.is_loaded:
        print("Chat modeli belleğe yükleniyor...")
        chat_model.load()
        
    chat_client = chat_model.get_chat_client()
    
    # Yapay zekaya vereceğimiz sistem komutu (Prompt Engineering)
    prompt = f"""Sen Microsoft Foundry Local altyapısını kullanan güvenli bir asistansın.
Lütfen sadece aşağıdaki 'Bilgi' kısmında verilen metinlere dayanarak soruyu cevapla. Dışarıdan bilgi ekleme.

Bilgi: {context_text}

Soru: {query}"""

    print("\n--------------------------------------------------")
    print("Asistanın Cevabı:")
    try:
        # BULDUĞUMUZ DOĞRU KOMUTU KULLANIYORUZ
        chat_response = chat_client.complete_chat(
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Çıktı formatını güvenceye alıyoruz
        if hasattr(chat_response, 'choices'):
            print(chat_response.choices[0].message.content)
        elif hasattr(chat_response, 'message'):
            print(chat_response.message.content)
        else:
            print(chat_response) # Eğer doğrudan metin dönüyorsa
            
    except Exception as e:
        print(f"\nBir hata oluştu: {e}")
        # Hata anında objenin içini görmek için
        if 'chat_response' in locals(): print(dir(chat_response))

if __name__ == "__main__":
    soru = "Bu proje ne işe yarıyor ve kodlar nerede paylaşılacak?"
    ask_copilot(soru)