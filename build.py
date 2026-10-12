#!/usr/bin/env python3
"""Gera o site estático em dist/ a partir de config.json e frases.json.

Uso: python3 build.py
Requer: Pillow (pip install pillow)
"""
import hashlib
import json
import math
import re
import shutil
import unicodedata
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent
DIST = RAIZ / "dist"
FONTE_TITULO = RAIZ / "fontes" / "ArchivoBlack-Regular.ttf"
FONTE_TEXTO = RAIZ / "fontes" / "WorkSans.ttf"

# (fundo, texto) de cada cartão de frase
PALETAS = [
    ("#1E1C19", "#F4F0E8"),
    ("#E0B13A", "#1E1C19"),
    ("#3A5A78", "#FFFFFF"),
    ("#B5462F", "#FFFFFF"),
    ("#F4F0E8", "#1E1C19"),
    ("#2F6B4F", "#FFFFFF"),
]

CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
DADOS = json.loads((RAIZ / "frases.json").read_text(encoding="utf-8"))
URL = CONFIG["url"].rstrip("/")
NOME = CONFIG["nome"]
DOMINIO = re.sub(r"^https?://", "", URL)
ANUNCIOS = CONFIG.get("anuncios", {})
POR_PAGINA = int(CONFIG.get("frases_por_pagina", 10))
ICONES = json.loads((RAIZ / "icones.json").read_text(encoding="utf-8"))


def slugify(texto, limite=70):
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    if len(s) > limite:
        s = s[:limite].rsplit("-", 1)[0]
    return s


# ---------- dados ----------

CATEGORIAS = {c["slug"]: c for c in DADOS["categorias"]}
FRASES = []
_usados = set()
for i, f in enumerate(DADOS["frases"]):
    if f["categoria"] not in CATEGORIAS:
        raise SystemExit(f"Categoria desconhecida na frase {i + 1}: {f['categoria']}")
    slug = base = slugify(f["texto"])
    n = 2
    while slug in _usados:
        slug, n = f"{base}-{n}", n + 1
    _usados.add(slug)
    FRASES.append({**f, "slug": slug, "num": i + 1})
FRASES.reverse()  # as mais novas (fim do arquivo) aparecem primeiro
for c in CATEGORIAS.values():
    c["frases"] = [f for f in FRASES if f["categoria"] == c["slug"]]


# ---------- imagens ----------

def paleta(frase):
    h = int(hashlib.md5(frase["slug"].encode()).hexdigest(), 16)
    return PALETAS[h % len(PALETAS)]


def quebrar(draw, texto, fonte, largura):
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if draw.textlength(teste, font=fonte) <= largura or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    linhas.append(atual)
    return linhas


def gerar_imagem(frase, destino_jpg, destino_webp):
    W = H = 1080
    margem = 110
    fundo, cor = paleta(frase)
    img = Image.new("RGB", (W, H), fundo)
    d = ImageDraw.Draw(img)
    area_h = H - 2 * margem - 90
    for tam in range(112, 40, -4):
        fonte = ImageFont.truetype(str(FONTE_TITULO), tam)
        linhas = quebrar(d, frase["texto"], fonte, W - 2 * margem)
        altura_linha = int(tam * 1.18)
        if altura_linha * len(linhas) <= area_h:
            break
    y = (H - 90 - altura_linha * len(linhas)) // 2
    for linha in linhas:
        d.text((margem, y), linha, font=fonte, fill=cor)
        y += altura_linha
    marca = ImageFont.truetype(str(FONTE_TEXTO), 34)
    try:
        marca.set_variation_by_name("SemiBold")
    except Exception:
        pass
    d.text((margem, H - margem - 10), DOMINIO, font=marca, fill=cor)
    img.save(destino_jpg, "JPEG", quality=86, optimize=True, progressive=True)
    img.resize((540, 540), Image.LANCZOS).save(destino_webp, "WEBP", quality=82)


# ---------- html ----------

def anuncio(chave, classe):
    codigo = ANUNCIOS.get(chave, "").strip()
    return f'<div class="anuncio {classe}">{codigo}</div>' if codigo else ""


def url_frase(f):
    return f"/frase/{f['slug']}/"


