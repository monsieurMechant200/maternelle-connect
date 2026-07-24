# Maternelle Connect - Backend

Backend de l'application **Maternelle Connect**, un assistant conversationnel de triage obstétrical destiné aux femmes enceintes des zones périurbaines et rurales du Cameroun.  
Il fournit une API REST qui alimente l'application mobile et le tableau de bord administrateur.

## Fonctionnalités

- **Agent conversationnel IA** : dialogue avec la patiente via Mistral (modèle `mistral-small-latest` gratuit).
- **Géolocalisation** : suggestion automatique des hôpitaux les plus proches (distance Haversine).
- **Alertes email** aux centres de santé en cas de symptôme grave.
- **Inscription dynamique des hôpitaux** (validation administrateur obligatoire).
- **Règles cliniques modifiables** depuis le dashboard (stockées en base PostgreSQL).
- **Suivi de grossesse** : poids, tension, vaccination, rendez-vous.
- **Messagerie agent → patiente** : le personnel de santé peut envoyer des messages aux patientes.
- **FAQ et quiz éducatif** intégrés.
- **Statistiques avancées** et **exports CSV** pour les administrateurs.
- **Administration sécurisée** par clé API (superadmin / agent).

## Stack technique

| Composant       | Technologie                                      |
|-----------------|--------------------------------------------------|
| API             | FastAPI (Python 3.9+)                            |
| Base de données | Supabase (PostgreSQL)                            |
| IA              | Mistral AI (API gratuite)                        |
| Email           | Brevo (SMTP gratuit, 300 emails/jour)            |
| Géocodage       | OpenStreetMap / Nominatim (gratuit)              |
| Déploiement     | Render (gratuit)                                 |

## Déploiement rapide (Render)

1. Forker ou cloner ce dépôt.
2. Créer un projet sur [Supabase](https://supabase.com) et exécuter le fichier `schema.sql` pour créer les tables.
3. Créer un compte [Mistral AI](https://console.mistral.ai) et générer une clé API.
4. Créer un compte [Brevo](https://www.brevo.com) pour les emails (gratuit).
5. Copier le fichier `.env.example` en `.env` et remplir toutes les variables.
6. Déployer sur Render :
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Ajouter les variables d'environnement depuis `.env`.

## Développement local

```bash
git clone <url-du-dépôt>
cd maternel-backend
python -m venv venv
source venv/bin/activate   # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # puis modifier .env
uvicorn main:app --reload
```

L'interface Swagger est disponible sur `http://127.0.0.1:8000/docs`.

## Structure du projet

```
maternel-backend/
├── main.py              # Application FastAPI et toutes les routes
├── config.py            # Chargement des variables d'environnement
├── db.py                # Fonctions d'accès à Supabase
├── rules.json           # Règles cliniques de secours (synchronisées avec la DB)
├── schema.sql           # Script de création des tables PostgreSQL
├── requirements.txt     # Dépendances Python
├── services/
│   ├── auth.py          # Vérification de la clé admin
│   ├── mistral_conversation.py  # Dialogue avec l'IA
│   ├── geoloc.py        # Géocodage et calcul de distance
│   └── alerting.py      # Envoi d'emails d'alerte
└── ...
```

## Endpoints principaux

- `POST /api/chat` - Envoyer un symptôme et recevoir une réponse de l'IA.
- `POST /api/alert` - Déclencher une alerte vers un hôpital.
- `GET /api/hospitals` - Liste des hôpitaux approuvés.
- `GET/PUT /api/admin/rules` - Lire/modifier les règles cliniques (admin).
- `GET /api/admin/stats` - Statistiques (admin).
- `GET /api/admin/export/patients` - Export CSV des patientes (admin).
- `GET /api/rules` - Règles publiques (pour l'application mobile).

Voir la documentation complète sur `/docs`.

## Contribution

Ce projet est développé dans le cadre d’un partenariat pilote avec un centre de santé partenaire.  
Les contributions (remontées terrain, améliorations des règles cliniques, nouvelles fonctionnalités) sont les bienvenues.  
Veuillez ouvrir une issue avant de proposer une pull request.

## Contact

Pour toute question, contacter l’équipe DataIkos [notre site](https://dataikos.netlify.app).
