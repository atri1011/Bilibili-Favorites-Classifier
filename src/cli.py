import asyncio
import sys
from typing import Dict, List, Tuple

import click
from rich.console import Console
from rich.progress import Progress
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from ai_classifier import AIClassifier
from bilibili_client import BilibiliClient
from config_manager import ConfigManager
from models import ClassificationResult, FavoriteFolder, VideoInfo
from interactive_config import InteractiveConfig


@click.command()
def cli():
    """
    Bilibili-Favorites-Classifier: 一个使用 AI 对 Bilibili 收藏夹进行分类的工具。
    主要功能是：对 Bilibili 收藏夹中的视频进行 AI 智能分类。
    """
    try:
        asyncio.run(classify_async())
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[yellow]操作被用户中断。[/yellow]")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"[bold red]执行过程中发生未处理的错误: {e}[/bold red]")
        sys.exit(1)


async def ensure_config_is_ready() -> Tuple[Dict, Dict]:
    """
    确保所有配置都准备就绪，如果缺少配置则启动交互式向导。
    """
    config_manager = ConfigManager()
    console = Console()

    # 尝试加载现有配置
    bili_config = config_manager.load_bili_credential()
    ai_config = config_manager.load_ai_config()

    # 检查配置是否完整
    if bili_config and ai_config:
        console.print("✅ 配置加载成功。", style="green")
        return bili_config, ai_config

    # 如果配置不完整，启动交互式设置
    console.print("\n[bold yellow]⚠️  检测到配置不完整或缺失，启动交互式配置向导...[/bold yellow]")
    interactive_config = InteractiveConfig(config_manager)
    
    # 运行交互式设置
    cookie, new_ai_config = await interactive_config.run_interactive_setup()

    if cookie and new_ai_config:
        # 保存配置
        config_manager.save_bili_credential_from_cookie(cookie)
        config_manager.save_ai_config(new_ai_config)
        console.print("\n[bold green]✅ 配置已成功保存。[/bold green]")
        
        # 重新加载以确保一致性
        bili_config = config_manager.load_bili_credential()
        ai_config = config_manager.load_ai_config()
        return bili_config, ai_config
    else:
        console.print("\n[bold red]❌ 配置未完成，程序无法继续。[/bold red]")
        sys.exit(1)


