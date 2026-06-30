const API = window.location.origin + '/api';
function getToken(){return localStorage.getItem('token')}
function setToken(t){localStorage.setItem('token',t)}
function clearToken(){localStorage.removeItem('token');localStorage.removeItem('esnaf')}
function isAuth(){return !!getToken()}
function apiHeaders(){const h={'Content-Type':'application/json'};if(getToken())h['Authorization']='Bearer '+getToken();return h}
async function apiCall(method,path,body=null){
  const opt={method,headers:apiHeaders()};
  if(body)opt.body=JSON.stringify(body);
  try{
    const r=await fetch(API+path,opt);
    if(r.status===401){logout();return null}
    return await r.json()
  }catch(e){showAlert('Baglanti hatasi: '+e.message,'error');return null}
}
function getEsnaf(){try{return JSON.parse(localStorage.getItem('esnaf'))}catch{return null}}
function setEsnaf(e){localStorage.setItem('esnaf',JSON.stringify(e))}
function logout(){clearToken();navigate('giris')}

const PAGES=['dashboard','muhasebe','analiz','urunler','egitim','whatsapp','cari','profil'];
function navigate(page,data){
  if(page==='giris'||page==='kayit'){
    document.getElementById('loginPage').style.display='flex';
    document.getElementById('appPage').style.display='none';
    document.getElementById('loginForm').style.display=page==='giris'?'block':'none';
    document.getElementById('registerForm').style.display=page==='kayit'?'block':'none';
    document.getElementById('formSwitch').innerHTML=page==='giris'
      ?'Hesabin yok mu? <a onclick="navigate('kayit')">Kayit Ol</a>'
      :'Zaten hesabin var mi? <a onclick="navigate('giris')">Giris Yap</a>';
    return
  }
  if(!PAGES.includes(page))return;
  document.getElementById('loginPage').style.display='none';
  document.getElementById('appPage').style.display='flex';
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  const ni=document.querySelector('[data-page="'+page+'"]');
  if(ni)ni.classList.add('active');
  const t={dashboard:'Panel',muhasebe:'On Muhasebe',analiz:'Dukkan Analizi',urunler:'Urunlerim',egitim:'Dijital Egitim',whatsapp:'WhatsApp',cari:'Cari Hesap',profil:'Profil'};
  document.getElementById('pageTitle').textContent=t[page]||page;
  loadPage(page)
}
function loadPage(p){const c=document.getElementById('pageContent');if(p==='dashboard')renderDashboard(c);else if(p==='muhasebe')renderMuhasebe(c);else if(p==='analiz')renderAnaliz(c);else if(p==='urunler')renderUrunler(c);else if(p==='egitim')renderEgitim(c);else if(p==='whatsapp')renderWhatsApp(c);else if(p==='cari')renderCari(c);else if(p==='profil')renderProfil(c)}
function updateSidebar(){const e=getEsnaf();if(!e)return;document.getElementById('sidebarName').textContent=e.firma_adi;document.getElementById('sidebarRole').textContent=e.dukkan_turu||'Esnaf';document.getElementById('sidebarAvatar').textContent=e.firma_adi[0].toUpperCase()}
function toggleSidebar(){document.querySelector('.sidebar').classList.toggle('open')}
function fmt(n){if(n===undefined||n===null)return'0';return Number(n).toLocaleString('tr-TR',{minimumFractionDigits:0,maximumFractionDigits:0})}
function tarih(iso){if(!iso)return'---';try{return new Date(iso).toLocaleDateString('tr-TR',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}catch{return iso}}
function showModal(t,b,onC,cT){document.getElementById('modalTitle').textContent=t;document.getElementById('modalBody').innerHTML=b;const f=document.getElementById('modalFooter');f.innerHTML='<button class="btn btn-outline" onclick="closeModal()">Iptal</button>'+(onC?'<button class="btn btn-primary" id="modalConfirmBtn">'+(cT||'Kaydet')+'</button>':'');if(onC)document.getElementById('modalConfirmBtn').onclick=onC;document.getElementById('modalOverlay').classList.add('active')}
function closeModal(){document.getElementById('modalOverlay').classList.remove('active')}
async function handleLogin(e){e.preventDefault();const d=await apiCall('POST','/auth/giris',{email:document.getElementById('loginEmail').value,sifre:document.getElementById('loginSifre').value});if(d&&d.access_token){setToken(d.access_token);setEsnaf(d.esnaf);navigate('dashboard');updateSidebar()}else showAlert('Hata!','error')}
async function handleRegister(e){e.preventDefault();const d=await apiCall('POST','/auth/kayit',{firma_adi:document.getElementById('regFirma').value,sahip_adi:document.getElementById('regSahip').value,telefon:document.getElementById('regTel').value,email:document.getElementById('regEmail').value,sifre:document.getElementById('regSifre').value,dukkan_turu:document.getElementById('regTur').value});if(d&&d.access_token){setToken(d.access_token);setEsnaf(d.esnaf);navigate('dashboard');updateSidebar()}else showAlert('Hata!','error')}
function showAlert(m,t,el){const e=document.getElementById(el||'loginAlert');if(!e)return;e.textContent=m;e.className='alert alert-'+t}

async function renderDashboard(c){
  c.innerHTML='<div class="loading"><div class="spinner"></div> Yukleniyor...</div>';
  const d=await apiCall('GET','/dashboard');
  if(!d){c.innerHTML='<div class="empty-state"><p>Veri yuklenemedi.</p></div>';return};
  const e=getEsnaf();
  const sb=d.toplam_esnaf<=1?'<button class="btn btn-accent btn-sm" onclick="seedDemo()"> Demo Verisi Yukle</button>':'';
  c.innerHTML='<div class="stats-grid">'+
    '<div class="stat-card"><div class="stat-icon green"> Gelir</div><div class="stat-label">Bu Ay Gelir</div><div class="stat-value">'+fmt(d.bu_ay_gelir)+' TL</div></div>'+
    '<div class="stat-card"><div class="stat-icon red"> Gider</div><div class="stat-label">Bu Ay Gider</div><div class="stat-value">'+fmt(d.bu_ay_gider)+' TL</div></div>'+
    '<div class="stat-card"><div class="stat-icon gold"> Kar</div><div class="stat-label">Bu Ay Kar</div><div class="stat-value '+(d.bu_ay_kar>=0?'green':'red')+'">'+fmt(d.bu_ay_kar)+' TL</div></div>'+
    '<div class="stat-card"><div class="stat-icon blue"> Satis</div><div class="stat-label">Bugun</div><div class="stat-value">'+fmt(d.bugun_gelir)+' TL</div><div class="stat-change">'+d.bugun_satis+' islem</div></div>'+
    '<div class="stat-card"><div class="stat-icon green"> Esnaf</div><div class="stat-label">Toplam Esnaf</div><div class="stat-value">'+d.toplam_esnaf+'</div></div></div>'+
    '<div class="grid-2"><div class="card"><div class="card-header"><h3>Son Islemler</h3><button class="btn btn-outline btn-sm" onclick="navigate('muhasebe')">Tumu</button></div><div class="card-body">'+
    (d.son_islemler.length===0?'<div class="empty-state"><p>Henuz islem yok.</p>'+sb+'</div>':'<table><tr><th>Tarih</th><th>Tur</th><th>Aciklama</th><th>Tutar</th></tr>'+
    d.son_islemler.map(i=>'<tr><td>'+tarih(i.tarih)+'</td><td><span class="badge '+(i.tur==='gelir'?'badge-green':'badge-red')+'">'+i.tur+'</span></td><td>'+(i.aciklama||i.kategori)+'</td><td>'+fmt(i.tutar)+' TL</td></tr>').join('')+'</table>')+'</div></div>'+
    '<div class="card"><div class="card-header"><h3>WhatsApp</h3></div><div class="card-body">'+
    (d.son_mesajlar.length===0?'<div class="empty-state"><p>Henuz mesaj yok.</p></div>':d.son_mesajlar.map(m=>'<div class="whatsapp-mesaj '+m.yon+'" style="padding:10px"><div class="mesaj-icerik"><div class="meta">'+(m.musteri_adi||'?')+' - '+tarih(m.tarih)+'</div><div class="text">'+m.mesaj+'</div></div></div>').join(''))+
    '</div></div></div>';updateSidebar()}

async function seedDemo(){const r=await apiCall('POST','/demo/seed');if(r){alert(r.mesaj);navigate('dashboard')}}

async function renderMuhasebe(c){
  c.innerHTML='<div class="loading"><div class="spinner"></div> Yukleniyor...</div>';
  const d=await apiCall('GET','/islemler?limit=100');
  if(!d)return;
  const g=d.islemler.filter(i=>i.tur==='gelir').reduce((s,i)=>s+i.tutar,0);
  const gr=d.islemler.filter(i=>i.tur==='gider').reduce((s,i)=>s+i.tutar,0);
  c.innerHTML='<div class="muhasebe-header"><div><h3>On Muhasebe</h3></div><button class="btn btn-primary" onclick="islemEkleModal()">+ Yeni Islem</button></div>'+
    '<div class="muhasebe-summary"><div class="summary-item"><div class="amount green">'+fmt(g)+' TL</div><div class="label">Gelir</div></div><div class="summary-item"><div class="amount red">'+fmt(gr)+' TL</div><div class="label">Gider</div></div><div class="summary-item"><div class="amount" style="color:'+(g-gr>=0?'var(--success)':'var(--danger)')+'">'+fmt(g-gr)+' TL</div><div class="label">Kar/Zarar</div></div></div>'+
    '<div class="card"><div class="card-header"><h3>Islemler</h3></div><div class="card-body">'+
    (d.islemler.length===0?'<div class="empty-state"><p>Henuz islem yok.</p></div>'
      :'<table><tr><th>Tarih</th><th>Tur</th><th>Kategori</th><th>Aciklama</th><th>Tutar</th><th></th></tr>'+
      d.islemler.map(i=>'<tr><td>'+tarih(i.tarih)+'</td><td><span class="badge '+(i.tur==='gelir'?'badge-green':'badge-red')+'">'+i.tur+'</span></td><td>'+i.kategori+'</td><td>'+(i.aciklama||'')+'</td><td>'+fmt(i.tutar)+' TL</td><td><button class="btn btn-danger btn-sm" onclick="silIslem('+i.id+')">X</button></td></tr>').join('')+
      '</table>')+'</div></div>'}

async function silIslem(id){if(!confirm('Sil?'))return;await apiCall('DELETE','/islemler/'+id);loadPage('muhasebe')}

function islemEkleModal(){
  showModal('Yeni Islem','<div class="form-group"><label>Tur</label><select id="modalTur"><option value="gelir">Gelir</option><option value="gider">Gider</option></select></div><div class="form-group"><label>Kategori</label><input id="modalKat" placeholder="bilet, akaryakit..."></div><div class="form-group"><label>Tutar</label><input id="modalTut" type="number" step="0.01"></div><div class="form-group"><label>Aciklama</label><input id="modalAcik" placeholder="..."></div><div class="form-group"><label>Musteri</label><input id="modalMus" placeholder="..."></div><div class="form-group"><label>Odeme</label><select id="modalOde"><option value="nakit">Nakit</option><option value="kredi_karti">Kredi Karti</option><option value="havale">Havale</option><option value="qr">QR</option></select></div>',
  async()=>{const b={tur:document.getElementById('modalTur').value,kategori:document.getElementById('modalKat').value,tutar:parseFloat(document.getElementById('modalTut').value),aciklama:document.getElementById('modalAcik').value,musteri_adi:document.getElementById('modalMus').value,odeme_yontemi:document.getElementById('modalOde').value};if(!b.kategori||!b.tutar){alert('Zorunlu!');return};const r=await apiCall('POST','/islemler',b);if(r){closeModal();loadPage('muhasebe')}},'Ekle')
}

async function renderAnaliz(c){
  const n=new Date();
  c.innerHTML='<div class="analiz-kontrol"><h3>Dukkan Analizi</h3><select id="analizAy" onchange="loadAnaliz()">'+
    ['Ocak','Subat','Mart','Nisan','Mayis','Haziran','Temmuz','Agustos','Eylul','Ekim','Kasim','Aralik'].map((a,i)=>'<option value="'+(i+1)+'"'+(i+1==n.getMonth()+1?' selected':'')+'>'+a+'</option>').join('')+
    '</select><select id="analizYil" onchange="loadAnaliz()"><option value="2026">2026</option><option value="2025">2025</option></select></div><div id="analizContent"><div class="loading"><div class="spinner"></div> Yukleniyor...</div></div>';await loadAnaliz()}

async function loadAnaliz(){
  const ay=document.getElementById('analizAy').value,yil=document.getElementById('analizYil').value,c=document.getElementById('analizContent');
  c.innerHTML='<div class="loading"><div class="spinner"></div> Yukleniyor...</div>';
  const d=await apiCall('GET','/analiz?ay='+ay+'&yil='+yil);
  if(!d){c.innerHTML='<div class="empty-state"><p>Veri yok.</p></div>';return}
  const m={};d.aylik_veri.forEach(v=>{if(!m[v.ay])m[v.ay]={gelir:0,gider:0};m[v.ay][v.tur]=v.toplam});
  const mx=Math.max(...Object.values(m).flatMap(v=>[v.gelir,v.gider]),1);
  const ayA=['Ocak','Subat','Mart','Nisan','Mayis','Haziran','Temmuz','Agustos','Eylul','Ekim','Kasim','Aralik'];
  c.innerHTML='<div class="grid-2"><div class="chart-container"><h3>Aylik Gelir-Gider</h3>'+
    Object.entries(m).map(([no,v])=>'<div class="chart-bar"><span class="label">'+ayA[no-1]+'</span><div style="flex:1"><div class="bar-track" style="height:18px;margin-bottom:4px"><div class="bar-fill green" style="width:'+(v.gelir/mx*100)+'%">'+(v.gelir>0?fmt(v.gelir):'')+'</div></div><div class="bar-track" style="height:18px"><div class="bar-fill red" style="width:'+(v.gider/mx*100)+'%">'+(v.gider>0?fmt(v.gider):'')+'</div></div></div></div>').join('')+
    '</div><div class="chart-container"><h3>Kategoriler</h3>'+
    (d.kategori_dagilim.length===0?'<div class="empty-state"><p>Veri yok.</p></div>'
      :d.kategori_dagilim.map(k=>{const mk=Math.max(...d.kategori_dagilim.map(x=>x.toplam));return '<div class="chart-bar"><span class="label">'+k.kategori+'</span><div class="bar-track"><div class="bar-fill blue" style="width:'+(k.toplam/mk*100)+'%">'+fmt(k.toplam)+' TL</div></div></div>'}).join(''))+'</div></div>'}

async function renderEgitim(c){
  c.innerHTML='<div class="loading"><div class="spinner"></div> Yukleniyor...</div>';
  const e=await apiCall('GET','/egitimler'),p=await apiCall('GET','/egitimler/progress');
  if(!e)return;const tam=p?.tamamlanan_ids||[];
  const clr={baslangic:'badge-green',orta:'badge-gold',ileri:'badge-red'},zrk={baslangic:'Baslangic',orta:'Orta',ileri:'Ileri'};
  c.innerHTML='<div style="margin-bottom:24px"><h3>Dijital Egitim</h3><p style="color:var(--text-light)">'+(p?'Ilerleme: '+p.tamamlanan_sayisi+'/'+p.toplam_sayisi+' ders':'')+'</p></div>'+
    '<div class="egitim-grid">'+e.map(eg=>{
      const t=tam.includes(eg.id),rn=eg.kategori==='muhasebe'?'muhasebe':eg.kategori==='pazarlama'?'pazarlama':'dijital';
      return '<div class="egitim-card" onclick="egitimDetay('+eg.id+')"><div class="card-top '+rn+'">'+(eg.kategori==='muhasebe'?'MH':eg.kategori==='pazarlama'?'PA':'DI')+'</div><div class="card-body"><span class="badge '+(clr[eg.zorluk]||'badge-blue')+'">'+(zrk[eg.zorluk]||eg.zorluk)+'</span><h4>'+eg.baslik+'</h4><p>'+eg.icerik.substring(0,100)+'...</p><div class="egitim-meta"><span>'+eg.sure+' dk</span>'+(t?'<span style="color:var(--success)">Tamam</span>':'')+'</div><div class="egitim-progress"><div class="fill" style="width:'+(t?100:0)+'%"></div></div></div></div>'
    }).join('')+'</div>'
}

function egitimDetay(id){
  const e=window._egitimData.find(x=>x.id===id);if(!e)return;
  const tam=window._tamamlanan.includes(id);
  showModal(e.baslik,'<div style="line-height:1.8"><p>'+e.icerik+'</p></div>',
    tam?null:async()=>{const r=await apiCall('POST','/egitimler/'+id+'/tamamla');if(r){closeModal();loadPage('egitim')}},tam?'Kapat':'Tamamla')
}

async function renderWhatsApp(c){
  c.innerHTML='<div class="loading"><div class="spinner"></div> Yukleniyor...</div>';
  const d=await apiCall('GET','/whatsapp/mesajlar');
  if(!d)return;
  c.innerHTML='<div class="muhasebe-header"><div><h3>WhatsApp Mesajlari</h3></div></div><div class="card"><div class="card-header"><h3>Mesajlar</h3></div><div class="card-body">'+
    (d.length===0?'<div class="empty-state"><p>Henuz mesaj yok.</p></div>':d.map(m=>'<div class="whatsapp-mesaj '+m.yon+'"><div class="mesaj-icerik"><div class="meta">'+(m.musteri_adi||'?')+' - '+tarih(m.tarih)+'</div><div class="text">'+m.mesaj+'</div></div></div>').join(''))+'</div></div>'}

async function renderCari(c){
  c.innerHTML='<div class="loading"><div class="spinner"></div> Yukleniyor...</div>';
  const d=await apiCall('GET','/cari');if(!d)return;
  c.innerHTML='<div class="muhasebe-header"><div><h3>Cari Hesap</h3></div></div><div class="card"><div class="card-body">'+
    (d.length===0?'<div class="empty-state"><p>Kayit yok.</p></div>':'<table><tr><th>Musteri</th><th>Borc</th><th>Alacak</th><th>Bakiye</th></tr>'+
    d.map(cr=>'<tr><td>'+cr.musteri_adi+'</td><td style="color:var(--danger)">'+fmt(cr.borc)+' TL</td><td style="color:var(--success)">'+fmt(cr.alacak)+' TL</td><td style="font-weight:700;color:'+(cr.bakiye>0?'var(--danger)':'var(--success)')+'">'+fmt(Math.abs(cr.bakiye))+' TL</td></tr>').join('')+'</table>')+'</div></div>'}

async function renderUrunler(c){
  c.innerHTML='<div class="loading"><div class="spinner"></div> Yukleniyor...</div>';
  const d=await apiCall('GET','/urunler');if(!d)return;
  c.innerHTML='<div class="muhasebe-header"><div><h3>Urunlerim</h3></div><button class="btn btn-primary" onclick="urunEkleModal()">+ Yeni Urun</button></div><div class="card"><div class="card-body">'+
    (d.length===0?'<div class="empty-state"><p>Urun yok.</p></div>':'<table><tr><th>Urun</th><th>Fiyat</th><th>Stok</th><th></th></tr>'+
    d.map(u=>'<tr><td>'+u.ad+'</td><td style="font-weight:700;color:var(--success)">'+fmt(u.fiyat)+' TL</td><td><span class="badge '+(u.stok>0?'badge-green':'badge-red')+'">'+u.stok+'</span></td><td><button class="btn btn-danger btn-sm" onclick="silUrun('+u.id+')">X</button></td></tr>').join('')+'</table>')+'</div></div>'}

function urunEkleModal(){
  showModal('Yeni Urun','<div class="form-group"><label>Ad</label><input id="modalUAd"></div><div class="form-group"><label>Fiyat</label><input id="modalUF" type="number" step="0.01"></div><div class="form-group"><label>Stok</label><input id="modalUS" type="number" value="0"></div>',
  async()=>{const b={ad:document.getElementById('modalUAd').value,fiyat:parseFloat(document.getElementById('modalUF').value),stok:parseInt(document.getElementById('modalUS').value)||0,kategori:'',birim:'adet',aciklama:''};if(!b.ad){alert('Ad zorunlu!');return};const r=await apiCall('POST','/urunler',b);if(r){closeModal();loadPage('urunler')}},'Ekle')}

async function silUrun(id){if(!confirm('Sil?'))return;await apiCall('DELETE','/urunler/'+id);loadPage('urunler')}

async function renderProfil(c){
  const e=getEsnaf();if(!e)return;
  c.innerHTML='<div class="profil-header"><div class="profil-avatar">'+e.firma_adi[0].toUpperCase()+'</div><div class="profil-info"><h2>'+e.firma_adi+'</h2><p>'+e.sahip_adi+'</p></div></div>'+
    '<div class="card"><div class="card-header"><h3>Profil</h3></div><div class="card-body"><table><tr><td>Firma</td><td>'+e.firma_adi+'</td></tr><tr><td>Sahip</td><td>'+e.sahip_adi+'</td></tr><tr><td>Email</td><td>'+e.email+'</td></tr><tr><td>Telefon</td><td>'+e.telefon+'</td></tr></table></div></div>'+
    '<div class="card" style="margin-top:24px"><div class="card-body"><button class="btn btn-danger" onclick="logout()" style="width:100%">Cikis Yap</button></div></div>'}

document.addEventListener('DOMContentLoaded',()=>{if(isAuth()){navigate('dashboard');updateSidebar()}else navigate('giris')});
