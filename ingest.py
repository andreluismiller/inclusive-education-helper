import requests
from minsearch import Index
import csv 


import json
import pandas as pd


def load_legal_data():
    """Carrega o dataset de legislação de educação especial inclusiva a partir de

    um arquivo CSV fixo, realiza o pré-processamento dos dados e retorna
    uma lista de dicionários pronta para uso em aplicações RAG.
    """
    # Definição do caminho fixo diretamente no corpo da função
    csv_path = "dataset_taged.csv"

    # 1. Carrega o arquivo CSV utilizando pandas
    df = pd.read_csv(csv_path)

    # 2. Pré-processamento e Limpeza de Dados
    # Substitui valores nulos (NaN) por strings vazias
    df = df.fillna("")

    # Função interna para tratar e formatar o campo de tags
    def clean_tags(tags_str):
        if not tags_str:
            return ""
        try:
            tags_list = json.loads(tags_str)
            if isinstance(tags_list, list):
                return " ".join(tags_list)
        except Exception:
            pass
        return str(tags_str)

    # Aplica a limpeza customizada no campo de tags
    df["tags_array"] = df["tags_array"].apply(clean_tags)

    # Garante que os campos estruturais de metadados sejam limpos como strings
    df["doc_id"] = df["doc_id"].astype(str).str.strip()
    df["doc_type"] = df["doc_type"].astype(str).str.strip()
    df["doc_number"] = df["doc_number"].astype(str).str.strip()
    df["doc_year"] = df["doc_year"].astype(str).str.strip()
    df["chunck_id"] = df["chunck_id"].astype(str).str.strip()

    # 3. Converte o DataFrame tratado em uma lista de dicionários (records)
    documents = df.to_dict(orient="records")

    return documents


# def load_faq_data():
#     docs_url = 'https://datatalks.club/faq/json/courses.json'
#     response = requests.get(docs_url)
#     courses_raw = response.json()

#     documents = []
#     url_prefix = 'https://datatalks.club/faq'

#     for course in courses_raw:
#         course_url = f'{url_prefix}{course["path"]}'
#         course_response = requests.get(course_url)
#         course_response.raise_for_status()
#         course_data = course_response.json()

#         documents.extend(course_data)

#     for doc in documents:
#         doc["doc_id"] = doc.pop("id") #we do this so we can add the id key to sqlite so we don't reimport the same records

#     return documents


def build_index(documents):
    index = Index(
        text_fields=['doc_name', 'doc_summary', 'text_original', 'tags_array'],
        keyword_fields=['doc_type', 'doc_year', 'doc_id', 'article_number']
    )
    index.fit(documents)
    return index
