from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
import csv, io

from db import (
    get_patient, upsert_patient, save_message, get_recent_messages,
    save_alert, get_hospital_by_id, insert_pending_hospital, get_approved_hospitals,
    approve_hospital, reject_hospital, save_feedback, count_patients, count_hospitals,
    count_alerts, count_alerts_today, feedback_positive_rate,
    get_patients_paginated, get_hospitals_paginated, get_alerts_paginated,
    get_alerts_geojson, export_patients, export_alerts,
    get_rules_from_db, save_rules_to_db,
    save_health_record, get_health_records,
    get_appointments, create_appointment,
    save_admin_message, get_unread_admin_messages, mark_admin_message_read,
    get_weekly_tip, upsert_weekly_tip,
    get_all_faq, insert_faq, update_faq, delete_faq,
    get_quiz_questions, get_quiz_question_by_id, insert_quiz_question, save_quiz_result,
    get_admin_user, create_admin_user
)
from services.mistral_conversation import chat_with_mistral, normalize_risk
from services.geoloc import get_nearest_hospitals
from services.alerting import send_email_alert
from services.auth import verify_admin
from fastapi.responses import StreamingResponse, JSONResponse
import traceback

app = FastAPI(title="Maternelle Connect Backend", version="3.0")

# --- Gestionnaire d'erreurs global TEMPORAIRE pour diagnostiquer les 500 silencieux ---
# Affiche le vrai message d'erreur (ex: erreur Supabase/PostgREST) dans la réponse JSON
# au lieu d'un simple "Internal Server Error" sans détail.
# À retirer (ou à restreindre) une fois les problèmes actuels résolus, pour ne pas
# exposer de détails internes en production.
@app.exception_handler(Exception)
async def debug_exception_handler(request, exc):
    tb = traceback.format_exc()
    print(tb)  # visible dans les logs Render
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__, "traceback": tb},
    )

# Modèles
class PatientRegister(BaseModel):
    phone: str
    name: str
    weeks_pregnant: int
    lat: Optional[float] = None
    lon: Optional[float] = None
    location: Optional[str] = None

class HospitalRegister(BaseModel):
    name: str
    lat: float
    lon: float
    phone: str
    email: str
    address: Optional[str] = None

class ChatRequest(BaseModel):
    phone: str
    message: str
    lat: Optional[float] = None
    lon: Optional[float] = None

class AlertRequest(BaseModel):
    phone: str
    hospital_id: int
    symptom: str
    risk: str
    lat: float
    lon: float

class FeedbackRequest(BaseModel):
    phone: str
    useful: bool
    message_id: Optional[int] = None

class HealthRecordRequest(BaseModel):
    phone: str
    weight_kg: Optional[float] = None
    systolic: Optional[int] = None
    diastolic: Optional[int] = None
    vaccine_tetanus: bool = False
    notes: Optional[str] = None

class AdminMessageRequest(BaseModel):
    phone: str
    message: str

class WeeklyTipRequest(BaseModel):
    week: int
    tip_fr: str
    tip_local: Optional[str] = None

class FAQRequest(BaseModel):
    question_fr: str
    answer_fr: str

class QuizQuestionRequest(BaseModel):
    question_fr: str
    options: list
    correct: int

class QuizAnswerRequest(BaseModel):
    phone: str
    question_id: int
    chosen: int

class AdminUserRequest(BaseModel):
    username: str
    password: str
    role: str = "agent"
    hospital_id: Optional[int] = None

# Routes publiques
@app.get("/")
def root():
    return {"message": "Maternelle Connect API v3.0"}

@app.post("/api/register/patient")
def register_patient(data: PatientRegister):
    upsert_patient(data.phone, data.name, data.weeks_pregnant, data.lat, data.lon, data.location)
    return {"status": "ok"}

@app.post("/api/register/hospital")
def register_hospital(data: HospitalRegister):
    insert_pending_hospital(data.name, data.lat, data.lon, data.phone, data.email, data.address)
    return {"status": "ok", "message": "Inscription en attente de validation"}

@app.get("/api/hospitals")
def list_hospitals():
    return get_approved_hospitals()

