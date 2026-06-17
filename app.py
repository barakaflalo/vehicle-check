"""
בדיקת רכב ישראל — גרסה מלאה v3
==================================
הפעלה: pip install flask requests → python app.py → http://localhost:5000
"""
from flask import Flask, jsonify
import requests, re, json, os
from datetime import datetime

app = Flask(__name__)
API = "https://data.gov.il/api/3/action/datastore_search"
PKG = "https://data.gov.il/api/3/action/package_show"
HDR = {"User-Agent": "Mozilla/5.0"}
KM_FILE = "km_history.json"

KNOWN = {
    "vehicle":"053cea08-09bc-40ec-8f7a-156f0677aff3",
    "history1":"56063a99-8a3e-4ff4-912e-5966c0279bad",
    "history2":"bb2355dc-9ec7-4f06-9c3f-3344672171da",
    "recall":"36bf1404-0be4-49d2-82dc-2f1ead4a8b93",
    "disabled":"c8b9f9c8-4612-4068-934f-d4acd2e3c06e",
    "wltp":"142afde2-6228-49f9-8a29-9b6c3a0cbe40",
}
DATASETS_TO_DISCOVER = {
    "motorcycle":"motorcycle","heavy_truck":"heavy-truck",
    "bus":"kli_rechev_ciburiim","bus_fleet":"bus_fleet",
    "construction":"construction_equipment","electric":"rechavim_hashmalim",
    "personal_import":"personal_import_vehicles",
    "inactive_w_model":"rechev_le_pail_with_degem",
    "inactive_no_model":"rechev_le_pail_without-degem",
    "cancelled":"reshev_bitul_sofi","recall_notices":"recall",
    "filters":"vehicles_filters_reduce_emissions","aircraft":"aircraft_data_il",
    "disabled_tag":"rechev-tag-nachim",
}
DISCOVERED = {}

