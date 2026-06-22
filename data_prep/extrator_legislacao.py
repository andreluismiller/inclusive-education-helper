import re
import os
import requests
import json
import time
from bs4 import BeautifulSoup
from typing import List, Dict

# Novos imports para o Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def fetch_html_dynamic(url: str) -> str:
    """Usa um navegador fantasma (Selenium) para carregar páginas que dependem de JavaScript."""
    # Configura o Chrome para rodar em background (headless)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    # Instala e inicia o driver automaticamente
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(url)
        # Aguarda 5 segundos para dar tempo do JavaScript do MEC carregar o texto
        time.sleep(5) 
        html = driver.page_source
        return html
    finally:
        driver.quit()

def fetch_and_clean_html(url: str, dynamic: bool = False) -> BeautifulSoup:
    """Faz o download da página (estática ou dinâmica) e retorna o HTML limpo."""
    
    if dynamic:
        print(f"  -> Usando Selenium para renderizar página dinâmica: {url}")
        html_content = fetch_html_dynamic(url)
    else:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        html_content = response.content
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Remove textos revogados por tags HTML nativas
    for strike in soup.find_all(['strike', 's', 'del']):
        strike.decompose()
        
    # 2. Remove elementos que usam CSS inline para riscar o texto (line-through)
    for elem in soup.find_all(style=True):
        if 'line-through' in elem['style'].lower():
            elem.decompose()
            
    return soup

def parse_legal_document(url: str, doc_metadata: Dict) -> List[Dict]:
    """Lê o HTML limpo e gera os chunks a nível de Artigo."""
    try:
        # Passa a flag 'dynamic' para a função de download
        is_dynamic = doc_metadata.get('dynamic', False)
        soup = fetch_and_clean_html(url, dynamic=is_dynamic)
    except Exception as e:
        print(f"Erro ao baixar/limpar a URL {url}: {e}")
        return []
    
    # ... (O RESTANTE DA FUNÇÃO PERMANECE EXATAMENTE IGUAL AO CÓDIGO ANTERIOR) ...
    # Extrai as tags de texto relevantes sequencialmente
    elements = soup.find_all(['p', 'div', 'span', 'h1', 'h2', 'h3', 'h4'])
    paragraphs = [elem.get_text(strip=True) for elem in elements if elem.get_text(strip=True)]
    
    current_livro = None
    current_titulo = None
    current_capitulo = None
    current_secao = None
    current_art_num = None
    current_art_text = []
    
    chunks = []
    
    re_livro = re.compile(r'^LIVRO\s+([IVXLCDM]+)', re.IGNORECASE)
    re_titulo = re.compile(r'^TÍTULO\s+([IVXLCDM]+)', re.IGNORECASE)
    re_capitulo = re.compile(r'^CAPÍTULO\s+([IVXLCDM]+)', re.IGNORECASE)
    re_secao = re.compile(r'^SEÇÃO\s+([IVXLCDM]+)', re.IGNORECASE)
    re_artigo = re.compile(r'^Art\.?\s+(\d+[A-Z]*[ºo\.]?-?)', re.IGNORECASE)

    def save_chunk():
        if current_art_num and current_art_text:
            chunks.append({
                "doc_id": doc_metadata['id'],
                "doc_type": doc_metadata['type'],
                "doc_name": doc_metadata['name'],
                "hierarquia": {
                    "livro": current_livro,
                    "titulo": current_titulo,
                    "capitulo": current_capitulo,
                    "secao": current_secao
                },
                "artigo": current_art_num,
                "texto_chunk": "\n".join(current_art_text),
                "source_url": f"{url}#art{current_art_num.replace('º', '').replace('.', '')}"
            })

    for p in paragraphs:
        if re_livro.match(p):
            current_livro = p
            current_titulo, current_capitulo, current_secao = None, None, None
            continue
        if re_titulo.match(p):
            current_titulo = p
            current_capitulo, current_secao = None, None
            continue
        if re_capitulo.match(p):
            current_capitulo = p
            current_secao = None
            continue
        if re_secao.match(p):
            current_secao = p
            continue
            
        art_match = re_artigo.match(p)
        if art_match:
            save_chunk() 
            current_art_num = art_match.group(1).strip('.- ')
            current_art_text = [p] 
        else:
            if current_art_num:
                current_art_text.append(p)

    save_chunk()
    return chunks

# --- Execução do Pipeline ---

documentos = [
    {
        "id": "L13146",
        "type": "Lei",
        "name": "Estatuto da Pessoa com Deficiência",
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13146.htm",
        "dynamic": False # Estático, usa requests rápido
    },
    {
        "id": "D12686",
        "type": "Decreto",
        "name": "Decreto nº 12.686",
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2025/decreto/d12686.htm",
        "dynamic": False # Estático, usa requests rápido
    },
    {
        "id": "P11240",
        "type": "Portaria",
        "name": "Portaria MEC 11240",
        "url": "https://mecnormas.mec.gov.br/pesquisa/detalhar/11240",
        "dynamic": True # Dinâmico! Vai acionar o Selenium
    }
]

# ... (O CÓDIGO DE SALVAR O JSONL CONTINUA O MESMO DA RESPOSTA ANTERIOR) ...
todos_os_chunks = []
for doc in documentos:
    print(f"Processando: {doc['name']}...")
    chunks = parse_legal_document(doc['url'], doc)
    todos_os_chunks.extend(chunks)

print(f"\nTotal de chunks gerados: {len(todos_os_chunks)}")

output_dir = os.path.join("data", "processed")
os.makedirs(output_dir, exist_ok=True)
output_file_path = os.path.join(output_dir, "chunks_legislacao.jsonl")

with open(output_file_path, 'w', encoding='utf-8') as f:
    for chunk in todos_os_chunks:
        f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

print("Processo concluído com sucesso!")