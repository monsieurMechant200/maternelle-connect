from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
from typing import Optional, List

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ----- Patients -----
def get_patient(phone: str):
    if not supabase: return None
    res = supabase.table("patients").select("*").eq("phone", phone).execute()
    return res.data[0] if res.data else None

def upsert_patient(phone: str, name: str = None, weeks: int = None,
                   lat: float = None, lon: float = None, location: str = None):
    if not supabase: return None
    data = {"phone": phone}
    if name is not None: data["name"] = name
    if weeks is not None: data["weeks_pregnant"] = weeks
    if lat is not None: data["lat"] = lat
    if lon is not None: data["lon"] = lon
    if location is not None: data["location"] = location
    return supabase.table("patients").upsert(data).execute()

# ----- Hôpitaux -----
def get_approved_hospitals() -> List[dict]:
    if not supabase: return []
    res = supabase.table("hospitals").select("*").eq("status", "approved").execute()
    return res.data if res.data else []

def get_hospital_by_id(hospital_id: int):
    if not supabase: return None
    res = supabase.table("hospitals").select("*").eq("id", hospital_id).execute()
    return res.data[0] if res.data else None

def insert_pending_hospital(name: str, lat: float, lon: float, phone: str, email: str, address: str = None):
    if not supabase: return None
    return supabase.table("hospitals").insert({
        "name": name, "lat": lat, "lon": lon, "phone": phone,
        "email": email, "address": address, "status": "pending"
    }).execute()

def approve_hospital(hospital_id: int):
    if not supabase: return None
    return supabase.table("hospitals").update({"status": "approved"}).eq("id", hospital_id).execute()

def reject_hospital(hospital_id: int):
    if not supabase: return None
    return supabase.table("hospitals").update({"status": "rejected"}).eq("id", hospital_id).execute()

def count_hospitals(status=None):
    if not supabase: return 0
    query = supabase.table("hospitals").select("count", count="exact")
    if status:
        query = query.eq("status", status)
    res = query.execute()
    return res.count

def get_hospitals_paginated(limit=20, offset=0, status=None):
    if not supabase: return []
    query = supabase.table("hospitals").select("*").order("created_at", desc=True).limit(limit).offset(offset)
    if status:
        query = query.eq("status", status)
    res = query.execute()
    return res.data if res.data else []

# ----- Messages -----
def save_message(phone: str, role: str, content: str) -> Optional[int]:
    if not supabase: return None
    res = supabase.table("messages").insert({
        "phone": phone, "role": role, "content": content
    }).execute()
    return res.data[0]["id"] if res.data else None

def get_recent_messages(phone: str, limit: int = 10):
    if not supabase: return []
    res = supabase.table("messages") \
        .select("role, content") \
        .eq("phone", phone) \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute()
    messages = res.data[::-1] if res.data else []
    return [{"role": m["role"], "content": m["content"]} for m in messages]

# ----- Alertes -----
def save_alert(phone: str, hospital_id: int, hospital_name: str,
               symptom: str, risk: str, lat: float, lon: float):
    if not supabase: return None
    return supabase.table("alerts").insert({
        "phone": phone, "hospital_id": hospital_id,
        "hospital_name": hospital_name, "symptom": symptom,
        "risk": risk, "lat": lat, "lon": lon
    }).execute()

def count_alerts(since=None):
    if not supabase: return 0
    query = supabase.table("alerts").select("count", count="exact")
    if since:
        query = query.gte("sent_at", since)
    res = query.execute()
    return res.count

def count_alerts_today():
    from datetime import datetime
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return count_alerts(since=today)

def get_alerts_paginated(limit=20, offset=0):
    if not supabase: return []
    res = supabase.table("alerts").select("*").order("sent_at", desc=True).limit(limit).offset(offset).execute()
    return res.data if res.data else []

def get_alerts_geojson():
    if not supabase: return {"type": "FeatureCollection", "features": []}
    res = supabase.table("alerts").select("*").execute()
    features = []
    for alert in res.data:
        if alert.get("lat") and alert.get("lon"):
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [alert["lon"], alert["lat"]]
                },
                "properties": {
                    "phone": alert["phone"],
                    "hospital_name": alert["hospital_name"],
                    "symptom": alert["symptom"],
                    "risk": alert["risk"],
                    "sent_at": alert["sent_at"]
                }
            })
    return {"type": "FeatureCollection", "features": features}

# ----- Feedbacks -----
def save_feedback(phone: str, useful: bool, message_id: int = None):
    if not supabase: return None
    return supabase.table("feedbacks").insert({
        "phone": phone, "useful": useful, "message_id": message_id
    }).execute()

def feedback_positive_rate():
    if not supabase: return 0.0
    total_res = supabase.table("feedbacks").select("count", count="exact").execute()
    positive_res = supabase.table("feedbacks").select("count", count="exact").eq("useful", True).execute()
    if total_res.count == 0:
        return 0.0
    return round(positive_res.count / total_res.count * 100, 1)