# ====== תרגום מלא ======
H = {
    # זיהוי
    "mispar_rechev":"מספר רכב","shnat_yitzur":"שנת ייצור",
    "moed_aliya_lakvish":"עלייה לכביש","tokef_dt":"תוקף רישיון",
    "mivchan_acharon_dt":"טסט אחרון","baalut":"בעלות",
    "misgeret":"שלדה (VIN)","horaat_rishum":"הוראת רישום",
    "mispar_shilda":"מספר שלדה","mispar_shildah":"מספר שלדה",
    # יצרן
    "tozeret_nm":"שם יצרן","tozeret_cd":"קוד יצרן","degem_nm":"שם דגם",
    "degem_cd":"קוד דגם","kinuy_mishari":"כינוי מסחרי","sug_degem":"סוג דגם",
    "ramat_gimur":"רמת גימור","tozeret_eretz_nm":"ארץ ייצור","tozar":"מותג",
    # מכני
    "degem_manoa":"דגם מנוע","sug_delek_nm":"סוג דלק","sug_delek_cd":"קוד דלק",
    "delek_cd":"קוד דלק","delek_nm":"סוג דלק",
    "nefach_manoa":"נפח מנוע (סמ״ק)","nefah_manoa":"נפח מנוע (סמ״ק)",
    "hanaa_cd":"קוד הנעה","hanaa_nm":"סוג הנעה",
    "technologiat_hanaa_cd":"קוד טכנולוגיית הנעה","technologiat_hanaa_nm":"טכנולוגיית הנעה",
    "koah_sus":"כוח סוס (כ״ס)","mispar_susar":"כוח סוס",
    "merkav":"מרכב","mishkal_kolel":"משקל כולל (ק״ג)",
    "mishkal_azmi":"משקל עצמי (ק״ג)","mishkal_max":"משקל מרבי (ק״ג)",
    "mishkal_mitan_harama":"משקל מיתן הרמה (ק״ג)",
    "kosher_grira_bli_blamim":"כושר גרירה ללא בלמים (ק״ג)",
    "kosher_grira_im_blamim":"כושר גרירה עם בלמים (ק״ג)",
    "mispar_tsirim":"מספר צירים",
    # מראה
    "tzeva_cd":"קוד צבע","tzeva_rechev":"צבע","zmig_kidmi":"צמיג קדמי",
    "zmig_ahori":"צמיג אחורי","mispar_dlatot":"מספר דלתות",
    "mispar_moshavim":"מספר מושבים",
    # סיווג
    "ramat_eivzur_betihuty":"רמת אבזור בטיחותי","kvutzat_zihum":"קבוצת זיהום",
    "kvuzat_agra_cd":"קבוצת אגרה","sug_tkina_cd":"קוד תקינה",
    "sug_tkina_nm":"סוג תקינה","tkina_EU":"תקינה אירופאית",
    "madad_yarok":"מדד ירוק","nikud_betihut":"ניקוד בטיחות",
    "sug_mamir_nm":"סוג ממיר","sug_mamir_cd":"קוד ממיר",
    "sug_rechev":"סוג רכב",
    # בטיחות אקטיבית
    "abs_ind":"ABS","bakarat_yatzivut_ind":"בקרת יציבות (ESP)",
    "bakarat_stiya_menativ_ind":"בקרת סטייה מנתיב",
    "bakarat_stiya_menativ_makor_hatkana":"מקור התקנה — סטייה",
    "bakarat_stiya_activ_stearing_ind":"בקרת סטייה אקטיבית",
    "bakarat_shyut_adaptivit_ind":"בקרת שיוט אדפטיבית",
    "bakarat_mehirut_isa_ind":"בקרת מהירות ISA",
    "blima_otomatit_nesia_leahor_ind":"בלימה אוטומטית בנסיעה לאחור",
    "blimat_hirum_lifnei_holhei_regel_ofanaim_ind":"בלימת חירום — הולכי רגל ואופניים",
    "maarechet_ezer_labalam_ind":"מערכת עזר לבלימה",
    "nitur_merhak_milfanim_ind":"ניטור מרחק מלפנים",
    "nitur_merhak_milfanim_makor_hatkana":"מקור — ניטור מרחק",
    "zihuy_holchey_regel_ind":"זיהוי הולכי רגל",
    "zihuy_holchey_regel_makor_hatkana":"מקור — זיהוי הולכי רגל",
    "zihuy_matzav_hitkarvut_mesukenet_ind":"זיהוי התקרבות מסוכנת",
    "zihuy_rechev_do_galgali":"זיהוי רכב דו-גלגלי",
    "zihuy_tamrurey_tnua_ind":"זיהוי תמרורים",
    "zihuy_tamrurey_tnua_makor_hatkana":"מקור — זיהוי תמרורים",
    "zihuy_beshetah_nistar_ind":"זיהוי בשטח מת (נסתר)",
    "hitnagshut_cad_shetah_met_ind":"התנגשות קדמית — שטח מת",
    "teura_automatit_benesiya_kadima_ind":"תאורה אוטומטית בנסיעה",
    "shlita_automatit_beorot_gvohim_ind":"שליטה אוטומטית באורות גבוהים",
    "shlita_automatit_beorot_gvohim_makor_hatkana":"מקור — אורות גבוהים",
    # אבזור
    "automatic_ind":"גיר אוטומטי","mazgan_ind":"מזגן",
    "hege_koah_ind":"הגה כוח","matzlemat_reverse_ind":"מצלמת רוורס",
    "galgaley_sagsoget_kala_ind":"גלגלי סגסוגת קלה",
    "hayshaney_hagorot_ind":"חישני חגורות",
    "hayshaney_lahatz_avir_batzmigim_ind":"חישני לחץ אוויר בצמיגים",
    "halonot_hashmal_source":"חלונות חשמליים","mispar_halonot_hashmal":"מס׳ חלונות חשמל",
    "kariot_avir_source":"כריות אוויר","mispar_kariot_avir":"מספר כריות אוויר",
    "halon_bagg_ind":"חלון באגאז׳","argaz_ind":"ארגז",
    "alco_lock_ind":"נעילת אלכוהול",
    # פליטות
    "CO2_WLTP":"CO₂ WLTP (g/km)","CO2_WLTP_NEDC":"CO₂ NEDC (g/km)",
    "CO_WLTP":"CO WLTP (mg/km)","HC_WLTP":"HC WLTP (mg/km)",
    "NOX_WLTP":"NOx WLTP (mg/km)",
    "kamut_CO2_city":"CO₂ עירוני","kamut_CO2_hway":"CO₂ בינעירוני",
    "kamut_CO_city":"CO עירוני","kamut_CO_hway":"CO בינעירוני",
    "kamut_HC_city":"HC עירוני","kamut_HC_hway":"HC בינעירוני",
    "kamut_NOX_city":"NOx עירוני","kamut_NOX_hway":"NOx בינעירוני",
    # בעלויות/היסטוריה
    "baalut_nm":"סוג בעלות","baalut_dt":"תאריך בעלות","baalut_cd":"קוד בעלות",
    "rishum_rishon_dt":"רישום ראשון","mkoriut_nm":"מקוריות","mispar_manoa":"מספר מנוע",
    "kilometer_test_aharon":"קילומטראז׳","mispar_baaluyot_kodem":"בעלויות קודמות",
    # ריקול
    "recall_number":"מספר ריקול","recall_description":"תיאור",
    "tozeret_rechev":"יצרן","degem_rechev":"דגם","status":"סטטוס",
    # מטוסים
    "aircraft_type":"סוג כלי טיס","aircraft_model":"דגם","registration_mark":"סימן רישום",
    "owner_name":"שם בעלים",
    # אופנועים
    "hespek":"הספק (כ״ס)","kod_mehirut_zmig_ahori":"קוד מהירות צמיג אחורי",
    "kod_mehirut_zmig_kidmi":"קוד מהירות צמיג קדמי",
    "kod_omes_zmig_ahori":"קוד עומס צמיג אחורי",
    "kod_omes_zmig_kidmi":"קוד עומס צמיג קדמי",
    "mida_zmig_ahori":"מידת צמיג אחורי","mida_zmig_kidmi":"מידת צמיג קדמי",
    "mispar_mekomot_leyd_nahag":"מקומות ליד נהג",
    # היסטוריה ושינויים
    "shinui_mivne_dt":"תאריך שינוי","sug_shinui":"סוג שינוי",
    "gapam_ind":"גפ״מ (גז)","shinui_mivne_ind":"שינוי מבנה",
    "shinui_zmig_ind":"שינוי צמיגים","shnui_zeva_ind":"שינוי צבע",
    "mispar_shildot":"מספר שלדה",
}

# שדות בוליאניים
BOOLS = {k for k in H if k.endswith("_ind")}

# ====== קבוצות שדות לרכב ======
VEH_GROUPS = [
    ("🪪","זיהוי ורישוי",["mispar_rechev","shnat_yitzur","moed_aliya_lakvish","tokef_dt","mivchan_acharon_dt","baalut","horaat_rishum","rishum_rishon_dt"]),
    ("🚗","יצרן ודגם",["tozeret_nm","tozeret_cd","degem_nm","degem_cd","kinuy_mishari","sug_degem","ramat_gimur","tozeret_eretz_nm","tozar"]),
    ("⚙️","מפרט מכני",["misgeret","mispar_manoa","kilometer_test_aharon","degem_manoa","sug_delek_nm","nefach_manoa","nefah_manoa","hanaa_nm","technologiat_hanaa_nm","koah_sus","mispar_susar","hespek","zmig_kidmi","zmig_ahori","mida_zmig_kidmi","mida_zmig_ahori","merkav","mishkal_kolel","mishkal_azmi","mishkal_max","mishkal_mitan_harama","kosher_grira_bli_blamim","kosher_grira_im_blamim","mispar_tsirim","mispar_mekomot_leyd_nahag"]),
    ("🎨","מראה וגוף",["tzeva_rechev","tzeva_cd","kod_mehirut_zmig_kidmi","kod_mehirut_zmig_ahori","kod_omes_zmig_kidmi","kod_omes_zmig_ahori","mispar_dlatot","mispar_moshavim"]),
    ("📊","סיווג ותקינה",["ramat_eivzur_betihuty","kvutzat_zihum","kvuzat_agra_cd","sug_tkina_nm","sug_tkina_cd","tkina_EU","madad_yarok","nikud_betihut","sug_mamir_nm","sug_mamir_cd","sug_rechev"]),
]

