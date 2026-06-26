# import re
# import json
# import yaml
# import requests
# import pandas as pd

# from pathlib import Path
# from bs4 import BeautifulSoup


# class GenericLegalParser:

#     def __init__(
#         self,
#         url: str,
#         document_number: str,
#         document_year: int,
#         document_name: str,
#         config_file: str,
#         output_dir: str = "data/processed"
#     ):

#         self.url = url

#         with open(
#             config_file,
#             encoding="utf-8"
#         ) as f:
#             self.config = yaml.safe_load(f)

#         self.document = {
#             "document_id":
#                 (
#                     f"{self.config['document_type']}"
#                     f"_{document_number}"
#                     f"_{document_year}"
#                 ),

#             "document_type":
#                 self.config[
#                     "document_type"
#                 ],

#             "document_number":
#                 str(document_number),

#             "document_year":
#                 document_year,

#             "document_name":
#                 document_name
#         }

#         self.output_dir = Path(
#             output_dir
#         )

#         self.output_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         self.html = None
#         self.lines = []
#         self.chunks = []

#     #################################################
#     # DOWNLOAD
#     #################################################

#     def download(self):

#         headers = {
#             "User-Agent":
#                 (
#                     "Mozilla/5.0 "
#                     "(Windows NT 10.0; Win64; x64)"
#                 )
#         }

#         response = requests.get(
#             self.url,
#             headers=headers,
#             timeout=30
#         )

#         response.raise_for_status()

#         self.html = response.text

#     #################################################
#     # LIMPEZA
#     #################################################

#     def clean_html(self):

#         soup = BeautifulSoup(
#             self.html,
#             "lxml"
#         )

#         for tag in soup(
#             [
#                 "script",
#                 "style",
#                 "noscript"
#             ]
#         ):
#             tag.decompose()

#         text = soup.get_text(
#             separator="\n",
#             strip=True
#         )

#         text = text.replace(
#             "\xa0",
#             " "
#         )

#         text = re.sub(
#             r"[ \t]+",
#             " ",
#             text
#         )

#         text = re.sub(
#             r"\n{2,}",
#             "\n\n",
#             text
#         )

#         self.lines = [
#             line.strip()
#             for line
#             in text.splitlines()
#             if line.strip()
#         ]

# #################################################
# # NORMALIZAÇÃO JURÍDICA
# #################################################

#     def normalize_legal_text(
#         self,
#         text: str
#     ):

#         if not text:
#             return ""

#         text = text.replace(
#             "\xa0",
#             " "
#         )

#         #################################################
#         # Junta quebras artificiais
#         #################################################

#         text = re.sub(
#             r"\n+",
#             " ",
#             text
#         )

#         text = re.sub(
#             r"\s+",
#             " ",
#             text
#         )

#         #################################################
#         # Preserva estruturas jurídicas
#         #################################################

#         text = re.sub(
#             r"\s+(§\s*\d+[ºo]?)",
#             r"\n\1",
#             text
#         )

#         text = re.sub(
#             r"\s+([IVXLCDM]+\s*-)",
#             r"\n\1",
#             text
#         )

#         text = re.sub(
#             r"\s+([a-z]\))",
#             r"\n\1",
#             text,
#             flags=re.IGNORECASE
#         )

#         return text.strip()


#     #################################################
#     # EXTRAÇÃO DOS ARTIGOS
#     #################################################

#     def extract_articles(self):

#         hierarchy_state = {}

#         compiled_hierarchy = []

#         for item in self.config[
#             "hierarchy"
#         ]:

#             compiled_hierarchy.append(
#                 {
#                     "type":
#                         item["type"],

#                     "regex":
#                         re.compile(
#                             item[
#                                 "pattern"
#                             ],
#                             re.IGNORECASE
#                         )
#                 }
#             )

#         article_regex = re.compile(
#             self.config[
#                 "article_pattern"
#             ],
#             re.IGNORECASE
#         )

#         articles = []

#         current_article = None
#         current_text = []

#         document_started = False

#         for line in self.lines:

#             #################################################
#             # IGNORA O PREÂMBULO
#             #################################################

#             if not document_started:

#                 if re.match(
#                     r"^Art\.\s*1[ºo]?",
#                     line,
#                     re.IGNORECASE
#                 ):
#                     document_started = True
#                 else:
#                     continue            

#             #################################################
#             # HIERARQUIA
#             #################################################

#             hierarchy_found = False

#             for item in compiled_hierarchy:

#                 if item[
#                     "regex"
#                 ].match(line):

#                     hierarchy_state[
#                         item["type"]
#                     ] = line

#                     hierarchy_found = True
#                     break

