# Bilibili Favorites Classifier  B站收藏夹AI分类整理工具

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

一个使用 AI 智能分析 Bilibili 收藏夹内容，并自动将视频移动到指定收藏夹的自动化工具。

---

## ✨ 功能特性

- **🤖 智能分类**：利用大语言模型（如 OpenAI GPT 系列、Gemini 等）分析视频的标题和简介，从你指定的收藏夹列表中，为视频匹配最合适的分类。
- **📂 全自动整理**：根据 AI 的分类结果，自动将视频从源收藏夹移动到目标收藏夹，整个过程在你的 B站账号内完成，无需本地下载。
- **🔒 安全登录**：支持通过扫描二维码登录B站，无需手动填写和暴露复杂的 Cookie，安全又便捷。
- **🎮 交互式体验**：通过美观、直观的命令行界面 (CLI) 与用户交互，每一步操作都有清晰的指引。
- **⚙️ 灵活配置**：通过简单的配置文件 (`.env` 和 `ai_config.json`) 管理个人凭证和 AI 服务，易于修改和维护。

## 🚀 快速开始

### 1. 环境准备

- 确保你的电脑已经安装了 Python 3.7 或更高版本。
- 准备好你的 Bilibili 账号和一个能够提供大语言模型服务的 API Key。

### 2. 克隆与安装

首先，将项目克隆到你的本地：
```bash
git clone https://github.com/atri1011/Bilibili-Favorites-Classifier.git
cd Bilibili-Favorites-Classifier
```

然后，安装所有必需的依赖库：
```bash
pip install -r requirements.txt
```

### 3. 配置

在第一次运行前，你需要创建两个配置文件。项目已经为你准备好了模板，你只需要复制并修改即可。

1.  **创建B站配置文件**：
    复制 `.env.example` 并重命名为 `.env`。暂时将 `BILIBILI_COOKIE` 的值留空，程序会在首次运行时引导你通过扫码登录来自动填充。

2.  **创建AI服务配置文件**：
    复制 `ai_config.json.example` 并重命名为 `ai_config.json`。然后，填入你的 AI 服务信息：
    ```json
    {
      "api_key": "YOUR_OPENAI_API_KEY",
      "base_url": "YOUR_OPENAI_BASE_URL",
      "model": "YOUR_MODEL_NAME"
    }
    ```

### 4. 运行程序

一切准备就绪！现在，运行主程序：
```bash
python main.py classify
```

## 📖 使用流程

程序启动后，会引导你完成以下步骤：

1.  **登录B站**：如果这是你第一次运行，程序会提示你通过扫描命令行中出现的二维码来登录你的B站账号。
2.  **选择源收藏夹**：程序会列出你所有的收藏夹，你需要输入一个序号，选择你想要整理的那个收藏夹。
3.  **选择目标收藏夹**：接下来，你需要再次输入一个或多个收藏夹的序号（用英文逗号隔开），告诉 AI 只能在这些你指定的收藏夹里做选择。
4.  **AI自动分类与移动**：程序会遍历源收藏夹里的所有视频，让 AI 为每个视频在你的目标收藏夹里找到最合适的“新家”，然后自动完成移动。
5.  **查看结果**：所有操作完成后，程序会用一个清晰的表格向你汇报每个视频的整理结果。

---

希望这份文档能帮助你更好地使用和分享这个项目！( ´ ▽ ` )ﾉ