# ====== קבוצות WLTP ======
WLTP_GROUPS = [
    ("🛡️","מערכות בטיחות אקטיבית",["abs_ind","bakarat_yatzivut_ind","bakarat_stiya_menativ_ind","bakarat_stiya_menativ_makor_hatkana","bakarat_stiya_activ_stearing_ind","bakarat_shyut_adaptivit_ind","bakarat_mehirut_isa_ind","blima_otomatit_nesia_leahor_ind","blimat_hirum_lifnei_holhei_regel_ofanaim_ind","maarechet_ezer_labalam_ind","nitur_merhak_milfanim_ind","nitur_merhak_milfanim_makor_hatkana"]),
    ("👁️","מערכות זיהוי וחיישנים",["zihuy_holchey_regel_ind","zihuy_holchey_regel_makor_hatkana","zihuy_matzav_hitkarvut_mesukenet_ind","zihuy_rechev_do_galgali","zihuy_tamrurey_tnua_ind","zihuy_tamrurey_tnua_makor_hatkana","zihuy_beshetah_nistar_ind","hitnagshut_cad_shetah_met_ind","hayshaney_hagorot_ind","hayshaney_lahatz_avir_batzmigim_ind"]),
    ("💡","תאורה ואורות",["teura_automatit_benesiya_kadima_ind","shlita_automatit_beorot_gvohim_ind","shlita_automatit_beorot_gvohim_makor_hatkana"]),
    ("🪑","אבזור ונוחות",["automatic_ind","mazgan_ind","hege_koah_ind","matzlemat_reverse_ind","galgaley_sagsoget_kala_ind","halonot_hashmal_source","mispar_halonot_hashmal","kariot_avir_source","mispar_kariot_avir","halon_bagg_ind","argaz_ind","alco_lock_ind"]),
    ("⛽","פליטות ודלק",["CO2_WLTP","CO2_WLTP_NEDC","CO_WLTP","HC_WLTP","NOX_WLTP","kamut_CO2_city","kamut_CO2_hway","kamut_CO_city","kamut_CO_hway","kamut_HC_city","kamut_HC_hway","kamut_NOX_city","kamut_NOX_hway"]),
    ("📏","מידות, משקל וביצועים",["koah_sus","nefach_manoa","nefah_manoa","mishkal_kolel","mishkal_azmi","kosher_grira_bli_blamim","kosher_grira_im_blamim","mispar_dlatot","mispar_moshavim","merkav","mispar_kariot_avir"]),
    ("📋","סיווג ותקינה",["madad_yarok","nikud_betihut","kvutzat_zihum","kvuzat_agra_cd","sug_tkina_nm","sug_tkina_cd","sug_mamir_nm","sug_mamir_cd","sug_degem","ramat_gimur","technologiat_hanaa_nm","hanaa_nm"]),
]


def tr(k):
    if k in H: return H[k]
    for hk in H:
        if len(k)>4 and (hk.startswith(k) or k.startswith(hk)):
            return H[hk]
    return k

def trv(k,v):
    s=str(v).strip()
    if k in BOOLS or k.endswith("_ind"):
        if s=="1":return "כן ✓"
        if s=="0":return "לא"
    if s=="יצרן":return "יצרן ✓"
    return s

def fetch(rid,flt,lim=100):
    try:
        r=requests.get(API,params={"resource_id":rid,"filters":json.dumps(flt),"limit":lim},headers=HDR,timeout=15)
        if r.status_code==200:return r.json().get("result",{}).get("records",[])
    except:pass
    return []

def discover_resources():
    global DISCOVERED
    print("🔍 מגלה מאגרים...")
    for key,ds in DATASETS_TO_DISCOVER.items():
        try:
            r=requests.get(PKG,params={"id":ds},headers=HDR,timeout=10)
            if r.status_code==200:
                for res in r.json().get("result",{}).get("resources",[]):
                    if res.get("datastore_active"):
                        DISCOVERED[key]=res["id"]
                        print(f"  ✅ {key}: {res['id'][:12]}...")
                        break
        except:pass
    print(f"  סה״כ: {len(DISCOVERED)} מאגרים\n")

def variants(c):
    v=[c]
    if len(c)==7:v.append("0"+c)
    elif len(c)==8 and c.startswith("0"):v.append(c[1:])
    return v

def find_km(r):
    for k in["kilometer_test_aharon","mispar_km","kilometer"]:
        v=r.get(k)
        if v and str(v).strip() not in("","0","None"):
            d=re.sub(r'\D','',str(v))
            if d:return int(d)
    return None

def find_date(r):
    for k in["mivchan_acharon_dt","test_dt","rishum_rishon_dt"]:
        v=r.get(k)
        if v and str(v).strip() not in("","None"):return str(v).split("T")[0]
    return None

def clean_rec(rec):
    o={}
    for k,v in rec.items():
        if k.startswith("_") or k in("mispar_rechev","rank"):continue
        if v is not None and str(v).strip() not in("","None","null"):
            val=str(v).split("T")[0] if "T" in str(v) else str(v)
            o[tr(k)]=trv(k,val)
    return o

def raw_rec(rec):
    """Like clean_rec but keeps original English keys for grouping"""
    o={}
    for k,v in rec.items():
        if k.startswith("_") or k in("mispar_rechev","rank"):continue
        if v is not None and str(v).strip() not in("","None","null"):
            o[k]=str(v).split("T")[0] if "T" in str(v) else str(v)
    return o

def load_km():
    if os.path.exists(KM_FILE):
        with open(KM_FILE,"r",encoding="utf-8") as f:return json.load(f)
    return {}