#             if hierarchy_found:
#                 continue

#             #################################################
#             # ARTIGO
#             #################################################

#             match = article_regex.match(
#                 line
#             )

#             if match:

#                 if current_article:

#                     current_article[
#                         "text_original"
#                     ] = self.normalize_legal_text(
#                         "\n".join(
#                             current_text
#                         )
#                     )                    

#                     # current_article[
#                     #     "text_original"
#                     # ] = "\n".join(
#                     #     current_text
#                     # ).strip()

#                     articles.append(
#                         current_article
#                     )

#                 hierarchy = []

#                 for level, item in enumerate(
#                     compiled_hierarchy,
#                     start=1
#                 ):

#                     value = hierarchy_state.get(
#                         item["type"]
#                     )

#                     if value:

#                         hierarchy.append(
#                             {
#                                 "level":
#                                     level,

#                                 "type":
#                                     item[
#                                         "type"
#                                     ],

#                                 "label":
#                                     value
#                             }
#                         )

#                 current_article = {
#                     "article_number":
#                         match.group(1),

#                     "hierarchy":
#                         hierarchy
#                 }

#                 current_text = [line]

#             elif current_article:
#                 current_text.append(
#                     line
#                 )

#         #################################################
#         # ÚLTIMO ARTIGO
#         #################################################

#         if current_article:

#             current_article[
#                 "text_original"
#             ] = self.normalize_legal_text(
#                 "\n".join(
#                     current_text
#                 )
#             )            

#             # current_article[
#             #     "text_original"
#             # ] = "\n".join(
#             #     current_text
#             # ).strip()

#             articles.append(
#                 current_article
#             )

#         return articles

#     #################################################
#     # CONSTRUÇÃO DOS CHUNKS
#     #################################################

#     def build_chunks(
#         self,
#         articles
#     ):

#         chunks = []

#         for article in articles:

#             hierarchy_path = (
#                 " > ".join(
#                     item["label"]
#                     for item
#                     in article[
#                         "hierarchy"
#                     ]
#                 )
#             )

#             article_number = article[
#                 "article_number"
#             ]

#             chunk_id = (
#                 f"{self.document['document_id']}"
#                 f"_art_{article_number}"
#             )

#             expanded = [
#                 self.document[
#                     "document_name"
#                 ]
#             ]

#             if hierarchy_path:
#                 expanded.append(
#                     hierarchy_path
#                 )

#             expanded.append(
#                 article[
#                     "text_original"
#                 ]
#             )

#             chunk = {
#                 **self.document,

#                 "chunk_id":
#                     chunk_id,

#                 "parent_chunk_id":
#                     self.document[
#                         "document_id"
#                     ],

#                 "chunk_level":
#                     self.config[
#                         "chunk_level"
#                     ],

#                 "article_number":
#                     article_number,

#                 "hierarchy":
#                     article[
#                         "hierarchy"
#                     ],

#                 "hierarchy_path":
#                     hierarchy_path,

#                 "text_original":
#                     article[
#                         "text_original"
#                     ],

#                 "text_expanded":
#                     "\n\n".join(
#                         item.strip()
#                         for item in expanded
#                         if item
#                     ),

#                 # "text_expanded":
#                 #     "\n".join(
#                 #         expanded
#                 #     ),

#                 "themes":
#                     [],

#                 "keywords":
#                     []
#             }

#             chunks.append(
#                 chunk
#             )

#         self.chunks = chunks

#     #################################################
#     # PIPELINE
#     #################################################

#     def parse(self):

#         self.download()
#         self.clean_html()

#         articles = (
#             self.extract_articles()
#         )

#         self.build_chunks(
#             articles
#         )

#         return self.chunks

#     #################################################
#     # DATAFRAME OPCIONAL
#     #################################################

#     def to_dataframe(self):

#         if not self.chunks:
#             return pd.DataFrame()

#         df = pd.DataFrame(
#             self.chunks
#         )

#         df[
#             "hierarchy"
#         ] = df[
#             "hierarchy"
#         ].apply(
#             json.dumps,
#             ensure_ascii=False
#         )

#         return df

#     #################################################
#     # EXPORTAÇÃO JSONL
#     #################################################

#     def save_jsonl(self):

#         file_path = (
#             self.output_dir /
#             f"{self.document['document_id']}.jsonl"
#         )

#         with open(
#             file_path,
#             "w",
#             encoding="utf-8"
#         ) as f:

#             for chunk in self.chunks:

#                 f.write(
#                     json.dumps(
#                         chunk,
#                         ensure_ascii=False
#                     )
#                 )

#                 f.write("\n")

#         return file_path