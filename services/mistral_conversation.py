import traceback
import re
from mistralai import Mistral
from config import MISTRAL_API_KEY

client = Mistral(api_key=MISTRAL_API_KEY)

SYSTEM_PROMPT = """Tu es une sage-femme expérimentée et bienveillante qui dialogue avec une femme enceinte au Cameroun. 
Ton rôle est de recueillir les symptômes, poser des questions complémentaires pour évaluer la gravité, puis fournir un conseil adapté.

**Directives importantes :**
- Sois chaleureuse, rassurante, et utilise un français simple.
- Si le symptôme est clairement inquiétant (saignement, maux de tête sévères, perte de vision, absence de mouvements du bébé après 28 semaines), donne immédiatement un conseil d'urgence et indique que l'application va proposer les hôpitaux les plus proches.
- Ne dépasse pas 3-4 questions au total avant de donner une première évaluation.
- Lorsque tu estimes avoir assez d'informations, conclus par un message rassurant qui inclut le niveau de risque entre les balises <risk> (valeur : faible, moyen, élevé).
- N'invente jamais de diagnostic médical. Rappelle que tu es un assistant d'orientation, pas un médecin.

Format de réponse : 
<risk>niveau</risk>
Ton message ici...
"""

def chat_with_mistral(phone: str, user_message: str, patient_name: str, history: list = None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=messages,
            max_tokens=400,
            temperature=0.7
        )
        full_reply = response.choices[0].message.content

        risk = "faible"
        match = re.search(r'<risk>(.*?)</risk>', full_reply, re.IGNORECASE)
        if match:
            risk = match.group(1).strip().lower()
            if risk not in ("faible", "moyen", "élevé", "eleve"):
                risk = "faible"

        reply_clean = re.sub(r'<risk>.*?</risk>', '', full_reply, flags=re.DOTALL).strip()

        if history is None:
            history = []
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": full_reply})
        if len(history) > 12:
            history = history[-12:]

        return reply_clean, risk, history

    except Exception as e:
        print("=" * 40)
        print("ERREUR MISTRAL BACKEND")
        traceback.print_exc()
        print("=" * 40)

        reply = "Je rencontre des difficultés techniques. Si vous ressentez un symptôme inquiétant, rendez-vous immédiatement au centre de santé le plus proche."
        if history is None:
            history = []
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        return reply, "eleve", history