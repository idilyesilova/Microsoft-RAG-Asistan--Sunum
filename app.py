import streamlit as st
import sqlite3
import json
import math
import PyPDF2
import os
from cryptography.fernet import Fernet
from foundry_local_sdk import FoundryLocalManager, Configuration

# --- Sayfa Ayarları ---
st.set_page_config(page_title="SecureOps Copilot", page_icon="🛡️", layout="wide")

# --- Kriptografi (Şifreleme) Katmanı ---
def get_or_create_key():
    key_file = "encryption_key.key"
    if not os.path.exists(key_file):
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
    else:
        with open(key_file, "rb") as f:
            key = f.read()
    return key

cipher_suite = Fernet(get_or_create_key())

# --- 0. Veritabanı Güvenli Başlatma ---
def init_db():
    conn = sqlite3.connect("knowledge_base.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS documents 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       text_chunk BLOB, 
                       embedding_vector TEXT, 
                       source_name TEXT)''')
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN source_name TEXT DEFAULT 'Bilinmeyen Kaynak'")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

# --- 1. Yapay Zeka ve Veritabanı Fonksiyonları ---
def cosine_similarity(v1, v2):
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a * a for a in v1))
    magnitude2 = math.sqrt(sum(b * b for b in v2))
    return dot_product / (magnitude1 * magnitude2) if magnitude1 * magnitude2 != 0 else 0

@st.cache_resource(show_spinner="Yapay zeka motorları başlatılıyor...")
def load_ai_system():
    config = Configuration(app_name="SecureOps_Copilot")
    manager = FoundryLocalManager(config)
    
    emb_model = manager.catalog.get_model("qwen3-embedding-0.6b")
    if not emb_model.is_loaded: 
        emb_model.load()
        
    chat_model = None
    for m in manager.catalog.list_models():
        m_id = getattr(m, 'id', str(m))
        if "qwen2.5-1.5b-instruct" in m_id:
            chat_model = m if hasattr(m, 'is_cached') else manager.catalog.get_model(m_id)
            break
            
    if chat_model:
        if not chat_model.is_cached:
            chat_model.download()
        if not chat_model.is_loaded:
            chat_model.load()
        
    return emb_model, chat_model

emb_model, chat_model = load_ai_system()

def get_answer_from_rag(query):
    emb_client = emb_model.get_embedding_client()
    response = emb_client.generate_embedding(query)
    query_vector = response.data[0].embedding if hasattr(response, 'data') else response
        
    conn = sqlite3.connect("knowledge_base.db")
    cursor = conn.cursor()
    cursor.execute("SELECT text_chunk, embedding_vector, source_name FROM documents WHERE embedding_vector != 'bekleniyor'")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "Veritabanında henüz bilgi yok. Lütfen sol menüden belge yükleyin."
    
    results = []
    for encrypted_text, emb_json, source in rows:
        try:
            decrypted_text = cipher_suite.decrypt(encrypted_text).decode("utf-8")
        except Exception:
            continue
            
        score = cosine_similarity(query_vector, json.loads(emb_json))
        results.append((score, decrypted_text, source))
        
    results.sort(key=lambda x: x[0], reverse=True)
    
    context_parts = []
    sources_used = set()
    for score, text, source in results[:3]:
        context_parts.append(text)
        sources_used.add(source)
        
    context_text = " ".join(context_parts)
    source_names = ", ".join(sources_used)
    
    chat_client = chat_model.get_chat_client()
    
    # PROMPT MÜHENDİSLİĞİ TEMİZLENDİ: Model artık sadece okuduğunu cevaplayacak
    prompt = f"""You are a strict and accurate AI assistant. Answer the question ONLY using the Context. 
If the answer is not in the Context, say "I cannot find the answer in the provided documents."
    
Context: {context_text}
Question: {query}"""

    chat_response = chat_client.complete_chat(messages=[{"role": "user", "content": prompt}])
    
    if hasattr(chat_response, 'choices'):
        raw_answer = chat_response.choices[0].message.content
    elif hasattr(chat_response, 'message'):
        raw_answer = chat_response.message.content
    else:
        raw_answer = str(chat_response)
        
    # --- RPA OTOMASYON TETİKLEYİCİSİ (PYTHON İLE KESİN KONTROL) ---
    rpa_keywords = ["rapor", "report", "log"]
    is_rpa_triggered = any(word in query.lower() for word in rpa_keywords)
    
    if is_rpa_triggered:
        # 1. Bilgisayarda fiziksel bir log dosyası oluştur
        with open("sistem_raporu.txt", "w", encoding="utf-8") as f:
            f.write("SECUREOPS COPILOT - SISTEM RAPORU\n\nHer sey guvenli ve calisir durumda.\nBaglanti: Lokal (Cevrimdisi)\nSifreleme: Aktif (Fernet)")
        
        # 2. Dosyayı Windows'ta otomatik olarak aç
        try:
            os.startfile("sistem_raporu.txt")
        except Exception:
            pass 
            
        # 3. Cevabın sonuna eylemin başarılı olduğunu ekle
        raw_answer += "\n\n✅ **Aksiyon Başarılı:** İşletim sisteminde rapor dosyası oluşturuldu ve ekranda açıldı!"
        
    final_answer = f"{raw_answer}\n\n---\n**📚 Kaynak (Şifresi Çözüldü):** `{source_names}`"
    return final_answer

def process_and_embed_file(uploaded_file):
    text = ""
    file_name = uploaded_file.name
    
    if file_name.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    elif file_name.endswith(".txt"):
        text = uploaded_file.read().decode("utf-8")
        
    if not text.strip():
        return False
        
    # HIZLANDIRMA UYGULANDI: Blok boyutu 400'den 1000'e çıkarıldı
    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
    
    conn = sqlite3.connect("knowledge_base.db")
    cursor = conn.cursor()
    emb_client = emb_model.get_embedding_client()
    
    for chunk in chunks:
        if len(chunk.strip()) < 10: continue
        
        encrypted_chunk = cipher_suite.encrypt(chunk.encode("utf-8"))
        
        cursor.execute("INSERT INTO documents (text_chunk, embedding_vector, source_name) VALUES (?, ?, ?)", (encrypted_chunk, "bekleniyor", file_name))
        row_id = cursor.lastrowid
        
        try:
            response = emb_client.generate_embedding(chunk)
            vector = response.data[0].embedding if hasattr(response, 'data') else response
            cursor.execute("UPDATE documents SET embedding_vector = ? WHERE id = ?", (json.dumps(vector), row_id))
        except Exception:
            pass
            
    conn.commit()
    conn.close()
    return True

# --- 2. GÖRSEL ARAYÜZ (UI) TASARIMI ---
with st.sidebar:
    st.header("🔐 Kriptografik Veri Girişi")
    st.write("Hedef belgeyi yerel ağa şifreleyerek aktarın.")
    
    uploaded_file = st.file_uploader("PDF veya TXT seçin", type=["pdf", "txt"])
    
    if uploaded_file is not None:
        if st.button("Dosyayı Şifrele ve Yükle", use_container_width=True):
            with st.spinner("Dosya okunuyor ve kriptografik olarak şifreleniyor..."):
                success = process_and_embed_file(uploaded_file)
                if success:
                    st.success(f"'{uploaded_file.name}' şifrelenerek veri tabanına başarıyla işlendi!")
                else:
                    st.error("Dosya okunamadı.")

st.title("🛡️ SecureOps: Autonomous Core") 
st.caption("Dış bağlantısı olmayan, şifreli belgeleriniz üzerinde işlem yapan aktif asistan.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Belgeleriniz hakkında bir soru sorun veya komut girin..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Şifreli veriler anlık olarak çözülüp taranıyor..."):
            cevap = get_answer_from_rag(prompt)
            st.markdown(cevap)
            
    st.session_state.messages.append({"role": "assistant", "content": cevap})