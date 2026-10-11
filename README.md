# Site de frases desmotivacionais

Site estático (sem backend) gerado por `build.py` e publicado no Cloudflare Pages.

## Como funciona
- `frases.json`: todas as frases e categorias. Para adicionar uma frase, coloque no fim da lista.
- `config.json`: nome do site, domínio, e-mail, códigos de anúncio e token do Cloudflare Web Analytics.
- `estatico/`: CSS, JavaScript, ícone e cabeçalhos de segurança (`_headers`).
- `fontes/`: Archivo Black e Work Sans (licença OFL).
- `python3 build.py` gera tudo em `dist/`: páginas, imagens 1080×1080 de cada frase, sitemap e busca.

## Rodar no computador
    pip install -r requirements.txt
    python3 build.py
    python3 -m http.server -d dist 8000

## Cloudflare (Workers)
- Build command: pode ficar vazio (o `wrangler.jsonc` já roda `python3 build.py`)
- Deploy command: `npx wrangler deploy`
- O Cloudflare instala o `requirements.txt` sozinho e o `wrangler.jsonc` publica a pasta `dist`.

## Anúncios
Cole o código de cada bloco em `config.json` > `anuncios`:
- `cabecalho_html`: scripts que a rede manda colocar no `<head>` (ex.: MultiTag da Monetag)
- `topo`, `lateral`, `entre_frases`, `rodape`: banners nas posições do layout
Bloco vazio não aparece no site.
