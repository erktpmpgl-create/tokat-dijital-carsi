
"""
Tokat Dijital Carsi - WhatsApp Bot & Sektor Demo Motoru
"""
import json
from sqlalchemy.orm import Session

SEKTORLER = {
    "otobus": {"isim": "Otobus Firmasi", "ikon": "\U0001f68c", "renk": "#3498DB",
        "sorgu_kelimeleri": ["otobus", "bilet", "sefer", "otogar", "yolculuk", "ulasim", "koltuk"]},
    "restoran": {"isim": "Restoran / Lokanta", "ikon": "\U0001f37d\ufe0f", "renk": "#E74C3C",
        "sorgu_kelimeleri": ["yemek", "restoran", "lokanta", "kebap", "corba", "doner", "menu", "tatli"]},
    "market": {"isim": "Market / Bakkal", "ikon": "\U0001f3ea", "renk": "#27AE60",
        "sorgu_kelimeleri": ["market", "bakkal", "manav", "kasap", "meyve", "sebze"]},
    "kafe": {"isim": "Kafe / Cay Ocagi", "ikon": "\u2615", "renk": "#8E44AD",
        "sorgu_kelimeleri": ["kafe", "kahve", "cay", "icecek", "tost"]},
    "kuyumcu": {"isim": "Kuyumcu", "ikon": "\U0001f48d", "renk": "#F1C40F",
        "sorgu_kelimeleri": ["kuyumcu", "altin", "bilezik", "yuzuk", "ceyrek", "gram"]},
    "yoresel": {"isim": "Yoresel Urunler", "ikon": "\U0001f9c0", "renk": "#E67E22",
        "sorgu_kelimeleri": ["yoresel", "hediyelik", "el emegi", "organik", "yemelik"]},
    "hizmet": {"isim": "Hizmet / Tamirci", "ikon": "\U0001f527", "renk": "#34495E",
        "sorgu_kelimeleri": ["tamir", "usta", "servis", "bakim", "berber", "kuaför"]},
}

SEHIRLER = ["Adana", "Ankara", "Antalya", "Bursa", "Diyarbakir",
    "Gaziantep", "Istanbul", "Izmir", "Kayseri", "Konya", "Mersin",
    "Samsun", "Sivas", "Tokat", "Trabzon"]

