"""
哔哩哔哩扫码登录模块
"""
import asyncio
import aiohttp
import json
import time
import logging
from typing import Optional, Dict, Any, Tuple
from urllib.parse import parse_qs, urlparse
import qrcode
from io import StringIO

logger = logging.getLogger(__name__)


class BilibiliAuthError(Exception):
    """哔哩哔哩认证错误"""
    pass


class BilibiliAuth:
    """哔哩哔哩扫码登录认证"""
    
    # API端点
    QRCODE_GENERATE_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
    QRCODE_POLL_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
    
    # 登录状态码
    LOGIN_SUCCESS = 0
    LOGIN_EXPIRED = 86038
    LOGIN_NOT_CONFIRMED = 86090
    LOGIN_NOT_SCANNED = 86101
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.qrcode_key: Optional[str] = None
        self.qrcode_url: Optional[str] = None
        
        # 基础请求头
        self.headers = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.7',
            'origin': 'https://www.bilibili.com',
            'priority': 'u=1, i',
            'referer': 'https://www.bilibili.com/',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }
        
        # 基础Cookie（用于生成二维码）
        self.base_cookies = {
            'buvid3': '127A077B-DE16-7403-BB56-E079C1D9317812887infoc',
            'b_nut': str(int(time.time())),
            'LIVE_BUVID': 'AUTO' + str(int(time.time() * 1000)),
            'enable_web_push': 'DISABLE',
            'theme-tip-show': 'SHOWED',
            'buvid4': '30194E18-8EDF-DAF4-708E-CCE89784A11D22705-025040510-uWz4dg8nAXqPGuD8wVFEsw%3D%3D',
            'home_feed_column': '5',
            'theme-avatar-tip-show': 'SHOWED',
            'CURRENT_QUALITY': '120',
            'sid': 'qrlogin',
            'timeMachine': '0',
            '_uuid': 'A5C95257-A6A9-10151-474F-241F103C86110557008infoc',
            'buvid_fp': '1223ce6c1942b5a12d05f3e4b5662462',
            'browser_resolution': '2327-1192',
            'CURRENT_FNVAL': '2000'
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def generate_qrcode(self) -> Tuple[str, str]:
        """生成登录二维码"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        params = {
            'source': 'main-fe-header',
            'go_url': 'https://www.bilibili.com/',
            'web_location': '333.1007'
        }
        
        try:
            async with self.session.get(
                self.QRCODE_GENERATE_URL,
                params=params,
                cookies=self.base_cookies
            ) as response:
                if response.status != 200:
                    raise BilibiliAuthError(f"Failed to generate QR code: HTTP {response.status}")
                
                data = await response.json()
                
                if data.get('code') != 0:
                    raise BilibiliAuthError(f"API Error: {data.get('message', 'Unknown error')}")
                
                qr_data = data.get('data', {})
                self.qrcode_key = qr_data.get('qrcode_key')
                self.qrcode_url = qr_data.get('url')
                
                if not self.qrcode_key or not self.qrcode_url:
                    raise BilibiliAuthError("Invalid QR code response")
                
                logger.info("QR code generated successfully")
                return self.qrcode_key, self.qrcode_url
                
        except aiohttp.ClientError as e:
            raise BilibiliAuthError(f"Network error: {e}")
    
    def display_qrcode(self, qrcode_url: str) -> str:
        """基于二维码URL生成并返回二维码的ASCII艺术"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=1,
            )
            qr.add_data(qrcode_url)
            qr.make(fit=True)

            # 生成ASCII二维码
            qr_ascii = StringIO()
            qr.print_ascii(out=qr_ascii)
            qr_ascii.seek(0)
            return qr_ascii.read()

        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}")
            return f"QR Code URL: {qrcode_url}\n(请手动复制链接到浏览器打开)"
    
    async def poll_login_status(self, qrcode_key: str) -> Dict[str, Any]:
        """轮询登录状态"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        params = {
            'qrcode_key': qrcode_key,
            'source': 'main-fe-header',
            'web_location': '333.1369'
        }
        
        try:
            async with self.session.get(
                self.QRCODE_POLL_URL,
                params=params,
                cookies=self.base_cookies
            ) as response:
                if response.status != 200:
                    raise BilibiliAuthError(f"Failed to poll login status: HTTP {response.status}")
                
                data = await response.json()
                
                # 获取响应中的Cookie
                cookies = {}
                if 'Set-Cookie' in response.headers:
                    # 解析Set-Cookie头
                    for cookie_header in response.headers.getall('Set-Cookie', []):
                        cookie_parts = cookie_header.split(';')[0].split('=', 1)
                        if len(cookie_parts) == 2:
                            cookies[cookie_parts[0]] = cookie_parts[1]
                
                # 根据你提供的响应格式，内部状态在data.code中
                inner_data = data.get('data', {})
                inner_code = inner_data.get('code', -1)

                return {
                    'code': data.get('code', -1),  # API响应码
                    'message': data.get('message', ''),
                    'data': inner_data,
                    'inner_code': inner_code,  # 登录状态码
                    'cookies': cookies,
                    'response': response  # 保存响应对象以获取完整Cookie
                }
                
        except aiohttp.ClientError as e:
            raise BilibiliAuthError(f"Network error: {e}")
    
    def get_status_message(self, code: int) -> str:
        """获取状态消息"""
        status_messages = {
            self.LOGIN_SUCCESS: "登录成功",
            self.LOGIN_EXPIRED: "二维码已过期，请重新获取",
            self.LOGIN_NOT_CONFIRMED: "请在手机上确认登录",
            self.LOGIN_NOT_SCANNED: "请使用哔哩哔哩APP扫描二维码"
        }
        return status_messages.get(code, f"未知状态码: {code}")
    
    async def wait_for_login(self, qrcode_key: str, timeout: int = 180) -> Optional[str]:
        """等待用户扫码登录，返回完整的Cookie字符串"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                result = await self.poll_login_status(qrcode_key)
                api_code = result['code']  # API响应码
                inner_code = result.get('inner_code', -1)  # 登录状态码

                if api_code == 0 and inner_code == self.LOGIN_SUCCESS:
                    # 登录成功，从响应中获取完整Cookie
                    response = result.get('response')
                    if response:
                        # 获取所有Cookie - 主要从响应的cookies中获取
                        all_cookies = {}

                        # 添加基础Cookie
                        all_cookies.update(self.base_cookies)

                        # 从aiohttp响应的cookies中获取
                        if hasattr(response, 'cookies') and response.cookies:
                            for cookie in response.cookies.values():
                                all_cookies[cookie.key] = cookie.value

                        # 构建Cookie字符串
                        cookie_parts = [f"{key}={value}" for key, value in all_cookies.items()]
                        cookie_string = "; ".join(cookie_parts)

                        logger.info("Login successful, cookie obtained")
                        logger.debug(f"Cookie keys: {list(all_cookies.keys())}")
                        return cookie_string
                    else:
                        logger.error("No response object available")
                        return None

                elif api_code == 0 and inner_code == self.LOGIN_EXPIRED:
                    logger.error("QR code expired")
                    return None

                elif api_code == 0 and inner_code in [self.LOGIN_NOT_SCANNED, self.LOGIN_NOT_CONFIRMED]:
                    # 继续等待
                    await asyncio.sleep(2)
                    continue

                else:
                    logger.warning(f"Unexpected status - API code: {api_code}, Inner code: {inner_code}")
                    await asyncio.sleep(2)
                    continue

            except Exception as e:
                logger.error(f"Error polling login status: {e}")
                await asyncio.sleep(2)
                continue

        logger.error("Login timeout")
        return None
    
    async def login_with_qrcode(self, timeout: int = 180) -> tuple[Optional[str], Optional[str]]:
        """完整的扫码登录流程，返回(cookie, qr_ascii)"""
        try:
            # 生成二维码
            qrcode_key, qrcode_url = await self.generate_qrcode()

            # 基于二维码URL生成ASCII二维码
            qr_ascii = self.display_qrcode(qrcode_url)

            logger.info("QR code generated, waiting for scan...")

            # 等待登录
            cookie = await self.wait_for_login(qrcode_key, timeout)

            return cookie, qr_ascii

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return None, None
    
    def extract_user_info_from_cookie(self, cookie: str) -> Dict[str, str]:
        """从Cookie中提取用户信息"""
        info = {}
        
        # 解析Cookie
        cookie_dict = {}
        for item in cookie.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookie_dict[key] = value
        
        # 提取用户ID
        if 'DedeUserID' in cookie_dict:
            info['user_id'] = cookie_dict['DedeUserID']
        
        # 提取CSRF token
        if 'bili_jct' in cookie_dict:
            info['csrf_token'] = cookie_dict['bili_jct']
        
        # 提取会话数据
        if 'SESSDATA' in cookie_dict:
            info['sessdata'] = cookie_dict['SESSDATA']
        
        return info