# ID Check - Backend FastAPI

## Installation
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # puis modifier les valeurs
```

## Base PostgreSQL
```sql
CREATE DATABASE idcheck;
```

## Lancer
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Documentation interactive : http://localhost:8000/docs
Au premier lancement, un admin est créé avec ADMIN_USERNAME / ADMIN_PASSWORD du .env.

## Endpoints
| Méthode | Route | Accès |
|---|---|---|
| POST | /auth/login | public |
| POST | /register | public |
| POST | /check | opérateur/admin |
| GET | /members, POST /members/{id}/approve, /reject | admin |
| GET/POST/DELETE | /blacklist | admin |
| POST | /staff | admin |

## Production
Mettre derrière Nginx avec HTTPS (Let's Encrypt), restreindre CORS à ton domaine, changer SECRET_KEY et le mot de passe admin.