LOGO_SVG = (
    '<svg class="logo-marca" viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="14" fill="#E0B13A"/>'
    '<path d="M20 46c4-6 20-6 24 0" stroke="#1E1C19" stroke-width="5" fill="none" stroke-linecap="round"/>'
    '<circle cx="23" cy="27" r="4" fill="#1E1C19"/><circle cx="41" cy="27" r="4" fill="#1E1C19"/></svg>'
)
DADO_SVG = (
    '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="3" width="18" height="18" rx="4"/><circle cx="8.5" cy="8.5" r="1.2" fill="currentColor"/>'
    '<circle cx="15.5" cy="15.5" r="1.2" fill="currentColor"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/></svg>'
)
BAIXAR_SVG = (
    '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 3v12M7 10l5 5 5-5M4 20h16"/></svg>'
)


def icone(nome):
    return f'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="{ICONES[nome]}"/></svg>'


def pagina(titulo, descricao, caminho, corpo, imagem=None, tipo="website", indexar=True, ativo=None, destaque=""):
    canonica = URL + caminho
    og_img = imagem or f"{URL}/og-padrao.jpg"
    analytics = ""
    if CONFIG.get("cloudflare_analytics_token"):
        analytics = (
            '<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
            f'data-cf-beacon=\'{{"token": "{escape(CONFIG["cloudflare_analytics_token"])}"}}\'></script>'
        )
    atual = ' aria-current="page"'
    menu = "".join(
        f'<a href="/categoria/{c["slug"]}/"{atual if c["slug"] == ativo else ""}>{escape(c["nome"])}</a>'
        for c in CATEGORIAS.values()
    )
    cats_rodape = "".join(
        f'<li><a href="/categoria/{c["slug"]}/">{escape(c["nome"])}</a></li>' for c in CATEGORIAS.values()
    )
    robots = "" if indexar else '<meta name="robots" content="noindex">'
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(titulo)}</title>
<meta name="description" content="{escape(descricao)}">
<link rel="canonical" href="{canonica}">
{robots}
<meta property="og:type" content="{tipo}">
<meta property="og:site_name" content="{escape(NOME)}">
<meta property="og:title" content="{escape(titulo)}">
<meta property="og:description" content="{escape(descricao)}">
<meta property="og:url" content="{canonica}">
<meta property="og:image" content="{og_img}">
<meta property="og:image:width" content="1080">
<meta property="og:image:height" content="1080">
<meta property="og:locale" content="pt_BR">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#1E1C19">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preload" href="/fontes/ArchivoBlack-Regular.ttf" as="font" type="font/ttf" crossorigin>
<link rel="stylesheet" href="/estilo.css">
{ANUNCIOS.get("cabecalho_html", "")}
</head>
<body>
<header class="topo">
  <div class="topo-linha">
    <a class="logo" href="/">{LOGO_SVG}<span class="logo-texto"><span class="logo-nome">{escape(NOME)}</span><span class="logo-lema">pra acabar com o seu dia</span></span></a>
    <form class="busca" action="/busca/" role="search">
      <label class="oculto" for="q">Buscar frases</label>
      <input id="q" name="q" type="search" placeholder="Buscar: chefe, ex, segunda...">
    </form>
    <a class="aleatoria" href="/aleatoria/">{DADO_SVG}<span>Frase aleatória</span></a>
  </div>
  <nav class="categorias" aria-label="Categorias"><div class="categorias-linha">{menu}</div></nav>
</header>
{destaque}
{anuncio("topo", "anuncio-topo")}
<div class="conteudo">
{corpo}
</div>
<footer class="rodape">
  {anuncio("rodape", "anuncio-rodape")}
  <div class="rodape-linha">
    <div class="rodape-marca">
      <a class="logo" href="/">{LOGO_SVG}<span class="logo-nome">{escape(NOME)}</span></a>
      <p>Frases desmotivacionais em imagens, prontas pra mandar no grupo da família. Humor, não leve a sério.</p>
    </div>
    <div>
      <h2>Categorias</h2>
      <ul class="rodape-lista">{cats_rodape}</ul>
    </div>
    <div>
      <h2>O site</h2>
      <ul class="rodape-lista">
        <li><a href="/aleatoria/">Frase aleatória</a></li>
        <li><a href="/sobre/">Sobre</a></li>
        <li><a href="/contato/">Contato</a></li>
        <li><a href="/politica-de-privacidade/">Política de privacidade</a></li>
      </ul>
    </div>
  </div>
  <p class="rodape-copy">© {date.today().year} {escape(NOME)}</p>
