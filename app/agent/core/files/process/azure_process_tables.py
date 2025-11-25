import re
from openai import AsyncAzureOpenAI
import asyncio
from loguru import logger
from azure.ai.documentintelligence.models import AnalyzeResult
from app.config.settings import _settings
from app.agent.utils.files_helper.process_file_helper import ProcessTableHelper


def identify_and_merge_cross_page_tables(
    azure_result: AnalyzeResult,
) -> str:
    
    try:
        merge_tables_candidates, table_integral_span_list = ProcessTableHelper.get_merge_table_candidates_and_table_integral_span(azure_result.tables)

        SEPARATOR_LENGTH_IN_MARKDOWN_FORMAT = 2
        merged_table_list = []
        for i, merged_table in enumerate(merge_tables_candidates):
            pre_table_idx = merged_table["pre_table_idx"]
            start = merged_table["start"]
            end = merged_table["end"]
            has_paragraph = ProcessTableHelper.check_paragraph_presence(azure_result.paragraphs, start, end)

            is_horizontal = ProcessTableHelper.check_tables_are_horizontal_distribution(azure_result, pre_table_idx)
            is_vertical = (
                not has_paragraph and
                azure_result.tables[pre_table_idx].column_count
                == azure_result.tables[pre_table_idx + 1].column_count
                and table_integral_span_list[pre_table_idx + 1]["min_offset"]
                - table_integral_span_list[pre_table_idx]["max_offset"]
                <= SEPARATOR_LENGTH_IN_MARKDOWN_FORMAT
            )

            if is_vertical or is_horizontal:

                remark = ""
                cur_content = azure_result.content[table_integral_span_list[pre_table_idx + 1]["min_offset"] : table_integral_span_list[pre_table_idx + 1]["max_offset"]]

                if is_horizontal:
                        remark = azure_result.content[table_integral_span_list[pre_table_idx]["max_offset"] : table_integral_span_list[pre_table_idx + 1]["min_offset"]]
                
                merged_list_len = len(merged_table_list)
                if merged_list_len > 0 and len(merged_table_list[-1]["table_idx_list"]) > 0 and merged_table_list[-1]["table_idx_list"][-1] == pre_table_idx:
                    merged_table_list[-1]["table_idx_list"].append(pre_table_idx + 1)
                    merged_table_list[-1]["offset"]["max_offset"]= table_integral_span_list[pre_table_idx + 1]["max_offset"]
                    if is_vertical:
                        merged_table_list[-1]["content"] = ProcessTableHelper.merge_vertical_tables(merged_table_list[-1]["content"], cur_content)
                    elif is_horizontal:
                        merged_table_list[-1]["content"] = ProcessTableHelper.merge_horizontal_tables(merged_table_list[-1]["content"], cur_content)
                        merged_table_list[-1]["remark"] += remark

                else:
                    pre_content = azure_result.content[table_integral_span_list[pre_table_idx]["min_offset"] : table_integral_span_list[pre_table_idx]["max_offset"]]
                    merged_table = {
                        "table_idx_list": [pre_table_idx, pre_table_idx + 1],
                        "offset": {
                            "min_offset": table_integral_span_list[pre_table_idx]["min_offset"],
                            "max_offset": table_integral_span_list[pre_table_idx + 1]["max_offset"],
                            },
                        "content": ProcessTableHelper.merge_vertical_tables(pre_content, cur_content) if is_vertical else ProcessTableHelper.merge_horizontal_tables(pre_content, cur_content),
                        "remark": remark.strip() if is_horizontal else ""
                        }
                    
                    if merged_list_len <= 0:
                        merged_table_list = [merged_table]
                    else:
                        merged_table_list.append(merged_table)

        
        optimized_content= ""
        if merged_table_list:
            start_idx = 0
            for merged_table in merged_table_list:

                optimized_content += azure_result.content[start_idx : merged_table["offset"]["min_offset"]] + merged_table["content"] + merged_table["remark"]
                start_idx = merged_table["offset"]["max_offset"]
            
            optimized_content += azure_result.content[start_idx:]
        else:
            optimized_content = azure_result.content

        return optimized_content
    
    except Exception as e:
        logger.warning(f"Error merging tables: {e}")
        return azure_result.content

async def describe_tables(
    azure_chat_client: AsyncAzureOpenAI,
    md_content: str
) -> list[str]:   
    try:
        table_descriptions = []
        pattern = r"<table>([\s\S]*?)</table>"
        tables = list(re.findall(pattern, md_content))  
        for table in tables:
            table_description = await ProcessTableHelper.describe(azure_chat_client, table)
            table_descriptions.append(table_description)
            
        return table_descriptions
    except Exception as e:
        logger.warning(f"Error describing tables: {e}")
        return []


        
    
    
    