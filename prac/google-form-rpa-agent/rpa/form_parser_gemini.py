import os, json, re, requests
from typing import Any, Dict, List
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv

# Load env early so main and library use same env context
load_dotenv()

# Prefer GEMINI_API_KEY, fall back to GOOGLE_API_KEY. Do not assert here –
# allow offline fallback if key missing or network blocked.
api = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
MODEL = os.environ.get('GEMINI_MODEL', 'models/gemini-2.5-flash')

if api:
    try:
        genai.configure(api_key=api)
    except Exception:
        # Do not block program start; we'll handle at call time
        pass

def fetch_form_html(u):
    r=requests.get(u,timeout=30); r.raise_for_status(); return r.text

def summarize_form_fields(html):
    s=BeautifulSoup(html,'lxml')
    fields={}
    # 1) Try direct DOM inputs first
    for inp in s.select('input[name^="entry."]'):
        name=inp.get('name','');
        if not name.startswith('entry.'): continue
        # Skip hidden/sentinel artifacts Google Forms adds for groups
        if name.endswith('_sentinel'): continue
        eid=name.split('.',1)[1]
        t=inp.get('type','text').lower()
        if t == 'hidden':
            # do not consider hidden inputs as user-fillable fields
            continue
        ft='text';
        if t=='radio': ft='choice'
        elif t=='checkbox': ft='checkbox'
        fields.setdefault(eid,{'entry_id':eid,'type':ft,'options':set(),'question_label':''})
    for ta in s.select('textarea[name^="entry."]'):
        eid=ta.get('name','').split('.',1)[1]
        fields.setdefault(eid,{'entry_id':eid,'type':'paragraph','options':set(),'question_label':''})
    for sel in s.select('select[name^="entry."]'):
        eid=sel.get('name','').split('.',1)[1]
        f=fields.setdefault(eid,{'entry_id':eid,'type':'dropdown','options':set(),'question_label':''})
        for o in sel.find_all('option'):
            txt=(o.get_text() or '').strip();
            if txt: f['options'].add(txt)
    # naive label grab
    for eid in list(fields):
        rep=s.select_one(f'[name="entry.{eid}"]')
        if rep:
            lab=rep.find_parent().get_text(' ', strip=True)
            fields[eid]['question_label']=lab[:200]

    if not fields:
        # 2) Fallback: parse embedded FB_PUBLIC_LOAD_DATA_ for Google Forms
        try:
            m = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[)', html)
            if m:
                start = m.end()-1
                count = 0; end = None
                for i in range(start, len(html)):
                    ch = html[i]
                    if ch == '[':
                        count += 1
                    elif ch == ']':
                        count -= 1
                        if count == 0:
                            end = i+1; break
                if end:
                    jtxt = html[start:end]
                    data = json.loads(jtxt)
                    # Questions array typically at data[1][1]
                    questions = []
                    if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list) and len(data[1]) > 1:
                        questions = data[1][1] or []
                    for q in questions:
                        # q format varies; guard heavily
                        if not isinstance(q, list) or len(q) < 5:
                            continue
                        qid = str(q[0]) if q and isinstance(q[0], (int,str)) else None
                        label = ''
                        if len(q) > 1 and isinstance(q[1], str):
                            label = q[1]
                        qtype = q[3] if len(q) > 3 else 0
                        # Map types
                        tmap = {0:'text',1:'paragraph',2:'choice',3:'checkbox',4:'dropdown',9:'date',10:'time'}
                        ftype = tmap.get(qtype, 'text')
                        # entry id lives inside q[4][0][0]
                        eid = None
                        try:
                            if isinstance(q[4], list) and len(q[4])>0 and isinstance(q[4][0], list) and len(q[4][0])>0:
                                if isinstance(q[4][0][0], (int,str)):
                                    eid = str(q[4][0][0])
                        except Exception:
                            eid = None
                        if not eid:
                            # skip if we cannot address the input
                            continue
                        # Attempt to extract options for selectable types (best-effort)
                        options = []
                        if ftype in ('choice','checkbox','dropdown'):
                            # Some forms store option labels under q[4][0][1] as list of [label, ...]
                            try:
                                opts = q[4][0][1] or []
                                for opt in opts:
                                    if isinstance(opt, list) and opt:
                                        txt = opt[0]
                                        if isinstance(txt, str) and txt.strip():
                                            options.append(txt.strip())
                            except Exception:
                                pass
                        fields[eid] = {
                            'entry_id': eid,
                            'type': ftype,
                            'options': set(options),
                            'question_label': (label or '')[:200]
                        }
        except Exception as e:
            # Silent fallback; return whatever we have (likely empty)
            print(f"⚠️  Failed to parse FB_PUBLIC_LOAD_DATA_: {e}")

    out=[]
    for eid,f in fields.items():
        out.append({'entry_id':eid,'question_label':f.get('question_label',''),'type':f['type'],'options':sorted(list(f['options']))})
    return out