</footer>
<script src="/app.js" defer></script>
{analytics}
</body>
</html>
"""


def botoes_compartilhar(f, grande=False):
    link = URL + url_frase(f)
    texto = f"{f['texto']} {link}"
    img = f"{URL}/img/{f['slug']}.jpg"
    redes = [
        ("facebook", "Facebook", f"https://www.facebook.com/sharer/sharer.php?u={quote(link)}"),
        ("pinterest", "Pinterest", f"https://pinterest.com/pin/create/button/?url={quote(link)}&amp;media={quote(img)}&amp;description={quote(f['texto'])}"),
        ("x", "X", f"https://twitter.com/intent/tweet?url={quote(link)}"),
        ("telegram", "Telegram", f"https://t.me/share/url?url={quote(link)}"),
    ]
    icones = "".join(
        f'<a class="rede rede-{n}" href="{u}" target="_blank" rel="noopener" aria-label="Compartilhar no {r}" title="{r}">{icone(n)}</a>'
        for n, r, u in redes
    )
    classe = "compartilhar compartilhar-grande" if grande else "compartilhar"
    return f"""<div class="{classe}" data-link="{link}" data-img="/img/{f['slug']}.jpg" data-titulo="{escape(f['texto'])}">
  <a class="btn btn-whats" href="https://wa.me/?text={quote(texto)}" target="_blank" rel="noopener">{icone("whatsapp")}<span>Enviar no WhatsApp</span></a>
  <div class="redes">
    {icones}
    <button class="rede rede-instagram btn-nativo" type="button" hidden aria-label="Compartilhar no Instagram e outros apps" title="Instagram e outros">{icone("instagram")}</button>
    <a class="rede rede-baixar" href="/img/{f['slug']}.jpg" download="{f['slug']}.jpg" aria-label="Baixar imagem" title="Baixar imagem">{BAIXAR_SVG}</a>
  </div>
</div>"""


def imagem_frase(f, grande=False):
    src = f"/img/{f['slug']}.jpg" if grande else f"/img/{f['slug']}-540.webp"
    tam = 1080 if grande else 540
    carregamento = 'fetchpriority="high"' if grande else 'loading="lazy"'
    return (
        f'<img class="frase-img" src="{src}" width="{tam}" height="{tam}" {carregamento} '
        f'draggable="false" alt="{escape(f["texto"])}">'
    )


def cartao(f):
    c = CATEGORIAS[f["categoria"]]
    return f"""<article class="cartao">
  <a class="cartao-img" href="{url_frase(f)}">{imagem_frase(f)}</a>
  <div class="cartao-info">
    <div class="cartao-topo"><a class="rotulo" href="/categoria/{c['slug']}/">{escape(c['nome'])}</a><span class="numero">nº {f['num']}</span></div>
    {botoes_compartilhar(f)}
    <a class="mais" href="/categoria/{c['slug']}/">Mais frases de {escape(c['nome'].lower())} →</a>
  </div>
</article>"""


def lateral():
    cats = "".join(
        f'<li><a href="/categoria/{c["slug"]}/"><span>{escape(c["nome"])}</span><span class="contagem">{len(c["frases"])}</span></a></li>'
        for c in CATEGORIAS.values()
    )
    dest = [f for f in FRASES if f.get("destaque")][:6]
    destaques = "".join(f'<li><a href="{url_frase(f)}">{imagem_frase(f)}</a></li>' for f in dest)
    return f"""<aside class="lateral">
  {anuncio("lateral", "anuncio-lateral")}
  <section class="caixa"><h2>Categorias</h2><ul class="lista-cats">{cats}</ul></section>
  <section class="caixa"><h2>Mais compartilhadas</h2><ul class="destaques">{destaques}</ul></section>
</aside>"""


def lista_com_anuncios(frases):
    partes = []
    for i, f in enumerate(frases):
        partes.append(cartao(f))
        if i == 2:
            partes.append(anuncio("entre_frases", "anuncio-meio"))
    return "\n".join(partes)


def paginacao(base, atual, total):
    if total <= 1:
        return ""
    links = []
    for n in range(1, total + 1):
        href = base if n == 1 else f"{base}pagina/{n}/"
        if n == atual:
            links.append(f'<span aria-current="page">{n}</span>')
        else:
            links.append(f'<a href="{href}">{n}</a>')
    return f'<nav class="paginacao" aria-label="Páginas">{"".join(links)}</nav>'


def escrever(caminho, html):
    destino = DIST / caminho.strip("/") / "index.html" if caminho != "/" else DIST / "index.html"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")


def bloco_destaque():
    f = next((x for x in FRASES if x.get("destaque")), FRASES[0])
    return f"""<section class="destaque">
  <div class="destaque-linha">
    <a class="destaque-img" href="{url_frase(f)}">{imagem_frase(f)}</a>
    <div class="destaque-texto">
      <p class="sobretitulo">Frase em destaque</p>
      <p class="destaque-chamada">{len(FRASES)} frases desmotivacionais pra mandar no grupo da família, no grupo da firma e pro seu ex.</p>
      <div class="destaque-acoes">
        <a class="btn btn-amarelo" href="/aleatoria/">{DADO_SVG}<span>Me desmotive de novo</span></a>
        <a class="btn btn-contorno" href="{url_frase(f)}">Ver esta frase</a>
      </div>
    </div>
  </div>
