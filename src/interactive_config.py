"""
交互式配置界面
"""
import asyncio
import logging
from typing import Dict, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from bilibili_auth import BilibiliAuth, BilibiliAuthError
from config_manager import ConfigManager

logger = logging.getLogger(__name__)
console = Console()


class InteractiveConfig:
    """交互式配置管理"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def display_welcome(self):
        """显示欢迎界面"""
        welcome_text = Text()
        welcome_text.append("🚀 哔哩哔哩关注列表智能分组工具\n", style="bold blue")
        welcome_text.append("欢迎使用交互式配置向导！\n\n", style="cyan")
        welcome_text.append("本向导将帮助您：\n", style="white")
        welcome_text.append("• 通过扫码登录获取哔哩哔哩认证\n", style="green")
        welcome_text.append("• 配置AI分析服务\n", style="green")
        welcome_text.append("• 保存配置以供后续使用\n", style="green")
        
        console.print(Panel(welcome_text, title="配置向导", style="bold blue"))
    
    def get_ai_config_interactive(self) -> Dict[str, str]:
        """交互式获取AI配置"""
        console.print(Panel.fit("🤖 AI服务配置", style="bold green"))
        
        # 检查是否有保存的配置
        saved_config = self.config_manager.load_ai_config()
        if saved_config:
            # 验证保存的配置是否完整
            required_keys = ["openai_api_key", "openai_base_url", "model_name"]
            if all(key in saved_config for key in required_keys) and Confirm.ask("检测到已保存的AI配置，是否使用？"):
                console.print("✅ 使用已保存的AI配置", style="green")
                return saved_config
            else:
                console.print("⚠️  检测到不完整的旧版AI配置，需要重新配置。", style="yellow")
        
        ai_config = {}
        
        # API Key
        console.print("\n📝 请输入OpenAI API Key:")
        console.print("  • 可从 https://platform.openai.com/api-keys 获取", style="dim")
        console.print("  • 输入内容将被隐藏", style="dim")
        
        api_key = Prompt.ask("API Key", password=True)
        if not api_key.strip():
            console.print("❌ API Key不能为空", style="red")
            return self.get_ai_config_interactive()
        
        ai_config["openai_api_key"] = api_key.strip()
        
        # Base URL
        console.print("\n🌐 请输入API Base URL (可选):")
        console.print("  • 默认: https://api.openai.com/v1", style="dim")
        console.print("  • 如使用代理或其他服务商，请修改此URL", style="dim")
        
        base_url = Prompt.ask("Base URL", default="https://api.openai.com/v1")
        ai_config["openai_base_url"] = base_url.strip()
        
        # Model
        console.print("\n🧠 请选择AI模型:")
        console.print("  • gpt-3.5-turbo (推荐，成本较低)", style="dim")
        console.print("  • gpt-4 (更准确，成本较高)", style="dim")
        console.print("  • gpt-4-turbo (平衡选择)", style="dim")
        
        model = Prompt.ask("模型名称", default="gpt-3.5-turbo")
        ai_config["model_name"] = model.strip()
        
        # 显示配置摘要
        table = Table(title="AI配置摘要")
        table.add_column("配置项", style="cyan")
        table.add_column("值", style="white")
        
        table.add_row("API Key", f"{'*' * (len(ai_config['openai_api_key']) - 8)}{ai_config['openai_api_key'][-8:]}")
        table.add_row("Base URL", ai_config["openai_base_url"])
        table.add_row("模型", ai_config["model_name"])
        
        console.print(table)
        
        # 确认保存
        if Confirm.ask("\n💾 是否保存AI配置以供后续使用？"):
            try:
                self.config_manager.save_ai_config(ai_config)
                console.print("✅ AI配置已保存", style="green")
            except Exception as e:
                console.print(f"⚠️  保存失败: {e}", style="yellow")
        
        return ai_config
    
    async def get_bilibili_auth_interactive(self) -> Optional[str]:
        """交互式获取哔哩哔哩认证"""
        console.print(Panel.fit("📱 哔哩哔哩登录认证", style="bold blue"))
        
        console.print("请选择登录方式:")
        console.print("1. 扫码登录 (推荐)")
        console.print("2. 手动输入Cookie")
        
        choice = Prompt.ask("请选择", choices=["1", "2"], default="1")
        
        if choice == "1":
            return await self._qrcode_login()
        else:
            return self._manual_cookie_input()
    
    async def _qrcode_login(self) -> Optional[str]:
        """扫码登录流程"""
        console.print("\n🔄 正在生成登录二维码...", style="yellow")
        
        try:
            async with BilibiliAuth() as auth:
                console.print("\n🔄 正在生成登录二维码...", style="yellow")

                # 生成二维码
                qrcode_key, qrcode_url = await auth.generate_qrcode()

                # 显示二维码
                console.print(Panel.fit("📱 请使用哔哩哔哩APP扫描二维码", style="bold green"))

                qr_ascii = auth.display_qrcode(qrcode_url)
                console.print(qr_ascii)

                console.print(f"🔗 二维码链接: {qrcode_url}", style="dim")
                console.print("\n⏳ 等待扫码登录...", style="yellow")

                # 显示进度并等待登录
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("等待扫码登录...", total=None)

                    # 等待登录
                    cookie = await auth.wait_for_login(qrcode_key, timeout=180)

                    progress.update(task, description="登录完成" if cookie else "登录超时")

                if cookie:
                    console.print("✅ 登录成功！", style="green")

                    # 显示用户信息
                    user_info = auth.extract_user_info_from_cookie(cookie)
                    if user_info.get('user_id'):
                        console.print(f"👤 用户ID: {user_info['user_id']}", style="cyan")

                    return cookie
                else:
                    console.print("❌ 登录失败或超时", style="red")
                    return None
                    
        except BilibiliAuthError as e:
            console.print(f"❌ 登录失败: {e}", style="red")
            return None
        except Exception as e:
            console.print(f"❌ 未知错误: {e}", style="red")
            return None
    
    def _manual_cookie_input(self) -> Optional[str]:
        """手动输入Cookie"""
        console.print("\n📝 请输入哔哩哔哩Cookie:")
        console.print("获取方法:", style="bold")
        console.print("1. 登录哔哩哔哩网站")
        console.print("2. 按F12打开开发者工具")
        console.print("3. 切换到Network标签页")
        console.print("4. 刷新页面")
        console.print("5. 找到任意请求，复制Cookie值")
        console.print()
        
        cookie = Prompt.ask("Cookie", password=True)
        
        if not cookie.strip():
            console.print("❌ Cookie不能为空", style="red")
            return None
        
        # 验证Cookie
        if not self.config_manager.validate_cookie(cookie):
            console.print("❌ Cookie格式无效，缺少必要字段", style="red")
            if Confirm.ask("是否重新输入？"):
                return self._manual_cookie_input()
            return None
        
        console.print("✅ Cookie验证通过", style="green")
        return cookie
    
    async def run_interactive_setup(self) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
        """运行完整的交互式设置流程"""
        self.display_welcome()
        
        # 获取AI配置
        console.print("\n" + "="*50)
        ai_config = self.get_ai_config_interactive()
        
        # 获取哔哩哔哩认证
        console.print("\n" + "="*50)
        cookie = await self.get_bilibili_auth_interactive()
        
        if cookie and ai_config:
            console.print("\n" + "="*50)
            console.print(Panel.fit("🎉 配置完成！", style="bold green"))
            console.print("✅ 所有配置已完成，可以开始使用工具了", style="green")
        else:
            console.print("\n" + "="*50)
            console.print(Panel.fit("⚠️  配置未完成", style="bold yellow"))
            if not cookie:
                console.print("❌ 哔哩哔哩认证失败", style="red")
            if not ai_config:
                console.print("❌ AI配置失败", style="red")
        
        return cookie, ai_config
    
    def show_config_status(self):
        """显示当前配置状态"""
        console.print(Panel.fit("📊 配置状态", style="bold blue"))
        
        # 检查AI配置
        has_ai_config = self.config_manager.has_saved_ai_config()
        ai_status = "✅ 已配置" if has_ai_config else "❌ 未配置"
        
        # 检查环境变量中的Cookie
        import os
        has_cookie = bool(os.getenv("BILIBILI_COOKIE"))
        cookie_status = "✅ 已配置" if has_cookie else "❌ 未配置"
        
        table = Table()
        table.add_column("配置项", style="cyan")
        table.add_column("状态", style="white")
        
        table.add_row("AI服务", ai_status)
        table.add_row("哔哩哔哩认证", cookie_status)
        
        console.print(table)
        
        if has_ai_config and has_cookie:
            console.print("\n🎉 所有配置已完成，可以直接运行工具！", style="green")
        else:
            console.print("\n⚠️  请完成缺失的配置项", style="yellow")