from fastapi import Header, HTTPException, Query
from config import ADMIN_KEY

def verify_admin(x_admin_key: str = Header(None), admin_key_query: str = Query(None)):
    key = x_admin_key or admin_key_query
    if key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    return True