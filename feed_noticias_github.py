# Feed de notícias guardado e executado no github
from os          import getenv
from unicodedata import normalize
from re          import sub
from difflib     import SequenceMatcher
from base64      import b64decode, b64encode
from json        import loads, dumps
from requests    import get, put, post
from time        import sleep#, time
from datetime    import datetime, timedelta
from zoneinfo    import ZoneInfo
from dateutil    import parser #pip install python-dateutil
from feedparser  import parse
from gc          import collect

# CONFIGURAÇÕES
ALTO_IMP  = "🔥 ALTO IMPACTO"
MEDIO_IMP = "⚠️ MÉDIO IMPACTO"
BAIXO_IMP = "💤 BAIXO IMPACTO"
TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN")
CHAT_ID = getenv("CHAT_ID")
FEED_TOKEN = getenv("FEED_TOKEN")
FEED_USER = "deciofloripa"
FEED_REPO = "bot-noticias"
FEED_FILE = "vistos.json"
URL = f"https://api.github.com/repos/{FEED_USER}/{FEED_REPO}/contents/{FEED_FILE}"
FEEDS = [
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^DJI&region=US&lang=en-US"#,
]

# FUNÇÕES

# Normalização
def normalizar_titulo(titulo):
    t = titulo.lower()
    t = normalize('NFKD', t) # remove acentos
    t = t.encode('ascii', 'ignore').decode('utf-8')
    t = sub(r'\d+', '', t)           # remove números
    t = sub(r'[^\w\s]', '', t)       # remove pontuação
    t = sub(r'\s+', ' ', t).strip()  # remove espaços duplicados
    # stopwords
    stopwords = {
        "the", "a", "an", "to", "of", "in", "on",
        "for", "at", "by", "with", "from",
        "is", "are", "be", "as"
    }
    palavras = [
        p for p in t.split()
        if p not in stopwords
    ]
    return " ".join(palavras)

def titulo_parecido(novo, vistos, limite=0.88): # para melhorar, limite=0.92
    for antigo in vistos:
        similaridade = SequenceMatcher(None, novo, antigo).ratio()
        if similaridade >= limite:
            print(f"🔁 Similaridade detectada: {similaridade:.2f}")
            return True
    return False

# GITHUB Storage
def carregar_vistos():
    headers = { "Authorization": f"token {FEED_TOKEN}" }
    try:
        r = get(URL, headers=headers, timeout=20)
        if r.status_code == 200:
            content = r.json()["content"]
            decoded = b64decode(content).decode("utf-8")
            dados = loads(decoded)
            print(f"📥 {len(dados)} notícias carregadas do GitHub")
            return set(dados)
    except Exception as e:
        print("Erro carregando vistos:", e)
    return set()

def salvar_vistos(vistos):
    headers = { "Authorization": f"token {FEED_TOKEN}" }
    sha = None
    try:
        r = get(URL, headers=headers, timeout=20)
        if r.status_code == 200:
            sha = r.json()["sha"]
    except Exception as e:
        print("Erro buscando SHA:", e)
    try:
        content = dumps(list(vistos), ensure_ascii=False, indent=2)
        encoded = b64encode(content.encode("utf-8")).decode("utf-8")
        data = {"message": "Atualizando vistos.json",
                "content": encoded,
                "sha": sha}
        r = put(URL, headers=headers, json=data, timeout=20)
        if r.status_code in [200, 201]:
            print("💾 vistos.json salvo no GitHub")
        else:
            print("STATUS GITHUB:", r.status_code)
            print("RESPOSTA:", r.text[:200])
    except Exception as e:
        print("Erro salvando vistos:", e)

# Telegram
def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        post(url, data=data, timeout=10)
    except:
        print("Erro Telegram")

# Tradução
def traduzir(texto, tentativas=2):
    from deep_translator import MyMemoryTranslator, GoogleTranslator
    for i in range(tentativas): # Tenta MyMemory
        try:
            translator_memory = MyMemoryTranslator(source='en-US', target='pt-BR')
            sleep(0.2)
            return translator_memory.translate(texto)
        except:
            sleep(0.5)
    for i in range(tentativas): # Tenta Google
        try:
            translator_google = GoogleTranslator(source='auto', target='pt')
            sleep(0.2)
            return translator_google.translate(texto)
        except:
            sleep(0.5)
    return f"(EN) {texto}"

# Datas
def agora_brasil():
    return datetime.now(ZoneInfo("America/Sao_Paulo"))

def ajustar_data(pubDate, fonte):
    try:
        dt = parser.parse(pubDate)
        if dt.tzinfo is None:
            if "yahoo" in fonte.lower():
                dt = dt.replace(tzinfo=ZoneInfo("America/New_York"))
            else:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(ZoneInfo("America/Sao_Paulo"))
    except Exception:
        return agora_brasil()

