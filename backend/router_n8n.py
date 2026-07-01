"""
Tokat Dijital Çarşı — n8n köprü router'ı
=========================================
n8n akışlarının çağırdığı uçlar + n8n'e giden olay bildirimleri.
Mevcut BotYonetici ve Esnaf modeline bağlanır.

main.py'ye eklemek için (app tanımından sonra):
    from router_n8n import router as n8n_router
    app.include_router(n8n_router)

Ortam değişkenleri:
    BACKEND_API_KEY : n8n ile paylaşılan gizli anahtar (X-API-Key). Boşsa doğrulama kapalı.
    N8N_SIPARIS_URL : https://<n8n>/webhook/tokat-siparis
    N8N_KURYE_URL   : https://<n8n>/webhook/tokat-kurye
"""

import asyncio
import json
import os
import secrets
import urllib.request
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import Esnaf
from bot_engine import BotYonetici

BACKEND_API_KEY = os.getenv("BACKEND_API_KEY", "")
N8N_SIPARIS_URL = os.getenv("N8N_SIPARIS_URL", "")
N8N_KURYE_URL = os.getenv("N8N_KURYE_URL", "")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def dogrula_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """n8n her istekte X-API-Key gönderir; BACKEND_API_KEY boşsa doğrulama atlanır (dev)."""
    if BACKEND_API_KEY and x_api_key != BACKEND_API_KEY:
        raise HTTPException(status_code=401, detail="Gecersiz API anahtari")


router = APIRouter(prefix="/api", tags=["n8n"], dependencies=[Depends(dogrula_api_key)])


# ---------------------------------------------------------------------------
# 1) POST /api/whatsapp/handle  —  gelen mesajı mevcut bota ver, yanıt döndür
# ---------------------------------------------------------------------------
class WhatsAppMesajIn(BaseModel):
    from_: str = Field(default="", alias="from")
    name: str = ""
    text: str = ""

    model_config = {"populate_by_name": True}


class WhatsAppYanit(BaseModel):
    reply: str


@router.post("/whatsapp/handle", response_model=WhatsAppYanit)
def whatsapp_handle(mesaj: WhatsAppMesajIn, db: Session = Depends(get_db)):
    """n8n Workflow 1 → {from, name, text}; BotYonetici yanıtını {reply} olarak döner."""
    bot = BotYonetici(db)
    cevap = bot.telgraf_mesaj(mesaj.text or "")
    return WhatsAppYanit(reply=cevap.get("mesaj", "Anlayamadim, tekrar dener misiniz?"))


# ---------------------------------------------------------------------------
# 2) POST /api/esnaf  —  n8n onboarding formundan yeni esnaf kaydı
# ---------------------------------------------------------------------------
class EsnafIn(BaseModel):
    isim: str = ""          # sahip adı
    dukkan: str             # firma adı
    telefon: str
    kategori: str = ""      # dukkan_turu
    email: Optional[str] = None
    sifre: Optional[str] = None


class EsnafOut(BaseModel):
    ok: bool
    id: int
    gecici_sifre: Optional[str] = None   # sifre verilmediyse üretilen geçici şifre


@router.post("/esnaf", response_model=EsnafOut)
def esnaf_olustur(data: EsnafIn, db: Session = Depends(get_db)):
    if not data.dukkan or not data.telefon:
        raise HTTPException(status_code=400, detail="Dukkan ve telefon zorunludur")
    email = data.email or f"{data.telefon}@tokatcarsi.local"
    if db.query(Esnaf).filter((Esnaf.email == email) | (Esnaf.telefon == data.telefon)).first():
        raise HTTPException(status_code=400, detail="Bu email veya telefon zaten kayitli")
    uretilen = None if data.sifre else secrets.token_urlsafe(6)
    sifre = data.sifre or uretilen
    esnaf = Esnaf(
        firma_adi=data.dukkan,
        sahip_adi=data.isim or data.dukkan,
        telefon=data.telefon,
        email=email,
        sifre_hash=pwd_context.hash(sifre),
        dukkan_turu=data.kategori,
    )
    db.add(esnaf)
    db.commit()
    db.refresh(esnaf)
    return EsnafOut(ok=True, id=esnaf.id, gecici_sifre=uretilen)


# ---------------------------------------------------------------------------
# 3) POST /api/kurye/en-yakin  —  (ileri faz) en yakın boştaki kurye
# ---------------------------------------------------------------------------
class KuryeIstek(BaseModel):
    alis_adres: str = ""
    teslim_konum: Optional[str] = None   # "enlem,boylam" ya da adres


class KuryeYanit(BaseModel):
    kurye_phone: str = ""
    kurye_adi: str = ""
    mesafe_km: float = 0.0
    ucret: int = 0


@router.post("/kurye/en-yakin", response_model=KuryeYanit)
def kurye_en_yakin(istek: KuryeIstek, db: Session = Depends(get_db)):
    """
    TODO: Kurye modülü henüz veri modelinde yok (yol haritası: Ay 6+).
    Kurye modeli eklendiğinde boştaki kuryeler arasından teslim_konum'a
    en yakınını haversine ile seç. Şu an boş dönüyor → n8n operatörü uyarır.
    """
    return KuryeYanit()


# ===========================================================================
# n8n'e giden olay bildirimleri (backend içinden çağır) — stdlib, ek bağımlılık yok
# ===========================================================================
def _post_json(url: str, payload: dict) -> None:
    if not url:
        return
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except Exception:
        pass  # bildirim best-effort; ana akışı bloklamasın


async def n8n_siparis_bildir(
    event: str, esnaf_phone: str = "", customer_phone: str = "",
    customer_name: str = "", ozet: str = "", tutar: str = "",
) -> None:
    """Sipariş/ödeme olayında Workflow 2'yi tetikle. event: 'yeni_siparis' | 'odeme_alindi'."""
    await asyncio.to_thread(_post_json, N8N_SIPARIS_URL, {
        "event": event, "esnaf_phone": esnaf_phone, "customer_phone": customer_phone,
        "customer_name": customer_name, "ozet": ozet, "tutar": tutar,
    })


async def n8n_kurye_iste(
    siparis_id: str, esnaf_adi: str, alis_adres: str,
    teslim_adres: str, teslim_konum: str = "",
) -> None:
    """Yeni teslimat gerektiğinde Workflow 4'ü tetikle."""
    await asyncio.to_thread(_post_json, N8N_KURYE_URL, {
        "siparis_id": siparis_id, "esnaf_adi": esnaf_adi, "alis_adres": alis_adres,
        "teslim_adres": teslim_adres, "teslim_konum": teslim_konum,
    })