async def classify_async():
    """
    异步执行分类的核心逻辑。
    """
    console = Console()
    bili_client = None
    ai_classifier = None

    try:
        # 1. 确保配置就绪
        bili_config, ai_config = await ensure_config_is_ready()

        # 2. 初始化客户端
        console.print("[cyan]正在初始化客户端...[/cyan]")
        bili_client = BilibiliClient(bili_config)
        ai_classifier = AIClassifier(ai_config)

        # 3. 获取并选择收藏夹
        console.print("[cyan]正在获取您的收藏夹列表...[/cyan]")
        folders: List[FavoriteFolder] = await bili_client.get_favorite_folders()
        if not folders:
            console.print("[yellow]您没有任何收藏夹，或者无法获取收藏夹列表。[/yellow]")
            return

        folder_table = Table(title="您的 Bilibili 收藏夹", show_header=True, header_style="bold magenta")
        folder_table.add_column("序号", style="dim", width=6)
        folder_table.add_column("收藏夹名称", min_width=20)
        folder_table.add_column("视频数量", justify="right")

        for i, folder in enumerate(folders, 1):
            folder_table.add_row(str(i), folder.title, str(folder.media_count))

        console.print(folder_table)

        # 提示用户选择
        choice = IntPrompt.ask(
            "[bold green]请输入要分类的收藏夹序号[/bold green]",
            choices=[str(i) for i in range(1, len(folders) + 1)],
            show_choices=False
        )
        selected_folder = folders[choice - 1]
        console.print(f"您选择了: [bold yellow]{selected_folder.title}[/bold yellow]")

        # 3.5. 获取用户指定的目标收藏夹
        while True:
            target_choices_str = Prompt.ask(
                "\n[bold green]请输入目标收藏夹序号（多个请用英文逗号隔开，例如 1,3,4）[/bold green]",
                default=str(choice)
            )
            try:
                target_indices = [int(i.strip()) for i in target_choices_str.split(',')]
                if all(1 <= i <= len(folders) for i in target_indices):
                    target_folders = [folders[i - 1] for i in target_indices]
                    break
                else:
                    console.print("[red]输入包含无效的序号，请重新输入。[/red]")
            except ValueError:
                console.print("[red]输入格式不正确，请输入数字并用逗号隔开。[/red]")

        target_folder_names = [f.title for f in target_folders]
        console.print(f"您选择的目标收藏夹是: [bold yellow]{', '.join(target_folder_names)}[/bold yellow]")

        # 4. 获取视频
        console.print(f"\n[cyan]正在获取 “{selected_folder.title}” 中的所有视频...[/cyan]")
        videos: List[VideoInfo] = await bili_client.get_videos_in_folder(selected_folder.id)
        if not videos:
            console.print(f"[yellow]收藏夹 “{selected_folder.title}” 中没有视频。[/yellow]")
            return

        # 5. 获取批处理大小并进行分类
        batch_size = IntPrompt.ask(
            "\n[bold green]您想一次分类多少个视频？ (建议 5-20)[/bold green]",
            default=10
        )
        
        # 将视频列表切分为批次
        video_batches = [videos[i:i + batch_size] for i in range(0, len(videos), batch_size)]
        
        classification_results: List[ClassificationResult] = []
        console.print(f"\n[cyan]准备对 {len(videos)} 个视频进行分类（每批 {batch_size} 个），请稍候...[/cyan]")

        with Progress(console=console) as progress:
            task = progress.add_task("[green]AI 批量分类中...", total=len(videos))
            
            for i, batch in enumerate(video_batches):
                progress.update(task, description=f"[green]正在处理第 {i+1}/{len(video_batches)} 批...[/green]")
                
                # 调用新的批量分类方法
                batch_results = await ai_classifier.batch_classify_videos(batch, target_folders=target_folder_names)
                
                # 处理批量返回的结果
                for video, category in zip(batch, batch_results):
                    if category:
                        classification_results.append(
                            ClassificationResult(video=video, category=category)
                        )
                    else:
                        # 可以在这里添加处理分类失败的逻辑
                        console.print(f"[yellow]警告：视频 '{video.title}' 分类失败，已跳过。[/yellow]")

                # 更新进度条
                progress.update(task, advance=len(batch))

        console.print("\n[bold green]🎉 所有视频分类完成！[/bold green]")

        # 6. 处理分类结果并移动视频
        console.print("\n[cyan]开始整理收藏夹...[/cyan]")
        result_table = Table(title="AI 智能分类与整理结果", show_header=True, header_style="bold cyan")
        result_table.add_column("视频标题", min_width=40, style="yellow")
        result_table.add_column("目标收藏夹", min_width=20, style="green")
        result_table.add_column("状态", min_width=20, style="blue")

        # 创建一个现有收藏夹名称到ID的映射，方便查找
        folder_map = {f.title: f.id for f in folders}

        for res in classification_results:
            video = res.video
            category = res.category.strip().replace("：", "/").replace(":", "/")
            
            # 检查AI返回的分类是否在用户指定的目标收藏夹列表中
            if category not in target_folder_names:
                status = f"[yellow]⚠️ 跳过：AI分类 '{category}' 不在目标列表中[/yellow]"
                result_table.add_row(video.title, category, status)
                continue

            target_folder_id = folder_map.get(category)
            status = ""
            try:
                # 移动视频
                if target_folder_id:
                    console.print(f"  [cyan]正在移动视频 '{video.title[:20]}...' 到 '{category}'...[/cyan]")
                    success = await bili_client.move_video(
                        video_aid=video.aid,
                        source_folder_id=selected_folder.id,
                        target_folder_id=target_folder_id,
                    )
                    if success:
                        status = f"[green]✔ 已移动到 '{category}'[/green]"
                    else:
                        status = f"[red]✘ 移动失败[/red]"
                else:
                    # 如果分类在 target_folder_names 但不在 folder_map 中，这表示逻辑错误
                    status = f"[bold red]❌ 内部错误：无法找到收藏夹 '{category}' 的ID[/bold red]"

            except Exception as e:
                status = f"[bold red]处理时发生错误: {e}[/bold red]"

            result_table.add_row(video.title, category, status)
            await asyncio.sleep(0.5) # 防止API调用过于频繁

        console.print(result_table)
        console.print("\n[bold green]✨ 所有视频整理完成！[/bold green]")

    except Exception as e:
        console.print(f"\n[bold red]发生错误: {e}[/bold red]")
        # 在这里可以添加更详细的错误处理逻辑
    finally:
        # 7. 确保关闭客户端
        if bili_client:
            console.print("[cyan]正在关闭 Bilibili 客户端...[/cyan]")
            await bili_client.close()
        if ai_classifier:
            console.print("[cyan]正在关闭 AI 客户端...[/cyan]")
            await ai_classifier.close()
        console.print("[bold]✨ 操作完成，感谢使用！[/bold]")