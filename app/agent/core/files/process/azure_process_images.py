import os
from loguru import logger
from tqdm import tqdm
from openai import AsyncAzureOpenAI
from azure.ai.documentintelligence.models import AnalyzeResult
from app.agent.utils.files_helper.process_file_helper import ProcessImageHelper
from app.config.settings import _settings


async def describe_figures(
    azure_chat_client: AsyncAzureOpenAI,
    input_file_path: str, 
    output_folder: str,
    azure_result: AnalyzeResult,
):
    
    md_content = azure_result.content
    img_descriptions = []
    img_captions = []
    img_paths = []
    
    try:
        if azure_result.figures:
            for idx, figure in tqdm(enumerate(azure_result.figures), total=len(azure_result.figures), desc="Describing figures"):
                figure_content = ""
                img_description = ""
                for i, span in enumerate(figure.spans):
                    figure_content += md_content[span.offset:span.offset + span.length]

                if figure.caption:
                    caption_region = figure.caption.bounding_regions
                    for region in figure.bounding_regions:
                        try:
                            if region not in caption_region:
                                boundingbox = (
                                        region.polygon[0],  # x0 (left)
                                        region.polygon[1],  # y0 (top)
                                        region.polygon[4],  # x1 (right)
                                        region.polygon[5]   # y1 (bottom)
                                    )
                                
                                cropped_image = ProcessImageHelper.crop_image_from_file(input_file_path, region.page_number - 1, boundingbox) # page_number is 1-indexed
                                base_name = os.path.basename(input_file_path)
                                file_name_without_extension = os.path.splitext(base_name)[0]

                                output_file = f"{file_name_without_extension}_cropped_image_{idx}.png"
                                cropped_image_filename = os.path.join(output_folder, output_file)
                                cropped_image.save(cropped_image_filename)
                                img_captions.append(figure.caption.content)
                                img_paths.append(cropped_image_filename)
                                
                        except Exception as e:
                            logger.error(f"Error cropping image with idx: {idx}, error: {e}")
                            img_paths.append("")
                else:
                    for region in figure.bounding_regions:
                        try:
                            boundingbox = (
                                    region.polygon[0],  # x0 (left)
                                    region.polygon[1],  # y0 (top
                                    region.polygon[4],  # x1 (right)
                                    region.polygon[5]   # y1 (bottom)
                                )

                            cropped_image = ProcessImageHelper.crop_image_from_file(input_file_path, region.page_number - 1, boundingbox) # page_number is 1-indexed

                            base_name = os.path.basename(input_file_path)
                            file_name_without_extension = os.path.splitext(base_name)[0]

                            output_file = f"{file_name_without_extension}_cropped_image_{idx}.png"
                            cropped_image_filename = os.path.join(output_folder, output_file)
                            cropped_image.save(cropped_image_filename)
                            img_captions.append("")
                            img_paths.append(cropped_image_filename)
                        except Exception as e:
                            logger.error(f"Error cropping image with idx: {idx}, error: {e}")
                            img_paths.append("")
        

            for caption, cropped_image_filename in zip(img_captions, img_paths):
                response = await ProcessImageHelper.describe(azure_chat_client, cropped_image_filename, caption)
                img_descriptions.append(response)    
            
        return img_descriptions, img_paths
    except Exception as e:  
        logger.error(f"Error describing figures: {e}")
        return img_descriptions, img_paths

