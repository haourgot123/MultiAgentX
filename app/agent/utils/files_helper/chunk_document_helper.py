import re
from uuid import uuid4
import hashlib
import os

from app.config.settings import _settings


def get_pos_page(md_text: str):
    pattern = r"<!--\s*PageBreak\s*-->"
    matches = list(re.finditer(pattern, md_text))
    pages = []
    start = 0

    for m in matches:
        end = m.start()  
        pages.append((start, end))
        start = m.end()  
    
    pos_pages = {}
    for i, (start, end) in enumerate(pages, 1):
        pos_pages[f"{i}"] = (start, end)

    pos_pages[len(pages) + 1] = (start, len(md_text))
    return pos_pages



def find_page_number(pos_pages: dict, start_pos: int, end_pos: int):
    start_page = 1
    end_page = 1
    for page, (start, end) in pos_pages.items():
        if start_pos >= start and start_pos <= end:
            start_page = int(page)
        if end_pos >= start and end_pos <= end:
            end_page = int(page)
    return start_page, end_page


def find_table_doc_ids_in_chunk(chunk: str):
    pattern = re.compile(
        r"<table\s+doc_id=['\"]?([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})['\"]?>",
        flags=re.IGNORECASE
    )

    doc_ids = pattern.findall(chunk)
    return doc_ids

def find_image_urls_in_chunk(chunk: str):
    pattern = re.compile(
        r"!\[\]\((.*?)\)",
        flags=re.IGNORECASE
    )
    urls = pattern.findall(chunk)
    return urls

def split_image(
    md_text: str,
    file_id: str,
    file_name: str,
    pos_pages: dict,
    kb_id: str,
):
    pattern = re.compile(
        r"<figure>\s*"
        r"(?:<figcaption>(?P<caption>.*?)</figcaption>)?" 
        r"[\s\S]*?"
        r"!\[\]\((?P<url>.+?)\)(?=\s*<!--)"                
        r"[\s\S]*?<!--\s*FigureContent=(?P<desc>[\s\S]*?)-->"
        r"[\s\S]*?</figure>",
        flags=re.DOTALL | re.IGNORECASE
    )
    img_chunks = []

    
    def replace_img_markdown(matches):
        doc_id = str(uuid4())
        caption = matches.group("caption") if matches.group("caption") else ""
        url = matches.group("url")
        desc = matches.group("desc")
        start = matches.start()
        end = matches.end()
        start_page, end_page = find_page_number(pos_pages, start, end)
        
        try:
            img_chunks.append({
                "payload": {
                    "document_type": "image",
                    "knowledge_base_id": kb_id,
                    "file_id": file_id,
                    "file_name": file_name,
                    "start_page": start_page,
                    "end_page": end_page,
                    "document_id": doc_id,
                    "s3_path": f"{_settings.s3.prefix}/{os.path.basename(url)}",
                    "content": f"Caption: {caption}\nDescription: {desc}"
                }
            })
        
            return ""
        except Exception as e:
            return f"Caption: {caption}\nDescription: {desc}"

    md_without_image = re.sub(pattern, replace_img_markdown, md_text)
    return md_without_image, img_chunks

def split_table(
    md_text: str, 
    file_id: str,
    file_name: str,
    pos_pages: dict,
    kb_id: str

):
    pattern = r"<table>\s*<description>(.*?)</description>([\s\S]*?)</table>"
    table_chunks = []
    def replace_table_markdown(match):
        doc_id = str(uuid4())
        description = match.group(1).strip()
        table = match.group(2).strip()
        start = match.start()
        end = match.end()
        
        start_page, end_page = find_page_number(pos_pages, start, end)
        
        try:
            table_chunks.append(
                {
                    "payload": {
                        "document_type": "table",
                        "knowledge_base_id": kb_id,
                        "start_page": start_page,
                        "end_page": end_page,
                        "document_id": doc_id,
                        "file_id": file_id,
                        "file_name": file_name,
                        "table_content": table,
                        "content": description
                    }
                }
            )
            return ""
        except Exception as e:
            return ""
    md_without_table = re.sub(pattern, replace_table_markdown, md_text, flags=re.DOTALL | re.IGNORECASE)
    return md_without_table, table_chunks

def clean_final_text(final_text: str):
    cleaned = re.sub(r"<!--.*?-->", "", final_text, flags=re.DOTALL)
    return cleaned
