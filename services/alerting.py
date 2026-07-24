import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL, FROM_NAME
from db import get_hospital_by_id

def send_email_alert(hospital_id: int, patient_name: str, phone: str,
                     symptom: str, risk: str, lat: float, lon: float):
    hospital = get_hospital_by_id(hospital_id)
    if not hospital or "email" not in hospital:
        print(f"Hôpital ID {hospital_id} sans email, alerte non envoyée.")
        return False

    subject = f"ALERTE MATERNITÉ - Patiente {patient_name}"
    body = f"""
Bonjour,

Une patiente a signalé des symptômes via l'application Maternelle Connect.

**Détails :**
- Nom : {patient_name}
- Téléphone : {phone}
- Symptôme déclaré : {symptom}
- Niveau de risque estimé : {risk}
- Localisation GPS : {lat}, {lon}
- Lien carte : https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=16

La patiente a été orientée vers votre établissement.
Merci de la prendre en charge rapidement.

Cordialement,
L'équipe Maternelle Connect
"""
    msg = MIMEMultipart()
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = hospital["email"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(FROM_EMAIL, [hospital["email"]], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Erreur envoi email: {e}")
        return False