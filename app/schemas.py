from typing import Literal, Optional
from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    nom: str = Field(min_length=2, max_length=100)
    prenom: str = Field(min_length=2, max_length=100)
    id_type: Literal["cin", "permis"]
    id_number: str = Field(min_length=4, max_length=50)


class CheckIn(BaseModel):
    id_number: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None


class CheckOut(BaseModel):
    result: Literal["BLACKLIST", "BLACKLIST_POSSIBLE", "MEMBER", "MEMBER_POSSIBLE", "OK"]
    message: str
    needs_confirmation: bool = False
    matched_name: Optional[str] = None
    motif: Optional[str] = None


class BlacklistIn(BaseModel):
    nom: str
    prenom: str
    id_number: Optional[str] = None
    motif: str = Field(min_length=3)


class StaffIn(BaseModel):
    username: str
    password: str = Field(min_length=8)
    role: Literal["operator", "admin"] = "operator"


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