# ----- Règles cliniques -----
def get_rules_from_db():
    if not supabase: return None
    res = supabase.table("rules").select("content").eq("id", 1).execute()
    if res.data:
        return res.data[0]["content"]
    return None

def save_rules_to_db(content: dict):
    if not supabase: return False
    supabase.table("rules").upsert({
        "id": 1,
        "content": content,
        "updated_at": "now()"
    }).execute()
    return True

# ----- Patients (admin) -----
def count_patients():
    if not supabase: return 0
    res = supabase.table("patients").select("count", count="exact").execute()
    return res.count

def get_patients_paginated(limit=20, offset=0, search=""):
    if not supabase: return []
    query = supabase.table("patients").select("*").order("created_at", desc=True).limit(limit).offset(offset)
    if search:
        query = query.ilike("name", f"%{search}%")
    res = query.execute()
    return res.data if res.data else []

def export_patients():
    if not supabase: return []
    res = supabase.table("patients").select("*").execute()
    return res.data if res.data else []

def export_alerts():
    if not supabase: return []
    res = supabase.table("alerts").select("*").execute()
    return res.data if res.data else []

# ----- Health Records -----
def save_health_record(phone: str, weight: float = None, systolic: int = None, diastolic: int = None, vaccine: bool = False, notes: str = None):
    if not supabase: return None
    return supabase.table("health_records").insert({
        "phone": phone, "weight_kg": weight, "systolic": systolic,
        "diastolic": diastolic, "vaccine_tetanus": vaccine, "notes": notes
    }).execute()

def get_health_records(phone: str):
    if not supabase: return []
    res = supabase.table("health_records").select("*").eq("phone", phone).order("record_date", desc=True).execute()
    return res.data if res.data else []

# ----- Appointments -----
def get_appointments(phone: str):
    if not supabase: return []
    res = supabase.table("appointments").select("*").eq("phone", phone).order("due_date").execute()
    return res.data if res.data else []

def create_appointment(phone: str, due_date: str):
    if not supabase: return None
    return supabase.table("appointments").insert({"phone": phone, "due_date": due_date}).execute()

# ----- Admin Messages -----
def save_admin_message(phone: str, message: str):
    if not supabase: return None
    return supabase.table("admin_messages").insert({"phone": phone, "message": message}).execute()

def get_unread_admin_messages(phone: str):
    if not supabase: return []
    res = supabase.table("admin_messages").select("*").eq("phone", phone).eq("read", False).order("created_at", desc=True).execute()
    return res.data if res.data else []

def mark_admin_message_read(message_id: int):
    if not supabase: return None
    return supabase.table("admin_messages").update({"read": True}).eq("id", message_id).execute()

# ----- Weekly Tips -----
def get_weekly_tip(week: int):
    if not supabase: return None
    res = supabase.table("weekly_tips").select("*").eq("week", week).execute()
    return res.data[0] if res.data else None

def upsert_weekly_tip(week: int, tip_fr: str, tip_local: str = None):
    if not supabase: return None
    data = {"week": week, "tip_fr": tip_fr, "tip_local": tip_local}
    return supabase.table("weekly_tips").upsert(data).execute()

# ----- FAQ -----
def get_all_faq():
    if not supabase: return []
    res = supabase.table("faq").select("*").execute()
    return res.data if res.data else []

def insert_faq(question: str, answer: str):
    if not supabase: return None
    return supabase.table("faq").insert({"question_fr": question, "answer_fr": answer}).execute()

def update_faq(faq_id: int, question: str, answer: str):
    if not supabase: return None
    return supabase.table("faq").update({"question_fr": question, "answer_fr": answer}).eq("id", faq_id).execute()

def delete_faq(faq_id: int):
    if not supabase: return None
    return supabase.table("faq").delete().eq("id", faq_id).execute()

# ----- Quiz -----
def get_quiz_questions(limit: int = 5):
    if not supabase: return []
    res = supabase.table("quiz_questions").select("*").limit(limit).execute()
    return res.data if res.data else []

def get_quiz_question_by_id(question_id: int):
    if not supabase: return None
    res = supabase.table("quiz_questions").select("*").eq("id", question_id).execute()
    return res.data[0] if res.data else None

def insert_quiz_question(question: str, options: list, correct: int):
    if not supabase: return None
    return supabase.table("quiz_questions").insert({
        "question_fr": question, "options": options, "correct": correct
    }).execute()

def save_quiz_result(phone: str, question_id: int, chosen: int, correct: bool):
    if not supabase: return None
    return supabase.table("quiz_results").insert({
        "phone": phone, "question_id": question_id, "chosen": chosen, "correct": correct
    }).execute()

# ----- Admin Users -----
def get_admin_user(username: str):
    if not supabase: return None
    res = supabase.table("admin_users").select("*").eq("username", username).execute()
    return res.data[0] if res.data else None

def create_admin_user(username: str, password_hash: str, role: str = "agent", hospital_id: int = None):
    if not supabase: return None
    return supabase.table("admin_users").insert({
        "username": username, "password_hash": password_hash, "role": role, "hospital_id": hospital_id
    }).execute()