def _extract_json_text(txt: str) -> str:
    """Try to extract a JSON object from arbitrary model output.
    Looks for json code fences first, then the last {...} block.
    Returns a JSON string or raises ValueError.
    """
    if not txt or not isinstance(txt, str):
        raise ValueError('Empty response text')

    s = txt.strip()
    # Prefer fenced ```json ... ``` blocks
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.IGNORECASE)
    if fence:
        candidate = fence.group(1).strip()
        if candidate:
            return candidate

    # Fall back to last JSON-looking object
    m = re.search(r"\{[\s\S]*\}\s*$", s)
    if m:
        return m.group(0)

    # If still nothing but contains braces at all, try widest range
    first = s.find('{'); last = s.rfind('}')
    if first != -1 and last > first:
        return s[first:last+1]

    raise ValueError('No JSON object found in model output')


def _guess_value(label: str, ftype: str, options: List[str], basic: Dict[str, Any]):
    """Heuristic fallback mapping for common fields from BASIC_INFO.
    Keeps logic intentionally simple and conservative.
    """
    l = (label or '').lower()
    def pick(keys, default=''):
        for k in keys:
            if k in basic and basic[k] not in (None, ''):
                return basic[k]
        return default

    if ftype in ('text','paragraph'):
        if 'email' in l:
            return pick(['email','mail'])
        if 'phone' in l or 'mobile' in l:
            return pick(['phone','phone_number','mobile'])
        if 'first name' in l:
            return pick(['first_name','firstname','given_name','name_first'])
        if 'last name' in l or 'surname' in l:
            return pick(['last_name','lastname','family_name','name_last'])
        if 'name' in l:
            # Prefer full name if available, otherwise compose
            full = pick(['name','full_name'])
            if full:
                return full
            fn = pick(['first_name','firstname'])
            ln = pick(['last_name','lastname'])
            return (fn + ' ' + ln).strip()
        if 'company' in l or 'organization' in l or 'organisation' in l:
            return pick(['company','organization','organisation','employer'])
        if 'title' in l or 'role' in l or 'position' in l:
            return pick(['title','role','position','job_title'])
        if 'city' in l:
            return pick(['city'])
        if 'state' in l or 'province' in l:
            return pick(['state','province'])
        if 'country' in l:
            return pick(['country'])
        if 'zip' in l or 'postal' in l:
            return pick(['zip','postal','postal_code','zip_code'])
        if 'address' in l:
            return pick(['address','street'])
        if 'website' in l or 'url' in l:
            return pick(['website','url'])
        if 'message' in l or 'comments' in l or 'notes' in l:
            return pick(['message','notes','comment'])
        return ''
    if ftype == 'date':
        v = pick(['date','dob','birthday'])
        return v if re.match(r"^\d{4}-\d{2}-\d{2}$", str(v or '')) else ''
    if ftype == 'time':
        v = pick(['time'])
        return v if re.match(r"^\d{2}:\d{2}$", str(v or '')) else ''
    if ftype in ('dropdown','choice'):
        # Choose a matching option if BASIC_INFO has a hint
        v = pick(['choice','selection','option','answer','value'])
        if isinstance(v, str) and options:
            for o in options:
                if str(o).strip().lower() == v.strip().lower():
                    return o
        return options[0] if options else ''
    if ftype == 'checkbox':
        v = basic.get('selections') or basic.get('options') or basic.get('answers') or []
        if isinstance(v, str):
            v = [v]
        # keep only matches
        ret = []
        for o in (v or []):
            for cand in options:
                if str(cand).strip().lower() == str(o).strip().lower():
                    ret.append(cand)
        return ret
    return ''


