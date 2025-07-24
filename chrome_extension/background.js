// Service Worker for Chrome Extension
// 处理扩展的生命周期和后台任务
// 
// 架构说明：
// - 扩展现在会在所有网站加载，但只在检测到支持的AI聊天网站时激活功能
// - 网站配置使用数组格式，便于管理和扩展
// - 支持多域名配置，便于AI平台的镜像站点或备用域名

// 安装时的初始化
chrome.runtime.onInstalled.addListener(() => {
    console.log('Prompt Agent Extension 已安装');
    
    // 设置默认值
    chrome.storage.sync.set({
        'enabled': 'false',
        'apikey': ''
    });
});

// 监听来自content script或popup的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    switch (request.action) {
        case 'getSettings':
            // 获取设置
            chrome.storage.sync.get(['enabled', 'apikey'], (result) => {
                sendResponse({
                    enabled: result.enabled === 'true',
                    apiKey: result.apikey || ''
                });
            });
            return true; // 保持消息通道开放
            
        case 'saveSettings':
            // 保存设置
            chrome.storage.sync.set({
                'enabled': request.enabled.toString(),
                'apikey': request.apiKey
            }, () => {
                sendResponse({ success: true });
            });
            return true;
            
        case 'makeApiRequest':
            // 处理API请求（如果需要从background处理）
            handleApiRequest(request.data)
                .then(response => sendResponse({ success: true, data: response }))
                .catch(error => sendResponse({ success: false, error: error.message }));
            return true;
            
        case 'getSupportedSites':
            // 获取支持的网站列表
            sendResponse({ 
                success: true, 
                sites: SITE_CONFIGS.map(config => ({
                    name: config.name,
                    domains: config.domains
                }))
            });
            return true;
    }
});

// API请求处理函数
async function handleApiRequest(requestData) {
    const { endpoint, headers, body } = requestData;
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(body)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Background API请求失败:', error);
        throw error;
    }
}

// 扩展更新时的处理
chrome.runtime.onUpdateAvailable.addListener(() => {
    console.log('Prompt Agent Extension 有更新可用');
});

// 网站配置列表 - 与 content.js 保持一致
const SITE_CONFIGS = [
    {
        domains: ['chat.deepseek.com'],
        name: 'DeepSeek'
    },
    {
        domains: ['chatgpt.com', 'chat.openai.com'],
        name: 'ChatGPT'
    },
    {
        domains: ['claude.ai'],
        name: 'Claude'
    },
    {
        domains: ['gemini.google.com'],
        name: 'Gemini'
    },
    {
        domains: ['doubao.com', 'www.doubao.com'],
        name: '豆包'
    },
    {
        domains: ['grok.com'],
        name: 'Grok'
    },
    {
        domains: ['tongyi.com', 'qianwen.com'],
        name: '千问'
    },
    {
        domains: ['hunyuan.tencent.com'],
        name: '混元'
    },
    {
        domains: ['yuanbao.tencent.com'],
        name: '元宝'
    },
    {
        domains: ['yiyan.baidu.com'],
        name: '文心一言'
    },
    {
        domains: ['www.perplexity.ai', 'perplexity.ai'],
        name: 'Perplexity'
    },
    {
        domains: ['poe.com'],
        name: 'Poe'
    }
];

// 检查域名是否被支持
function isSupportedSite(hostname) {
    return SITE_CONFIGS.find(config => 
        config.domains.some(domain => hostname === domain || hostname.endsWith('.' + domain))
    );
}

// 处理标签页更新
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    // 当页面加载完成时，检查是否是支持的网站
    if (changeInfo.status === 'complete' && tab.url) {
        try {
            const hostname = new URL(tab.url).hostname;
            const siteConfig = isSupportedSite(hostname);
            
            if (siteConfig) {
                // 可以在这里添加特定网站的处理逻辑
                console.log('Prompt Agent: 检测到支持的网站', siteConfig.name, '域名:', hostname);
            }
        } catch (error) {
            // 忽略无效URL
        }
    }
});

// 处理存储变化
chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === 'sync') {
        console.log('Prompt Agent: 设置已更改', changes);
        
        // 通知所有活跃的content scripts设置已更改
        chrome.tabs.query({ active: true }, (tabs) => {
            tabs.forEach(tab => {
                if (tab.id) {
                    chrome.tabs.sendMessage(tab.id, {
                        action: 'settingsChanged',
                        changes: changes
                    }).catch(() => {
                        // 忽略无法发送消息的标签页
                    });
                }
            });
        });
    }
});

// 错误处理
self.addEventListener('error', (event) => {
    console.error('Prompt Agent Background Error:', event.error);
});

self.addEventListener('unhandledrejection', (event) => {
    console.error('Prompt Agent Background Unhandled Rejection:', event.reason);
});

console.log('Prompt Agent Background Script 已加载');