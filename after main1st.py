from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional
import sqlite3

app = FastAPI(title="Nestor Retail Central Sync Server")

# Jina la database siri ya mtandaoni
DB_ONLINE = "nestor_central_backup.db"

# ==============================================================================
# 🔒 EDIT SECURITY KEY HAPA (SERVER SIDE)
# ==============================================================================
# Hakikisha neno hili linafanana herufi kwa herufi na lile lililopo kwenye App yako!
SERVER_SECURITY_KEY = "Delandawitsii****" 
# ==============================================================================

def init_online_db():
    conn = sqlite3.connect(DB_ONLINE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS central_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id_local INTEGER,
            tenant_id INTEGER,
            item_id INTEGER,
            quantity_sold INTEGER,
            profit REAL,
            total_amount REAL,
            sale_date TEXT,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_online_db()

class SaleItem(BaseModel):
    sale_id: int
    tenant_id: int
    item_id: int
    quantity_sold: int
    profit: float
    total_amount: float
    sale_date: str

class SyncPayload(BaseModel):
    sales: List[SaleItem]

@app.get("/")
def home():
    return {"status": "Nestor Server Is Running Successfully!", "secure_mode": "Enabled"}

@app.post("/sync")
def sync_data(payload: SyncPayload, x_security_key: Optional[str] = Header(None)):
    """Inapokea mauzo kutoka kwenye simu na kuyalinda yasiibiwe kwa kuangalia Security Key."""
    
    # 🛡️ DATABASE & API SECURITY CHECK
    if x_security_key != SERVER_SECURITY_KEY:
        raise HTTPException(
            status_code=403, 
            detail="❌ Umekataliwa kuingia! Security Key yako si sahihi au huna mamlaka."
        )

    if not payload.sales:
        return {"status": "empty", "message": "Hakuna data mpya iliyotumwa"}
        
    conn = sqlite3.connect(DB_ONLINE)
    cursor = conn.cursor()
    saved_count = 0
    
    try:
        for sale in payload.sales:
            # Zuia data ya duka lile lile kujirudia (Duplication Check)
            exists = cursor.execute(
                "SELECT id FROM central_sales WHERE tenant_id = ? AND sale_id_local = ?", 
                (sale.tenant_id, sale.sale_id)
            ).fetchone()
            
            if not exists:
                cursor.execute(
                    """
                    INSERT INTO central_sales (sale_id_local, tenant_id, item_id, quantity_sold, profit, total_amount, sale_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (sale.sale_id, sale.tenant_id, sale.item_id, sale.quantity_sold, sale.profit, sale.total_amount, sale.sale_date)
                )
                saved_count += 1
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Hitilafu ya Server Kuu: {str(e)}")
        
    conn.close()
    return {"status": "success", "message": f"✔️ Mauzo {saved_count} yamehifadhiwa salama kwenye Central DB!"}