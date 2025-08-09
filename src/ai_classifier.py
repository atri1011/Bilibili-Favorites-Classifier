import openai
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
            api_key=self.config["openai_api_key"],
            base_url=self.config["openai_base_url"],
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
                model=self.config["model_name"],
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

    async def close(self):
        """
        关闭OpenAI客户端会话。
        """
        await self.client.close()