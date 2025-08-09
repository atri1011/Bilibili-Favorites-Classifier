from pydantic import BaseModel, Field
from typing import List, Optional

class Config(BaseModel):
    """应用程序配置"""
    vmid: str = Field(..., description="用户ID")
    cookie: str = Field(..., description="B站登录Cookie")
    csrf_token: str = Field(..., description="CSRF Token")
    openai_api_key: str = Field(..., description="OpenAI API Key")
    openai_base_url: str = Field(..., description="OpenAI API Base URL")
    model_name: str = Field(..., description="OpenAI模型名称")
    request_delay: float = Field(1.0, description="请求之间的延迟（秒）")
    max_retries: int = Field(3, description="最大重试次数")
    timeout: int = Field(30, description="请求超时时间（秒）")
    page_size: int = Field(24, description="每页获取的视频数量")
    max_pages: int = Field(100, description="最大获取页数")
    ai_batch_size: int = Field(10, description="AI分析的批处理大小")

# --- 新增的B站认证相关模型 ---

class BiliCredential(BaseModel):
    """B站登录凭证"""
    bili_jct: str = Field(..., description="CSRF Token")
    sessdata: str = Field(..., description="Session Data")
    dedeuserid: str = Field(..., description="用户ID")

class QRCodeLoginInfo(BaseModel):
    """二维码登录信息"""
    url: str = Field(..., description="二维码链接")
    qrcode_key: str = Field(..., description="二维码key")


# --- 项目原有的视频分类相关模型 ---

class VideoInfo(BaseModel):
    """视频基本信息"""
    aid: int  # 视频aid，移动视频时需要
    bvid: str
    title: str
    desc: str = Field(alias="description")
    owner_name: str

class FavoriteFolder(BaseModel):
    """收藏夹信息"""
    id: int
    title: str
    media_count: int

class ClassificationResult(BaseModel):
    """单个视频的分类结果"""
    video: VideoInfo
    category: str