# Resumos
def resumir_trader(titulo):
    t = titulo.lower()
    if "inflation" in t or "cpi" in t:
        return "Inflação em foco → impacto direto nos juros"
    if "interest rate" in t or "fed" in t or "fomc" in t:
        return "Juros / Fed → movimento forte no dólar"
    if "oil" in t:
        return "Petróleo → impacto em inflação e moedas"
    if "payroll" in t or "jobs" in t:
        return "Emprego EUA → volatilidade forte"
    if "gdp" in t:
        return "PIB → leitura da força econômica"
    if "recession" in t:
        return "Risco de recessão → aversão a risco"
    if "stocks" in t or "nasdaq" in t or "sp500" in t:
        return "Bolsas → influência no índice (WIN)"
    if "dollar" in t or "treasury" in t:
        return "Dólar / Treasuries → impacto direto no WDO"
    return "Notícia macro relevante"

# Classificação WDO
def classificar_wdo(titulo):
    t = titulo.lower()
    score = 0
    motivo = []
    # 🔥 EVENTOS QUE MOVEM FORTE, ...
    if any(k in t for k in ["fed", "fomc", "interest rate", "rates"]):
        score += 5
        motivo.append("Juros/Fed")
    if any(k in t for k in ["cpi", "inflation", "pce"]):
        score += 5
        motivo.append("Inflação")
    if any(k in t for k in ["payroll", "nonfarm", "jobs report"]):
        score += 5
        motivo.append("Emprego EUA")
    # ⚠️ E MÉDIO
    if any(k in t for k in ["treasury", "bond", "yield"]):
        score += 3
        motivo.append("Juros mercado")
    if any(k in t for k in ["dollar", "usd", "currency"]):
        score += 3
        motivo.append("Moedas")
    if any(k in t for k in ["oil", "crude"]):
        score += 3
        motivo.append("Petróleo")
    # 🧨 GEOPOLÍTICO (muito importante)
    if any(k in t for k in ["war", "iran", "china", "russia", "conflict", "strait"]):
        score += 5
        motivo.append("Geopolítica")
    # 🚨 BREAKING
    breaking = any(k in t for k in ["breaking", "urgent", "alert"])
    return score, motivo, breaking

def buscar(vistos):
    noticias = []
    for url in FEEDS:
        try:
            feed = parse(url)
            entries = feed.entries[:15]
            for e in entries:
                titulo = e.title.strip()
                link = e.link.strip()
                # evita duplicação de notícias
                chave = normalizar_titulo(titulo) + link[-20:]
                if chave in vistos:                 # ignora repetidos
                    continue
                vistos_recentes = list(vistos)[-500:]
                if titulo_parecido(chave, vistos_recentes, limite=0.92):
                    continue
                vistos.add(chave)
                noticias.append({
                    "titulo": titulo,
                    "link": link,
                    "data": e.get("published", ""),
                    "fonte": url
                })
        except:
            print("Erro feed:", url)
    return noticias

def run_once():
    global vistos
    if len(vistos) > 2000:
        vistos = set(list(vistos)[-1500:])
    noticias = buscar(vistos)
    noticias.sort(key=lambda n: ajustar_data(n.get("data", ""), n.get("fonte", "")))
    print("Noticias encontradas:", len(noticias))
    if noticias:
        agora = agora_brasil().strftime("%d/%m %H:%M:%S")
        print(f"🔄 Atualizando {agora}")
        for n in noticias:
            try:
                print("DEBUG:", n["titulo"])
                data_noticia = ajustar_data(n.get("data", ""), n.get("fonte", ""))
                if data_noticia < agora_brasil() - timedelta(minutes=45):
                    continue
                titulo_en = n['titulo']
                titulo_pt = titulo_en if len(titulo_en) < 5 else traduzir(titulo_en)
                resumo = resumir_trader(titulo_en)
                score_wdo, motivos, breaking = classificar_wdo(titulo_en)
                motivo_txt = " | ".join(motivos) if motivos else "Macro"
                if score_wdo > 5 or breaking: # quanto menor, mais notícias
                    alerta = "🚨 BREAKING NEWS\n" if breaking else ""
                    msg = (
                        f"{alerta}"
                        f"🕒 {data_noticia.strftime('%H:%M')}\n"
                        f"💰 IMPACTO: {score_wdo}\n"
                        f"📌 {motivo_txt}\n"
                        f"📰 <b>{titulo_pt}</b>\n"
                        f"📊 {resumo}\n"
                        f"<a href='{n['link']}'>Ler notícia</a>"
                    )
                    print(msg + "\n")
                    enviar_telegram(msg)
            except Exception as e:
                print("Erro notícia:", e)                    
    salvar_vistos(vistos)
    collect()


if __name__ == "__main__":
    print("Iniciando execução...")
    vistos = carregar_vistos()
    try:
        run_once()
    except Exception as e:
        print("Erro geral:", e)
    print("✅ Execução concluída.")
