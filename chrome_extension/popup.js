// 存储管理类
class StorageManager {
    static async setItem(key, value) {
        return chrome.storage.sync.set({ [key]: value });
    }

    static async getItem(key, defaultValue = '') {
        const result = await chrome.storage.sync.get([key]);
        return result[key] !== undefined ? result[key] : defaultValue;
    }

    static async removeItem(key) {
        return chrome.storage.sync.remove([key]);
    }
}

// UI元素
let elements = {};

// 网站配置列表 - 与 content.js 保持一致
const SITE_CONFIGS = [
    {
        domains: ['chat.deepseek.com'],
        name: 'DeepSeek'
    },
    {
        domains: ['chatgpt.com', 'chat.openai.com',  ],
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

// 检查域名是否被支持并返回配置
function getSiteConfig(hostname) {
    return SITE_CONFIGS.find(config => 
        config.domains.some(domain => hostname === domain || hostname.endsWith('.' + domain))
    );
}

// 初始化UI元素
function initElements() {
    elements = {
        enableAgent: document.getElementById('enableAgent'),
        siteName: document.getElementById('siteName'),
        siteDesc: document.getElementById('siteDesc'),
        supportedSites: document.getElementById('supportedSites'),
        totalDomains: document.getElementById('totalDomains'),
        openSettings: document.getElementById('openSettings')
    };
    
    console.log('Popup: UI元素初始化完成');
}

// 更新网站状态显示
function updateSiteStatus(siteConfig, hostname) {
    const indicator = elements.siteName.querySelector('.status-indicator');
    
    if (siteConfig) {
        elements.siteName.innerHTML = `
            <span class="status-indicator status-active"></span>
            ${siteConfig.name}
        `;
        elements.siteDesc.textContent = `已支持 | ${hostname}`;
    } else {
        elements.siteName.innerHTML = `
            <span class="status-indicator status-inactive"></span>
            未支持的网站
        `;
        elements.siteDesc.textContent = `当前网站不在AI聊天平台列表中 | ${hostname}`;
    }
}

// 获取当前网站信息
async function getCurrentSiteInfo() {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab && tab.url) {
            const url = new URL(tab.url);
            const hostname = url.hostname;
            const siteConfig = getSiteConfig(hostname);
            
            updateSiteStatus(siteConfig, hostname);
            return { hostname, siteConfig };
        }
    } catch (error) {
        elements.siteName.innerHTML = `
            <span class="status-indicator status-unknown"></span>
            检测失败
        `;
        elements.siteDesc.textContent = '无法检测当前网站';
        console.error('获取网站信息失败:', error);
    }
    return null;
}

// 加载设置
async function loadSettings() {
    try {
        const isEnabled = await StorageManager.getItem('enabled', 'false') === 'true';
        if (elements.enableAgent) {
            elements.enableAgent.checked = isEnabled;
        }
    } catch (error) {
        console.error('加载设置失败:', error);
    }
}

// 保存启用状态
async function saveEnableState() {
    try {
        const isEnabled = elements.enableAgent ? elements.enableAgent.checked : false;
        await StorageManager.setItem('enabled', isEnabled.toString());
        
        // 发送消息到content script
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab) {
            chrome.tabs.sendMessage(tab.id, {
                action: 'updateEnabled',
                enabled: isEnabled
            }).catch(() => {}); // 忽略错误
        }
        
        console.log('启用状态已更新:', isEnabled);
    } catch (error) {
        console.error('保存启用状态失败:', error);
    }
}

// 打开详细设置 - 通知content script显示浮动UI
async function openDetailedSettings() {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab) {
            // 发送消息给content script，让它显示详细设置界面
            chrome.tabs.sendMessage(tab.id, {
                action: 'showDetailedSettings'
            }).catch(() => {
                // 如果content script没有加载，尝试注入
                chrome.scripting.executeScript({
                    target: { tabId: tab.id },
                    files: ['content.js']
                }).catch(error => {
                    console.error('无法注入content script:', error);
                });
            });
            
            // 关闭popup
            window.close();
        }
    } catch (error) {
        console.error('打开详细设置失败:', error);
    }
}

// 更新统计信息
function updateStatistics() {
    const supportedSitesCount = SITE_CONFIGS.length;
    const totalDomains = SITE_CONFIGS.reduce((total, config) => total + config.domains.length, 0);
    
    if (elements.supportedSites) {
        elements.supportedSites.textContent = supportedSitesCount;
    }
    if (elements.totalDomains) {
        elements.totalDomains.textContent = totalDomains;
    }
    
    console.log(`Popup: 支持 ${supportedSitesCount} 个AI平台，${totalDomains} 个域名`);
}

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Popup: DOM已加载，开始初始化');
    
    // 初始化UI元素
    initElements();
    
    // 绑定事件监听器
    if (elements.enableAgent) {
        elements.enableAgent.addEventListener('change', saveEnableState);
    }
    if (elements.openSettings) {
        elements.openSettings.addEventListener('click', openDetailedSettings);
    }
    
    // 更新统计信息
    updateStatistics();
    
    // 获取网站信息并加载设置
    await getCurrentSiteInfo();
    await loadSettings();
    
    console.log('Popup: 初始化完成');
});