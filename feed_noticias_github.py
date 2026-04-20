import os
import json
import subprocess
import requests
import feedparser
#import time
#from funcoes         import HoraMinuto
from deep_translator import MyMemoryTranslator
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# CONFIGURAÇÕES
ALTO_IMP  = "🔥 ALTO IMPACTO"
MEDIO_IMP = "⚠️ MÉDIO IMPACTO"
BAIXO_IMP = "💤 BAIXO IMPACTO"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
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

vistos = set()
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
    try:
        subprocess.run(["git", "config", "--global", "user.email", "bot@github.com"])
        subprocess.run(["git", "config", "--global", "user.name", "bot"])
        subprocess.run(["git", "add", "vistos.json"])
        subprocess.run(["git", "commit", "-m", "update vistos"], check=False)
        subprocess.run(["git", "push"], check=False)
        print("💾 Histórico salvo no GitHub")
    except Exception as e:
        print("Erro ao salvar histórico:", e)        

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        print("Erro Telegram")

def traduzir(texto):
    try:
        return translator.translate(texto)
    except:
        return texto

def relevante(titulo):
    t = titulo.lower()
    return any(k in t for k in KEYWORDS)

def agora_brasil():
    return datetime.now(ZoneInfo("America/Sao_Paulo"))

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
            feed = feedparser.parse(url)
            for e in feed.entries:
                titulo = e.title.strip()
                link = e.link.strip()
                if link in vistos:
                    continue
                vistos.add(link)
                if relevante(titulo):
                    noticias.append({
                        "titulo": titulo,
                        "link": link})
        except:
            print("Erro feed:", url)
    return noticias

def run_once():
    vistos = carregar_vistos()
    noticias = buscar(vistos)
    if noticias:
        agora = agora_brasil().strftime("%d/%m %H:%M:%S")
        print(f"🔄 Atualizando {agora}")
        for n in noticias:
            titulo_en = n['titulo']
            titulo_pt = traduzir(titulo_en)
            resumo = resumir_trader(titulo_en)
            impacto = classificar_impacto(titulo_en)
            msg = (
                    f"🕒 {agora_brasil().strftime('%H:%M')}\n"
                    f"{impacto}\n"
                    f"📰 {titulo_pt}\n"
                    f"📊 {resumo}\n"
                    f"{n['link']}"
            )
            print(msg + "\n")
            if impacto != BAIXO_IMP:
                enviar_telegram(msg)
    salvar_vistos(vistos)

#def dentro_do_horario():
#    agora = agora_brasil()
#    if agora.weekday() >= 5:
#        return False
#    return (500 <= HoraMinuto()[0] <= 990) # 8h20~16h30

#def loop_controlado():
#    print("🚀 Rodando em modo contínuo controlado...\n")
#    while True:
#        if dentro_do_horario():
#            run_once()
#        else:
#            print("Fora do horário...")
#        time.sleep(120)  # 2 minutos

if __name__ == "__main__":
    run_once() #loop_controlado()
