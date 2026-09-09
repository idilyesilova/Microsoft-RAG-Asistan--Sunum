import sqlite3

def init_db():
    # SQLite veritabanı bağlantısı oluşturur (dosya yoksa otomatik yaratır)
    conn = sqlite3.connect("knowledge_base.db")
    cursor = conn.cursor()
    
    # Doküman metinlerini ve vektörlerini (embeddings) tutacağımız tabloyu oluşturuyoruz
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text_chunk TEXT NOT NULL,
            embedding_vector TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print("Veritabanı (knowledge_base.db) başarıyla kuruldu ve tablolar oluşturuldu!")

if __name__ == "__main__":
    init_db()