def _fallback_config(url: str, summary: List[Dict[str, Any]], basic: Dict[str, Any]) -> Dict[str, Any]:
    fields = []
    for f in summary:
        eid = f.get('entry_id')
        ql = f.get('question_label','')
        ftype = f.get('type','text')
        options = f.get('options') or []
        val = _guess_value(ql, ftype, options, basic)
        if ftype == 'checkbox' and not isinstance(val, list):
            val = [val] if val else []
        fields.append({
            'entry_id': eid,
            'question_label': ql,
            'type': ftype,
            'value': val,
            'option_hints': options or None,
        })
    return {'form_url': url, 'fields': fields}


def call_gemini(url, summary, basic, prompt_path):
    base_guidance = (
        open(prompt_path,'r',encoding='utf-8').read()
        if os.path.exists(prompt_path) else ''
    )
    # Construct a strict instruction that yields deterministic JSON schema
    field_spec = [
        {
            'entry_id': f.get('entry_id'),
            'question_label': f.get('question_label',''),
            'type': f.get('type','text'),
            'options': f.get('options',[]) or []
        } for f in summary
    ]
    instruction = (
        "You are mapping BASIC_INFO to Google Form fields.\n"
        "- Fill every field in FIELD_SPEC.\n"
        "- Use BASIC_INFO when it clearly matches the question.\n"
        "- If info is missing or unclear, IMAGINE a plausible value consistent with the field type.\n"
        "- For type 'dropdown' or 'choice', pick one of the provided options.\n"
        "- For 'checkbox', choose zero or more provided options.\n"
        "- For 'date' use format YYYY-MM-DD (e.g., 2025-06-09).\n"
        "- For 'time' use format HH:MM 24-hour (e.g., 09:45).\n"
        "- Output ONLY JSON with this schema: {\n"
        "    \"fields\": [ {\n"
        "        \"entry_id\": string,\n"
        "        \"question_label\": string,\n"
        "        \"type\": string,\n"
        "        \"value\": string | [string],\n"
        "        \"option_hints\": [string] | null\n"
        "    } ]\n"
        "}\n"
        "Do not add explanations. Return JSON only.\n"
    )
    full_prompt = (
        instruction + "\n" + base_guidance + "\n\n" +
        "FORM_URL\n" + url + "\n\n" +
        "FIELD_SPEC (JSON)\n" + json.dumps(field_spec, indent=2) + "\n\n" +
        "BASIC_INFO (JSON)\n" + json.dumps(basic, indent=2)
    )

    # If API key is missing, skip online call and use fallback
    if not api:
        print('⚠️  GEMINI_API_KEY not set. Using heuristic fallback mapping.')
        return _fallback_config(url, summary, basic)

    try:
        model = genai.GenerativeModel(MODEL)
        resp = model.generate_content([
            {
                'role': 'user',
                'parts': [ {'text': full_prompt} ]
            }
        ])
    except Exception as e:
        # Network issues, auth issues, etc.
        print(f"⚠️  Gemini call failed ({type(e).__name__}): {e}. Using fallback mapping.")
        return _fallback_config(url, summary, basic)

    # Collect text best-effort
    txt = getattr(resp, 'text', None)
    if not txt:
        # try digging into candidates
        try:
            parts = []
            for c in getattr(resp, 'candidates', []) or []:
                content = getattr(c, 'content', None)
                for p in getattr(content, 'parts', []) or []:
                    t = getattr(p, 'text', None)
                    if t:
                        parts.append(t)
            txt = '\n'.join(parts)
        except Exception:
            txt = ''

    # Try to extract and parse JSON
    try:
        jtxt = _extract_json_text(txt)
        data = json.loads(jtxt)
        # Validate expected schema: dict with a list 'fields'
        if isinstance(data, dict) and isinstance(data.get('fields'), list):
            return data
        else:
            print("⚠️  Gemini returned unexpected schema (no 'fields' list). Using fallback mapping.")
            return _fallback_config(url, summary, basic)
    except Exception as e:
        # Provide a short preview for debugging, then fallback
        preview = (txt or '').strip().replace('\n',' ')[:240]
        print(f"⚠️  Gemini returned non-JSON or empty output. Preview: '{preview}'")
        print('➡️  Falling back to heuristic mapping based on parsed fields.')
        return _fallback_config(url, summary, basic)

def build_config_from_gemini(url, basic, system_prompt_path='prompts/mapping_prompt.md'):
    html = fetch_form_html(url)
    summ = summarize_form_fields(html)
    cfg = call_gemini(url, summ, basic, system_prompt_path)
    # Ensure form_url present
    cfg['form_url'] = url
    return cfg
