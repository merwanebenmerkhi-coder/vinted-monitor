from __future__ import annotations
import csv,json,logging,os,re,sys,time
from pathlib import Path
from typing import Any
import requests
from vinted import Vinted
ROOT=Path(__file__).resolve().parents[1]
STATE_PATH=ROOT/'data/seen_items.json'; MODELS_PATH=ROOT/'config/models.json'; PRICES_PATH=ROOT/'config/cdiscount_prices.csv'; BLACKLIST_PATH=ROOT/'config/blacklist.txt'; DEFECTS_PATH=ROOT/'config/defects.txt'
MIN_MARGIN=float(os.getenv('MIN_MARGIN_EUR','80')); MAX_ITEMS=int(os.getenv('MAX_ITEMS_PER_RUN','96'))
DISCORD_WEBHOOK_URL=os.getenv('DISCORD_WEBHOOK_URL','').strip(); VINTED_SEARCH_URL=os.getenv('VINTED_SEARCH_URL','').strip()
logging.basicConfig(level=logging.INFO,format='%(asctime)s | %(levelname)s | %(message)s')
def req(v,n):
 if not v: raise RuntimeError(f'Secret GitHub manquant : {n}')
 return v
def norm(t):
 return t.lower().replace('é','e').replace('è','e').replace('ê','e').replace('à','a').replace('ç','c').replace('’',"'")
def lines(p): return [norm(x.strip()) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def load_models(): return json.loads(MODELS_PATH.read_text(encoding='utf-8'))
def load_prices():
 out={}
 with PRICES_PATH.open(encoding='utf-8') as f:
  for r in csv.DictReader(f):
   raw=(r.get('cdiscount_price_eur') or '').strip().replace(',','.')
   if raw: out[(r['model'],int(r['storage_gb']))]=float(raw)
 return out
def load_state(): return json.loads(STATE_PATH.read_text(encoding='utf-8')) if STATE_PATH.exists() else {'initialized':False,'seen_ids':[]}
def save_state(s): STATE_PATH.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def detect_model(text,models):
 t=norm(text); aliases={'iPhone SE 2020':['iphone se 2020','iphone se 2'],'iPhone SE 2022':['iphone se 2022','iphone se 3'],'iPhone 17 Air':['iphone 17 air','iphone air 17']}
 for m in sorted(models,key=len,reverse=True):
  for c in [norm(m)]+[norm(x) for x in aliases.get(m,[])]:
   if c in t or c.replace(' ','') in t.replace(' ',''): return m
 return None
def detect_storage(text,allowed):
 t=norm(text)
 vals=re.findall(r'\b(64|128|256|512|1024)\s*(?:go|gb|g)\b',t)
 if re.search(r'\b1\s*(?:to|tb)\b',t): vals.append('1024')
 for v in vals:
  if int(v) in allowed:return int(v)
 return None
def is_bad(text,bl):
 t=norm(text); return any(x in t for x in bl)
def defects(text,terms):
 t=norm(text); return [x for x in terms if x in t][:8]
def dec(v):
 try:return float(str(v).replace(',','.'))
 except:return 0.0
def photo_url(item):
 p=getattr(item,'photo',None)
 if not p:return None
 for a in ('url','full_size_url','high_resolution_url'):
  v=getattr(p,a,None)
  if v:return str(v)
 return None
def describe(client,item):
 try:return client.fetch_offer_description(str(getattr(item,'url','') or '')) or ''
 except Exception as e: logging.warning('Description indisponible: %s',e); return ''
def notify(item,model,storage,total,resale,defs):
 image=photo_url(item); title=str(getattr(item,'title','') or f'{model} {storage} Go'); url=str(getattr(item,'url','') or '')
 embed={'title':f'{model} — {storage} Go','url':url,'description':f'**Prix d’achat total : {total:.2f} €**\n**Prix de revente estimé Cdiscount : {resale:.2f} €**\n**Écart brut : {resale-total:.2f} €**\n\n**Défauts indiqués :**\n'+(('\n'.join('• '+d for d in defs)) if defs else 'Aucun défaut détecté dans le texte.'),'fields':[{'name':'Titre de l’annonce','value':title[:1024],'inline':False}],'footer':{'text':'Vinted • vérification toutes les 5 minutes'}}
 if image: embed['image']={'url':image}
 r=requests.post(req(DISCORD_WEBHOOK_URL,'DISCORD_WEBHOOK_URL'),json={'username':'iPhone Deals Bot','content':'📱 **Nouvelle annonce correspondant à tes critères**','embeds':[embed]},timeout=25); r.raise_for_status()
def main():
 req(VINTED_SEARCH_URL,'VINTED_SEARCH_URL'); req(DISCORD_WEBHOOK_URL,'DISCORD_WEBHOOK_URL')
 models=load_models(); prices=load_prices(); bl=lines(BLACKLIST_PATH); dterms=lines(DEFECTS_PATH); state=load_state(); seen=set(map(str,state.get('seen_ids',[])))
 client=Vinted(domain='fr',language='fr-FR'); result=client.search(url=VINTED_SEARCH_URL,page=1,per_page=MAX_ITEMS,order='newest_first'); items=getattr(result,'items',[]) or []
 ids=[str(getattr(i,'id','')) for i in items if getattr(i,'id',None)]
 if not state.get('initialized'):
  save_state({'initialized':True,'seen_ids':ids}); requests.post(DISCORD_WEBHOOK_URL,json={'username':'iPhone Deals Bot','content':f'✅ Surveillance Vinted activée. {len(ids)} annonce(s) actuelle(s) enregistrée(s) comme référence.'},timeout=25).raise_for_status(); return 0
 updated=set(seen)
 for item in reversed(items):
  iid=str(getattr(item,'id','') or '')
  if not iid or iid in seen: continue
  title=str(getattr(item,'title','') or ''); desc=describe(client,item); text=title+'\n'+desc
  if is_bad(text,bl): updated.add(iid); continue
  model=detect_model(text,models)
  if not model: updated.add(iid); continue
  storage=detect_storage(text,models[model])
  if storage is None: updated.add(iid); continue
  resale=prices.get((model,storage))
  if resale is None: updated.add(iid); continue
  total=dec(getattr(item,'total_item_price',None))
  if total>0 and total<=resale-MIN_MARGIN:
   notify(item,model,storage,total,resale,defects(text,dterms)); time.sleep(1)
  updated.add(iid)
 ordered=list(dict.fromkeys(ids+list(updated))); save_state({'initialized':True,'seen_ids':ordered[:5000]}); return 0
if __name__=='__main__':
 try:sys.exit(main())
 except Exception:logging.exception('Échec du bot');sys.exit(1)
