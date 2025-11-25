import re
import os
from uuid import uuid4
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from app.config.settings import _settings
from agent.utils.files_helper.chunk_document_helper import split_table, split_image, get_pos_page, clean_final_text

class DocumentChunking:
    
    def __init__(self, kb_id: str):
        self.kb_id = kb_id
    def split_markdown_recursively(
        self,
        md_text: str,
        headers=_settings.chunk.markdown_headers,
        chunk_size=_settings.chunk.chunk_size,
        chunk_overlap=_settings.chunk.chunk_overlap,
    ):
        md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=list(headers))
        sections = md_splitter.split_text(md_text)  # -> List[Document] (page_content, metadata)

        rec = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=_settings.chunk.separators,
        )
        chunks = rec.split_documents(sections)
        return chunks


    def run_pipeline(
        self,
        md_path: str,
        md_text: str,
        file_id: str,
    ):
        file_name = os.path.basename(md_path)
        file_name = file_name.replace(".md", ".pdf")
        pos_pages = get_pos_page(md_text)
        _, table_chunks = split_table(md_text, file_id, file_name, pos_pages, self.kb_id)
        _, img_chunks = split_image(md_text, file_id, file_name, pos_pages, self.kb_id)
        text_without_table, _ = split_table(md_text, file_id, file_name, pos_pages, self.kb_id)
        final_text, _ = split_image(text_without_table, file_id, file_name, pos_pages, self.kb_id) 
        
        chunks = self.split_markdown_recursively(final_text)
        start_page = 1
        end_page = 1
        for chunk in chunks:
            pattern = r"<!--\s*PageBreak\s*-->"
            matches = list(re.finditer(pattern, chunk.page_content))
            if len(matches) > 0:
                chunk.metadata["start_page"] = start_page
                chunk.metadata["end_page"] = end_page
                start_page = end_page + len(matches)
                end_page = end_page + len(matches)
            else:
                chunk.metadata["start_page"] = start_page
                chunk.metadata["end_page"] = end_page
                
        text_chunks = []
        for chunk in chunks:
            doc_id = str(uuid4())        
            clean_chunk = {
                "payload": {
                    "document_type": "text",
                    "knowledge_base_id": self.kb_id,
                    "file_id": file_id,
                    "file_name": file_name,
                    "start_page": chunk.metadata["start_page"],
                    "end_page": chunk.metadata["end_page"],
                    "document_id": doc_id,
                    "content": clean_final_text(chunk.page_content).strip(),
                }
            }
            
            if clean_chunk["payload"]["content"] != "":
                text_chunks.append(clean_chunk)
        
        final_chunks = text_chunks + table_chunks + img_chunks
        return final_chunks

            