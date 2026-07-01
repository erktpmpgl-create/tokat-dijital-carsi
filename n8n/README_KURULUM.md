# Tokat Dijital Çarşı — n8n Otomasyon Akışları

WhatsApp (Meta Cloud API) tabanlı 4 otomasyon akışı. n8n = köprü; iş mantığı FastAPI backend'inde.

## Dosyalar

| Dosya | Ne yapar | Tetikleyici |
|-------|----------|-------------|
| `1_whatsapp_sorgulama_botu.json` | Müşteri mesajı → backend → otomatik yanıt (sefer/fiyat/koltuk/ürün) | Meta webhook (GET doğrulama + POST mesaj) |
| `2_siparis_odeme_bildirimi.json` | Yeni sipariş → esnafa bildirim; ödeme alındı → müşteriye onay | Backend `POST /webhook/tokat-siparis` |
| `3_esnaf_onboarding.json` | Kayıt formu → backend'e esnaf ekle → karşılama mesajı | Web formu `POST /webhook/tokat-esnaf-kayit` |
| `4_kurye_eslestirme.json` | Teslimat → en yakın kurye → WhatsApp'tan iş atama (Kabul/Reddet) | Backend `POST /webhook/tokat-kurye` |

---

## 1. Ön koşullar

- Çalışan bir **n8n** (self-host öneri: `docker run -it --rm -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n`)
- **Meta WhatsApp Cloud API** uygulaması: bir App + WhatsApp ürünü + test/gerçek telefon numarası
- n8n'in dışarıdan erişilebilir bir HTTPS adresi (Meta webhook için). Lokal test: `n8n` + Cloudflare Tunnel / ngrok.

## 2. n8n ortam değişkenleri (Environment Variables)

n8n'i başlatırken şu değişkenleri tanımla (docker `-e` veya `.env`):

| Değişken | Açıklama | Örnek |
|----------|----------|-------|
| `WA_TOKEN` | Meta kalıcı erişim tokenı (System User token önerilir) | `EAAG...` |
| `WA_PHONE_NUMBER_ID` | WhatsApp numarasının Phone Number ID'si | `123456789012345` |
| `WA_VERIFY_TOKEN` | Webhook doğrulama için senin belirlediğin gizli dize | `tokat-2026-xyz` |
| `BACKEND_URL` | FastAPI taban adresi (n8n aynı ağdaysa servis adı) | `http://api:8000` |
| `BACKEND_API_KEY` | Backend'in n8n'i doğrulaması için paylaşılan anahtar | `uzun-gizli-anahtar` |
| `PANEL_URL` | Esnaf paneli linki | `https://panel.tokatcarsi.com` |
| `OPERATOR_PHONE` | Kurye bulunamayınca uyarılacak operatör no (E.164) | `905xxxxxxxxx` |

> Not: Token/anahtarları düz metin olarak paylaşma. Mümkünse n8n **Credentials** özelliğiyle sakla; bu akışlar kolay taşınsın diye env değişkeni kullanıyor.

## 3. Meta Cloud API webhook ayarı

1. Meta App → WhatsApp → **Configuration → Webhook**
2. **Callback URL:** `https://<n8n-adresin>/webhook/tokat-whatsapp`
3. **Verify token:** `WA_VERIFY_TOKEN` ile aynı değeri gir
4. Meta bir **GET** isteği atar → Workflow 1'deki "Webhook Doğrulama (GET)" bunu karşılar ve `hub.challenge` döndürür ✅
5. Webhook fields: **messages** aboneliğini aç
6. Gelen her mesaj **POST** olarak `/webhook/tokat-whatsapp` adresine düşer

> n8n'de webhook'lar iki modda: **Test URL** (`/webhook-test/...`, editör açıkken tek seferlik) ve **Production URL** (`/webhook/...`, akış "Active" olunca kalıcı). Meta'ya **production** URL ver ve akışı **Active** yap.

## 4. İçe aktarma (Import)

n8n arayüzü → sağ üst **⋮ → Import from File** → her `.json` dosyasını sırayla yükle. Ardından her akışı aç, sağ üstten **Active** yap.

## 5. Backend'in sağlaması gereken uçlar

Bu akışlar şu endpoint'leri çağırır — FastAPI tarafında hazır olmalı:

| Endpoint | Metod | Gövde (istek) | Dönüş (beklenen) |
|----------|-------|----------------|-------------------|
| `/api/whatsapp/handle` | POST | `{ from, name, text }` | `{ reply: "..." }` |
| `/api/esnaf` | POST | `{ isim, dukkan, telefon, kategori, email }` | `{ ok, id }` |
| `/api/kurye/en-yakin` | POST | `{ alis_adres, teslim_konum }` | `{ kurye_phone, kurye_adi, mesafe_km, ucret }` |

Backend, n8n'e giden sipariş/ödeme/teslimat olaylarını da şu webhook'lara POST eder:
- `POST https://<n8n>/webhook/tokat-siparis` → `{ event: "yeni_siparis" | "odeme_alindi", esnaf_phone, customer_phone, customer_name, ozet, tutar }`
- `POST https://<n8n>/webhook/tokat-kurye` → `{ siparis_id, esnaf_adi, alis_adres, teslim_adres, teslim_konum }`

## 6. Kurye butonları (Workflow 4)

Kuryeye giden **Kabul Et / Reddet** interaktif butonlarının yanıtı, Workflow 1'in webhook'una `interactive.button_reply` olarak düşer. Backend `/api/whatsapp/handle` içinde `id` alanını (`kabul_<siparis>` / `ret_<siparis>`) yakalayıp atamayı sonuçlandırmalı.

## 7. Hızlı test

1. Workflow 1'i Active yap, Meta'dan test numarana bir mesaj at → otomatik yanıt gelmeli.
2. Workflow 2/3/4 için n8n webhook Production URL'ine `curl` ile örnek gövde POST et:
```bash
curl -X POST https://<n8n>/webhook/tokat-siparis \
  -H "Content-Type: application/json" \
  -d '{"event":"yeni_siparis","esnaf_phone":"905xxxxxxxxx","customer_name":"Ahmet","ozet":"2x çay bardağı","tutar":"180"}'
```

## Güvenlik notları

- 24 saat kuralı: müşteri son 24 saatte yazmadıysa serbest metin gönderemezsin → **onaylı şablon (template)** gerekir. Sipariş/onay bildirimlerinde utility template kullanmayı planla.
- `WA_TOKEN`'ı System User kalıcı tokenı yap; kısa ömürlü token üretimde kesilir.
- Backend ↔ n8n arası `BACKEND_API_KEY` ile doğrula ki webhook'lar dışarıdan tetiklenemesin.
