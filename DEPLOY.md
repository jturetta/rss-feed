# Deploy com GitHub Actions + Pages (recomendado)

Solução **gratuita, sempre online e com URL pública** — sem servidor dormindo.

## Como funciona

```
feeds.json  →  GitHub Action (cron 6h)  →  docs/feeds/*.xml  →  GitHub Pages
```

| | Render (antes) | GitHub Actions + Pages |
|---|---|---|
| URL pública | Sim | Sim |
| Servidor dorme | Sim (~15 min) | Não (arquivos estáticos) |
| Feeds persistem | Não (SQLite) | Sim (no repositório) |
| Atualização | Ao acessar | Automática a cada 6h |
| Custo | Grátis limitado | Grátis (repo público) |

## Passo a passo

### 1. Criar repositório no GitHub

```bash
cd rss_feed
git init
git add .
git commit -m "feat: gerador RSS com GitHub Actions"
git branch -M main
git remote add origin https://github.com/jturetta/rss-feed.git
git push -u origin main
```

### 2. Ativar GitHub Pages

1. Repositório → **Settings** → **Pages**
2. **Source:** Deploy from a branch
3. **Branch:** `main` → pasta **`/docs`**
4. Salvar

### 3. Rodar o Action pela 1ª vez

1. Aba **Actions** → **Atualizar feeds RSS** → **Run workflow**

O Action gera os XML em `docs/feeds/` e faz commit automático.

### 4. Usar o feed

URL pública (exemplo):

```
https://jturetta.github.io/rss-feed/feeds/investidor10-noticias.xml
```

Funciona em Feedly, Inoreader, celular, etc.

## Adicionar novos feeds

**Opção A — pelo app local:**

1. Rode o app: `uvicorn main:app --port 8000`
2. Analise a URL e gere o feed
3. Preencha `usuario/repo` no campo GitHub
4. Copie a config JSON e adicione em `feeds.json`
5. Commit + push → Action atualiza automaticamente

**Opção B — editar `feeds.json` direto:**

```json
{
  "feeds": [
    {
      "id": "investidor10-noticias",
      "title": "Investidor10 - Notícias",
      "source_url": "https://investidor10.com.br/noticias/"
    },
    {
      "id": "outro-site",
      "title": "Meu Feed",
      "source_url": "https://exemplo.com/noticias/",
      "title_selector": "h2.title",
      "link_selector": "a.link"
    }
  ]
}
```

## Atualizar manualmente

Actions → **Atualizar feeds RSS** → **Run workflow**

Ou localmente:

```bash
cd backend && source .venv/bin/activate
pip install -r requirements.txt
python ../scripts/update_feeds.py
```

## Alternativa: Render (servidor dinâmico)

Veja `render.yaml` se preferir app web 24/7 com preview interativo. Menos indicado para feeds permanentes no plano grátis.
