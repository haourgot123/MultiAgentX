from typing import List, Dict, Any
from app.config.settings import _settings
from .s3 import S3Service
from .model import S3ServiceGetPresignedURLModel

s3_service = S3Service()

def format_text_response(result: Dict[str, Any]) -> str:
    formatted_result = ""
    formatted_result += f"Content: {result.get('content', '')}\n"
    formatted_result += f"From File: {result.get('file_name', '')}\n"
    formatted_result += f"Start Page: {result.get('start_page', '')}\n"
    formatted_result += f"End Page: {result.get('end_page', '')}\n"
    formatted_result += f"Reference link: {_settings.web.fe_url}/references/{result.get('file_id', '')}?page={result.get('start_page', '')}\n"
    formatted_result += f"-----------------------------------\n"
    return formatted_result

def format_table_response(result: Dict[str, Any]) -> str:
    formatted_result = ""
    formatted_result += f"Table: {result.get('table', '')}\n"
    formatted_result += f"Description: {result.get('content', '')}\n"
    formatted_result += f"From File: {result.get('file_name', '')}\n"
    formatted_result += f"Start Page: {result.get('start_page', '')}\n"
    formatted_result += f"End Page: {result.get('end_page', '')}\n"
    formatted_result += f"Reference link: {_settings.web.fe_url}/references/{result.get('file_id', '')}?page={result.get('start_page', '')}\n"
    formatted_result += f"-----------------------------------\n"
    return formatted_result

def format_image_response(result: Dict[str, Any]) -> str:
    presigned_url = s3_service.get_presigned_url(S3ServiceGetPresignedURLModel(key=result.get('file_id', '')))
    formatted_result = ""
    formatted_result += f"Image URL: {presigned_url.url}\n"
    formatted_result += f"From File: {result.get('file_name', '')}\n"
    formatted_result += f"Start Page: {result.get('start_page', '')}\n"
    formatted_result += f"End Page: {result.get('end_page', '')}\n"
    formatted_result += f"From File Reference link: {_settings.web.fe_url}/references/{result.get('file_id', '')}?page={result.get('start_page', '')}\n"
    formatted_result += f"Image Reference link: {presigned_url.url}\n"
    formatted_result += f"-----------------------------------\n"
    return formatted_result


def format_experience_response(result: Dict[str, Any]) -> str:
    formatted_result = ""
    formatted_result += f"Content: {result.get('content', '')}\n"
    formatted_result += f"Reference URL: {_settings.web.fe_url}/corrective-actions/{result.get('experience_id', '')}\n"
    formatted_result += f"-----------------------------------\n"
    return formatted_result

def format_web_search_response(query: str, raw: Any) -> str:
    
    response: Dict[str, Any] = {"query": query, "results": [], "answer": None}
    if isinstance(raw, dict):
        if "results" in raw:
            response["results"] = raw["results"]
        if "answer" in raw:
            response["answer"] = raw["answer"]
    
    elif isinstance(raw, list):
        response["results"] = [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "content": item.get("content") or item.get("snippet"),
                "score": item.get("score"),
            }
            for item in raw
            if isinstance(item, dict)
        ]
    
    results = response.get("results", [])
    if not results:
        return "No search results found for the query."

    formatted_results = f"Web Search Results for: {query}\n\n"

    if response.get("answer"):
        formatted_results += f"Summary: {response['answer']}\n\n"
        formatted_results += "-----------------------------------\n\n"

    for i, result in enumerate(results, 1):
        title = result.get("title", "No title")
        url = result.get("url", "")
        content = result.get("content", "No content available")
        score = result.get("score", 0)

        formatted_results += f"Result {i}:\n"
        formatted_results += f"Title: {title}\n"
        formatted_results += f"URL: {url}\n"
        if score:
            formatted_results += f"Relevance Score: {score:.2f}\n"
        formatted_results += f"Content: {content}\n"
        formatted_results += "-----------------------------------\n"

    return formatted_results


def format_authen_check_response(result: Dict[str, Any], found: bool) -> str:
    formatted_result = ""
    if found:
        response = f"Status: AUTHENTIC\n"
        response += f"Transaction Serial Number (or Transaction Lot Number): {result.serial_number}\n"
        response += f"Item: {result.item}\n"
        response += f"Memo (Main): {result.memo_main}\n"
        response += f"Inventory transaction type: {result.inventory_transaction_type}\n"
        response += f"Type: {result.type}\n"
        response += f"Transaction Number: {result.transaction_number}\n"
        response += f"Document Number: {result.document_number}\n"
        response += f"Date: {result.date}\n"
        response += f"Main Line Name: {result.main_line_name}\n"
    else:
        response = f"Status: FAKE\n"
        response += "This transaction serial number was not found in the database."
    return formatted_result