def save_km(p,km):
    if not km:return
    d=load_km()
    if p not in d:d[p]=[]
    t=datetime.now().strftime("%Y-%m-%d")
    for e in d[p]:
        if e.get("date")==t:return
    d[p].append({"date":t,"km":km})
    d[p].sort(key=lambda x:x["date"],reverse=True)
    with open(KM_FILE,"w",encoding="utf-8") as f:json.dump(d,f,ensure_ascii=False,indent=2)

def group_fields(raw, groups):
    """Sort raw dict fields into defined groups, leftover goes to 'אחר'"""
    result=[]
    used=set()
    for icon,title,fields in groups:
        items={}
        for f in fields:
            if f in raw:
                items[tr(f)]=trv(f,raw[f])
                used.add(f)
        if items:
            result.append({"icon":icon,"title":title,"fields":items})
    # leftover
    leftover={}
    for k,v in raw.items():
        if k not in used:
            leftover[tr(k)]=trv(k,v)
    if leftover:
        result.append({"icon":"📎","title":"נתונים נוספים","fields":leftover})
    return result


@app.route("/api/search/<plate>")
def search(plate):
    from flask import request as req
    clean=re.sub(r'\D','',plate)
    if len(clean)<2 or len(clean)>10:return jsonify({"error":"מספר רישוי לא תקין"}),400
    vrs=variants(clean)
    vtype=req.args.get("type","all")
    result={"plate":clean,"found_in":None}

    ALL_SOURCES=[
        ("vehicle",KNOWN["vehicle"],"רכב פרטי/מסחרי"),
        ("motorcycle",DISCOVERED.get("motorcycle"),"אופנוע"),
        ("heavy_truck",DISCOVERED.get("heavy_truck"),"משאית כבדה"),
        ("bus",DISCOVERED.get("bus"),"רכב ציבורי/אוטובוס"),
        ("construction",DISCOVERED.get("construction"),"כלי צמ״ה"),
        ("electric",DISCOVERED.get("electric"),"רכב חשמלי"),
        ("personal_import",DISCOVERED.get("personal_import"),"ייבוא אישי"),
        ("aircraft",DISCOVERED.get("aircraft"),"כלי טיס"),
    ]
    INACTIVE_SOURCES=["inactive_w_model","inactive_no_model","cancelled"]

    # Filter sources by type
    if vtype=="all":
        sources=ALL_SOURCES
    else:
        sources=[s for s in ALL_SOURCES if s[0]==vtype]

    vehicle=None
    for _,rid,label in sources:
        if not rid:continue
        for p in vrs:
            recs=fetch(rid,{"mispar_rechev":p},1)
            if recs:vehicle=recs[0];result["plate"]=p;result["found_in"]=label;break
        if vehicle:break

    if not vehicle:
        for db in INACTIVE_SOURCES:
            rid=DISCOVERED.get(db)
            if not rid:continue
            for p in vrs:
                recs=fetch(rid,{"mispar_rechev":p},1)
                if recs:vehicle=recs[0];result["plate"]=p;result["found_in"]="רכב לא פעיל / ירד מהכביש";break
            if vehicle:break

    if not vehicle:return jsonify({"error":f"מספר {clean} לא נמצא באף מאגר"}),404

    vrs=variants(result["plate"])

    # History (fetch early to merge mispar_manoa)
    h1=[]
    for p in vrs:h1.extend(fetch(KNOWN["history1"],{"mispar_rechev":p},200))
    km_history=[]
    for rec in h1:
        km=find_km(rec);date=find_date(rec)
        tokef=None
        for k in["tokef_dt","tokef"]:
            if rec.get(k):tokef=str(rec[k]).split("T")[0];break
        if km or date:km_history.append({"date":date,"km":km,"tokef":tokef})
    km_history.sort(key=lambda x:x.get("date") or "",reverse=True)
    result["km_history"]=km_history
    result["raw_history1"]=[clean_rec(r) for r in h1]
    latest_km=km_history[0]["km"] if km_history and km_history[0].get("km") else None
    save_km(result["plate"],latest_km)

    # WLTP (fetch early to merge koah_sus, nefach_manoa)
    wltp_raw={}
    dc=vehicle.get("degem_cd");tc=vehicle.get("tozeret_cd")
    if dc and tc:
        recs=fetch(KNOWN["wltp"],{"tozeret_cd":str(tc),"degem_cd":str(dc)},5)
        if recs:wltp_raw=raw_rec(recs[0])
    result["wltp_groups"]=group_fields(wltp_raw, WLTP_GROUPS) if wltp_raw else []

    # Vehicle grouped — merge key fields from WLTP and history
    vraw=raw_rec(vehicle)
    # Add from WLTP
    for f in["koah_sus","nefach_manoa","nefah_manoa","mishkal_kolel","mishkal_azmi","kosher_grira_bli_blamim","kosher_grira_im_blamim","mispar_moshavim","mispar_dlatot","merkav"]:
        if f not in vraw and f in wltp_raw:vraw[f]=wltp_raw[f]
    # Add from history
    if h1:
        h1r=raw_rec(h1[0])
        for f in["mispar_manoa","kilometer_test_aharon","mkoriut_nm"]:
            if f not in vraw and f in h1r:vraw[f]=h1r[f]
    result["vehicle_groups"]=group_fields(vraw, VEH_GROUPS)
    result["vehicle"]=vehicle

    # Ownership
    h2=[]
    for p in vrs:h2.extend(fetch(KNOWN["history2"],{"mispar_rechev":p},200))
    result["ownership"]=[clean_rec(r) for r in h2]

    # Recall
    recall=[]
    for p in vrs:recall.extend(fetch(KNOWN["recall"],{"mispar_rechev":p},50))
    result["recall"]=[clean_rec(r) for r in recall]

    # Disabled tag - field name has SPACE not underscore!
    dis=[]
    dis_rid = DISCOVERED.get("disabled_tag") or KNOWN["disabled"]
    for p in vrs:
        for field in ["MISPAR RECHEV","mispar_rechev"]:
            recs = fetch(dis_rid, {field: p}, 5)
            if recs: dis.extend(recs); break
            # Try as integer
            try:
                recs = fetch(dis_rid, {field: int(p)}, 5)
                if recs: dis.extend(recs); break
            except: pass
        if dis: break
    result["disabled_tag"]=len(dis)>0

    # Filters
    frid=DISCOVERED.get("filters")
    fd=[]
    if frid:
        for p in vrs:fd.extend(fetch(frid,{"mispar_rechev":p},10))
    result["filters"]=[clean_rec(r) for r in fd]

    # Local KM
    result["local_km"]=load_km().get(result["plate"],[])

    print(f"✅ {result['plate']} [{result['found_in']}] owners={len(h2)} recall={len(recall)} wltp={'✓' if wltp_raw else '✗'}")
    return jsonify(result)


