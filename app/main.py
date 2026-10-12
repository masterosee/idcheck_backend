from typing import Optional
import os
import pathlib
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db, SessionLocal
from .models import User, Member, Blacklist, AuditLog
from .schemas import (RegisterIn, CheckIn, CheckOut, BlacklistIn, StaffIn, TokenOut)
from .auth import (hash_password, verify_password, create_token, current_user, admin_only)
from .utils import norm_id, norm_name
from .pages import INSCRIPTION_HTML

THRESHOLD = int(os.getenv("FUZZY_THRESHOLD", "88"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:  # crée le premier admin
        if not db.scalar(select(User).limit(1)):
            db.add(User(username=os.getenv("ADMIN_USERNAME", "admin"),
                        password_hash=hash_password(os.getenv("ADMIN_PASSWORD", "ChangeMoi123!")),
                        role="admin"))
            db.commit()
    yield


app = FastAPI(title="ID Check API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def log(db: Session, user_id, action, detail=""):
    db.add(AuditLog(user_id=user_id, action=action, detail=detail))


# ---------- Pages publiques ----------
@app.get("/health", include_in_schema=False)
def health():
    return {"ok": True}


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/inscription")


_FOND = pathlib.Path(__file__).parent / "fond.jpg"


@app.get("/fond.jpg", include_in_schema=False)
def fond():
    return FileResponse(_FOND, media_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=86400"})


@app.get("/inscription", response_class=HTMLResponse, include_in_schema=False)
def inscription_page():
    return INSCRIPTION_HTML


_reg_hits = defaultdict(deque)


def _rate_limit(request: Request, limit: int = 30, window: int = 3600):
    """Limite simple par IP (large, car les réseaux mobiles partagent des IP)."""
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")
    now = time.time()
    q = _reg_hits[ip]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "Trop de tentatives. Réessayez plus tard.")
    q.append(now)


# ---------- Auth ----------
@app.post("/auth/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == form.username))
    if not user or not user.active or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Identifiants incorrects")
    return TokenOut(access_token=create_token(user), role=user.role)


@app.post("/staff", status_code=201)
def create_staff(data: StaffIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == data.username)):
        raise HTTPException(409, "Nom d'utilisateur déjà pris")
    db.add(User(username=data.username, password_hash=hash_password(data.password), role=data.role))
    log(db, admin.id, "staff_create", data.username)
    db.commit()
    return {"ok": True}


# ---------- Inscription publique ----------
@app.post("/register", status_code=201)
def register(data: RegisterIn, request: Request, db: Session = Depends(get_db)):
    _rate_limit(request)
    idn = norm_id(data.id_number)
    if len(idn) < 4:
        raise HTTPException(422, "Numéro d'identification invalide")
    if db.scalar(select(Member).where(Member.id_norm == idn)):
        raise HTTPException(409, "Ce numéro est déjà inscrit")
    m = Member(nom=data.nom.strip(), prenom=data.prenom.strip(),
               nom_norm=norm_name(f"{data.prenom} {data.nom}"),
               id_type=data.id_type, id_number=data.id_number.strip(), id_norm=idn)
    db.add(m)
    log(db, None, "register", idn)
    db.commit()
    return {"message": "Inscription reçue, en attente de validation."}


# ---------- Gestion des membres (admin) ----------
@app.get("/members")
def list_members(status: Optional[str] = None, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    q = select(Member).order_by(Member.created_at.desc())
    if status:
        q = q.where(Member.status == status)
    return [{"id": m.id, "nom": m.nom, "prenom": m.prenom, "id_type": m.id_type,
             "id_number": m.id_number, "status": m.status, "created_at": m.created_at}
            for m in db.scalars(q)]


def _set_status(member_id: int, status: str, admin: User, db: Session):
    m = db.get(Member, member_id)
    if not m:
        raise HTTPException(404, "Membre introuvable")
    m.status = status
    log(db, admin.id, f"member_{status}", m.id_norm)
    db.commit()
    return {"ok": True, "status": status}


@app.post("/members/{member_id}/approve")
def approve(member_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    return _set_status(member_id, "approved", admin, db)


@app.post("/members/{member_id}/reject")
def reject(member_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    return _set_status(member_id, "rejected", admin, db)


# ---------- Liste noire (admin) ----------
@app.get("/blacklist")
def list_blacklist(admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [{"id": b.id, "nom": b.nom, "prenom": b.prenom, "id_number": b.id_number,
             "motif": b.motif, "created_at": b.created_at} for b in db.scalars(select(Blacklist))]


@app.post("/blacklist", status_code=201)
def add_blacklist(data: BlacklistIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    b = Blacklist(nom=data.nom.strip(), prenom=data.prenom.strip(),
                  nom_norm=norm_name(f"{data.prenom} {data.nom}"),
                  id_number=data.id_number, id_norm=norm_id(data.id_number) if data.id_number else None,
                  motif=data.motif, added_by=admin.id)
    db.add(b)
    log(db, admin.id, "blacklist_add", f"{data.prenom} {data.nom} | {data.motif}")
    db.commit()
    return {"id": b.id}


@app.delete("/blacklist/{bid}")
def remove_blacklist(bid: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    b = db.get(Blacklist, bid)
    if not b:
        raise HTTPException(404, "Introuvable")
    log(db, admin.id, "blacklist_remove", f"{b.prenom} {b.nom}")
    db.delete(b)
    db.commit()
    return {"ok": True}


# ---------- Vérification (scan) ----------
def _best_name_match(name_norm: str, rows):
    best, score = None, 0
    for r in rows:
        s = fuzz.token_sort_ratio(name_norm, r.nom_norm)
        if s > score:
            best, score = r, s
    return (best, score) if score >= THRESHOLD else (None, 0)


@app.post("/check", response_model=CheckOut)
def check(data: CheckIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    idn = norm_id(data.id_number) if data.id_number else ""
    name = norm_name(f"{data.prenom or ''} {data.nom or ''}")
    if not idn and not name:
        raise HTTPException(422, "Fournir un numéro ou un nom")

    blacklist = list(db.scalars(select(Blacklist)))
    members = list(db.scalars(select(Member).where(Member.status == "approved")))

    # 1) Liste noire d'abord : numéro exact
    if idn:
        for b in blacklist:
            if b.id_norm and b.id_norm == idn:
                log(db, user.id, "check_blacklist", idn); db.commit()
                return CheckOut(result="BLACKLIST", message="LISTE NOIRE",
                                matched_name=f"{b.prenom} {b.nom}", motif=b.motif)
    # 2) Liste noire : nom approchant -> confirmation requise
    if name:
        b, score = _best_name_match(name, blacklist)
        if b:
            log(db, user.id, "check_blacklist_possible", f"{name} ~ {b.nom_norm} ({score})"); db.commit()
            return CheckOut(result="BLACKLIST_POSSIBLE", needs_confirmation=True,
                            message="Correspondance possible avec la liste noire, vérifier manuellement",
                            matched_name=f"{b.prenom} {b.nom}", motif=b.motif)
    # 3) Membre : numéro exact
    if idn:
        for m in members:
            if m.id_norm == idn:
                return CheckOut(result="MEMBER", message="MEMBRE", matched_name=f"{m.prenom} {m.nom}")
    # 4) Membre : nom approchant
    if name:
        m, score = _best_name_match(name, members)
        if m:
            return CheckOut(result="MEMBER_POSSIBLE", needs_confirmation=True,
                            message="Membre probable, vérifier le numéro", matched_name=f"{m.prenom} {m.nom}")
    return CheckOut(result="OK", message="OK")