@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    phone = req.phone
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message vide")

    patient = get_patient(phone)
    patient_name = patient["name"] if patient else "Maman"

    if req.lat is not None and req.lon is not None:
        upsert_patient(phone, lat=req.lat, lon=req.lon)

    history = get_recent_messages(phone, limit=10)
    msg_id = save_message(phone, "user", message)

    reply, risk, updated_history = chat_with_mistral(phone, message, patient_name, history)

    save_message(phone, "assistant", reply)

    hospitals = []
    if req.lat is not None and req.lon is not None and normalize_risk(risk) == "eleve":
        hospitals = get_nearest_hospitals(req.lat, req.lon, 3)

    return {"reply": reply, "risk": risk, "hospitals": hospitals}

@app.post("/api/alert")
async def api_alert(req: AlertRequest):
    hospital = get_hospital_by_id(req.hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hôpital non trouvé")

    patient = get_patient(req.phone)
    patient_name = patient["name"] if patient else "Patiente inconnue"

    success = await send_email_alert(
        hospital_id=req.hospital_id,
        patient_name=patient_name,
        phone=req.phone,
        symptom=req.symptom,
        risk=req.risk,
        lat=req.lat,
        lon=req.lon
    )

    save_alert(req.phone, req.hospital_id, hospital["name"], req.symptom, req.risk, req.lat, req.lon)

    if success:
        return {"status": "ok", "message": "Alerte envoyée avec succès"}
    else:
        raise HTTPException(status_code=500, detail="Échec de l'envoi de l'email")

@app.get("/api/rules")
def get_rules():
    db_rules = get_rules_from_db()
    if db_rules:
        return db_rules
    raise HTTPException(status_code=404, detail="Règles non disponibles")

@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    save_feedback(req.phone, req.useful, req.message_id)
    return {"status": "ok"}

# Health records
@app.post("/api/health-record")
def add_health_record(req: HealthRecordRequest):
    save_health_record(req.phone, req.weight_kg, req.systolic, req.diastolic, req.vaccine_tetanus, req.notes)
    return {"status": "ok"}

@app.get("/api/health-records/{phone}")
def list_health_records(phone: str):
    return get_health_records(phone)

# Appointments
@app.get("/api/appointments/{phone}")
def list_appointments(phone: str):
    return get_appointments(phone)

@app.post("/api/appointments")
def add_appointment(phone: str, due_date: str):
    create_appointment(phone, due_date)
    return {"status": "ok"}

# Admin messages (patient)
@app.get("/api/admin/messages/{phone}")
def list_admin_messages(phone: str):
    return get_unread_admin_messages(phone)

@app.put("/api/admin/messages/{message_id}/read")
def read_admin_message(message_id: int):
    mark_admin_message_read(message_id)
    return {"status": "ok"}

# Weekly tips
@app.get("/api/weekly-tip")
def get_tip(week: int = Query(...)):
    tip = get_weekly_tip(week)
    if tip:
        return tip
    raise HTTPException(status_code=404, detail="Conseil non disponible pour cette semaine")

# FAQ
@app.get("/api/faq")
def list_faq():
    return get_all_faq()

# Quiz
@app.get("/api/quiz")
def get_quiz(limit: int = 5):
    return get_quiz_questions(limit)

@app.post("/api/quiz-answer")
def submit_quiz_answer(req: QuizAnswerRequest):
    question = get_quiz_question_by_id(req.question_id)
    correct = bool(question) and question["correct"] == req.chosen
    save_quiz_result(req.phone, req.question_id, req.chosen, correct)
    return {"correct": correct}

# ------------ ADMIN ENDPOINTS ------------
@app.get("/api/admin/stats", dependencies=[Depends(verify_admin)])
def admin_stats():
    return {
        "total_patients": count_patients(),
        "total_hospitals": count_hospitals(),
        "pending_hospitals": count_hospitals("pending"),
        "approved_hospitals": count_hospitals("approved"),
        "total_alerts": count_alerts(),
        "alerts_today": count_alerts_today(),
        "feedback_positive_rate": feedback_positive_rate()
    }

@app.get("/api/admin/patients", dependencies=[Depends(verify_admin)])
def admin_patients(search: str = Query(None), limit: int = 20, offset: int = 0):
    return get_patients_paginated(limit, offset, search)

@app.get("/api/admin/patients/{phone}/history", dependencies=[Depends(verify_admin)])
def patient_history(phone: str):
    return get_recent_messages(phone, 100)

@app.get("/api/admin/hospitals", dependencies=[Depends(verify_admin)])
def admin_hospitals(status: str = Query(None), limit: int = 20, offset: int = 0):
    return get_hospitals_paginated(limit, offset, status)

@app.put("/api/admin/hospitals/{id}/approve", dependencies=[Depends(verify_admin)])
def approve_hospital_route(id: int):
    approve_hospital(id)
    return {"status": "ok"}

@app.put("/api/admin/hospitals/{id}/reject", dependencies=[Depends(verify_admin)])
def reject_hospital_route(id: int):
    reject_hospital(id)
    return {"status": "ok"}

@app.get("/api/admin/alerts", dependencies=[Depends(verify_admin)])
def admin_alerts(limit: int = 20, offset: int = 0):
    return get_alerts_paginated(limit, offset)

@app.get("/api/admin/alerts/geojson", dependencies=[Depends(verify_admin)])
def alerts_geojson():
    return get_alerts_geojson()

@app.get("/api/admin/export/patients", dependencies=[Depends(verify_admin)])
def export_patients_csv():
    data = export_patients()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["phone","name","weeks_pregnant","lat","lon","created_at"])
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=patients.csv"})