@app.route("/")
def home():return HTML

HTML=r"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>בדיקת רכב ישראל</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:linear-gradient(135deg,#0f172a,#1e3a5f,#0f172a);min-height:100vh;color:#1e293b}
.hdr{text-align:center;padding:2.2rem 1rem 1.3rem}
.hdr h1{font-size:1.6rem;font-weight:800;color:#fff}
.hdr p{color:#94a3b8;font-size:.82rem;margin-top:.3rem}
.sb{max-width:540px;margin:0 auto;padding:0 1rem}
.si{display:flex;gap:8px;background:#fff;border-radius:14px;padding:6px;box-shadow:0 8px 32px rgba(0,0,0,.2)}
.si input{flex:1;border:none;outline:none;padding:.85rem 1rem;font-size:1.15rem;border-radius:10px;direction:ltr;text-align:center;font-weight:600;letter-spacing:.1em;color:#1e293b}
.si button{padding:.8rem 1.4rem;border:none;border-radius:10px;background:linear-gradient(135deg,#2563eb,#1d4ed8);color:#fff;font-weight:700;font-size:1rem;cursor:pointer;white-space:nowrap}
.si button:disabled{background:#94a3b8;cursor:not-allowed}
.cr{text-align:center;color:#64748b;font-size:.72rem;margin-top:.5rem}
.tb{cursor:pointer}.tb input{display:none}
.tb span{display:inline-block;padding:.4rem .7rem;border-radius:8px;font-size:.78rem;font-weight:600;background:rgba(255,255,255,.12);color:#94a3b8;border:1.5px solid transparent;transition:all .2s}
.tb input:checked+span{background:#fff;color:#1e3a5f;border-color:#2563eb;box-shadow:0 2px 8px rgba(37,99,235,.3)}
.res{max-width:660px;margin:1.2rem auto;padding:0 1rem 3rem}
.pb{text-align:center;margin-bottom:1rem;background:rgba(255,255,255,.08);border-radius:12px;padding:1rem}
.pn{display:inline-block;padding:.4rem 1.2rem;background:#fbbf24;border-radius:8px;font-weight:800;font-size:1.3rem;letter-spacing:.15em;color:#1e293b;direction:ltr;font-family:monospace;border:2px solid #1e293b}
.ct{margin:.4rem 0 0;color:#e2e8f0;font-size:1rem;font-weight:600}
.tp{margin:.2rem 0 0;color:#94a3b8;font-size:.78rem}
.al{padding:.7rem 1rem;border-radius:10px;margin-bottom:.5rem;font-weight:600;font-size:.88rem;text-align:center}
.al-r{background:#fef2f2;border:2px solid #fca5a5;color:#991b1b}
.al-g{background:#f0fdf4;border:2px solid #86efac;color:#166534}
.al-b{background:#eff6ff;border:2px solid #93c5fd;color:#1e40af}
.sec{background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);border:1px solid #e8ecf1;margin-bottom:.6rem;overflow:hidden}
.sec-h{display:flex;align-items:center;gap:8px;padding:.85rem 1.1rem;cursor:pointer;user-select:none;border-bottom:1px solid #f1f5f9}
.sec-h:hover{background:#f8fafc}
.sec-h h3{font-size:.9rem;font-weight:700;color:#1e3a5f;flex:1}
.sec-h .arr{color:#94a3b8;font-size:.8rem;transition:transform .2s}
.sec-b{display:none;padding:0}
.sec-b.open{display:block}
.fr{display:flex;justify-content:space-between;align-items:center;padding:.42rem 1.1rem;border-bottom:1px solid #f5f7fa}
.fr:last-child{border:none}
.fl{color:#64748b;font-size:.8rem;font-weight:500}
.fv{color:#1e293b;font-size:.83rem;font-weight:600;direction:ltr;text-align:left;max-width:55%}
.yes{color:#16a34a}.no{color:#94a3b8}
table{width:100%;border-collapse:collapse;font-size:.82rem}
thead tr{background:#f8fafc}
th{padding:.55rem .8rem;text-align:right;color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0}
td{padding:.45rem .8rem;border-bottom:1px solid #f1f5f9}
.km{font-weight:600;color:#2563eb;direction:ltr;text-align:right}
.eb{max-width:540px;margin:1rem auto;padding:1rem;background:#fef2f2;border:1px solid #fecaca;border-radius:10px;color:#991b1b;font-size:.9rem;text-align:center}
.sp{display:flex;flex-direction:column;align-items:center;padding:2rem}
.sr{width:40px;height:40px;border:4px solid #e2e8f0;border-top:4px solid #2563eb;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.sp p{color:#94a3b8;font-size:.85rem;margin-top:.8rem}
.cnt{font-size:.72rem;color:#94a3b8;font-weight:400;margin-right:.3rem}
@media print{
body{background:#fff!important}
.hdr,.sb,.cr,.tb,#recent,#about{display:none!important}
.pb{background:#f8f8f8!important;color:#000!important;-webkit-print-color-adjust:exact}
.pn{border:2px solid #000!important}
.ct,.tp{color:#333!important}
.sec-b{display:block!important}
.sec{break-inside:avoid;margin-bottom:4px}
.sec-h .arr{display:none}
.res{max-width:100%;padding:0}
.al{-webkit-print-color-adjust:exact;print-color-adjust:exact}
.disc{color:#333!important;border-color:#ccc!important;background:#f9f9f9!important;-webkit-print-color-adjust:exact}
.print-footer{display:block!important;color:#333!important}
button{display:none!important}
}
@media(max-width:500px){
.hdr h1{font-size:1.3rem}
.si input{font-size:1rem;padding:.7rem .5rem}
.si button{padding:.7rem 1rem;font-size:.9rem}
.tb span{padding:.3rem .5rem;font-size:.7rem}
.fr{padding:.35rem .8rem}
.fl{font-size:.75rem}.fv{font-size:.78rem}
}
.disc{margin-top:1.2rem;padding:1rem 1.2rem;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);border-radius:10px;color:#94a3b8;font-size:.72rem;line-height:1.5;text-align:center}
.print-footer{display:none}
</style>
</head>
<body>
<div class="hdr"><div style="font-size:2.5rem">🚘</div><h1>בדיקת רכב ישראל</h1>
<p>רכב • אופנוע • משאית • אוטובוס • צמ״ה • מטוס</p>
<button onclick="document.getElementById('about').style.display='flex'" style="margin-top:.6rem;padding:.35rem .9rem;border-radius:8px;border:1.5px solid rgba(255,255,255,.2);background:rgba(255,255,255,.08);color:#94a3b8;font-size:.8rem;cursor:pointer;font-weight:600">ℹ️ אודות</button>
</div>

<!-- About Modal -->
<div id="about" onclick="if(event.target===this)this.style.display='none'" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.6);z-index:999;justify-content:center;align-items:center;padding:1rem">
<div style="background:#fff;border-radius:16px;padding:2rem;max-width:380px;width:100%;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.3);position:relative">
<button onclick="document.getElementById('about').style.display='none'" style="position:absolute;top:12px;left:12px;border:none;background:none;font-size:1.3rem;cursor:pointer;color:#94a3b8">✕</button>
<div style="font-size:2.5rem;margin-bottom:.5rem">🚘</div>
<h2 style="font-size:1.2rem;color:#1e3a5f;margin-bottom:.3rem">בדיקת רכב ישראל</h2>
<p style="color:#64748b;font-size:.82rem;margin-bottom:1rem">נתוני רישוי, מפרט טכני, היסטוריית בעלויות וקילומטראז׳</p>
<div style="background:#f8fafc;border-radius:10px;padding:.8rem;margin-bottom:.8rem">
<p style="color:#1e293b;font-size:.85rem;font-weight:600">נוצר על ידי ברק אפללו</p>
<p style="color:#64748b;font-size:.78rem;margin-top:.2rem">במסגרת AppNest — קן האפליקציות</p>
</div>
<p style="color:#94a3b8;font-size:.72rem;margin-bottom:1rem">© 2026 · כל הזכויות שמורות לברק אפללו</p>
<a href="https://barakaflalo.github.io/appnest" target="_blank" style="display:inline-block;padding:.6rem 1.4rem;background:linear-gradient(135deg,#2563eb,#1d4ed8);color:#fff;border-radius:10px;text-decoration:none;font-weight:700;font-size:.85rem">🪺 AppNest — עוד אפליקציות בחינם</a>
</div></div>
<div class="sb"><div class="si">
<input id="pi" inputmode="numeric" placeholder="הזן מספר רישוי..." onkeydown="if(event.key==='Enter')go()">
<button id="btn" onclick="go()">🔍 חפש</button></div>
<div style="display:flex;flex-wrap:wrap;gap:6px;justify-content:center;margin-top:10px">
<label class="tb"><input type="radio" name="vt" value="all" checked><span>🔍 הכל</span></label>
<label class="tb"><input type="radio" name="vt" value="vehicle"><span>🚗 רכב</span></label>
<label class="tb"><input type="radio" name="vt" value="motorcycle"><span>🏍️ אופנוע</span></label>
<label class="tb"><input type="radio" name="vt" value="heavy_truck"><span>🚛 משאית</span></label>
<label class="tb"><input type="radio" name="vt" value="bus"><span>🚌 אוטובוס</span></label>
<label class="tb"><input type="radio" name="vt" value="construction"><span>🚜 צמ״ה</span></label>
<label class="tb"><input type="radio" name="vt" value="aircraft"><span>✈️ מטוס</span></label>
<label class="tb"><input type="radio" name="vt" value="electric"><span>⚡ חשמלי</span></label>
</div>
<p class="cr">data.gov.il — מאגרי משרד התחבורה</p></div>
<div class="disc" style="max-width:540px;margin:.8rem auto;padding:.7rem 1rem">⚠️ <strong>הבהרה:</strong> הנתונים נשאבים ממאגרי data.gov.il ומוצגים AS IS. אין אנו אחראים לדיוק המידע. <strong>יש לאמת מול הגורמים המוסמכים</strong> לפני קבלת החלטות.</div>
<div id="err"></div><div id="ld"></div><div id="recent"></div><div id="out"></div>
<script>
function fd(v){if(!v||v==='None'||v==='null'||v==='—')return'—';let d=String(v).split('T')[0].split(' ')[0],p=d.split('-');
if(p.length===3&&p[0].length===4)return p[2]+'/'+p[1]+'/'+p[0];
if(/^\d{6}$/.test(d))return d.slice(4,6)+'/'+d.slice(0,4);
if(/^\d{4}-\d{1,2}$/.test(d)){let pp=d.split('-');return pp[1].padStart(2,'0')+'/'+pp[0]}
return d}
function fp(s){if(!s)return'';s=String(s);if(s.length===8)return s.slice(0,3)+'-'+s.slice(3,5)+'-'+s.slice(5);
if(s.length===7)return s.slice(0,2)+'-'+s.slice(2,5)+'-'+s.slice(5);return s}
function toggle(el){let b=el.nextElementSibling;b.classList.toggle('open');el.querySelector('.arr').textContent=b.classList.contains('open')?'▴':'▾'}

// Recent searches
function getRecent(){try{return JSON.parse(localStorage.getItem('recent_searches')||'[]')}catch(e){return[]}}
function addRecent(plate,title){
let r=getRecent().filter(x=>x.p!==plate);
r.unshift({p:plate,t:title,d:new Date().toLocaleDateString('he-IL')});
if(r.length>8)r=r.slice(0,8);
try{localStorage.setItem('recent_searches',JSON.stringify(r))}catch(e){}}
function showRecent(){
const r=getRecent();if(!r.length)return;
let h='<div style="max-width:540px;margin:.8rem auto;padding:0 1rem"><p style="color:#64748b;font-size:.75rem;margin-bottom:.4rem">חיפושים אחרונים:</p><div style="display:flex;flex-wrap:wrap;gap:5px">';
r.forEach(x=>{h+=`<button onclick="document.getElementById('pi').value='${x.p}';go()" style="padding:.3rem .6rem;border-radius:7px;border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.08);color:#cbd5e1;font-size:.73rem;cursor:pointer;direction:ltr" title="${x.t}">${fp(x.p)}</button>`});
h+='</div></div>';document.getElementById('recent').innerHTML=h}
showRecent();

async function go(){
const input=document.getElementById('pi').value.replace(/[^0-9]/g,'');
if(input.length<2){se('נא להזין מספר רישוי');return}
document.getElementById('err').innerHTML='';document.getElementById('out').innerHTML='';
document.getElementById('ld').innerHTML='<div class="sp"><div class="sr"></div><p>מחפש בכל המאגרים...</p></div>';
document.getElementById('btn').disabled=true;
try{const vt=document.querySelector('input[name="vt"]:checked').value;
const r=await fetch('/api/search/'+input+'?type='+vt);const d=await r.json();
document.getElementById('ld').innerHTML='';document.getElementById('btn').disabled=false;
if(d.error){se(d.error);return}
const t=[d.vehicle?.tozeret_nm,d.vehicle?.kinuy_mishari||d.vehicle?.degem_nm].filter(Boolean).join(' ');
addRecent(d.plate,t);showRecent();render(d)}
catch(e){document.getElementById('ld').innerHTML='';document.getElementById('btn').disabled=false;se('שגיאה: '+e.message)}}
function se(m){document.getElementById('err').innerHTML='<div class="eb">⚠️ '+m+'</div>'}

function grpSec(icon,title,fields,open){
let rows='';for(const[k,v]of Object.entries(fields)){
let cls='';if(v==='כן ✓')cls=' yes';else if(v==='לא')cls=' no';
rows+=`<div class="fr"><span class="fl">${k}</span><span class="fv${cls}">${v}</span></div>`}
const cnt=Object.keys(fields).length;
return`<div class="sec"><div class="sec-h" onclick="toggle(this)"><span style="font-size:1.05rem">${icon}</span><h3>${title}<span class="cnt">(${cnt})</span></h3><span class="arr">${open?'▴':'▾'}</span></div><div class="sec-b${open?' open':''}">${rows}</div></div>`}

function tblSec(icon,title,arr,open){
if(!arr||!arr.length)return`<div class="sec"><div class="sec-h" onclick="toggle(this)"><span style="font-size:1.05rem">${icon}</span><h3>${title}<span class="cnt">(0)</span></h3><span class="arr">▾</span></div><div class="sec-b"><p style="text-align:center;color:#94a3b8;padding:1rem">אין נתונים</p></div></div>`;
const ks=[];arr.forEach(r=>Object.keys(r).forEach(k=>{if(!ks.includes(k))ks.push(k)}));
let t='<div style="overflow-x:auto"><table><thead><tr>';ks.forEach(k=>{t+=`<th>${k}</th>`});
t+='</tr></thead><tbody>';arr.forEach((r,i)=>{t+=`<tr style="background:${i%2?'#fafbfc':'#fff'}">`;
ks.forEach(k=>{t+=`<td style="white-space:nowrap">${r[k]||'—'}</td>`});t+='</tr>'});
t+='</tbody></table></div>';
return`<div class="sec"><div class="sec-h" onclick="toggle(this)"><span style="font-size:1.05rem">${icon}</span><h3>${title}<span class="cnt">(${arr.length})</span></h3><span class="arr">${open?'▴':'▾'}</span></div><div class="sec-b${open?' open':''}">${t}</div></div>`}

function render(d){
const v=d.vehicle;if(!v)return;
const title=[v.tozeret_nm,v.kinuy_mishari||v.degem_nm,v.shnat_yitzur].filter(Boolean).join(' • ');
let h=`<div class="pb"><div class="pn">${fp(d.plate)}</div>`;
if(title)h+=`<p class="ct">${title}</p>`;
if(d.found_in)h+=`<p class="tp">נמצא: ${d.found_in}</p>`;
h+='</div>';

// KM/year calculation
const yr=parseInt(v.shnat_yitzur);const kmVal=d.km_history&&d.km_history[0]?d.km_history[0].km:null;
if(yr&&kmVal&&yr>1990){const age=new Date().getFullYear()-yr;if(age>0){const perYear=Math.round(kmVal/age);
h+=`<div style="display:flex;gap:8px;margin-bottom:.6rem;flex-wrap:wrap">`;
h+=`<div style="flex:1;min-width:120px;background:#fff;border-radius:10px;padding:.7rem;text-align:center;border:1px solid #e8ecf1"><div style="font-size:.7rem;color:#64748b">ק״מ ממוצע/שנה</div><div style="font-size:1.1rem;font-weight:800;color:#2563eb">${perYear.toLocaleString()}</div></div>`;
h+=`<div style="flex:1;min-width:120px;background:#fff;border-radius:10px;padding:.7rem;text-align:center;border:1px solid #e8ecf1"><div style="font-size:.7rem;color:#64748b">גיל הרכב</div><div style="font-size:1.1rem;font-weight:800;color:#1e3a5f">${age} שנים</div></div>`;
h+=`<div style="flex:1;min-width:120px;background:#fff;border-radius:10px;padding:.7rem;text-align:center;border:1px solid #e8ecf1"><div style="font-size:.7rem;color:#64748b">ק״מ נוכחי</div><div style="font-size:1.1rem;font-weight:800;color:#16a34a">${Number(kmVal).toLocaleString()}</div></div>`;
h+=`</div>`}}

if(d.recall&&d.recall.length>0)h+=`<div class="al al-r">⚠️ ${d.recall.length} קריאות ריקול פתוחות!</div>`;
else h+='<div class="al al-g">✅ אין קריאות ריקול פתוחות</div>';
if(d.disabled_tag)h+='<div class="al al-g">♿ לרכב זה רשום תו חניה לנכה</div>';
else h+='<div class="al al-r">♿ אין תו חניה לנכה</div>';
if(d.found_in&&d.found_in.includes('לא פעיל'))h+='<div class="al al-r">🚫 רכב לא פעיל — ירד מהכביש!</div>';

// Vehicle groups
const vg=d.vehicle_groups||[];
vg.forEach((g,i)=>{h+=grpSec(g.icon,g.title,g.fields,i<2)});

// WLTP groups
const wg=d.wltp_groups||[];
if(wg.length)wg.forEach(g=>{h+=grpSec(g.icon,'WLTP — '+g.title,g.fields,false)});

// KM
const km=d.km_history||[];
let kh='';if(!km.length)kh='<p style="text-align:center;color:#94a3b8;padding:1rem">אין נתונים</p>';
else{kh='<table><thead><tr><th>#</th><th>תאריך</th><th>ק״מ</th><th>תוקף</th></tr></thead><tbody>';
km.forEach((r,i)=>{kh+=`<tr style="background:${i%2?'#fafbfc':'#fff'}"><td style="color:#94a3b8">${i+1}</td><td style="direction:ltr;text-align:right;font-weight:500">${fd(r.date)}</td><td class="km">${r.km?Number(r.km).toLocaleString()+' ק״מ':'—'}</td><td style="direction:ltr;text-align:right">${fd(r.tokef)}</td></tr>`});kh+='</tbody></table>'}
h+=`<div class="sec"><div class="sec-h" onclick="toggle(this)"><span style="font-size:1.05rem">📊</span><h3>קילומטראז׳ ממשלתי<span class="cnt">(${km.length})</span></h3><span class="arr">▴</span></div><div class="sec-b open">${kh}</div></div>`;

// Local KM
const lk=d.local_km||[];
if(lk.length){let lt='<table><thead><tr><th>#</th><th>תאריך דגימה</th><th>ק״מ</th></tr></thead><tbody>';
lk.forEach((r,i)=>{lt+=`<tr style="background:${i%2?'#fafbfc':'#fff'}"><td style="color:#94a3b8">${i+1}</td><td style="direction:ltr;text-align:right;font-weight:500">${fd(r.date)}</td><td class="km">${Number(r.km).toLocaleString()} ק״מ</td></tr>`});lt+='</tbody></table>';
h+=`<div class="sec"><div class="sec-h" onclick="toggle(this)"><span style="font-size:1.05rem">📈</span><h3>מעקב ק״מ אישי<span class="cnt">(${lk.length})</span></h3><span class="arr">▴</span></div><div class="sec-b open">${lt}</div></div>`}

// Ownership
if(d.ownership&&d.ownership.length)h+=tblSec('👤','היסטוריית בעלויות',d.ownership,true);
// Changes
if(d.raw_history1&&d.raw_history1.length)h+=tblSec('📋','שינויים ברכב',d.raw_history1,false);
// Recall
if(d.recall&&d.recall.length)h+=tblSec('🔔','פרטי ריקול',d.recall,true);
// Filters
if(d.filters&&d.filters.length)h+=tblSec('🌿','מסנני פליטות',d.filters,false);

// Print button
h+=`<div style="text-align:center;margin-top:1rem"><button onclick="window.print()" style="padding:.7rem 2rem;border:none;border-radius:10px;background:#1e3a5f;color:#fff;font-weight:700;font-size:.9rem;cursor:pointer">🖨️ הדפס / שמור PDF</button></div>`;

// Disclaimer
h+=`<div class="disc">⚠️ <strong>הבהרה חשובה:</strong> הנתונים המוצגים באתר זה נשאבים ממאגרי המידע הפתוחים של משרד התחבורה (data.gov.il) ומוצגים כפי שהם (AS IS). אין אנו אחראים לדיוק, שלמות או עדכניות המידע המוצג. <strong>יש לאמת כל נתון מול הגורמים המוסמכים</strong> (משרד הרישוי, מכון טסט מורשה) לפני קבלת החלטות. אתר זה אינו מהווה תחליף לבדיקה רשמית של הרכב.</div>`;

// Print-only footer with about info
h+=`<div class="print-footer">
<div style="border-top:1px solid #ccc;padding-top:.6rem;margin-top:.3rem;text-align:center">
<div style="font-size:.9rem;font-weight:700">🚘 בדיקת רכב ישראל</div>
<div style="font-size:.75rem;margin-top:.2rem">נוצר על ידי <strong>ברק אפללו</strong> במסגרת AppNest — קן האפליקציות</div>
<div style="font-size:.7rem;color:#666;margin-top:.15rem">© 2026 · כל הזכויות שמורות לברק אפללו · barakaflalo.github.io/appnest</div>
</div></div>`;

document.getElementById('out').innerHTML='<div class="res">'+h+'</div>'}
</script></body></html>"""

_discovered = False
@app.before_request
def ensure_discovered():
    global _discovered
    if not _discovered:
        discover_resources()
        _discovered = True

if __name__=="__main__":
    discover_resources()
    _discovered = True
    print("="*55)
    print("  🚘  בדיקת רכב ישראל — v3")
    print("  פתח: http://localhost:5000")
    print("="*55+"\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
