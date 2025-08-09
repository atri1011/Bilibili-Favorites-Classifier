"""
配置管理模块
"""
import os
import re
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv, set_key

from models import Config, BiliCredential

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or ".env"
        self.ai_config_file = "ai_config.json"  # AI配置单独保存
        self.load_env_file()
    
    def load_env_file(self):
        """加载环境变量文件"""
        if os.path.exists(self.config_file):
            load_dotenv(self.config_file)
            logger.info(f"Loaded configuration from {self.config_file}")
        else:
            logger.warning(f"Configuration file {self.config_file} not found")
    
    def extract_csrf_from_cookie(self, cookie: str) -> Optional[str]:
        """从Cookie中提取CSRF token"""
        match = re.search(r'bili_jct=([^;]+)', cookie)
        return match.group(1) if match else None
    
    def extract_vmid_from_cookie(self, cookie: str) -> Optional[str]:
        """从Cookie中提取用户ID"""
        match = re.search(r'DedeUserID=([^;]+)', cookie)
        return match.group(1) if match else None
    
    def extract_sessdata_from_cookie(self, cookie: str) -> Optional[str]:
        """从Cookie中提取SESSDATA"""
        match = re.search(r'SESSDATA=([^;]+)', cookie)
        return match.group(1) if match else None
    
    def validate_cookie(self, cookie: str) -> bool:
        """验证Cookie格式"""
        required_fields = ['SESSDATA', 'bili_jct', 'DedeUserID']
        return all(field in cookie for field in required_fields)
    
    def create_config_from_env(self) -> Config:
        """从环境变量和保存的配置创建配置"""
        # 获取必需的配置
        cookie = os.getenv("BILIBILI_COOKIE")
        if not cookie:
            raise ValueError("BILIBILI_COOKIE environment variable is required")

        if not self.validate_cookie(cookie):
            raise ValueError("Invalid cookie format. Missing required fields: SESSDATA, bili_jct, DedeUserID")

        # 提取CSRF token和用户ID
        csrf_token = self.extract_csrf_from_cookie(cookie)
        if not csrf_token:
            raise ValueError("Could not extract CSRF token from cookie")

        vmid = self.extract_vmid_from_cookie(cookie)
        if not vmid:
            raise ValueError("Could not extract user ID from cookie")

        # 尝试从环境变量获取OpenAI配置
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_base_url = os.getenv("OPENAI_BASE_URL")
        model_name = os.getenv("OPENAI_MODEL")

        # 如果环境变量中没有，尝试从保存的AI配置加载
        if not openai_api_key:
            saved_ai_config = self.load_ai_config()
            if saved_ai_config:
                openai_api_key = saved_ai_config.get("openai_api_key")
                openai_base_url = openai_base_url or saved_ai_config.get("openai_base_url", "https://api.openai.com/v1")
                model_name = model_name or saved_ai_config.get("model_name", "gpt-3.5-turbo")
                logger.info("Loaded AI configuration from saved file")
            else:
                raise ValueError("OPENAI_API_KEY not found in environment variables or saved configuration")

        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")

        # 设置默认值
        openai_base_url = openai_base_url or "https://api.openai.com/v1"
        model_name = model_name or "gpt-3.5-turbo"

        # 创建配置对象
        config = Config(
            vmid=vmid,
            cookie=cookie,
            csrf_token=csrf_token,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            model_name=model_name,
            request_delay=float(os.getenv("REQUEST_DELAY", "1.0")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            timeout=int(os.getenv("TIMEOUT", "30")),
            page_size=int(os.getenv("PAGE_SIZE", "24")),
            max_pages=int(os.getenv("MAX_PAGES", "100")),
            ai_batch_size=int(os.getenv("AI_BATCH_SIZE", "10"))
        )

        logger.info("Configuration created successfully")
        return config
    
    def create_sample_env_file(self, file_path: str = ".env.example"):
        """创建示例配置文件"""
        sample_content = """# 哔哩哔哩配置
# 从浏览器开发者工具中复制完整的Cookie
BILIBILI_COOKIE=your_complete_cookie_here

# OpenAI配置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo

# 请求配置
REQUEST_DELAY=1.0
MAX_RETRIES=3
TIMEOUT=30

# 分页配置
PAGE_SIZE=24
MAX_PAGES=100

# AI分析配置
AI_BATCH_SIZE=10
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        logger.info(f"Sample configuration file created: {file_path}")
    
    def validate_config(self, config: Config) -> Dict[str, Any]:
        """验证配置"""
        issues = []
        warnings = []
        
        # 验证必需字段
        if not config.vmid:
            issues.append("User ID (vmid) is missing")
        
        if not config.cookie:
            issues.append("Cookie is missing")
        elif not self.validate_cookie(config.cookie):
            issues.append("Cookie format is invalid")
        
        if not config.csrf_token:
            issues.append("CSRF token is missing")
        
        if not config.openai_api_key:
            issues.append("OpenAI API key is missing")
        
        # 验证数值范围
        if config.request_delay < 0.1:
            warnings.append("Request delay is very low, may cause rate limiting")
        
        if config.max_retries < 1:
            issues.append("Max retries must be at least 1")
        
        if config.timeout < 10:
            warnings.append("Timeout is very low, may cause request failures")
        
        if config.page_size < 1 or config.page_size > 50:
            warnings.append("Page size should be between 1 and 50")
        
        if config.max_pages < 1:
            issues.append("Max pages must be at least 1")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }

    def save_ai_config(self, ai_config: Dict[str, str]):
        """保存AI配置到JSON文件"""
        try:
            with open(self.ai_config_file, 'w', encoding='utf-8') as f:
                json.dump(ai_config, f, indent=2, ensure_ascii=False)
            logger.info(f"AI configuration saved to {self.ai_config_file}")
        except Exception as e:
            logger.error(f"Failed to save AI config: {e}")
            raise

    def save_bili_credential_from_cookie(self, cookie: str):
        """通过cookie保存B站凭证"""
        try:
            set_key(self.config_file, "BILIBILI_COOKIE", cookie)
            logger.info("Bilibili credential saved from cookie.")
        except Exception as e:
            logger.error(f"Failed to save Bilibili credential from cookie: {e}")
            raise

    def load_ai_config(self) -> Dict[str, str]:
        """从JSON文件加载AI配置"""
        if not os.path.exists(self.ai_config_file):
            return {}

        try:
            with open(self.ai_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"AI configuration loaded from {self.ai_config_file}")
            return config
        except Exception as e:
            logger.warning(f"Failed to load AI config: {e}")
            return {}

    def load_bili_credential(self) -> Optional[BiliCredential]:
        """从环境变量加载B站凭证"""
        self.load_env_file()
        cookie = os.getenv("BILIBILI_COOKIE")
        if not cookie or not self.validate_cookie(cookie):
            logger.warning("Bilibili cookie not found or invalid in environment variables.")
            return None

        bili_jct = self.extract_csrf_from_cookie(cookie)
        dedeuserid = self.extract_vmid_from_cookie(cookie)
        sessdata = self.extract_sessdata_from_cookie(cookie)

        if not all([bili_jct, dedeuserid, sessdata]):
            logger.error("Failed to extract all required fields from cookie.")
            return None

        logger.info("Bilibili credential loaded successfully.")
        return BiliCredential(
            bili_jct=bili_jct,
            sessdata=sessdata,
            dedeuserid=dedeuserid
        )

    def save_bilibili_cookie(self, cookie: str):
        """保存哔哩哔哩Cookie到环境变量文件"""
        try:
            set_key(self.config_file, "BILIBILI_COOKIE", cookie)
            logger.info("Bilibili cookie saved to environment file")
        except Exception as e:
            logger.error(f"Failed to save cookie: {e}")
            raise

    def create_config_interactive(self, cookie: str, ai_config: Dict[str, str]) -> Config:
        """从交互式输入创建配置"""
        # 验证Cookie格式
        if not self.validate_cookie(cookie):
            raise ValueError("Invalid cookie format")

        # 提取CSRF token和用户ID
        csrf_token = self.extract_csrf_from_cookie(cookie)
        if not csrf_token:
            raise ValueError("Could not extract CSRF token from cookie")

        vmid = self.extract_vmid_from_cookie(cookie)
        if not vmid:
            raise ValueError("Could not extract user ID from cookie")

        # 创建配置对象
        config = Config(
            vmid=vmid,
            cookie=cookie,
            csrf_token=csrf_token,
            openai_api_key=ai_config.get("openai_api_key", ""),
            openai_base_url=ai_config.get("openai_base_url", "https://api.openai.com/v1"),
            model_name=ai_config.get("model_name", "gpt-3.5-turbo"),
            request_delay=float(os.getenv("REQUEST_DELAY", "1.0")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            timeout=int(os.getenv("TIMEOUT", "30")),
            page_size=int(os.getenv("PAGE_SIZE", "24")),
            max_pages=int(os.getenv("MAX_PAGES", "100")),
            ai_batch_size=int(os.getenv("AI_BATCH_SIZE", "10"))
        )

        logger.info("Interactive configuration created successfully")
        return config

    def has_saved_ai_config(self) -> bool:
        """检查是否有保存的AI配置"""
        return os.path.exists(self.ai_config_file) and bool(self.load_ai_config())


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """设置日志配置"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 设置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 添加文件处理器（如果指定）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    logger.info(f"Logging configured with level: {level}")


def get_cookie_instructions() -> str:
    """获取Cookie获取说明"""
    return """
获取哔哩哔哩Cookie的步骤：

1. 打开浏览器，登录哔哩哔哩网站 (https://www.bilibili.com)
2. 按F12打开开发者工具
3. 切换到"网络"(Network)标签页
4. 刷新页面
5. 在网络请求列表中找到任意一个请求
6. 点击该请求，在右侧面板中找到"请求标头"(Request Headers)
7. 复制完整的Cookie值

Cookie应该包含以下关键字段：
- SESSDATA: 会话数据
- bili_jct: CSRF令牌
- DedeUserID: 用户ID

示例Cookie格式：
SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx; ...

注意：
- Cookie包含敏感信息，请妥善保管
- Cookie有有效期，过期后需要重新获取
- 不要在公共场所或代码仓库中暴露Cookie
"""


def create_project_structure():
    """创建项目目录结构"""
    directories = [
        "logs",
        "data",
        "config"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        logger.info(f"Created directory: {directory}")


class ErrorHandler:
    """错误处理器"""
    
    @staticmethod
    def handle_api_error(error: Exception, context: str = "") -> str:
        """处理API错误"""
        error_msg = f"API Error in {context}: {str(error)}"
        logger.error(error_msg)
        return error_msg
    
    @staticmethod
    def handle_config_error(error: Exception) -> str:
        """处理配置错误"""
        error_msg = f"Configuration Error: {str(error)}"
        logger.error(error_msg)
        return error_msg
    
    @staticmethod
    def handle_network_error(error: Exception, context: str = "") -> str:
        """处理网络错误"""
        error_msg = f"Network Error in {context}: {str(error)}"
        logger.error(error_msg)
        return error_msg
    
    @staticmethod
    def handle_ai_error(error: Exception) -> str:
        """处理AI分析错误"""
        error_msg = f"AI Analysis Error: {str(error)}"
        logger.error(error_msg)
        return error_msg