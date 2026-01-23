from enum import Enum


class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class DocumentSuffix(str, Enum):
    PDF = [".pdf"]
    DOCX = [".docx"]
    DOC = [".doc"]
    EXCEL = [".xlsx", ".xls"]
    POWERPOINT = [".pptx", ".ppt"]
    IMAGE = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".ico", ".webp"]
    AUDIO = [".mp3", ".wav", ".ogg", ".aac", ".m4a", ".wma", ".flac"]
    VIDEO = [".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm"]
