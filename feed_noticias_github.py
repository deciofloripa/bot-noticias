# Feed de notícias guardado no github e rodando 24h no Render
from os import getenv
from deep_translator import MyMemoryTranslator
from requests   import post
from time       import sleep
from datetime   import datetime, timedelta
from zoneinfo   import ZoneInfo
from dateutil   import parser #pip install python-dateutil
from feedparser import parse
from flask      import Flask
from threading  import Thread
import json

# CONFIGURAÇÕES
ALTO_IMP  = "🔥 ALTO IMPACTO"
MEDIO_IMP = "⚠️ MÉDIO IMPACTO"
BAIXO_IMP = "💤 BAIXO IMPACTO"
TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN")
CHAT_ID = getenv("CHAT_ID")
FEEDS = [
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^DJI&region=US&lang=en-US"#,
]
KEYWORDS = [
    "fed", "interest rate", "inflation", "cpi",
    "central bank", "fomc", "economy",
    "oil", "dollar", "treasury", "bond",
    "payroll", "gdp", "recession",
    "stocks", "nasdaq", "sp500", "dow jones"
]

translator = MyMemoryTranslator(source='en-US', target='pt-BR')

# FUNÇÕES
def carregar_vistos():
    try:
        with open("vistos.json", "r") as f:
            return set(json.load(f))
    except:
        return set()

def salvar_vistos(vistos):
    with open("vistos.json", "w") as f:
        json.dump(list(vistos), f)
    print("💾 Histórico salvo localmente")      

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        post(url, data=data, timeout=10)
    except:
        print("Erro Telegram")

def traduzir(texto, tentativas=3):
    for i in range(tentativas):
        try:
            return translator.translate(texto)
        except:
            sleep(1)
    return texto

def relevante(titulo):
    t = titulo.lower()
    return any(k in t for k in KEYWORDS)

def agora_brasil():
    return datetime.now(ZoneInfo("America/Sao_Paulo"))

def ajustar_data(pubDate, fonte):
    try:
        dt = parser.parse(pubDate)
        if "yahoo" in fonte.lower():
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(ZoneInfo("America/Sao_Paulo"))
    except Exception as e:
        return agora_brasil()
    
# 🧠 RESUMO ESTILO TRADER
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

def classificar_impacto(titulo):
    t = titulo.lower()
    alto = ["cpi", "inflation", "interest rate", "fed", "fomc",
            "pce", "payroll", "jobs report", "nonfarm"]
    medio = ["gdp", "oil", "treasury", "bond", "yields"]
    if any(k in t for k in alto):
        return ALTO_IMP
    elif any(k in t for k in medio):
        return MEDIO_IMP
    else:
        return BAIXO_IMP

def buscar(vistos):
    noticias = []
    for url in FEEDS:
        try:
            feed = parse(url)
            for e in feed.entries:
                titulo = e.title.strip()
                link = e.link.strip()
                
                #evita duplicação de notícias
                chave = titulo.lower().strip()
                if chave in vistos:
                    continue
                vistos.add(chave)

                if relevante(titulo):
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
    if len(vistos) > 500:
        vistos = set(list(vistos)[-500:])
    noticias = buscar(vistos)
    if noticias:
        agora = agora_brasil().strftime("%d/%m %H:%M:%S")
        print(f"🔄 Atualizando {agora}")
        for n in noticias:
            data_noticia = ajustar_data(n.get("data", ""), n.get("fonte", ""))
            if data_noticia < agora_brasil() - timedelta(hours=2):
                continue
            titulo_en = n['titulo']
            titulo_pt = traduzir(titulo_en)
            resumo = resumir_trader(titulo_en)
            impacto = classificar_impacto(titulo_en)
            msg = (
                    f"🕒 {data_noticia.strftime('%H:%M')}\n"
                    f"{impacto}\n"
                    f"📰 {titulo_pt}\n"
                    f"📊 {resumo}\n"
                    f"{n['link']}"
            )
            print(msg + "\n")
            if impacto != BAIXO_IMP:
                enviar_telegram(msg)
    salvar_vistos(vistos)

def loop():
    print("🚀 Bot rodando continuamente...\n")
    while True:
        try:
            run_once()
        except Exception as e:
            print("Erro no loop:", e)
        sleep(120)  # 2 minutos      

# Flask - Exigência do Render
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot rodando!"

def iniciar_bot():
    loop()

vistos = carregar_vistos()

if __name__ == "__main__":
    Thread(target=iniciar_bot).start()
    app.run(host="0.0.0.0", port=10000)