</section>"""


def gerar_listagem(base, titulo_h1, intro, frases, titulo_pag, descricao, migalha, ativo=None, com_destaque=False):
    total = max(1, math.ceil(len(frases) / POR_PAGINA))
    for n in range(1, total + 1):
        parte = frases[(n - 1) * POR_PAGINA:n * POR_PAGINA]
        caminho = base if n == 1 else f"{base}pagina/{n}/"
        sufixo = "" if n == 1 else f" (página {n})"
        corpo = f"""<main class="principal">
  <div class="migalha">{migalha}</div>
  <h1>{escape(titulo_h1)}{sufixo}</h1>
  <p class="intro">{escape(intro)}</p>
  {lista_com_anuncios(parte)}
  {paginacao(base, n, total)}
</main>
{lateral()}"""
        destaque = bloco_destaque() if com_destaque and n == 1 else ""
        escrever(caminho, pagina(titulo_pag + sufixo, descricao, caminho, corpo, ativo=ativo, destaque=destaque))


def gerar_frase(f, anterior, proxima):
    c = CATEGORIAS[f["categoria"]]
    rel = [x for x in c["frases"] if x["slug"] != f["slug"]][:4]
    relacionadas = "".join(f'<li><a href="{url_frase(x)}">{imagem_frase(x)}</a></li>' for x in rel)
    corpo = f"""<main class="principal">
  <div class="migalha"><a href="/">Início</a> › <a href="/categoria/{c['slug']}/">{escape(c['nome'])}</a></div>
  <h1>Frase desmotivacional de {escape(c['nome'].lower())} nº {f['num']}</h1>
  <article class="frase-unica">
    {imagem_frase(f, grande=True)}
    {botoes_compartilhar(f, grande=True)}
    <nav class="navega" aria-label="Outras frases">
      <a class="btn btn-contorno" href="{url_frase(anterior)}" rel="prev">← Anterior</a>
      <a class="btn btn-amarelo" href="{url_frase(proxima)}" rel="next">Próxima frase →</a>
    </nav>
  </article>
  {anuncio("entre_frases", "anuncio-meio")}
  <section class="relacionadas"><h2>Mais frases de {escape(c['nome'].lower())}</h2><ul class="grade">{relacionadas}</ul></section>
</main>
{lateral()}"""
    titulo = f"{f['texto']} | {NOME}"
    descricao = f"Frase desmotivacional de {c['nome'].lower()}: {f['texto']} Baixe a imagem e compartilhe."
    escrever(url_frase(f), pagina(titulo, descricao, url_frase(f), corpo, f"{URL}/img/{f['slug']}.jpg", "article", ativo=c["slug"]))


def pagina_texto(caminho, titulo, html_corpo):
    corpo = f'<main class="principal texto"><h1>{escape(titulo)}</h1>{html_corpo}</main>'
    escrever(caminho, pagina(f"{titulo} | {NOME}", f"{titulo} - {NOME}", caminho, corpo))


def gerar_institucionais():
    pagina_texto("/sobre/", "Sobre", f"""
<p>O {escape(NOME)} é um site de humor com frases desmotivacionais em imagens, feitas para rir e compartilhar.</p>
<p>Nada aqui é conselho de verdade. Se você estiver passando por um momento difícil de verdade, procure ajuda: o CVV atende 24 horas pelo telefone 188 ou em <a href="https://cvv.org.br">cvv.org.br</a>.</p>""")
    email = escape(CONFIG["email_contato"])
    pagina_texto("/contato/", "Contato", f'<p>Sugestões de frases, parcerias ou pedidos de remoção: <a href="mailto:{email}">{email}</a>.</p>')
    pagina_texto("/politica-de-privacidade/", "Política de privacidade", f"""
