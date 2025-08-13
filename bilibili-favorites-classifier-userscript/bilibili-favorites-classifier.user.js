// ==UserScript==
// @name         Bilibili 收藏夹 AI 分类助手 (新版UI)
// @namespace    http://tampermonkey.net/
// @version      1.2.4
// @description  利用AI（GPT）智能、批量地整理Bilibili收藏夹，采用全新的悬浮按钮和侧滑面板UI，提供流畅的交互体验，支持多源收藏夹。
// @author       Roo
// @match        *://space.bilibili.com/*
// @icon         https://www.bilibili.com/favicon.ico
// @grant        GM_addStyle
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @connect      *
// @license      MIT
// ==/UserScript==

(function() {
    'use strict';

    // 1. --- 注入CSS样式 ---
    GM_addStyle(`
        /* 悬浮操作按钮 (FAB) */
        #bfc-fab {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 50px;
            height: 50px;
            background-color: #fb7299; /* B站粉色 */
            border-radius: 50%;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
            z-index: 10000;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            opacity: 0.8;
        }

        #bfc-fab:hover {
            opacity: 1;
            transform: scale(1.1);
        }

        #bfc-fab span {
            font-size: 24px;
            color: white;
            transition: transform 0.3s ease;
        }

        #bfc-fab.active {
            transform: rotate(360deg);
        }

        #bfc-settings-view {
            padding: 20px;
            border-top: 1px solid #e3e5e7;
            background-color: #fff;
        }

        .bfc-hidden {
            display: none !important;
        }

        #bfc-panel {
            position: fixed;
            top: 0;
            right: -360px;
            width: 350px;
            height: 100%;
            background-color: #f4f5f7;
            box-shadow: -5px 0 15px rgba(0, 0, 0, 0.1);
            z-index: 9999;
            transition: right 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
            display: flex;
            flex-direction: column;
            border-left: 1px solid #e3e5e7;
        }

        #bfc-panel.active {
            right: 0;
        }

        .bfc-panel-header {
            padding: 15px 20px;
            border-bottom: 1px solid #e3e5e7;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .bfc-panel-header h2 {
            margin: 0;
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
        }
        .bfc-panel-header .icons span {
            font-size: 20px;
            cursor: pointer;
            margin-left: 15px;
            color: #666;
        }

        .bfc-panel-body {
            flex-grow: 1;
            padding: 20px;
            overflow-y: auto;
        }

        .bfc-panel-footer {
            padding: 15px 20px;
            border-top: 1px solid #e3e5e7;
            background-color: #fff;
            font-size: 12px;
            color: #999;
        }

        .bfc-form-group {
            margin-bottom: 20px;
        }
        .bfc-form-group label {
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
            font-weight: 500;
            color: #333;
        }
        .bfc-select, .bfc-input, .bfc-button {
            width: 100%;
            padding: 10px;
            border-radius: 6px;
            border: 1px solid #ccc;
            font-size: 14px;
            box-sizing: border-box;
        }

        .bfc-checkbox-group {
            background-color: #fff;
            border: 1px solid #ccc;
            border-radius: 6px;
            padding: 10px;
            height: 120px;
            overflow-y: auto;
        }

        .bfc-checkbox-item {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }

        .bfc-checkbox-item input[type="checkbox"] {
            margin-right: 8px;
        }

        .bfc-checkbox-item label {
            font-weight: normal;
            font-size: 14px;
            cursor: pointer;
            flex-grow: 1;
        }

        .bfc-button {
            background-color: #fb7299;
            color: white;
            border: none;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        .bfc-button:hover {
            background-color: #e56a8a;
        }

        .bfc-log-item {
            padding: 8px;
            border-bottom: 1px solid #eee;
            font-size: 13px;
        }
        .bfc-log-item.success { color: #28a745; }
        .bfc-log-item.error { color: #dc3545; }
        .bfc-log-item.info { color: #17a2b8; }

        #bfc-batch-create-btn {
            background-color: #00a1d6; /* B站蓝 */
            color: white;
            border: none;
            cursor: pointer;
            margin-top: 10px; /* 与上一个按钮的间距 */
            transition: background-color 0.3s, opacity 0.3s;
        }
        #bfc-batch-create-btn:hover {
            background-color: #00b5e5;
        }
        #bfc-batch-create-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
    `);

    const RECOMMENDED_FOLDERS = [
        '学习 - 方法论与效率', '学习 - 学科知识', '学习 - 语言',
        '科普 - 前沿科技', '科普 - 硬核原理', '科普 - 人文社科', '科普 - 趣味百科',
        '技能 - 编程开发', '技能 - 设计创作', '技能 - 办公软件', '技能 - 生活实用',
        '游戏 - 实况集锦', '游戏 - 攻略教学', '游戏 - 文化杂谈',
        '生活 - 美食探店', '生活 - 萌宠动物', '生活 - 旅行Vlog',
        '娱乐 - 搞笑整活', '娱乐 - 影视动漫', '娱乐 - 音乐'
    ];

    const UIManager = {
        init() {
            this.injectFAB();
            this.injectPanel();
            this.cacheDOMElements();
            this.setupEventListeners();
            this.loadSettings();
            // 不再需要外部注入
        },

        cacheDOMElements() {
            this.fab = document.getElementById('bfc-fab');
            this.panel = document.getElementById('bfc-panel');
            this.settingsView = document.getElementById('bfc-settings-view');
            this.settingsToggle = document.getElementById('bfc-settings-toggle');
            this.closePanelBtn = document.getElementById('bfc-close-panel');
            this.startBtn = document.getElementById('bfc-start-btn');
            this.saveSettingsBtn = document.getElementById('bfc-save-settings-btn');
            this.apiKeyInput = document.getElementById('bfc-api-key');
            this.apiHostInput = document.getElementById('bfc-api-host');
            this.sourceFoldersContainer = document.getElementById('bfc-source-folders');
            this.targetFoldersContainer = document.getElementById('bfc-target-folders');
            this.logContainer = document.getElementById('bfc-log');
            this.modelSelect = document.getElementById('bfc-model-select');
            this.customModelInput = document.getElementById('bfc-custom-model');
            this.customModelGroup = document.getElementById('bfc-custom-model-group');
            this.batchCreateBtn = document.getElementById('bfc-batch-create-btn'); // 新增缓存
        },

        injectFAB() {
            const fabHTML = `<div id="bfc-fab"><span>AI</span></div>`;
            document.body.insertAdjacentHTML('beforeend', fabHTML);
        },

        injectPanel() {
            const panelHTML = `
                <div id="bfc-panel">
                    <div class="bfc-panel-header">
                        <h2>AI分类助手</h2>
                        <div class="icons">
                            <span id="bfc-settings-toggle" title="设置">⚙️</span>
                            <span id="bfc-close-panel" title="关闭">❌</span>
                        </div>
                    </div>
                    <div id="bfc-settings-view" class="bfc-hidden">
                        <div class="bfc-form-group">
                            <label for="bfc-api-key">API Key</label>
                            <input type="password" id="bfc-api-key" class="bfc-input" placeholder="请输入你的API Key">
                        </div>
                        <div class="bfc-form-group">
                            <label for="bfc-api-host">API Host</label>
                            <input type="text" id="bfc-api-host" class="bfc-input" placeholder="例如: https://api.openai.com">
                        </div>
                         <div class="bfc-form-group">
                            <label for="bfc-model-select">AI 模型</label>
                            <select id="bfc-model-select" class="bfc-select">
                                <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                                <option value="gpt-4">gpt-4</option>
                                <option value="gpt-4o">gpt-4o</option>
                                <option value="custom">自定义</option>
                            </select>
                        </div>
                        <div id="bfc-custom-model-group" class="bfc-form-group bfc-hidden">
                            <label for="bfc-custom-model">自定义模型名称</label>
                            <input type="text" id="bfc-custom-model" class="bfc-input" placeholder="请输入模型名称">
                        </div>
                        <button id="bfc-save-settings-btn" class="bfc-button">保存设置</button>
                    </div>
                    <div class="bfc-panel-body" id="bfc-main-view">
                        <div class="bfc-form-group">
                            <label for="bfc-source-folders">选择源收藏夹 (可多选)</label>
                            <div id="bfc-source-folders" class="bfc-checkbox-group"></div>
                        </div>
                        <div class="bfc-form-group">
                            <label for="bfc-target-folders">选择目标收藏夹 (可多选)</label>
                            <div id="bfc-target-folders" class="bfc-checkbox-group"></div>
                        </div>
                        <button id="bfc-start-btn" class="bfc-button">开始分类</button>
                        <button id="bfc-batch-create-btn" class="bfc-button">一键创建推荐收藏夹</button>
                        <div id="bfc-log" style="margin-top: 20px; height: 200px; overflow-y: scroll; background: #fff; border: 1px solid #e3e5e7; padding: 10px; border-radius: 6px;"></div>
                    </div>
                    <div class="bfc-panel-footer">
                        Made with ❤️ by Roo
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', panelHTML);
        },

        setupEventListeners() {
            this.fab.addEventListener('click', () => this.togglePanel());
            this.closePanelBtn.addEventListener('click', () => this.togglePanel(false));
            this.settingsToggle.addEventListener('click', () => this.toggleSettings());
            this.saveSettingsBtn.addEventListener('click', () => {
                this.saveSettings();
                this.log('设置已保存', 'success');
            });
            this.modelSelect.addEventListener('change', (e) => {
                this.customModelGroup.classList.toggle('bfc-hidden', e.target.value !== 'custom');
            });
            this.startBtn.addEventListener('click', () => App.start());
            this.batchCreateBtn.addEventListener('click', () => BatchCreator.start()); // 新增事件监听
        },

        loadSettings() {
            this.apiKeyInput.value = GM_getValue('apiKey', '');
            this.apiHostInput.value = GM_getValue('apiHost', 'https://api.openai.com');
            const apiModel = GM_getValue('apiModel', 'gpt-3.5-turbo');
            const customApiModel = GM_getValue('customApiModel', '');
            this.modelSelect.value = apiModel;
            if (apiModel === 'custom') {
                this.customModelInput.value = customApiModel;
                this.customModelGroup.classList.remove('bfc-hidden');
            }
        },

        saveSettings() {
            GM_setValue('apiKey', this.apiKeyInput.value);
            GM_setValue('apiHost', this.apiHostInput.value);
            const selectedModel = this.modelSelect.value;
            GM_setValue('apiModel', selectedModel);
            if (selectedModel === 'custom') {
                GM_setValue('customApiModel', this.customModelInput.value);
            }
        },

        togglePanel(forceState) {
            const isActive = this.panel.classList.contains('active');
            const nextState = typeof forceState === 'boolean' ? forceState : !isActive;
            this.panel.classList.toggle('active', nextState);
            this.fab.classList.toggle('active', nextState);
        },

        toggleSettings() {
            this.settingsView.classList.toggle('bfc-hidden');
        },

        renderFavorites(container, folders, idPrefix) {
            container.innerHTML = '';
            if (!folders || folders.length === 0) {
                container.innerHTML = '<p style="text-align: center; color: #999;">没有找到收藏夹哦</p>';
                return;
            }
            folders.forEach(folder => {
                const itemHTML = `
                    <div class="bfc-checkbox-item">
                      <input type="checkbox" id="${idPrefix}-${folder.id}" value="${folder.id}">
                      <label for="${idPrefix}-${folder.id}">${folder.title} (${folder.media_count})</label>
                    </div>
                `;
                container.insertAdjacentHTML('beforeend', itemHTML);
            });
        },

        getUserInput() {
            const apiKey = GM_getValue('apiKey');
            const apiHost = GM_getValue('apiHost');
            const apiModel = GM_getValue('apiModel');
            const customApiModel = GM_getValue('customApiModel');
            const modelName = apiModel === 'custom' ? customApiModel : apiModel;
            const sourceFavoriteIds = Array.from(this.sourceFoldersContainer.querySelectorAll('input[type="checkbox"]:checked'))
                .map(cb => cb.value);
            const targetFavoriteIds = Array.from(this.targetFoldersContainer.querySelectorAll('input[type="checkbox"]:checked'))
                .map(cb => cb.value);
            const csrf = document.cookie.match(/bili_jct=([^;]+)/) ? document.cookie.match(/bili_jct=([^;]+)/)[1] : null;
            return { apiKey, apiHost, modelName, sourceFavoriteIds, targetFavoriteIds, csrf };
        },

        log(message, type = 'info') {
            const logItem = document.createElement('div');
            logItem.className = `bfc-log-item ${type}`;
            logItem.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            this.logContainer.appendChild(logItem);
            this.logContainer.scrollTop = this.logContainer.scrollHeight;
        }
    };

    const BilibiliAPI = {
        async getAllFavorites(mid) {
            const url = `https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid=${mid}`;
            const response = await fetch(url, { headers: { 'Accept': 'application/json' }, credentials: 'include' });
            const data = await response.json();
            if (data.code === 0 && data.data) {
                return data.data.list || [];
            } else if (data.code === 0 && (data.data === null || data.data.list === null)) {
                return [];
            } else {
                throw new Error(`获取收藏夹列表失败: ${data.message}`);
            }
        },

        async getFavoriteVideos(media_id, ps = 20) {
            let allVideos = [];
            let pageNum = 1;
            let hasMore = true;
            while (hasMore) {
                const url = `https://api.bilibili.com/x/v3/fav/resource/list?media_id=${media_id}&pn=${pageNum}&ps=${ps}&order=mtime`;
                const response = await fetch(url, { headers: { 'Accept': 'application/json' }, credentials: 'include' });
                const data = await response.json();
                if (data.code === 0 && data.data && data.data.medias) {
                    allVideos = allVideos.concat(data.data.medias);
                    hasMore = data.data.has_more;
                    pageNum++;
                } else {
                    hasMore = false;
                    if (data.code !== 0) {
                        throw new Error(`获取收藏夹视频失败 (Code: ${data.code}): ${data.message}`);
                    }
                }
            }
            return allVideos;
        },

        async moveVideo(resourceId, targetMediaId, fromMediaId, csrf) {
             const url = 'https://api.bilibili.com/x/v3/fav/resource/deal';
             const params = new URLSearchParams();
             params.append('rid', resourceId);
             params.append('type', 2);
             params.append('add_media_ids', targetMediaId);
             params.append('del_media_ids', fromMediaId);
             params.append('csrf', csrf);
             const response = await fetch(url, {
                 method: 'POST',
                 body: params,
                 credentials: 'include',
                 headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' }
             });
             const data = await response.json();
             if (data.code !== 0) {
                 throw new Error(`移动视频失败: ${data.message}`);
             }
             return data;
        },

        createFolder(name, csrf) {
            return new Promise((resolve, reject) => {
                GM_xmlhttpRequest({
                    method: 'POST',
                    url: 'https://api.bilibili.com/x/v3/fav/folder/add',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
                    data: `title=${encodeURIComponent(name)}&public=0&csrf=${csrf}`,
                    onload: function(response) {
                        try {
                            const result = JSON.parse(response.responseText);
                            if (result.code === 0) {
                                resolve(result);
                            } else {
                                reject(new Error(result.message || '未知错误'));
                            }
                        } catch (e) {
                            reject(new Error('解析响应失败'));
                        }
                    },
                    onerror: function() {
                        reject(new Error('网络请求失败'));
                    }
                });
            });
        }
    };

    const AIClassifier = {
        classify(video, targetFolders, apiKey, apiHost, modelName) {
            return new Promise((resolve, reject) => {
                const prompt = `
                    我有一个B站收藏的视频，信息如下：
                    - 标题: "${video.title}"
                    - 简介: "${video.intro}"
                    - UP主: "${video.upper.name}"

                    请从以下目标收藏夹列表中，选择一个最合适的收藏夹来存放这个视频。
                    目标收藏夹列表:
                    ${targetFolders.map(f => `- ${f.title}`).join('\n')}

                    请仅返回最合适的收藏夹的名称，不要添加任何多余的解释或标点符号。
                `;
                GM_xmlhttpRequest({
                    method: "POST",
                    url: `${apiHost}/v1/chat/completions`,
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${apiKey}`
                    },
                    data: JSON.stringify({
                        model: modelName,
                        messages: [{ role: "user", content: prompt }],
                        temperature: 0.5,
                    }),
                    onload: function(response) {
                        if (response.status === 200) {
                            try {
                                const result = JSON.parse(response.responseText);
                                const folderName = result.choices[0].message.content.trim();
                                resolve(folderName);
                            } catch (e) {
                                reject(new Error(`解析API响应失败: ${e.message}`));
                            }
                        } else {
                             try {
                                const errorInfo = JSON.parse(response.responseText);
                                reject(new Error(`API请求失败 (状态: ${response.status}): ${errorInfo.error.message}`));
                            } catch (e) {
                                reject(new Error(`API请求失败 (状态: ${response.status})，且无法解析错误响应。`));
                            }
                        }
                    },
                    onerror: function(response) {
                        reject(new Error(`网络请求错误: ${response.statusText}`));
                    }
                });
            });
        }
    };

    const BatchCreator = {
        async start() {
            const btn = document.getElementById('bfc-batch-create-btn');
            if (!btn) return;

            const csrfMatch = document.cookie.match(/bili_jct=([^;]+)/);
            if (!csrfMatch) {
                alert('获取CSRF Token失败，请确保您已登录B站。');
                return;
            }
            const csrf = csrfMatch[1];

            if (!confirm(`即将创建 ${RECOMMENDED_FOLDERS.length} 个推荐收藏夹，确定吗？`)) {
                return;
            }

            btn.disabled = true;
            let successCount = 0;
            let failCount = 0;

            for (let i = 0; i < RECOMMENDED_FOLDERS.length; i++) {
                const name = RECOMMENDED_FOLDERS[i];
                btn.textContent = `创建中 (${i + 1}/${RECOMMENDED_FOLDERS.length})...`;
                try {
                    await BilibiliAPI.createFolder(name, csrf);
                    successCount++;
                } catch (error) {
                    failCount++;
                    console.error(`创建收藏夹 "${name}" 失败: ${error.message}`);
                }
                await new Promise(resolve => setTimeout(resolve, 500));
            }

            btn.textContent = '一键创建推荐收藏夹';
            btn.disabled = false;
            alert(`创建完成！\n成功: ${successCount}个\n失败: ${failCount}个\n\n页面即将刷新以展示新收藏夹。`);
            location.reload();
        }
    };

    const App = {
        allFolders: [],
        mid: null,

        async init() {
            UIManager.init();
            try {
                const midMatch = window.location.href.match(/space.bilibili.com\/(\d+)/);
                if (!midMatch) {
                    UIManager.log('无法从URL中获取用户MID，请确保在正确的空间页面', 'error');
                    return;
                }
                this.mid = midMatch[1];
                UIManager.log(`成功获取到用户MID: ${this.mid}`, 'info');

                UIManager.log('正在获取收藏夹列表...');
                const folders = await BilibiliAPI.getAllFavorites(this.mid);
                this.allFolders = folders;
                UIManager.renderFavorites(UIManager.sourceFoldersContainer, folders, 'source');
                UIManager.renderFavorites(UIManager.targetFoldersContainer, folders, 'target');
                UIManager.log('收藏夹列表加载成功', 'success');
            } catch (error) {
                UIManager.log(error.message, 'error');
            }
        },

        async start() {
            UIManager.log('开始分类任务...', 'info');
            const { apiKey, apiHost, modelName, sourceFavoriteIds, targetFavoriteIds, csrf } = UIManager.getUserInput();
            if (!apiKey || !apiHost || !modelName || sourceFavoriteIds.length === 0 || targetFavoriteIds.length === 0 || !csrf) {
                UIManager.log('请检查设置：API Key/Host/模型, 源/目标收藏夹 和 CSRF Token 不能为空', 'error');
                return;
            }
            const targetFolders = this.allFolders.filter(f => targetFavoriteIds.includes(f.id.toString()));
            const sourceFolders = this.allFolders.filter(f => sourceFavoriteIds.includes(f.id.toString()));
            try {
                for (const sourceId of sourceFavoriteIds) {
                    const sourceFolder = sourceFolders.find(f => f.id.toString() === sourceId);
                    if (!sourceFolder) continue;
                    UIManager.log(`正在从源收藏夹 [${sourceFolder.title}] 获取视频...`);
                    const videos = await BilibiliAPI.getFavoriteVideos(sourceId);
                    UIManager.log(`从 [${sourceFolder.title}] 获取到 ${videos.length} 个视频, 开始处理...`, 'info');
                    await this.handleMoves(videos, targetFolders, { apiKey, apiHost, modelName, csrf, sourceMediaId: sourceId });
                }
                UIManager.log('所有视频处理完毕！', 'success');
            } catch (error) {
                UIManager.log(`任务执行失败: ${error.message}`, 'error');
            }
        },

        async handleMoves(videos, targetFolders, config) {
            for (const video of videos) {
                try {
                    if (targetFolders.some(tf => tf.id.toString() === config.sourceMediaId)) {
                        UIManager.log(`视频「${video.title}」已在目标收藏夹中，跳过。`, 'info');
                        continue;
                    }

                    UIManager.log(`正在为视频「${video.title}」请求AI分类...`);
                    const predictedFolderName = await AIClassifier.classify(video, targetFolders, config.apiKey, config.apiHost, config.modelName);
                    UIManager.log(`AI建议分类到: 「${predictedFolderName}」`);

                    const targetFolder = targetFolders.find(f => f.title === predictedFolderName);
                    if (targetFolder) {
                        await BilibiliAPI.moveVideo(video.id, targetFolder.id, config.sourceMediaId, config.csrf);
                        UIManager.log(`成功将「${video.title}」移动到「${targetFolder.title}」`, 'success');
                    } else {
                        UIManager.log(`未找到匹配的目标收藏夹: 「${predictedFolderName}」, 跳过移动`, 'error');
                    }
                } catch (error) {
                    UIManager.log(`处理视频「${video.title}」时出错: ${error.message}`, 'error');
                }
            }
        }
    };

    App.init();

})();