class BotYonetici:
    def __init__(self, db: Session):
        self.db = db

    def mesaj_analiz(self, mesaj: str) -> dict:
        from models import Esnaf
        m = mesaj.strip().lower()
        sehirler = [s for s in SEHIRLER if s.lower() in m]
        sektorler = [k for k, v in SEKTORLER.items() for kw in v["sorgu_kelimeleri"] if kw in m]
        esnaf_bul = None
        for e in self.db.query(Esnaf).filter(Esnaf.aktif == True).all():
            if e.firma_adi.lower() in m:
                esnaf_bul = e
                break
        niyet = "sorgu"
        if any(k in m for k in ["siparis", "rezervasyon"]): niyet = "siparis"
        if any(k in m for k in ["fiyat", "ne kadar", "ucret"]): niyet = "fiyat_sorgu"
        if any(k in m for k in ["merhaba", "selam", "iyi gunler", "kolay gelsin"]): niyet = "selamlama"
        return {"sehirler": sehirler, "sektorler": sektorler,
                "esnaf_id": esnaf_bul.id if esnaf_bul else None,
                "esnaf_adi": esnaf_bul.firma_adi if esnaf_bul else None, "niyet": niyet}

    def cevap_olustur(self, a: dict) -> dict:
        from models import Esnaf, Urun
        if a["esnaf_id"]:
            e = self.db.query(Esnaf).filter(Esnaf.id == a["esnaf_id"]).first()
            if e:
                sb = SEKTORLER.get(e.dukkan_turu, {"ikon": "\U0001f3ea", "isim": e.dukkan_turu or "Isletme"})
                ikon = sb.get("ikon", "\U0001f3ea")
                urunler = self.db.query(Urun).filter(Urun.esnaf_id == e.id, Urun.aktif == True).all()
                lines = [f"{ikon} *{e.firma_adi}*"]
                lines.append(f"  {sb.get('isim', '')} | {e.ilce or 'Merkez'}, {e.sehir or 'Tokat'}")
                if e.telefon: lines.append(f"\U0001f4de {e.telefon}")
                if urunler:
                    lines.append("")
                    lines.append("\U0001f4e6 *Urunler:*")
                    for u in urunler[:5]:
                        lines.append(f"  \u2022 {u.ad} - {u.fiyat:.0f} TL" if u.fiyat else f"  \u2022 {u.ad}")
                lines.append("")
                lines.append("\u2500" * 18)
                lines.append("\U0001f4ac Ne yapmak istersiniz?")
                lines.append("1\ufe0f\u20e3 Siparis vermek")
                lines.append("2\ufe0f\u20e3 Bana ulassin")
                lines.append("3\ufe0f\u20e3 Ana menu")
                return {"tip": "esnaf_detay", "mesaj": "\n".join(lines)}

        if a["sehirler"] and a["sektorler"]:
            sehir = a["sehirler"][0]; sektor = a["sektorler"][0]
            sb = SEKTORLER.get(sektor, {"ikon": "\U0001f3ea", "isim": sektor})
            esnaflar = self.db.query(Esnaf).filter(Esnaf.sehir.ilike(f"%{sehir}%"), Esnaf.dukkan_turu == sektor, Esnaf.aktif == True).all()
            if esnaflar:
                lines = [f"{sb.get('ikon', '')} *{sehir}'daki {sb.get('isim', sektor)}lar*"]
                for i, e in enumerate(esnaflar[:6], 1):
                    lines.append(f"{i}. {e.firma_adi}" + (f" ({e.ilce})" if e.ilce else ""))
                lines.append(f"\n{len(esnaflar)} isletme. Detay icin isim yazin.")
                return {"tip": "menu", "mesaj": "\n".join(lines)}

        if a["sehirler"]:
            sehir = a["sehirler"][0]
            esnaflar = self.db.query(Esnaf).filter(Esnaf.sehir.ilike(f"%{sehir}%"), Esnaf.aktif == True).all()
            if esnaflar:
                gruplar = {}
                for e in esnaflar:
                    s = e.dukkan_turu or "diger"
                    if s not in gruplar: gruplar[s] = []
                    gruplar[s].append(e)
                lines = [f"\U0001f3d9\ufe0f *{sehir}'daki Isletmeler*"]
                for sk, liste in gruplar.items():
                    sbi = SEKTORLER.get(sk, {"isim": sk, "ikon": "\U0001f4cd"})
                    lines.append(f"{sbi['ikon']} {sbi['isim']} - {len(liste)} adet")
                lines.append("\nSektor secmek icin adini yazin")
                return {"tip": "menu", "mesaj": "\n".join(lines)}

        if a["sektorler"]:
            sb = SEKTORLER.get(a["sektorler"][0], {})
            return {"tip": "menu", "mesaj": f"{sb.get('ikon', '')} {sb.get('isim', '')}\n\nHangi sehir?\nOrn: Tokat otobus"}

        if a["niyet"] == "selamlama":
            return {"tip": "menu", "mesaj": "\U0001f44b *Tokat Dijital Carsi*\n\nDeneyin:\n\U0001f68c Tokat'tan Ankara'ya\n\U0001f37d\ufe0f Istanbul restoran\n\U0001f3ea Manav bul\n\u2615 Tokat merkez kafe"}

        return {"tip": "menu", "mesaj": "\U0001f914 Anlayamadim.\n\nDeneyin:\n\U0001f68c Tokat'tan Ankara'ya otobus\n\U0001f37d\ufe0f Istanbul restoran\n\U0001f3ea Manav ariyorum"}

    def telgraf_mesaj(self, mesaj: str) -> dict:
        return self.cevap_olustur(self.mesaj_analiz(mesaj))
