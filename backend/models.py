from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class Esnaf(Base):
    __tablename__ = "esnaf"

    id = Column(Integer, primary_key=True, index=True)
    firma_adi = Column(String(200), nullable=False)
    sahip_adi = Column(String(200), nullable=False)
    telefon = Column(String(20), unique=True, nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    sifre_hash = Column(String(200), nullable=False)
    dukkan_turu = Column(String(100))
    adres = Column(Text)
    sehir = Column(String(50), default="Tokat")
    ilce = Column(String(50))
    aktif = Column(Boolean, default=True)
    premium = Column(Boolean, default=False)
    whatsapp_onayli = Column(Boolean, default=False)
    kayit_tarihi = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    profil_fotografi = Column(String(500))
    aciklama = Column(Text)

    islemler = relationship("Islem", back_populates="esnaf")
    urunler = relationship("Urun", back_populates="esnaf")
    egitim_progres = relationship("EgitimProgress", back_populates="esnaf")


class Urun(Base):
    __tablename__ = "urunler"

    id = Column(Integer, primary_key=True, index=True)
    esnaf_id = Column(Integer, ForeignKey("esnaf.id"), nullable=False)
    ad = Column(String(200), nullable=False)
    kategori = Column(String(100))
    fiyat = Column(Float)
    birim = Column(String(20))
    stok = Column(Integer, default=0)
    aktif = Column(Boolean, default=True)
    fotograf = Column(String(500))
    aciklama = Column(Text)

    esnaf = relationship("Esnaf", back_populates="urunler")


class Islem(Base):
    __tablename__ = "islemler"

    id = Column(Integer, primary_key=True, index=True)
    esnaf_id = Column(Integer, ForeignKey("esnaf.id"), nullable=False)
    tur = Column(String(20), nullable=False)
    kategori = Column(String(100))
    tutar = Column(Float, nullable=False)
    aciklama = Column(Text)
    tarih = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    odeme_yontemi = Column(String(50))
    musteri_adi = Column(String(200))
    musteri_telefon = Column(String(20))
    fatura_no = Column(String(50))
    vergi_dahil = Column(Boolean, default=True)
    whatsapp_siparis = Column(Boolean, default=False)

    esnaf = relationship("Esnaf", back_populates="islemler")


class Cari(Base):
    __tablename__ = "cari_hesap"

    id = Column(Integer, primary_key=True, index=True)
    esnaf_id = Column(Integer, ForeignKey("esnaf.id"), nullable=False)
    musteri_adi = Column(String(200), nullable=False)
    musteri_telefon = Column(String(20))
    borc = Column(Float, default=0.0)
    alacak = Column(Float, default=0.0)
    son_islem = Column(DateTime)
    notlar = Column(Text)


class Egitim(Base):
    __tablename__ = "egitimler"

    id = Column(Integer, primary_key=True, index=True)
    baslik = Column(String(300), nullable=False)
    kategori = Column(String(100))
    icerik = Column(Text)
    video_url = Column(String(500))
    sure = Column(Integer)
    zorluk = Column(String(20))
    sira = Column(Integer, default=0)
    aktif = Column(Boolean, default=True)


class EgitimProgress(Base):
    __tablename__ = "egitim_progress"

    id = Column(Integer, primary_key=True, index=True)
    esnaf_id = Column(Integer, ForeignKey("esnaf.id"), nullable=False)
    egitim_id = Column(Integer, ForeignKey("egitimler.id"), nullable=False)
    tamamlandi = Column(Boolean, default=False)
    tamamlanma_tarihi = Column(DateTime)

    esnaf = relationship("Esnaf", back_populates="egitim_progres")


class WhatsAppMesaj(Base):
    __tablename__ = "whatsapp_mesajlari"

    id = Column(Integer, primary_key=True, index=True)
    esnaf_id = Column(Integer, ForeignKey("esnaf.id"), nullable=False)
    musteri_adi = Column(String(200))
    musteri_telefon = Column(String(20))
    mesaj = Column(Text)
    yon = Column(String(10))
    tur = Column(String(50))
    tarih = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    okundu = Column(Boolean, default=False)