@app.get("/api/admin/export/alerts", dependencies=[Depends(verify_admin)])
def export_alerts_csv():
    data = export_alerts()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id","phone","hospital_name","symptom","risk","lat","lon","sent_at"])
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=alerts.csv"})

@app.get("/api/admin/rules", dependencies=[Depends(verify_admin)])
def admin_get_rules():
    return get_rules()

@app.put("/api/admin/rules", dependencies=[Depends(verify_admin)])
def admin_update_rules(payload: dict):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Le contenu doit être un objet JSON valide.")
    if not save_rules_to_db(payload):
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde en base.")
    return {"status": "ok", "message": "Règles mises à jour avec succès."}

@app.post("/api/admin/send-message", dependencies=[Depends(verify_admin)])
def admin_send_message(req: AdminMessageRequest):
    save_admin_message(req.phone, req.message)
    return {"status": "ok"}

@app.post("/api/admin/weekly-tip", dependencies=[Depends(verify_admin)])
def admin_upsert_weekly_tip(req: WeeklyTipRequest):
    upsert_weekly_tip(req.week, req.tip_fr, req.tip_local)
    return {"status": "ok"}

@app.post("/api/admin/faq", dependencies=[Depends(verify_admin)])
def admin_add_faq(req: FAQRequest):
    insert_faq(req.question_fr, req.answer_fr)
    return {"status": "ok"}

@app.put("/api/admin/faq/{faq_id}", dependencies=[Depends(verify_admin)])
def admin_update_faq(faq_id: int, req: FAQRequest):
    update_faq(faq_id, req.question_fr, req.answer_fr)
    return {"status": "ok"}

@app.delete("/api/admin/faq/{faq_id}", dependencies=[Depends(verify_admin)])
def admin_delete_faq(faq_id: int):
    delete_faq(faq_id)
    return {"status": "ok"}

@app.post("/api/admin/quiz", dependencies=[Depends(verify_admin)])
def admin_add_quiz_question(req: QuizQuestionRequest):
    insert_quiz_question(req.question_fr, req.options, req.correct)
    return {"status": "ok"}

@app.post("/api/admin/create-user", dependencies=[Depends(verify_admin)])
def admin_create_user(req: AdminUserRequest):
    import hashlib
    pwd_hash = hashlib.sha256(req.password.encode()).hexdigest()
    existing = get_admin_user(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur déjà existant")
    create_admin_user(req.username, pwd_hash, req.role, req.hospital_id)
    return {"status": "ok"}