<p>Última atualização: {date.today().strftime('%d/%m/%Y')}.</p>
<h2>Dados coletados</h2>
<p>Não pedimos cadastro nem guardamos dados pessoais. Usamos o Cloudflare Web Analytics, que conta visitas sem cookies e sem identificar você.</p>
<h2>Anúncios</h2>
<p>Este site exibe anúncios de empresas parceiras, que podem usar cookies e tecnologias parecidas para mostrar anúncios e medir resultados. Essas empresas têm suas próprias políticas de privacidade. Você pode limpar ou bloquear cookies nas configurações do seu navegador.</p>
<h2>Seus direitos (LGPD)</h2>
<p>Você pode pedir informações ou a exclusão de dados escrevendo para <a href="mailto:{email}">{email}</a>.</p>""")
    corpo = """<main class="principal texto"><h1>Busca</h1>
<form class="busca-pagina" action="/busca/"><label class="oculto" for="q2">Buscar</label><input id="q2" name="q" type="search" placeholder="Digite uma palavra: chefe, ex, academia..."></form>
<p id="busca-status"></p><ul id="busca-resultados" class="grade"></ul></main>"""
    escrever("/busca/", pagina(f"Busca | {NOME}", "Busque frases desmotivacionais.", "/busca/", corpo, indexar=False))
    corpo = '<main class="principal texto"><h1>Sorteando uma frase...</h1><p><a href="/">Voltar ao início</a></p></main>'
    escrever("/aleatoria/", pagina(f"Frase aleatória | {NOME}", "Uma frase desmotivacional aleatória.", "/aleatoria/", corpo, indexar=False))
    corpo = '<main class="principal texto"><h1>Página não encontrada</h1><p>Assim como a sua motivação. <a href="/">Voltar ao início</a>.</p></main>'
    (DIST / "404.html").write_text(pagina(f"Página não encontrada | {NOME}", "Página não encontrada.", "/404", corpo, indexar=False), encoding="utf-8")


def gerar_arquivos_extras():
    busca = [{"t": f["texto"], "u": url_frase(f), "i": f"/img/{f['slug']}-540.webp"} for f in FRASES]
    (DIST / "busca.json").write_text(json.dumps(busca, ensure_ascii=False), encoding="utf-8")
    hoje = date.today().isoformat()
    urls = ["/"] + [f"/categoria/{c}/" for c in CATEGORIAS] + [url_frase(f) for f in FRASES] + ["/sobre/", "/contato/", "/politica-de-privacidade/"]
    itens = "".join(f"<url><loc>{URL}{u}</loc><lastmod>{hoje}</lastmod></url>" for u in urls)
    (DIST / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{itens}</urlset>',
        encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /busca/\nDisallow: /aleatoria/\n\nSitemap: {URL}/sitemap.xml\n", encoding="utf-8")


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(RAIZ / "estatico", DIST)
    (DIST / "fontes").mkdir(exist_ok=True)
    shutil.copy(FONTE_TITULO, DIST / "fontes")
    (DIST / "img").mkdir()

    cache = RAIZ / ".cache-img"
    cache.mkdir(exist_ok=True)
    for f in FRASES:
        chave = hashlib.md5(f"{f['texto']}|{paleta(f)}|{DOMINIO}|v1".encode()).hexdigest()[:12]
        jpg, webp = cache / f"{chave}.jpg", cache / f"{chave}.webp"
        if not jpg.exists():
            gerar_imagem(f, jpg, webp)
        shutil.copy(jpg, DIST / "img" / f"{f['slug']}.jpg")
        shutil.copy(webp, DIST / "img" / f"{f['slug']}-540.webp")
    destaque = next((f for f in FRASES if f.get("destaque")), FRASES[0])
    shutil.copy(DIST / "img" / f"{destaque['slug']}.jpg", DIST / "og-padrao.jpg")

    gerar_listagem("/", "Frases desmotivacionais",
                   f"{len(FRASES)} frases para acabar com o seu dia. Escolha, baixe e mande no grupo da família.",
                   FRASES, f"Frases desmotivacionais engraçadas | {NOME}", CONFIG["descricao"],
                   "Início", com_destaque=True)
    for c in CATEGORIAS.values():
        gerar_listagem(f"/categoria/{c['slug']}/", f"Frases desmotivacionais de {c['nome'].lower()}",
                       c["descricao"], c["frases"],
                       f"Frases desmotivacionais de {c['nome'].lower()} | {NOME}", c["descricao"],
                       f'<a href="/">Início</a> › {escape(c["nome"])}', ativo=c["slug"])
    for i, f in enumerate(FRASES):
        gerar_frase(f, FRASES[i - 1], FRASES[(i + 1) % len(FRASES)])
    gerar_institucionais()
    gerar_arquivos_extras()
    print(f"Pronto: {len(FRASES)} frases, {len(CATEGORIAS)} categorias em {DIST}")


if __name__ == "__main__":
    main()
