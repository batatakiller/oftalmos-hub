import os
import httpx
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from markdownify import markdownify as md
import time

# --- CONFIGURAÇÃO ---
BASE_URL = "https://hospitaloftalmos.com.br/"
DOMAIN = urlparse(BASE_URL).netloc
OUTPUT_DIR = "knowledge_base"
MARKDOWN_DIR = os.path.join(OUTPUT_DIR, "markdown")
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
PDF_DIR = os.path.join(OUTPUT_DIR, "pdfs")

# Criar diretórios se não existirem
for d in [MARKDOWN_DIR, IMAGE_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

# Controlo de navegação
visited_urls = set()
urls_to_visit = [BASE_URL]

def is_internal(url):
    return urlparse(url).netloc == DOMAIN

def clean_filename(url):
    path = urlparse(url).path
    if not path or path == "/":
        return "index.md"
    name = path.strip("/").replace("/", "_")
    return f"{name}.md"

def download_file(url, folder):
    try:
        filename = os.path.basename(urlparse(url).path)
        if not filename:
            return
        filepath = os.path.join(folder, filename)
        if os.path.exists(filepath):
            return
        
        with httpx.stream("GET", url, follow_redirects=True) as response:
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
                print(f"  [V] Salvo: {filename}")
    except Exception as e:
        print(f"  [X] Erro ao baixar {url}: {e}")

def scrape():
    while urls_to_visit:
        current_url = urls_to_visit.pop(0)
        if current_url in visited_urls or not is_internal(current_url):
            continue
        
        print(f"\n[*] Processando: {current_url}")
        visited_urls.add(current_url)
        
        try:
            response = httpx.get(current_url, follow_redirects=True, timeout=15)
            if response.status_code != 200:
                continue
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # --- 1. CAPTURAR LINKS ---
            for a in soup.find_all("a", href=True):
                full_url = urljoin(current_url, a["href"])
                # Se for link interno e não visitado, adiciona à fila
                if is_internal(full_url) and full_url not in visited_urls:
                    if not any(full_url.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".pdf", ".zip"]):
                        urls_to_visit.append(full_url)
                
                # Se for PDF
                if full_url.lower().endswith(".pdf"):
                    print(f"  [PDF] Encontrado: {full_url}")
                    download_file(full_url, PDF_DIR)

            # --- 2. CAPTURAR IMAGENS ---
            for img in soup.find_all("img", src=True):
                img_url = urljoin(current_url, img["src"])
                if any(img_url.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
                    download_file(img_url, IMAGE_DIR)

            # --- 3. CONVERTER PARA MARKDOWN ---
            # Remover tags ruidosas para o RAG
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            
            content_html = str(soup)
            markdown_text = md(content_html, heading_style="ATX")
            
            # Limpeza de linhas vazias excessivas
            markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
            
            # Salvar Arquivo com Frontmatter para RAG
            filename = clean_filename(current_url)
            filepath = os.path.join(MARKDOWN_DIR, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"---\nsource: {current_url}\ntitle: {soup.title.string if soup.title else 'Sem Título'}\ndownloaded_at: {time.ctime()}\n---\n\n")
                f.write(markdown_text)
            
            print(f"  [√] Markdown salvo: {filename}")
            
            # Delay amigável
            time.sleep(0.5)

        except Exception as e:
            print(f"  [X] Erro em {current_url}: {e}")

if __name__ == "__main__":
    print(f"🚀 Iniciando crawler em {BASE_URL}")
    scrape()
    print(f"\n✅ Concluído! {len(visited_urls)} páginas processadas.")
