from PIL import Image
import logging
import fitz  # PyMuPDF
import re
from typing import Any
import mimetypes
import base64
from mimetypes import guess_type
from openai import AsyncAzureOpenAI
from app.config.settings import _settings


logger = logging.getLogger(__name__)
MAX_TOKENS = 1000
BORDER_SYMBOL = "|"

class ProcessImageHelper:
    def __init__(self, azure_chat_client: AsyncAzureOpenAI):
        self.azure_chat_client = azure_chat_client
    
    @staticmethod
    def crop_image_from_image(image_path, page_number, bounding_box):
        with Image.open(image_path) as img:
            if img.format == "TIFF":
                img.seek(page_number)
                img = img.copy()
                
            cropped_image = img.crop(bounding_box)
            return cropped_image

    @staticmethod
    def crop_image_from_pdf_page(pdf_path, page_number, bounding_box):

        doc = fitz.open(pdf_path)
        page = doc.load_page(page_number)
        
        bbx = [x * 72 for x in bounding_box]
        rect = fitz.Rect(bbx)
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72), clip=rect)
        
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        doc.close()

        return img

    @staticmethod
    def crop_image_from_file(file_path, page_number, bounding_box):
        mime_type = mimetypes.guess_type(file_path)[0]
        
        if mime_type == "application/pdf":
            return ProcessImageHelper.crop_image_from_pdf_page(file_path, page_number, bounding_box)
        else:
            return ProcessImageHelper.crop_image_from_image(file_path, page_number, bounding_box)
    

    @staticmethod
    def local_image_to_data_url(image_path):
        mime_type, _ = guess_type(image_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        with open(image_path, "rb") as image_file:
            base64_encoded_data = base64.b64encode(image_file.read()).decode('utf-8')

        return f"data:{mime_type};base64,{base64_encoded_data}"

    @staticmethod
    def update_figure_description_with_regex(md_content, img_descriptions, img_paths):
        figures = []
        pattern = r"(<figure>[\s\S]*?)(</figure>)"
        matches = list(re.finditer(pattern, md_content))
        for i, match in enumerate(reversed(matches), 1):
            start, end = match.span()
            inside, closing = match.groups()
            insert_text = f"\n![]({img_paths[len(matches) - i]})<!-- FigureContent={img_descriptions[len(matches) - i]} -->\n"
            md_content = md_content[:end-len(closing)] + insert_text + closing + md_content[end:]

        return md_content

    @staticmethod
    async def describe(azure_chat_client: AsyncAzureOpenAI, image_path: str, caption: str):
        
        data_url = ProcessImageHelper.local_image_to_data_url(image_path)
        try:
            if caption != "":
                response = await azure_chat_client.chat.completions.create(
                        messages=[
                            { "role": "system", "content": "You are a helpful assistant." },
                            { "role": "user", "content": [  
                                { 
                                    "type": "text", 
                                    "text": f"Describe this image (note: it has image caption: {caption}):" 
                                },
                                { 
                                    "type": "image_url",
                                    "image_url": {
                                        "url": data_url
                                    }
                                }
                            ] } 
                        ],
                        max_tokens=MAX_TOKENS
                    )
            else:
                response = await azure_chat_client.chat.completions.create(
                    messages=[
                        { "role": "system", "content": "You are a helpful assistant." },
                        { "role": "user", "content": [  
                            { 
                                "type": "text", 
                                "text": "Describe this image:" 
                            },
                            { 
                                "type": "image_url",
                                "image_url": {
                                    "url": data_url
                                }
                            }
                        ] } 
                    ],
                    max_tokens=MAX_TOKENS
                )
            img_description = response.choices[0].message.content or ""
            
            return img_description
        except Exception as e:
            logger.warning(f"Error describing image: {e}")
            return ""
        
        
class ProcessTableHelper:
    @staticmethod
    def update_figure_description(md_content, img_description, idx):

        start_substring = f"![](figures/{idx})"
        end_substring = "</figure>"
        new_string = f"<!-- FigureContent=\"{img_description}\" -->"
        
        new_md_content = md_content
        start_index = md_content.find(start_substring)
        if start_index != -1:
            start_index += len(start_substring)
            end_index = md_content.find(end_substring, start_index)
            if end_index != -1:
                new_md_content = md_content[:start_index] + new_string + md_content[end_index:]
        
        return new_md_content
    
    @staticmethod
    def get_table_page_numbers(table):
        return [region.page_number for region in table.bounding_regions]

    @staticmethod
    def get_table_span_offsets(table):

        if table.spans:
            min_offset = table.spans[0].offset
            max_offset = table.spans[0].offset + table.spans[0].length

            for span in table.spans:
                if span.offset < min_offset:
                    min_offset = span.offset
                if span.offset + span.length > max_offset:
                    max_offset = span.offset + span.length

            return min_offset, max_offset
        else:
            return -1, -1
    

    @staticmethod
    def get_merge_table_candidates_and_table_integral_span(tables):
        
        table_integral_span_list = []
        merge_tables_candidates = []
        pre_table_idx = -1
        pre_table_page = -1
        pre_max_offset = 0

        for table_idx, table in enumerate(tables):
            min_offset, max_offset = ProcessTableHelper.get_table_span_offsets(table)
            if min_offset > -1 and max_offset > -1:
                table_page = min(ProcessTableHelper.get_table_page_numbers(table))

                if table_page == pre_table_page + 1:
                    pre_table = {
                        "pre_table_idx": pre_table_idx,
                        "start": pre_max_offset,
                        "end": min_offset,
                        "min_offset": min_offset,
                        "max_offset": max_offset,
                    }
                    merge_tables_candidates.append(pre_table)
                    
                table_integral_span_list.append(
                    {
                        "idx": table_idx,
                        "min_offset": min_offset,
                        "max_offset": max_offset,
                    }
                )

                pre_table_idx = table_idx
                pre_table_page = table_page
                pre_max_offset = max_offset
            else:
                # print(f"Table {table_idx} is empty")
                table_integral_span_list.append(
                    {"idx": {table_idx}, "min_offset": -1, "max_offset": -1}
                )

        return merge_tables_candidates, table_integral_span_list


    @staticmethod
    def check_paragraph_presence(paragraphs, start, end):
        for paragraph in paragraphs:
            for span in paragraph.spans:
                if span.offset > start and span.offset < end:
                    if not hasattr(paragraph, 'role'):
                        return True
                    elif hasattr(paragraph, 'role') and paragraph.role not in ["pageHeader", "pageFooter", "pageNumber"]:
                        return True
        return False


    @staticmethod
    def check_tables_are_horizontal_distribution(result, pre_table_idx):
        
        INDEX_OF_X_LEFT_TOP = 0
        INDEX_OF_X_LEFT_BOTTOM = 6
        INDEX_OF_X_RIGHT_TOP = 2
        INDEX_OF_X_RIGHT_BOTTOM = 4
        THRESHOLD_RATE_OF_RIGHT_COVER = 0.99
        THRESHOLD_RATE_OF_LEFT_COVER = 0.01

        is_right_covered = False
        is_left_covered = False

        if (
            result.tables[pre_table_idx].row_count
            == result.tables[pre_table_idx + 1].row_count
        ):
            for region in result.tables[pre_table_idx].bounding_regions:
                page_width = result.pages[region.page_number - 1].width
                x_right = max(
                    region.polygon[INDEX_OF_X_RIGHT_TOP],
                    region.polygon[INDEX_OF_X_RIGHT_BOTTOM],
                )
                right_cover_rate = x_right / page_width
                if right_cover_rate > THRESHOLD_RATE_OF_RIGHT_COVER:
                    is_right_covered = True
                    break

            for region in result.tables[pre_table_idx + 1].bounding_regions:
                page_width = result.pages[region.page_number - 1].width
                x_left = min(
                    region.polygon[INDEX_OF_X_LEFT_TOP],
                    region.polygon[INDEX_OF_X_LEFT_BOTTOM],
                )
                left_cover_rate = x_left / page_width
                if left_cover_rate < THRESHOLD_RATE_OF_LEFT_COVER:
                    is_left_covered = True
                    break

        return is_left_covered and is_right_covered


    @staticmethod
    def remove_header_from_markdown_table(markdown_table) :
        HEADER_SEPARATOR_CELL_CONTENT = " - "

        result = ""
        lines = markdown_table.splitlines()
        for line in lines:
            border_list = line.split(HEADER_SEPARATOR_CELL_CONTENT)
            border_set = set(border_list)
            if len(border_set) == 1 and border_set.pop() == BORDER_SYMBOL:
                continue
            else:
                result += f"{line}\n"

        return result


    @staticmethod
    def merge_horizontal_tables(md_table_1, md_table_2):
        rows1 = md_table_1.strip().splitlines()
        rows2 = md_table_2.strip().splitlines()

        merged_rows = []
        for row1, row2 in zip(rows1, rows2):
            merged_row = (
                (row1[:-1] if row1.endswith(BORDER_SYMBOL) else row1)
                + BORDER_SYMBOL
                + (row2[1:] if row2.startswith(BORDER_SYMBOL) else row2)
            )
            merged_rows.append(merged_row)

        merged_table = "\n".join(merged_rows)
        return merged_table

    @staticmethod
    def merge_vertical_tables(md_table_1, md_table_2) :
        
        table2_without_header = ProcessTableHelper.remove_header_from_markdown_table(md_table_2)
        rows1 = md_table_1.strip().splitlines()
        rows2 = table2_without_header.strip().splitlines()

        num_columns1 = len(rows1[0].split(BORDER_SYMBOL)) - 2
        num_columns2 = len(rows2[0].split(BORDER_SYMBOL)) - 2

        if num_columns1 != num_columns2:
            raise ValueError("Different count of columns")

        merged_rows = rows1 + rows2
        merged_table = '\n'.join(merged_rows)

        return merged_table


    @staticmethod
    def insert_table_description(md_content, descriptions):
        pattern = r"(<table>)([\s\S]*?)(</table>)"

        def replacer(match, counter=[0]):
            open_tag, body, close_tag = match.groups()
            idx = counter[0]
            counter[0] += 1
            desc = descriptions[idx] if idx < len(descriptions) else "No description"
            return f"{open_tag}\n<description>{desc}</description>{body}{close_tag}"

        return re.sub(pattern, replacer, md_content)
    
    
    @staticmethod
    async def describe(
        azure_chat_client: AsyncAzureOpenAI,
        table_content: str
    ) -> str:   
        try:
            response = await azure_chat_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that describes the tables in the markdown content."},
                        {"role": "user", "content": table_content},
                    ],
                    max_tokens=MAX_TOKENS,
                )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"Error describing table: {e}")
            return ""
