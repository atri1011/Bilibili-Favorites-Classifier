# Bilibili Favorites Classifier

一个使用AI分析和分类B站收藏夹的工具。

## ✨ 功能特性

- **自动分类**：利用大语言模型（如 OpenAI GPT）分析视频的标题和简介，智能地为视频打上分类标签。
- **交互式体验**：通过美观的命令行界面 (CLI) 与用户交互，操作直观友好。
- **扫码登录**：无需手动填写Cookie，通过扫描二维码即可安全登录B站。
- **灵活配置**：支持通过 `.env` 文件自定义 AI 模型、Prompt 和 API 地址。
- **（即将推出）自动整理**：根据分类结果，自动创建新的收藏夹并移动视频。

## 🚀 如何使用

1.  **克隆项目**
    ```bash
    git clone https://github.com/your-username/Bilibili-Favorites-Classifier.git
    cd Bilibili-Favorites-Classifier
    ```

2.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

3.  **运行程序**
    ```bash
    python main.py
    ```

程序启动后会自动检查配置。如果这是你第一次运行，或者配置不完整，它会启动一个交互式的配置向导，引导你完成以下步骤：
- **扫码登录B站**：会在命令行中显示一个二维码，请使用B站手机App扫描登录。
- **设置OpenAI**：提示你输入 OpenAI API Key 和 API Base URL (如果需要)。

配置完成后，凭证会安全地保存在本地，下次运行时就无需再次配置啦！(o´ω`o)ﾉ