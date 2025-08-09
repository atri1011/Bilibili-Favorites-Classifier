import asyncio
from typing import Any, Dict, List, Optional

import httpx
from models import BiliCredential, VideoInfo, FavoriteFolder

# B站API常量
FAVORITE_FOLDERS_URL = "https://api.bilibili.com/x/v3/fav/folder/created/list-all"
VIDEOS_IN_FOLDER_URL = "https://api.bilibili.com/x/v3/fav/resource/list"
CREATE_FOLDER_URL = "https://api.bilibili.com/x/v3/fav/folder/add"
DEAL_WITH_RESOURCE_URL = "https://api.bilibili.com/x/v3/fav/resource/deal"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


class BilibiliClient:
    """
    用于与Bilibili API交互的异步客户端。
    """

    def __init__(self, credential: BiliCredential):
        """
        初始化Bilibili客户端。

        Args:
            credential (BiliCredential): 包含用户认证信息的凭证对象。
        """
        cookies = {
            "SESSDATA": credential.sessdata,
            "bili_jct": credential.bili_jct,
            "DedeUserID": str(credential.dedeuserid),
        }
        headers = {"User-Agent": DEFAULT_USER_AGENT}
        
        self._client = httpx.AsyncClient(cookies=cookies, headers=headers, timeout=30.0)
        self._user_id = credential.dedeuserid
        self._csrf = credential.bili_jct

    async def get_favorite_folders(self) -> List[FavoriteFolder]:
        """
        异步获取指定用户的所有收藏夹列表。

        Returns:
            List[FavoriteFolder]: 一个包含收藏夹信息的FavoriteFolder对象列表。
        
        Raises:
            httpx.HTTPStatusError: 如果API请求返回一个错误的HTTP状态码。
            KeyError: 如果响应的JSON结构不符合预期。
        """
        params = {"up_mid": self._user_id}
        response = await self._client.get(FAVORITE_FOLDERS_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 0:
            raise Exception(f"获取收藏夹列表失败: {data.get('message', '未知错误')}")

        folders_data = data.get("data", {}).get("list", [])
        return [FavoriteFolder(**folder) for folder in folders_data]

    async def get_videos_in_folder(self, media_id: int) -> List[VideoInfo]:
        """
        异步获取指定收藏夹中的所有视频信息，自动处理分页。

        Args:
            media_id (int): 收藏夹的ID。

        Returns:
            List[VideoInfo]: 一个包含该收藏夹所有视频信息的VideoInfo对象列表。
        
        Raises:
            httpx.HTTPStatusError: 如果API请求返回一个错误的HTTP状态码。
        """
        all_videos: List[VideoInfo] = []
        page_number = 1
        page_size = 20

        while True:
            params = {
                "media_id": media_id,
                "pn": page_number,
                "ps": page_size,
            }
            response = await self._client.get(VIDEOS_IN_FOLDER_URL, params=params)
            response.raise_for_status()
            data = response.json().get("data", {})

            if not data or not data.get("medias"):
                break  # 如果没有数据或视频列表为空，则停止

            medias = data["medias"]
            for video_data in medias:
                # 将API返回的字典转换为VideoInfo模型对象
                video_info = VideoInfo(
                    aid=video_data.get("id"),
                    bvid=video_data.get("bvid"),
                    title=video_data.get("title", "无标题"),
                    description=video_data.get("intro", ""),
                    owner_name=video_data.get("upper", {}).get("name", "未知UP主"),
                )
                all_videos.append(video_info)

            if not data.get("has_more", False):
                break  # 如果API表明没有更多页了，则停止

            page_number += 1
            await asyncio.sleep(0.5)  # 礼貌地等待一下，避免请求过于频繁

        return all_videos

    async def create_favorite_folder(self, title: str) -> Optional[int]:
        """
        创建一个新的收藏夹。

        Args:
            title (str): 新收藏夹的标题。

        Returns:
            Optional[int]: 如果创建成功，返回新收藏夹的ID，否则返回None。
        """
        payload = {"title": title, "csrf": self._csrf}
        response = await self._client.post(CREATE_FOLDER_URL, data=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0:
            return data.get("data", {}).get("id")
        else:
            print(f"创建收藏夹 '{title}' 失败: {data.get('message')}")
            return None

    async def move_video(self, video_aid: int, source_folder_id: int, target_folder_id: int) -> bool:
        """
        将视频从一个收藏夹移动到另一个。

        Args:
            video_aid (int): 视频的aid。
            source_folder_id (int): 源收藏夹的ID。
            target_folder_id (int): 目标收藏夹的ID。

        Returns:
            bool: 如果操作成功，返回True，否则返回False。
        """
        payload = {
            "rid": video_aid,
            "type": 2,
            "add_media_ids": target_folder_id,
            "del_media_ids": source_folder_id,
            "csrf": self._csrf,
        }
        response = await self._client.post(DEAL_WITH_RESOURCE_URL, data=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("code") == 0

    async def close(self):
        """
        优雅地关闭httpx客户端会话。
        """
        await self._client.aclose()
