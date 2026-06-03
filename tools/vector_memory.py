from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
VECTOR_PATH = BASE / "vectors" / "chroma"

def init_vector_store():
    VECTOR_PATH.mkdir(parents=True, exist_ok=True)

    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(VECTOR_PATH))
        client.get_or_create_collection(name="stock_manager_memory")
        return {"ok": True, "path": str(VECTOR_PATH)}
    except Exception as e:
        return {"ok": False, "error": str(e), "path": str(VECTOR_PATH)}

def add_memory_document(doc_id, text, metadata=None):
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(VECTOR_PATH))
        collection = client.get_or_create_collection(name="stock_manager_memory")
        collection.add(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}]
        )
        return {"ok": True, "id": doc_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}
