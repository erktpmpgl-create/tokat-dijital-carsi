import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from database import engine, Base, get_db, SessionLocal
from models import Esnaf, Islem, Urun, Cari, Egitim, EgitimProgress, WhatsAppMesaj

SECRET_KEY = os.getenv("SECRET_KEY", "tokat-dijital-carsi-gizli-anahtar-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(esnaf_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE)
    return jwt.encode({"sub": str(esnaf_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_esnaf(creds: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        esnaf_id = int(payload["sub"])
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Gecersiz token")
    esnaf = db.query(Esnaf).filter(Esnaf.id == esnaf_id).first()
    if not esnaf:
        raise HTTPException(status_code=401, detail="Esnaf bulunamadi")
    return esnaf


class EsnafKayit(BaseModel):
    firma_adi: str
    sahip_adi: str
    telefon: str
    email: str
    sifre: str
    dukkan_turu: str = ""


class EsnafGiris(BaseModel):
    email: str
    sifre: str


class EsnafCevap(BaseModel):
    id: int
    firma_adi: str
    sahip_adi: str
    telefon: str
    email: str
    dukkan_turu: str
    sehir: str
    ilce: str
    aktif: bool
    premium: bool
    profil_fotografi: Optional[str] = None
    aciklama: Optional[str] = None

    class Config:
        from_attributes = True


class TokenCevap(BaseModel):
    access_token: str
    esnaf: EsnafCevap


class IslemInput(BaseModel):
    tur: str
    kategori: str
    tutar: float
    aciklama: Optional[str] = None
    odeme_yontemi: str = "nakit"
    musteri_adi: str = ""
    musteri_telefon: str = ""
    fatura_no: str = ""
    tarih: Optional[str] = None


class UrunInput(BaseModel):
    ad: str
    kategori: str = ""
    fiyat: float = 0.0
    birim: str = "adet"
    stok: int = 0
    aciklama: Optional[str] = None


class EsnafGuncelle(BaseModel):
    firma_adi: Optional[str] = None
    sahip_adi: Optional[str] = None
    telefon: Optional[str] = None
    dukkan_turu: Optional[str] = None
    sehir: Optional[str] = None
    ilce: Optional[str] = None
    aciklama: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_egitim(db=SessionLocal())
    yield


app = FastAPI(title="Tokat Dijital Carsi API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# n8n köprü uçları (/api/whatsapp/handle, /api/esnaf, /api/kurye/en-yakin)
from router_n8n import router as n8n_router
app.include_router(n8n_router)


def _seed_egitim(db: Session):
    if db.query(Egitim).count() > 0:
        return
    dersler = [
        ("Dijital Pazarlamaya Giris", "pazarlama",
         "Dijital pazarlama nedir? Esnaf icin sosyal medya kullanimi, WhatsApp pazarlamasi, hedef kitle belirleme. "
         "Bu derste isletmenizi dijitalde nasil buyuteceginizi ogreneceksiniz.",
         "", 15, "baslangic", 1),
        ("On Muhasebe Temelleri", "muhasebe",
         "Gelir-gider takibi, fatura kesme, cari hesap yonetimi. Her esnafin bilmesi gereken temel muhasebe "
         "prensipleri ve Tokat Dijital Carsi panelinde muhasebe kullanimi.",
         "", 20, "baslangic", 2),
        ("E-Ticaret ve Online Satis", "pazarlama",
         "Urunlerinizi dijital vitrinde sergileme, online siparis yonetimi, stok takibi. "
         "Komisyonsuz satis modeli ile kazancinizi artirin.",
         "", 18, "orta", 3),
        ("Musteri Iliskileri Yonetimi", "pazarlama",
         "Musteri memnuniyeti, sadakat programlari, sikayet yonetimi. "
         "Verileriniz sizin musteri lerinizi taniyin ve buyuyun.",
         "", 12, "baslangic", 4),
        ("Finansal Planlama", "muhasebe",
         "Butce planlamasi, nakit akisi yonetimi, karlilik analizi. "
         "Isletmenizin finansal sagligini nasil koruyacaginizi ogrenin.",
         "", 22, "orta", 5),
        ("Dijital Guvenlik", "dijital",
         "Siber guvenlik temelleri, guclu sifreler, dolandiriciliga karsi onlemler. "
         "Dijital dunyada isletmenizi guvende tutun.",
         "", 10, "baslangic", 6),
        ("Envanter ve Stok Yonetimi", "muhasebe",
         "Stok takibi, tedarik zinciri yonetimi, fire kontrolu. "
         "Urunlerinizi verimli yoneterek kayiplari azaltin.",
         "", 15, "orta", 7),
        ("Vergi ve Yasal Yukumlulukler", "muhasebe",
         "Esnaf icin vergi turleri, beyanname surecleri, e-fatura uygulamalari. "
         "Yasal yukumluluklerinizi ertelemeyin, firsata cevirin.",
         "", 25, "ileri", 8),
        ("WhatsApp ile Satis Artirma", "pazarlama",
         "WhatsApp Business ozellikleri, otomatik yanitlar, katalog paylasimi. "
         "Tokat Dijital Carsi WhatsApp entegrasyonu ile satislarinizi katlayin.",
         "", 14, "baslangic", 9),
        ("Kriz Yonetimi", "dijital",
         "Ekonomik dalgalanmalarda ayakta kalma, alternatif gelir kanallari, maliyet dusurme stratejileri.",
         "", 20, "ileri", 10),
    ]
    for (baslik, kat, icerik, video, sure, zorluk, sira) in dersler:
        db.add(Egitim(baslik=baslik, kategori=kat, icerik=icerik, video_url=video, sure=sure, zorluk=zorluk, sira=sira))
    db.commit()


@app.post("/api/auth/kayit", response_model=TokenCevap)
def kayit(data: EsnafKayit, db: Session = Depends(get_db)):
    if db.query(Esnaf).filter((Esnaf.email == data.email) | (Esnaf.telefon == data.telefon)).first():
        raise HTTPException(400, "Bu email veya telefon zaten kayitli")
    esnaf = Esnaf(firma_adi=data.firma_adi, sahip_adi=data.sahip_adi, telefon=data.telefon,
                  email=data.email, sifre_hash=hash_password(data.sifre), dukkan_turu=data.dukkan_turu)
    db.add(esnaf)
    db.commit()
    db.refresh(esnaf)
    token = create_token(esnaf.id)
    return TokenCevap(access_token=token, esnaf=EsnafCevap.model_validate(esnaf))


@app.post("/api/auth/giris", response_model=TokenCevap)
def giris(data: EsnafGiris, db: Session = Depends(get_db)):
    esnaf = db.query(Esnaf).filter(Esnaf.email == data.email).first()
    if not esnaf or not verify_password(data.sifre, esnaf.sifre_hash):
        raise HTTPException(401, "Email veya sifre hatali")
    token = create_token(esnaf.id)
    return TokenCevap(access_token=token, esnaf=EsnafCevap.model_validate(esnaf))


@app.get("/api/auth/profil", response_model=EsnafCevap)
def profil(esnaf: Esnaf = Depends(get_current_esnaf)):
    return EsnafCevap.model_validate(esnaf)


@app.put("/api/auth/profil")
def profil_guncelle(data: EsnafGuncelle, esnaf: Esnaf = Depends(get_current_esnaf), db: Session = Depends(get_db)):
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(esnaf, key, val)
    db.commit()
    return {"mesaj": "Profil guncellendi"}


@app.get("/api/dashboard")
def dashboard(esnaf: Esnaf = Depends(get_current_esnaf), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    ay_basi = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    bu_ay_gelir = db.query(func.coalesce(func.sum(Islem.tutar), 0)).filter(
        Islem.esnaf_id == esnaf.id, Islem.tur == "gelir", Islem.tarih >= ay_basi).scalar()
    bu_ay_gider = db.query(func.coalesce(func.sum(Islem.tutar), 0)).filter(
        Islem.esnaf_id == esnaf.id, Islem.tur == "gider", Islem.tarih >= ay_basi).scalar()
    bugun = now.replace(hour=0, minute=0, second=0, microsecond=0)
    bugun_gelir = db.query(func.coalesce(func.sum(Islem.tutar), 0)).filter(
        Islem.esnaf_id == esnaf.id, Islem.tur == "gelir", Islem.tarih >= bugun).scalar()
    bugun_satis = db.query(func.count(Islem.id)).filter(
        Islem.esnaf_id == esnaf.id, Islem.tur == "gelir", Islem.tarih >= bugun).scalar()
    son_islemler = db.query(Islem).filter(Islem.esnaf_id == esnaf.id).order_by(Islem.tarih.desc()).limit(10).all()
    son_mesaj = db.query(WhatsAppMesaj).filter(WhatsAppMesaj.esnaf_id == esnaf.id).order_by(WhatsAppMesaj.tarih.desc()).limit(5).all()
    toplam_esnaf = db.query(func.count(Esnaf.id)).filter(Esnaf.aktif == True).scalar()
    return {
        "bu_ay_gelir": bu_ay_gelir, "bu_ay_gider": bu_ay_gider,
        "bu_ay_kar": bu_ay_gelir - bu_ay_gider,
        "bugun_gelir": bugun_gelir, "bugun_satis": bugun_satis,
        "toplam_esnaf": toplam_esnaf,
        "son_islemler": [{"id": i.id, "tur": i.tur, "kategori": i.kategori, "tutar": i.tutar,
                          "aciklama": i.aciklama, "tarih": i.tarih.isoformat(), "odeme_yontemi": i.odeme_yontemi,
                          "musteri_adi": i.musteri_adi} for i in son_islemler],
        "son_mesajlar": [{"id": m.id, "musteri_adi": m.musteri_adi, "mesaj": m.mesaj[:100],
                          "yon": m.yon, "tarih": m.tarih.isoformat()} for m in son_mesaj],
    }


@app.get("/api/islemler")
def islem_listele(tur: Optional[str] = None, kategori: Optional[str] = None,
                  baslangic: Optional[str] = None, bitis: Optional[str] = None,
                  sayfa: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
                  esnaf: Esnaf = Depends(get_current_esnaf), db: Session = Depends(get_db)):
    q = db.query(Islem).filter(Islem.esnaf_id == esnaf.id)
    if tur: q = q.filter(Islem.tur == tur)
    if kategori: q = q.filter(Islem.kategori.ilike(f"%{kategori}%"))
    if baslangic: q = q.filter(Islem.tarih >= datetime.fromisoformat(baslangic))
    if bitis: q = q.filter(Islem.tarih <= datetime.fromisoformat(bitis))
    toplam = q.count()
    q = q.order_by(Islem.tarih.desc()).offset((sayfa - 1) * limit).limit(limit)
    return {"islemler": [{"id": i.id, "tur": i.tur, "kategori": i.kategori, "tutar": i.tutar,
                          "aciklama": i.aciklama, "tarih": i.tarih.isoformat(),
                          "odeme_yontemi": i.odeme_yontemi, "musteri_adi": i.musteri_adi,
                          "fatura_no": i.fatura_no} for i in q],
            "toplam": toplam, "sayfa": sayfa, "limit": limit}


@app.post("/api/islemler")
def islem_ekle(data: IslemInput, esnaf: Esnaf = Depends(get_current_esnaf), db: Session = Depends(get_db)):
    islem = Islem(esnaf_id=esnaf.id, tur=data.tur, kategori=data.kategori, tutar=data.tutar,
                  aciklama=data.aciklama, odeme_yontemi=data.odeme_yontemi,
                  musteri_adi=data.musteri_adi, musteri_telefon=data.musteri_telefon,
                  fatura_no=data.fatura_no,
                  tarih=datetime.fromisoformat(data.tarih) if data.tarih else datetime.now(timezone.utc))
    db.add(islem)
    db.commit()
    return {"mesaj": "Islem eklendi", "id": islem.id}


@app.delete("/api/islemler/{islem_id}")
def islem_sil(islem_id: int, esnaf: Esnaf = Depends(get_current_esnaf), db: Session = Depends(get_db)):
    islem = db.query(Islem).filter(Islem.id == islem_id, Islem.esnaf_id == esnaf.id).first()
    if not islem: raise HTTPException(404, "Islem bulunamadi")
    db.delete(islem)
    db.commit()
    return {"mesaj": "Islem silindi"}


@app.get("/api/analiz")
def analiz(ay: int = Query(default=None), yil: int = Query(default=None),
           esnaf: Esnaf = Depends(get_current_esnaf), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    ay = ay or now.month
    yil = yil or now.year
    aylik = db.query(extract("month", Islem.tarih).label("ay"), extract("year", Islem.tarih).label("yil"),
                     Islem.tur, func.coalesce(func.sum(Islem.tutar), 0).label("toplam")).filter(
        Islem.esnaf_id == esnaf.id, extract("year", Islem.tarih) == yil
    ).group_by(extract("month", Islem.tarih), Islem.tur).all()
    kategori_dagilim = db.query(Islem.kategori, func.coalesce(func.sum(Islem.tutar), 0).label("toplam"),
                                func.count(Islem.id).label("adet")).filter(
        Islem.esnaf_id == esnaf.id, extract("month", Islem.tarih) == ay,
        extract("year", Islem.tarih) == yil).group_by(Islem.kategori).all()
    odeme_dagilim = db.query(Islem.odeme_yontemi, func.count(Islem.id).label("adet"),
                             func.coalesce(func.sum(Islem.tutar), 0).label("toplam")).filter(
        Islem.esnaf_id == esnaf.id, Islem.tur == "gelir", extract("month", Islem.tarih) == ay,
        extract("year", Islem.tarih) == yil).group_by(Islem.odeme_yontemi).all()
    gunluk = db.query(func.date(Islem.tarih).label("gun"),
                      func.coalesce(func.sum(Islem.tutar), 0).label("toplam")).filter(
        Islem.esnaf_id == esnaf.id, Islem.tur == "gelir", extract("month", Islem.tarih) == ay,
        extract("year", Islem.tarih) == yil).group_by(func.date(Islem.tarih)).order_by(func.date(Islem.tarih)).all()
    musteri_sayisi = db.query(func.count(func.distinct(Islem.musteri_adi))).filter(
        Islem.esnaf_id == esnaf.id, Islem.musteri_adi != "").scalar()
    return {
        "aylik_veri": [{"ay": int(r.ay), "yil": int(r.yil), "tur": r.tur, "toplam": float(r.toplam)} for r in aylik],
        "kategori_dagilim": [{"kategori": r.kategori, "toplam": float(r.toplam), "adet": r.adet} for r in kategori_dagilim if r.kategori],
        "odeme_dagilim": [{"yontem": r.odeme_yontemi, "adet": r.adet, "toplam": float(r.toplam)} for r in odeme_dagilim],
        "gunluk_veri": [{"gun": str(r.gun), "toplam": float(r.toplam)} for r in gunluk],
        "musteri_sayisi": musteri_sayisi or 0, "secilen_ay": ay, "secilen_yil": yil,
    }


@app.get("/api/urunler")
def urun_listele(esnaf: Esnaf = Depends(get_current_esnaf), db: Session = Depends(get_db)):
    urunler = db.query(Urun).filter(Urun.esnaf_id == esnaf.id, Urun.aktif == True).all()
    return [{"id": u.id, "ad": u.ad, "kategori": u.kategori, "fiyat": u.fiyat,
             "birim": u.birim, "stok": u.stok, "aciklama": u.aciklama, "fotograf": u.fotograf} for u in urunler]


@app.post("/api/urunler")
def urun_ekle(data: UrunInput, esnaf: Esnaf = Depends(get_current_esnaf), db: Session = Depends(get_db)):
    urun = Urun(esnaf_id=esnaf.id, **data.model_dump())
    db.add(urun)
    db.commit()
    return {"mesaj": "Urun eklendi", "id": urun.id}


@app.delete("/api/urunler/{urun_id}")
def urun_sil(urun_id: int, esnaf: Esnaf = Depends(get_current_esnaf), db: Session = Depends(get_db)):
    urun = db.query(Urun).filter(Urun.id == urun_id, Urun.esnaf_id == esnaf.id).first()
    if not urun: raise HTTPException(404, "Urun bulunamadi")
    urun.aktif = False
    db.commit()
    return {"mesaj": "Urun silindi"}


@app.get("/api/egitimler")
def egitim_listele(db: Session = Depends(get_db)):
    egitimler = db.query(Egitim).filter(Egitim.aktif == True).order_by(Egitim.sira).all()
    return [{"id": e.id, "baslik": e.baslik, "kategori": e.kategori, "icerik": e.icerik,
             "video_url": e.video_url, "sure": e.sure, "zorluk": e.zorluk, "sira": e.sira} for e in egitimler]


@app.get("/api/egitimler/progress")
def egitim_progress(esnaf: Esnaf = Depends(get_current_esnaf), db: Session = Depends(get_db)):
    progress = db.query(EgitimProgress).filter(EgitimProgress.esnaf_id == esnaf.id).all()
    tamamlanan_ids = {p.egitim_id for p in progress}
    toplam = db.query(func.count(Egitim.id)).filter(Egitim.aktif == True).scalar()
    return {"tamamlanan_ids": list(tamamlanan_ids), "tamamlanan_sayisi": len(tamamlanan_ids), "toplam_sayisi": toplam}


@app.post("/api/egitimler/{egitim_id}/tamamla")
def egitim_tamamla(egitim_id: int, esnaf: Esnaf = Depends(get_current_esnaf), db: Session = Depends(get_db)):
    var = db.query(EgitimProgress).filter(EgitimProgress.esnaf_id == esnaf.id, EgitimProgress.egitim_id == egitim_id).first()
    if not var:
        var = EgitimProgress(esnaf_id=esnaf.id, egitim_id=egitim_id, tamamlandi=True, tamamlanma_tarihi=datetime.now(timezone.utc))
        db.add(var)
    else:
        var.tamamlandi = True
        var.tamamlanma_tarihi = datetime.now(timezone.utc)
    db.commit()
    return {"mesaj": "Egitim tamamlandi!"}


@app.get("/api/cari")
def cari_listele(esnaf: Esnaf = Depends(get_current_esnaf), db: Session = Depends(get_db)):
    cariler = db.query(Cari).filter(Cari.esnaf_id == esnaf.id).all()
    return [{"id": c.id, "musteri_adi": c.musteri_adi, "musteri_telefon": c.musteri_telefon,
             "borc": c.borc, "alacak": c.alacak, "bakiye": c.borc - c.alacak,
             "son_islem": c.son_islem.isoformat() if c.son_islem else None} for c in cariler]


@app.get("/api/whatsapp/mesajlar")
def whatsapp_mesajlar(esnaf: Esnaf = Depends(get_current_esnaf), db: Session = Depends(get_db)):
    mesajlar = db.query(WhatsAppMesaj).filter(WhatsAppMesaj.esnaf_id == esnaf.id).order_by(WhatsAppMesaj.tarih.desc()).limit(50).all()
    return [{"id": m.id, "musteri_adi": m.musteri_adi, "musteri_telefon": m.musteri_telefon,
             "mesaj": m.mesaj, "yon": m.yon, "tur": m.tur, "tarih": m.tarih.isoformat(), "okundu": m.okundu} for m in mesajlar]


@app.post("/api/demo/seed")
def demo_seed(db: Session = Depends(get_db)):
    if db.query(Esnaf).count() > 0:
        return {"mesaj": "Demo verisi zaten mevcut"}
    esnaf = Esnaf(firma_adi="Tokat Seyahat", sahip_adi="Mehmet Usta",
                  telefon="05551234567", email="demo@tokatcarsi.com",
                  sifre_hash=hash_password("demo123"), dukkan_turu="otobus", ilce="Merkez",
                  aciklama="Tokat'ta 15 yildir hizmet veren guvenilir otobus firmasi.")
    db.add(esnaf)
    db.commit()
    db.refresh(esnaf)
    import random
    for i in range(20):
        db.add(Islem(esnaf_id=esnaf.id, tur="gelir", kategori="bilet",
                     tutar=random.randint(200, 1500), aciklama="Tokat-Ankara seferi",
                     odeme_yontemi=random.choice(["nakit", "havale", "kredi_karti"]),
                     musteri_adi=random.choice(["Ali Yilmaz", "Ayse Demir", "Veli Kaya"]),
                     tarih=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 720))))
    for i in range(5):
        db.add(Islem(esnaf_id=esnaf.id, tur="gider", kategori="akaryakit",
                     tutar=random.randint(3000, 8000), aciklama="Mazot alimi",
                     odeme_yontemi="nakit",
                     tarih=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 720))))
    db.commit()
    return {"mesaj": "Demo verisi olusturuldu! Email: demo@tokatcarsi.com, Sifre: demo123"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


@app.post("/api/bot/soru")
def bot_soru(mesaj: dict, db: Session = Depends(get_db)):
    from bot_engine import BotYonetici
    bot = BotYonetici(db)
    cevap = bot.telgraf_mesaj(mesaj.get("mesaj", ""))
    return cevap
@app.get("/api/bot/sektorler")
def bot_sektorler():
    from bot_engine import SEKTORLER
    return [{"anahtar": k, **v} for k, v in SEKTORLER.items()]
@app.get("/api/bot/sehirler")
def bot_sehirler():
    from bot_engine import SEHIRLER
    return SEHIRLER


@app.post("/api/demo/seed-v2")
def demo_seed_v2(db: Session = Depends(get_db)):
    from models import Esnaf, Islem, Urun
    from datetime import datetime, timezone, timedelta
    import random
    if db.query(Esnaf).count() > 3:
        return {"mesaj": "Zaten yeterli demo verisi var"}
    demo = [
        ("Tokat Seyahat","Mehmet Usta","05551111111","tokat@demo.com","otobus","Merkez","Tokat","Tokat otobus firmasi."),
        ("Tarihi Tokat Kebabi","Ali Usta","05552222222","kebap@demo.com","restoran","Merkez","Tokat","1930dan beri Tokat kebabi."),
        ("Zile Kahvesi","Hasan Bey","05553333333","zile@demo.com","kafe","Zile","Tokat","Meshur Zile kahvesi."),
        ("Carsi Kuyumculuk","Ahmet","05554444444","kuyum@demo.com","kuyumcu","Merkez","Sivas","22 ayar bilezik."),
        ("Yesilirmak Pide","Osman Usta","05555555555","pide@demo.com","restoran","Carsamba","Samsun","Tas firinda pide."),
        ("Mardin Yoresel","Meryem","05556666666","mardin@demo.com","yoresel","Merkez","Mardin","El yapimi sabun."),
        ("Usta Eller","Kemal","05557777777","usta@demo.com","hizmet","Sehitkamil","Gaziantep","Telefon tamiri."),
        ("Bursa Iskenderci","Iskender","05558888888","bursa@demo.com","restoran","Osmangazi","Bursa","Iskender kebap."),
        ("Ankara Bakkal","Veli Amca","05559999999","bakkal@demo.com","market","Kecioren","Ankara","Mahalle bakkali."),
        ("Istanbul Deniz","Kaptan","05550000000","deniz@demo.com","otobus","Kadikoy","Istanbul","Sehirlerarasi otobus."),
    ]
    urunler = {
        "otobus":[("Ankara Seferi","bilet",350,"koltuk",45),("Istanbul Seferi","bilet",500,"koltuk",40)],
        "restoran":[("Porsiyon Kebap","yemek",180,"porsiyon",30),("Lahmacun","yemek",60,"adet",100)],
        "kafe":[("Turk Kahvesi","icecek",40,"fincan",50),("Zile Kahvesi","icecek",50,"fincan",40)],
        "kuyumcu":[("Ceyrek Altin","altin",4950,"adet",10),("Bilezik","altin",12500,"adet",5)],
        "yoresel":[("Zeytinyagi","gida",150,"litre",30),("Defne Sabunu","kozmetik",45,"adet",100)],
        "hizmet":[("Telefon Tamir","tamir",500,"islem",0),("Ekran Degisimi","tamir",1200,"islem",0)],
        "market":[("Ekmek","gida",12,"adet",200),("Sut 1L","gida",35,"adet",50)],
    }
    for d in demo:
        e = db.query(Esnaf).filter(Esnaf.email == d[3]).first()
        if not e:
            e = Esnaf(firma_adi=d[0],sahip_adi=d[1],telefon=d[2],email=d[3],
                      sifre_hash=hash_password("demo123"),dukkan_turu=d[4],ilce=d[5],sehir=d[6],aciklama=d[7])
            db.add(e); db.flush()
            for u in urunler.get(d[4], [("Urun","genel",50,"adet",20)]):
                db.add(Urun(esnaf_id=e.id,ad=u[0],kategori=u[1],fiyat=u[2],birim=u[3],stok=u[4]))
            for i in range(5):
                db.add(Islem(esnaf_id=e.id,tur="gelir",kategori="satis",tutar=random.randint(100,2000),
                           musteri_adi=random.choice(["Ali","Ayse","Veli"]),
                           tarih=datetime.now(timezone.utc)-timedelta(hours=random.randint(1,720))))
    db.commit()
    return {"mesaj": "10 esnaf, 7 sehir - demo verisi hazir! sifre: demo123"}

# Serve frontend static files
from fastapi.staticfiles import StaticFiles
import os
_fp = os.path.join(os.path.dirname(__file__), '..', 'frontend')
if os.path.exists(_fp):
    app.mount("/", StaticFiles(directory=_fp, html=True), name="frontend")
