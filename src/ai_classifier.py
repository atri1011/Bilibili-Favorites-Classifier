import openai
import json
import re
from typing import List, Optional
from models import VideoInfo
from config_manager import ConfigManager

class AIClassifier:
    """
    使用AI模型对Bilibili视频进行分类。
    """

    def __init__(self, ai_config: dict):
        """
        初始化AIClassifier。

        Args:
            ai_config (dict): 包含 AI 相关配置的字典。
        """
        self.config = ai_config
        self.client = openai.AsyncOpenAI(
            api_key=self.config.get("openai_api_key"),
            base_url=self.config.get("openai_base_url"),
        )

    async def classify_video(self, video: VideoInfo, target_folders: List[str]) -> Optional[str]:
        """
        对单个视频进行分类。

        Args:
            video (VideoInfo): 包含视频标题和描述的视频信息对象。
            target_folders (List[str]): 预设的收藏夹列表。

        Returns:
            Optional[str]: AI模型返回的分类结果，如果发生API错误则返回None。
        """
        prompt = f"""
请根据以下Bilibili视频信息，从我提供的分类列表中选择一个最合适的。
视频标题：{video.title}
视频描述：{video.desc}

请从以下列表中选择一个最匹配的分类，并只返回分类的名称，不要添加任何解释或无关文字。
分类列表：{', '.join(target_folders)}
"""
        
        messages = [
            {"role": "system", "content": "你是一个Bilibili视频分类助手，你的任务是根据视频信息返回最精准的分类路径。"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.config.get("model_name", "gpt-3.5-turbo"),
                messages=messages,
            )
            if response.choices and response.choices[0].message.content:
                classification = response.choices[0].message.content
                return classification.strip()
            return None
        except openai.APIError as e:
            print(f"An OpenAI API error occurred: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

    async def batch_classify_videos(self, videos: List[VideoInfo], target_folders: List[str]) -> List[Optional[str]]:
        """
        对一批视频进行分类。

        Args:
            videos (List[VideoInfo]): 包含多个视频信息的列表。
            target_folders (List[str]): 预设的收藏夹列表。

        Returns:
            List[Optional[str]]: AI模型返回的分类结果列表，顺序与输入一致。发生错误时对应位置为None。
        """
        video_list_formatted = [
            {"index": i, "title": v.title, "desc": v.desc}
            for i, v in enumerate(videos)
        ]

        prompt = f"""
请根据以下Bilibili视频信息列表（JSON格式），从我提供的分类列表中为每个视频选择一个最合适的分类。

分类列表：{', '.join(target_folders)}

视频信息列表：
{json.dumps(video_list_formatted, ensure_ascii=False, indent=2)}

你的任务是：
1. 仔细阅读每个视频的标题和描述。
2. 从“分类列表”中为每个视频选择一个最匹配的分类。
3. 严格按照输入视频的顺序，返回一个 JSON 数组，其中只包含每个视频对应的分类名称。数组的长度必须与输入的视频列表完全一致。

例如，如果输入了3个视频，你的回答应该是这样的格式：
["分类A", "分类B", "分类C"]

请不要添加任何解释、序号或无关文字，只返回纯粹的 JSON 数组。
"""
        messages = [
            {"role": "system", "content": "你是一个高效的Bilibili视频分类助手，专门处理批量分类请求并严格按照要求的JSON格式返回结果。"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.config.get("model_name", "gpt-3.5-turbo"),
                messages=messages,
                response_format={"type": "json_object"},
            )
            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content
                
                # 提取被```json ...```包裹的JSON内容
                match = re.search(r'```json\s*([\s\S]*?)\s*```', content, re.DOTALL)
                if match:
                    json_str = match.group(1)
                else:
                    json_str = content

                try:
                    result_data = json.loads(json_str)
                    classifications = None
                    if isinstance(result_data, list):
                        classifications = result_data
                    elif isinstance(result_data, dict):
                        # 兼容返回格式为 {"classifications": [...]} 的情况
                        for key, value in result_data.items():
                            if isinstance(value, list):
                                classifications = value
                                break
                    
                    if classifications and len(classifications) == len(videos):
                        return classifications
                    else:
                        print(f"AI response format error or length mismatch. Got: {classifications}")
                        return [None] * len(videos)
                except json.JSONDecodeError:
                    print(f"Failed to decode AI response as JSON: {content}")
                    return [None] * len(videos)
            return [None] * len(videos)
        except openai.APIError as e:
            print(f"An OpenAI API error occurred: {e}")
            return [None] * len(videos)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return [None] * len(videos)

    async def close(self):
        """
        关闭OpenAI客户端会话。
        """
        await self.client.close()