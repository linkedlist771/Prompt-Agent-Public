// Prompt Agent - AI聊天网站智能体扩展
// 此扩展会在所有网站上加载，但只在检测到支持的AI聊天网站时激活功能
// 支持的网站列表在 SITE_CONFIGS 数组中定义

// 存储管理类 - Chrome Extension版本
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

// 全局配置变量
let isEnabled = false;
let apiKey = '';
let isProcessing = false;
let currentSiteConfig = null;
let enableRetrival = false; // 新增：prompts知识库开关，默认关闭
let collectionName = 'default'; // 新增：选中的知识库名称，默认为default

// 网站配置列表
// 要添加新的AI聊天网站支持，请在此数组中添加新的配置对象
// 配置格式说明：
// - domains: 支持的域名列表，可以包含多个域名和子域名
// - name: 网站显示名称
// - textareaSelectors: 输入框选择器列表，按优先级排序
// - sendButtonSelectors: 发送按钮选择器列表，按优先级排序
// - textInputMethod: 输入方法 ('direct'|'simulate'|'chatgpt_safe'|'gemini_safe'|'contenteditable_safe')
const SITE_CONFIGS = [
    {
        domains: ['chat.deepseek.com'],
        name: 'DeepSeek',
        textareaSelectors: ['textarea'],
        sendButtonSelectors: [
            'button[type="submit"]',
            '[data-testid="send-button"]',
            '.send-button'
        ],
        textInputMethod: 'simulate'
    },
    {
        domains: ['chatgpt.com', 'chat.openai.com',  ],
        name: 'ChatGPT',
        textareaSelectors: [
            'div[contenteditable="true"]',
            'textarea',
            '[contenteditable="true"]'
        ], 
        sendButtonSelectors: [
            'button[data-testid="send-button"]',
            'button[aria-label*="Send"]',
            'button:has(svg)',
            'button[type="submit"]'
        ],
        textInputMethod: 'chatgpt_safe' // 使用专门的ChatGPT安全方法
    },
    {
        domains: ['claude.ai'],
        name: 'Claude',
        textareaSelectors: ['div[contenteditable="true"]', 'textarea', '[contenteditable="true"]'],
        sendButtonSelectors: [
            'button[aria-label*="Send"]',
            'button:has(svg)',
            'button[type="submit"]'
        ],
        textInputMethod: 'simulate'
    },
    {
        domains: ['gemini.google.com'],
        name: 'Gemini',
        textareaSelectors: [
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"]', 
            'textarea', 
            '[contenteditable="true"]'
        ],
        sendButtonSelectors: [
            'button[aria-label*="Send"]',
            'button[aria-label*="发送"]',
            'button:has(svg)',
            'button[type="submit"]',
            'button[data-testid="send-button"]'
        ],
        textInputMethod: 'gemini_safe' // 使用专门的Gemini安全方法
    },
    {
        domains: ['doubao.com', 'www.doubao.com'],
        name: '豆包',
        textareaSelectors: ['textarea'],
        sendButtonSelectors: [
            'button[type="submit"]',
            'button:has(svg)',
            'button[aria-label*="发送"]',
            'button[aria-label*="Send"]',
            '.send-button'
        ],
        textInputMethod: 'direct' // 使用直接设置value的方法
    },
    {
        domains: ['grok.com'],
        name: 'Grok',
        textareaSelectors: ['textarea'],
        sendButtonSelectors: [
            'button[type="submit"]',
            'button:has(svg)',
            'button[aria-label*="Send"]',
            'button[data-testid="send-button"]',
            '.send-button'
        ],
        textInputMethod: 'direct' // 使用直接设置value的方法
    },
    {
        domains: ['tongyi.com', 'qianwen.com'],
        name: '千问',
        textareaSelectors: ['textarea'],
        sendButtonSelectors: [
            'button[type="submit"]',
            'button:has(svg)',
            'button[aria-label*="发送"]',
            'button[aria-label*="Send"]',
            '.send-button'
        ],
        textInputMethod: 'direct' // 使用直接设置value的方法
    },
    {
        domains: ['hunyuan.tencent.com'],
        name: '混元',
        textareaSelectors: ['textarea'],
        sendButtonSelectors: [
            'button[type="submit"]',
            'button:has(svg)',
            'button[aria-label*="发送"]',
            'button[aria-label*="Send"]',
            '.send-button'
        ],
        textInputMethod: 'direct' // 使用直接设置value的方法
    },
    {
        domains: ['yuanbao.tencent.com'],
        name: '元宝',
        textareaSelectors: [
            'div[contenteditable="true"]',
            '[contenteditable="true"]',
            'textarea'
        ],
        sendButtonSelectors: [
            'button[type="submit"]',
            'button:has(svg)',
            'button[aria-label*="发送"]',
            'button[aria-label*="Send"]',
            '.send-button'
        ],
        textInputMethod: 'contenteditable_safe' // 使用contenteditable安全方法
    },
    {
        domains: ['yiyan.baidu.com'],
        name: '文心一言',
        textareaSelectors: [
            'div[contenteditable="true"]',
            '[contenteditable="true"]',
            'textarea'
        ],
        sendButtonSelectors: [
            'button[type="submit"]',
            'button:has(svg)',
            'button[aria-label*="发送"]',
            'button[aria-label*="Send"]',
            '.send-button'
        ],
        textInputMethod: 'contenteditable_safe' // 使用contenteditable安全方法
    },
    {
        domains: ['www.perplexity.ai', 'perplexity.ai'],
        name: 'Perplexity',
        textareaSelectors: ['textarea'],
        sendButtonSelectors: [
            'button[type="submit"]',
            'button:has(svg)',
            'button[aria-label*="Submit"]',
            'button[aria-label*="Send"]',
            '.send-button'
        ],
        textInputMethod: 'direct' // 使用直接设置value的方法
    },
    {
        domains: ['poe.com'],
        name: 'Poe',
        textareaSelectors: ['textarea'],
        sendButtonSelectors: [
            'button[type="submit"]',
            'button:has(svg)',
            'button[aria-label*="Send"]',
            'button[aria-label*="Submit"]',
            '.send-button'
        ],
        textInputMethod: 'direct' // 使用直接设置value的方法
    }
    
    // 添加新网站配置模板（取消注释并修改以添加新网站）：
    /*
    {
        domains: ['example.com', 'chat.example.com'], // 支持的域名列表
        name: '新AI网站', // 显示名称
        textareaSelectors: [ // 输入框选择器，按优先级排序
            'textarea',
            'div[contenteditable="true"]',
            '[contenteditable="true"]'
        ],
        sendButtonSelectors: [ // 发送按钮选择器，按优先级排序
            'button[type="submit"]',
            'button[aria-label*="Send"]',
            'button[aria-label*="发送"]',
            'button:has(svg)',
            '.send-button'
        ],
        textInputMethod: 'direct' // 可选值: 'direct', 'simulate', 'chatgpt_safe', 'gemini_safe', 'contenteditable_safe'
    }
    */
];

// API配置
const API_CONFIG = {
    endpoint: "http://127.0.0.1:3648/api/v1/chat/completions",
    usageEndpoint: "http://127.0.0.1:3648/api/v1/api_key/get_information",
    collectionsEndpoint: "http://127.0.0.1:3648/api/v1/prompt_db/list_collections",
    model: "mock-gpt-model",
    maxTokens: 512,
    temperature: 0.1,
    queryInterval: 10000 // 10秒查询一次
};

// 全局变量
let usageQueryTimer = null;

// 消息提示管理类 - 类似Ant Design
class MessageManager {
    static instances = [];
    static maxCount = 3;
    static zIndex = 10010;

    static show(content, type = 'info', duration = 3000) {
        const message = new Message(content, type, duration);
        this.instances.push(message);
        
        // 限制最大消息数量
        if (this.instances.length > this.maxCount) {
            const oldMessage = this.instances.shift();
            oldMessage.destroy();
        }
        
        this.updatePositions();
        return message;
    }

    static success(content, duration = 3000) {
        return this.show(content, 'success', duration);
    }

    static error(content, duration = 5000) {
        return this.show(content, 'error', duration);
    }

    static warning(content, duration = 4000) {
        return this.show(content, 'warning', duration);
    }

    static info(content, duration = 3000) {
        return this.show(content, 'info', duration);
    }

    static updatePositions() {
        this.instances.forEach((message, index) => {
            message.updatePosition(index);
        });
    }

    static removeInstance(message) {
        const index = this.instances.indexOf(message);
        if (index > -1) {
            this.instances.splice(index, 1);
            this.updatePositions();
        }
    }
}

class Message {
    constructor(content, type, duration) {
        this.content = content;
        this.type = type;
        this.duration = duration;
        this.element = null;
        this.timer = null;
        this.create();
        this.show();
        
        if (duration > 0) {
            this.timer = setTimeout(() => {
                this.destroy();
            }, duration);
        }
    }

    create() {
        const container = document.createElement('div');
        container.style.cssText = `
            position: fixed;
            top: 24px;
            left: 50%;
            transform: translateX(-50%);
            z-index: ${MessageManager.zIndex};
            pointer-events: auto;
            transition: all 0.3s ease;
            opacity: 0;
            transform: translateX(-50%) translateY(-20px);
        `;

        const messageBox = document.createElement('div');
        const colors = {
            success: { bg: '#f6ffed', border: '#b7eb8f', icon: '#52c41a', text: '#389e0d' },
            error: { bg: '#fff2f0', border: '#ffccc7', icon: '#ff4d4f', text: '#cf1322' },
            warning: { bg: '#fffbe6', border: '#ffe58f', icon: '#faad14', text: '#d46b08' },
            info: { bg: '#f0f5ff', border: '#91d5ff', icon: '#1890ff', text: '#096dd9' }
        };
        
        const color = colors[this.type] || colors.info;
        
        messageBox.style.cssText = `
            display: flex;
            align-items: center;
            padding: 9px 12px;
            border-radius: 6px;
            background: ${color.bg};
            border: 1px solid ${color.border};
            box-shadow: 0 3px 6px -4px rgba(0, 0, 0, 0.12), 0 6px 16px 0 rgba(0, 0, 0, 0.08), 0 9px 28px 8px rgba(0, 0, 0, 0.05);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 14px;
            line-height: 1.5715;
            color: ${color.text};
            max-width: 400px;
            word-break: break-word;
        `;

        const iconHtml = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ⓘ'
        };

        const icon = document.createElement('span');
        icon.textContent = iconHtml[this.type] || iconHtml.info;
        icon.style.cssText = `
            margin-right: 8px;
            font-weight: bold;
            color: ${color.icon};
        `;

        const text = document.createElement('span');
        text.textContent = this.content;
        text.style.cssText = 'flex: 1;';

        messageBox.appendChild(icon);
        messageBox.appendChild(text);
        container.appendChild(messageBox);

        this.element = container;
        document.body.appendChild(container);
    }

    show() {
        setTimeout(() => {
            if (this.element) {
                this.element.style.opacity = '1';
                this.element.style.transform = 'translateX(-50%) translateY(0)';
            }
        }, 50);
    }

    updatePosition(index) {
        if (this.element) {
            this.element.style.top = `${24 + index * 60}px`;
        }
    }

    destroy() {
        if (this.timer) {
            clearTimeout(this.timer);
            this.timer = null;
        }

        if (this.element) {
            this.element.style.opacity = '0';
            this.element.style.transform = 'translateX(-50%) translateY(-20px)';
            
            setTimeout(() => {
                if (this.element && this.element.parentNode) {
                    this.element.parentNode.removeChild(this.element);
                }
                MessageManager.removeInstance(this);
            }, 300);
        }
    }
}

// 初始化网站配置
function initSiteConfig() {
    const hostname = window.location.hostname;
    
    // 在配置数组中查找匹配的域名
    currentSiteConfig = SITE_CONFIGS.find(config => 
        config.domains.some(domain => hostname === domain || hostname.endsWith('.' + domain))
    );
    
    if (!currentSiteConfig) {
        console.log('Prompt Agent: 当前网站不在支持列表中:', hostname);
        return false;
    }
    
    console.log('Prompt Agent: 已加载配置for', currentSiteConfig.name, '域名:', hostname);
    return true;
}

// 输入管理类
class InputManager {
    constructor(siteConfig) {
        this.siteConfig = siteConfig;
    }

    findActiveTextarea() {
        // 针对ChatGPT的特殊处理
        if (this.siteConfig.name === 'ChatGPT') {
            return this.findChatGPTTextarea();
        }
        
        // 针对Gemini的特殊处理
        if (this.siteConfig.name === 'Gemini') {
            return this.findGeminiTextarea();
        }
        
        // 优先查找聚焦的输入框
        for (const selector of this.siteConfig.textareaSelectors) {
            const focused = document.querySelector(selector + ':focus');
            if (focused) return focused;
        }

        // 查找页面上的输入框
        for (const selector of this.siteConfig.textareaSelectors) {
            const elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                return elements[elements.length - 1];
            }
        }

        return null;
    }

    // 专门的ChatGPT输入框查找方法
    findChatGPTTextarea() {
        // ChatGPT的输入框选择器优先级
        const chatgptSelectors = [
            'div[contenteditable="true"][data-id]',
            'div[contenteditable="true"]',
            'textarea',
            '[contenteditable="true"]'
        ];
        
        // 优先查找聚焦的输入框
        for (const selector of chatgptSelectors) {
            try {
                const focused = document.querySelector(selector + ':focus');
                if (focused && this.isValidTextInput(focused)) {
                    console.log('Prompt Agent: 找到聚焦的ChatGPT输入框', focused);
                    return focused;
                }
            } catch (e) {
                // 忽略选择器错误
            }
        }

        // 查找可见的输入框（按优先级）
        for (const selector of chatgptSelectors) {
            try {
                const elements = document.querySelectorAll(selector);
                for (const element of elements) {
                    if (this.isValidTextInput(element) && this.isElementVisible(element)) {
                        // 额外检查：确保不是聊天历史中的元素
                        if (!this.isInChatHistory(element)) {
                            console.log('Prompt Agent: 找到可用的ChatGPT输入框', element);
                            return element;
                        }
                    }
                }
            } catch (e) {
                // 忽略选择器错误
            }
        }

        console.warn('Prompt Agent: 未找到ChatGPT输入框');
        return null;
    }

    // 检查元素是否在聊天历史中
    isInChatHistory(element) {
        // 检查父元素链，避免选择到聊天历史中的contenteditable元素
        let parent = element.parentElement;
        while (parent) {
            const className = parent.className || '';
            const role = parent.getAttribute('role') || '';
            
            // 如果是聊天消息容器，则不是输入框
            if (className.includes('conversation') || 
                className.includes('message') ||
                role === 'article' ||
                role === 'group') {
                return true;
            }
            
            parent = parent.parentElement;
        }
        
        return false;
    }

    // 专门的Gemini输入框查找方法
    findGeminiTextarea() {
        // Gemini的输入框选择器优先级
        const geminiSelectors = [
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"][data-gramm="false"]',
            'div[contenteditable="true"].ql-editor',
            'div[contenteditable="true"]'
        ];
        
        // 优先查找聚焦的输入框
        for (const selector of geminiSelectors) {
            try {
                const focused = document.querySelector(selector + ':focus');
                if (focused && this.isValidTextInput(focused)) {
                    return focused;
                }
            } catch (e) {
                // 忽略选择器错误
            }
        }

        // 查找可见的输入框
        for (const selector of geminiSelectors) {
            try {
                const elements = document.querySelectorAll(selector);
                for (const element of elements) {
                    if (this.isValidTextInput(element) && this.isElementVisible(element)) {
                        return element;
                    }
                }
            } catch (e) {
                // 忽略选择器错误
            }
        }

        return null;
    }

    // 检查是否是有效的文本输入元素
    isValidTextInput(element) {
        if (!element) return false;
        
        // 检查是否可编辑
        const isEditable = element.contentEditable === 'true' || 
                          element.tagName.toLowerCase() === 'textarea';
        
        // 检查是否不是只读
        const isNotReadonly = !element.readOnly && !element.disabled;
        
        // 检查是否有合适的尺寸（避免隐藏元素）
        const rect = element.getBoundingClientRect();
        const hasSize = rect.width > 0 && rect.height > 0;
        
        return isEditable && isNotReadonly && hasSize;
    }

    // 检查元素是否可见
    isElementVisible(element) {
        const style = window.getComputedStyle(element);
        return style.display !== 'none' && 
               style.visibility !== 'hidden' && 
               style.opacity !== '0';
    }

    getTextContent(element) {
        if (element.tagName.toLowerCase() === 'textarea') {
            const value = element.value || '';
            console.log('Prompt Agent: 从textarea.value获取内容，长度:', value.length);
            return value;
        } else if (element.contentEditable === 'true' || element.getAttribute('contenteditable') === 'true') {
            const content = element.textContent || element.innerText || '';
            console.log('Prompt Agent: 从contenteditable获取内容，长度:', content.length);
            return content;
        }
        return '';
    }

    async setTextContent(element, text) {
        if (this.siteConfig.textInputMethod === 'chatgpt_safe') {
            await this.chatgptSafeTextInput(element, text);
        } else if (this.siteConfig.textInputMethod === 'contenteditable_safe') {
            await this.contenteditableSafeTextInput(element, text);
        } else if (this.siteConfig.textInputMethod === 'gemini_safe') {
            await this.geminiSafeTextInput(element, text);
        } else if (this.siteConfig.textInputMethod === 'direct') {
            this.directSetText(element, text);
        } else if (this.siteConfig.textInputMethod === 'simulate') {
            await this.simulateTextInput(element, text);
        } else {
            this.directSetText(element, text);
        }
    }

    async simulateTextInput(element, text) {
        element.focus();
        await new Promise(resolve => setTimeout(resolve, 50));

        const currentContent = this.getTextContent(element);
        if (currentContent.length > 0) {
            await this.clearContent(element);
        }

        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            
            this.simulateKeyboardEvent(element, 'keydown', char);
            this.simulateKeyboardEvent(element, 'keypress', char);
            
            if (element.tagName.toLowerCase() === 'textarea') {
                element.value = text.substring(0, i + 1);
            } else {
                element.textContent = text.substring(0, i + 1);
            }
            
            const inputEvent = new Event('input', {
                bubbles: true,
                cancelable: true,
            });
            element.dispatchEvent(inputEvent);
            
            this.simulateKeyboardEvent(element, 'keyup', char);
            
            if (i % 5 === 0) {
                await new Promise(resolve => setTimeout(resolve, 10));
            }
        }

        if (element.tagName.toLowerCase() === 'textarea') {
            element.selectionStart = element.selectionEnd = element.value.length;
        }
    }

    // 专门为ChatGPT设计的安全输入方法
    async chatgptSafeTextInput(element, text) {
        try {
            console.log('Prompt Agent: 使用ChatGPT安全输入方法');
            element.focus();
            await new Promise(resolve => setTimeout(resolve, 100));

            // 清空现有内容
            const currentContent = this.getTextContent(element);
            if (currentContent.length > 0) {
                await this.chatgptSafeClear(element);
            }

            // ChatGPT使用React，需要特殊的输入方法
            await this.chatgptReactInput(element, text);
            
        } catch (error) {
            console.warn('ChatGPT安全输入失败，使用fallback方法:', error);
            this.directSetText(element, text);
        }
    }

    // ChatGPT安全清空方法
    async chatgptSafeClear(element) {
        element.focus();
        await new Promise(resolve => setTimeout(resolve, 50));
        
        // 选择所有内容
        try {
            // 使用execCommand选择所有
            document.execCommand('selectAll');
        } catch (e) {
            // fallback方法
            if (element.tagName.toLowerCase() === 'textarea') {
                element.select();
            } else {
                const range = document.createRange();
                range.selectNodeContents(element);
                const selection = window.getSelection();
                selection.removeAllRanges();
                selection.addRange(range);
            }
        }
        
        await new Promise(resolve => setTimeout(resolve, 30));
        
        // 删除选中内容
        try {
            document.execCommand('delete');
        } catch (e) {
            // fallback
            if (element.tagName.toLowerCase() === 'textarea') {
                element.value = '';
            } else {
                element.textContent = '';
            }
        }
        
        this.safeDispatchEvent(element, 'input');
    }

    // ChatGPT React输入方法
    async chatgptReactInput(element, text) {
        console.log('Prompt Agent: 开始ChatGPT React输入，文本长度:', text.length);
        
        // 方法1: 尝试剪贴板API
        if (navigator.clipboard && window.isSecureContext) {
            try {
                const originalClipboard = await navigator.clipboard.readText().catch(() => '');
                await navigator.clipboard.writeText(text);
                
                // 触发Ctrl+V粘贴
                const pasteEvent = new KeyboardEvent('keydown', {
                    key: 'v',
                    code: 'KeyV',
                    ctrlKey: true,
                    bubbles: true,
                    cancelable: true
                });
                element.dispatchEvent(pasteEvent);
                
                // 也触发paste事件
                const clipboardEvent = new ClipboardEvent('paste', {
                    clipboardData: new DataTransfer(),
                    bubbles: true,
                    cancelable: true
                });
                
                // 设置剪贴板数据
                if (clipboardEvent.clipboardData) {
                    clipboardEvent.clipboardData.setData('text/plain', text);
                }
                
                element.dispatchEvent(clipboardEvent);
                
                // 触发必要的React事件
                this.triggerReactEvents(element, text);
                
                // 恢复原剪贴板内容
                setTimeout(() => {
                    navigator.clipboard.writeText(originalClipboard).catch(() => {});
                }, 100);
                
                console.log('Prompt Agent: 剪贴板方法完成');
                return;
                
            } catch (clipboardError) {
                console.log('剪贴板API失败，使用直接输入方法:', clipboardError);
            }
        }

        // 方法2: 直接设置文本内容并触发React事件
        try {
            // 设置文本
            if (element.tagName.toLowerCase() === 'textarea') {
                element.value = text;
            } else {
                // 对于contenteditable，使用安全的方法
                element.textContent = text;
            }
            
            // 触发React需要的事件序列
            this.triggerReactEvents(element, text);
            
            console.log('Prompt Agent: 直接输入方法完成');
            
        } catch (directError) {
            console.warn('直接输入方法失败:', directError);
            throw directError;
        }
    }

    // 触发React需要的事件
    triggerReactEvents(element, text) {
        // React通常需要这些事件才能正确更新状态
        const events = [
            'focus',
            'input', 
            'change',
            'blur'
        ];
        
        events.forEach(eventType => {
            try {
                const event = new Event(eventType, {
                    bubbles: true,
                    cancelable: true
                });
                
                // 为input事件添加额外属性
                if (eventType === 'input') {
                    Object.defineProperty(event, 'inputType', {
                        value: 'insertText'
                    });
                    Object.defineProperty(event, 'data', {
                        value: text
                    });
                }
                
                element.dispatchEvent(event);
            } catch (eventError) {
                console.warn(`触发${eventType}事件失败:`, eventError);
            }
        });
        
        // 额外触发React的onChange (如果存在的话)
        if (element._valueTracker) {
            element._valueTracker.setValue('');
        }
    }

    // 通用的contenteditable安全输入方法
    async contenteditableSafeTextInput(element, text) {
        try {
            console.log('Prompt Agent: 使用通用contenteditable安全输入方法');
            element.focus();
            await new Promise(resolve => setTimeout(resolve, 100));

            // 清空现有内容
            const currentContent = this.getTextContent(element);
            if (currentContent.length > 0) {
                await this.contenteditableSafeClear(element);
            }

            // 使用通用的contenteditable输入方法
            await this.contenteditableInput(element, text);
            
        } catch (error) {
            console.warn('contenteditable安全输入失败，使用fallback方法:', error);
            this.directSetText(element, text);
        }
    }

    // contenteditable安全清空方法
    async contenteditableSafeClear(element) {
        element.focus();
        await new Promise(resolve => setTimeout(resolve, 50));
        
        // 选择所有内容
        try {
            document.execCommand('selectAll');
        } catch (e) {
            // fallback方法
            const range = document.createRange();
            range.selectNodeContents(element);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
        }
        
        await new Promise(resolve => setTimeout(resolve, 30));
        
        // 删除选中内容
        try {
            document.execCommand('delete');
        } catch (e) {
            // fallback
            element.textContent = '';
        }
        
        this.safeDispatchEvent(element, 'input');
    }

    // contenteditable输入方法
    async contenteditableInput(element, text) {
        console.log('Prompt Agent: 开始contenteditable输入，文本长度:', text.length);
        
        // 方法1: 尝试剪贴板API
        if (navigator.clipboard && window.isSecureContext) {
            try {
                const originalClipboard = await navigator.clipboard.readText().catch(() => '');
                await navigator.clipboard.writeText(text);
                
                // 触发粘贴
                document.execCommand('paste');
                
                // 触发必要的事件
                this.triggerContenteditableEvents(element, text);
                
                // 恢复原剪贴板内容
                setTimeout(() => {
                    navigator.clipboard.writeText(originalClipboard).catch(() => {});
                }, 100);
                
                console.log('Prompt Agent: contenteditable剪贴板方法完成');
                return;
                
            } catch (clipboardError) {
                console.log('剪贴板API失败，使用直接输入方法:', clipboardError);
            }
        }

        // 方法2: 直接设置文本内容
        try {
            element.textContent = text;
            this.triggerContenteditableEvents(element, text);
            console.log('Prompt Agent: contenteditable直接输入方法完成');
            
        } catch (directError) {
            console.warn('contenteditable直接输入方法失败:', directError);
            throw directError;
        }
    }

    // 触发contenteditable需要的事件
    triggerContenteditableEvents(element, text) {
        const events = [
            'focus',
            'input', 
            'change'
        ];
        
        events.forEach(eventType => {
            try {
                const event = new Event(eventType, {
                    bubbles: true,
                    cancelable: true
                });
                
                if (eventType === 'input') {
                    Object.defineProperty(event, 'inputType', {
                        value: 'insertText'
                    });
                    Object.defineProperty(event, 'data', {
                        value: text
                    });
                }
                
                element.dispatchEvent(event);
            } catch (eventError) {
                console.warn(`触发contenteditable ${eventType}事件失败:`, eventError);
            }
        });
    }

    async clearContent(element) {
        element.focus();
        await new Promise(resolve => setTimeout(resolve, 30));

        if (element.tagName.toLowerCase() === 'textarea') {
            element.select();
        } else {
            const range = document.createRange();
            range.selectNodeContents(element);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
        }
        
        await new Promise(resolve => setTimeout(resolve, 30));

        this.simulateKeyboardEvent(element, 'keydown', 'a', { ctrlKey: true });
        this.simulateKeyboardEvent(element, 'keyup', 'a', { ctrlKey: true });
        
        this.simulateKeyboardEvent(element, 'keydown', 'Delete');
        
        if (element.tagName.toLowerCase() === 'textarea') {
            element.value = '';
        } else {
            element.textContent = '';
            while (element.firstChild) {
                element.removeChild(element.firstChild);
            }
        }
        
        const inputEvent = new Event('input', {
            bubbles: true,
            cancelable: true,
            inputType: 'deleteContentBackward'
        });
        element.dispatchEvent(inputEvent);
        
        this.simulateKeyboardEvent(element, 'keyup', 'Delete');
        await new Promise(resolve => setTimeout(resolve, 30));
    }

    // 专门为Gemini设计的安全输入方法
    async geminiSafeTextInput(element, text) {
        try {
            element.focus();
            await new Promise(resolve => setTimeout(resolve, 100));

            // 清空现有内容（不使用innerHTML避免CSP问题）
            const currentContent = this.getTextContent(element);
            if (currentContent.length > 0) {
                await this.geminiSafeClear(element);
            }

            // 使用Clipboard API或者逐字符输入
            if (navigator.clipboard && window.isSecureContext) {
                try {
                    // 尝试使用剪贴板API（更安全）
                    const originalClipboard = await navigator.clipboard.readText().catch(() => '');
                    await navigator.clipboard.writeText(text);
                    
                    // 模拟Ctrl+V粘贴
                    document.execCommand('paste');
                    
                    // 触发必要的事件
                    this.safeDispatchEvent(element, 'input');
                    this.safeDispatchEvent(element, 'change');
                    
                    // 恢复原剪贴板内容
                    setTimeout(() => {
                        navigator.clipboard.writeText(originalClipboard).catch(() => {});
                    }, 100);
                    
                } catch (clipboardError) {
                    console.log('Clipboard API失败，使用fallback方法');
                    await this.geminiDirectInput(element, text);
                }
            } else {
                await this.geminiDirectInput(element, text);
            }
        } catch (error) {
            console.warn('Gemini安全输入失败，使用直接方法:', error);
            this.directSetText(element, text);
        }
    }

    // Gemini安全清空方法
    async geminiSafeClear(element) {
        element.focus();
        await new Promise(resolve => setTimeout(resolve, 50));
        
        // 选择所有内容
        if (element.tagName.toLowerCase() === 'textarea') {
            element.select();
        } else {
            try {
                document.execCommand('selectAll');
            } catch (e) {
                // fallback
                const range = document.createRange();
                range.selectNodeContents(element);
                const selection = window.getSelection();
                selection.removeAllRanges();
                selection.addRange(range);
            }
        }
        
        await new Promise(resolve => setTimeout(resolve, 30));
        
        // 删除选中内容
        document.execCommand('delete');
        this.safeDispatchEvent(element, 'input');
    }

    // Gemini直接输入方法
    async geminiDirectInput(element, text) {
        // 逐字符输入，避免CSP问题
        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            
            if (element.tagName.toLowerCase() === 'textarea') {
                element.value = text.substring(0, i + 1);
            } else {
                // 对于contenteditable，安全地添加文本
                try {
                    const textNode = document.createTextNode(text.substring(0, i + 1));
                    element.textContent = '';
                    element.appendChild(textNode);
                } catch (e) {
                    element.textContent = text.substring(0, i + 1);
                }
            }
            
            this.safeDispatchEvent(element, 'input');
            
            // 减少延迟，每10个字符暂停一次
            if (i % 10 === 0) {
                await new Promise(resolve => setTimeout(resolve, 20));
            }
        }
    }

    // 安全的事件分发
    safeDispatchEvent(element, eventType) {
        try {
            const event = new Event(eventType, {
                bubbles: true,
                cancelable: true,
            });
            element.dispatchEvent(event);
        } catch (error) {
            console.warn(`Failed to dispatch ${eventType} event:`, error);
        }
    }

    directSetText(element, text) {
        try {
            // 聚焦元素
            element.focus();
            
            if (element.tagName.toLowerCase() === 'textarea') {
                // 直接设置textarea的value - 这是最可靠的方法
                element.value = text;
                console.log('Prompt Agent: 直接设置textarea.value，长度:', text.length, '内容preview:', text.substring(0, 50));
                
                // 设置光标到最后
                element.selectionStart = element.selectionEnd = element.value.length;
                
                // 确保滚动到底部
                element.scrollTop = element.scrollHeight;
            } else {
                // 对于其他元素，设置textContent
                element.textContent = text;
                console.log('Prompt Agent: 设置textContent，长度:', text.length);
            }
            
            // 触发必要的事件
            const events = ['input', 'change'];
            events.forEach(eventType => {
                try {
                    const event = new Event(eventType, {
                        bubbles: true,
                        cancelable: true,
                    });
                    element.dispatchEvent(event);
                    console.log(`Prompt Agent: 成功触发${eventType}事件`);
                } catch (eventError) {
                    console.warn(`触发${eventType}事件失败:`, eventError);
                }
            });
            
        } catch (error) {
            console.error('Prompt Agent: directSetText失败:', error);
        }
    }

    simulateKeyboardEvent(element, eventType, key, options = {}) {
        const event = new KeyboardEvent(eventType, {
            key: key,
            code: key,
            charCode: key.charCodeAt ? key.charCodeAt(0) : 0,
            keyCode: key.charCodeAt ? key.charCodeAt(0) : 0,
            which: key.charCodeAt ? key.charCodeAt(0) : 0,
            bubbles: true,
            cancelable: true,
            ...options
        });
        
        element.dispatchEvent(event);
    }

    findSendButton() {
        for (const selector of this.siteConfig.sendButtonSelectors) {
            try {
                const button = document.querySelector(selector);
                if (button && button.offsetParent !== null) {
                    return button;
                }
            } catch (e) {
                // 忽略无效的选择器
            }
        }

        const buttons = document.querySelectorAll('button');
        for (const button of buttons) {
            const text = button.textContent || button.innerText || '';
            if ((text.includes('发送') || text.includes('Send') || text.includes('提交')) && 
                button.offsetParent !== null) {
                return button;
            }
        }

        return null;
    }
}

// AI代理类
class AIAgent {
    constructor(inputManager) {
        this.inputManager = inputManager;
    }

    // 获取知识库列表
    async getCollectionsList() {
        if (!apiKey.trim()) {
            console.log('Prompt Agent: API Key为空，不查询知识库列表');
            return ['default']; // 返回默认选项
        }

        console.log('Prompt Agent: 开始查询知识库列表');

        try {
            const response = await fetch(API_CONFIG.collectionsEndpoint, {
                method: 'GET',
                headers: {
                    "accept": "application/json"
                }
            });

            console.log('Prompt Agent: 知识库列表API响应状态:', response.status);

            if (response.ok) {
                const collections = await response.json();
                console.log('Prompt Agent: 知识库列表:', collections);
                
                if (Array.isArray(collections) && collections.length > 0) {
                    return collections;
                } else {
                    console.warn('Prompt Agent: 知识库列表为空或格式错误');
                    return ['default'];
                }
            } else {
                console.error('Prompt Agent: 知识库列表查询失败');
                return ['default'];
            }
        } catch (error) {
            console.error('Prompt Agent: 知识库列表查询网络错误:', error);
            return ['default'];
        }
    }

    // 获取API使用信息
    async getApiUsageInfo() {
        if (!apiKey.trim()) {
            console.log('Prompt Agent: API Key为空，不查询使用信息');
            return;
        }

        console.log('Prompt Agent: 开始查询API使用信息:', apiKey);

        try {
            const url = `${API_CONFIG.usageEndpoint}/${apiKey}`;
            console.log('Prompt Agent: 请求URL:', url);
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    "accept": "application/json"
                }
            });

            console.log('Prompt Agent: API响应状态:', response.status);

            if (response.ok) {
                const data = await response.json();
                console.log('Prompt Agent: API响应数据:', data);
                
                if (data.information) {
                    this.updateUsageDisplay(data.information);
                    // MessageManager.success('API信息查询成功');
                } else {
                    console.error('Prompt Agent: 响应数据中没有information字段');
                }
            } else if (response.status === 404) {
                const errorData = await response.json().catch(() => null);
                const errorMessage = errorData?.detail || 'API key不存在';
                
                // 显示错误消息
                MessageManager.error(errorMessage);
                
                // 清空API Key
                apiKey = '';
                await StorageManager.removeItem('apikey');
                
                // 更新UI中的API Key输入框
                const apiKeyInput = document.getElementById('ai-apikey');
                if (apiKeyInput) {
                    apiKeyInput.value = '';
                    apiKeyInput.dataset.realValue = '';
                }
                
                // 隐藏使用信息显示
                const usageInfoElement = document.getElementById('ai-usage-info');
                if (usageInfoElement) {
                    usageInfoElement.style.display = 'none';
                }
                
                // 停止查询定时器
                this.stopUsageQueryTimer();
                
                console.log('Prompt Agent: API Key不存在，已清空并停止查询');
            } else {
                const errorData = await response.json().catch(() => null);
                const errorMessage = errorData?.detail || '未知错误';
                MessageManager.error(`API查询失败: ${errorMessage}`);
                console.log('Prompt Agent: API使用信息查询失败:', errorMessage);
            }
        } catch (error) {
            MessageManager.error('网络请求失败');
            console.log('Prompt Agent: API使用信息查询网络错误:', error);
        }
    }

    // 更新使用信息显示
    updateUsageDisplay(infoData) {
        console.log('Prompt Agent: 更新使用信息显示:', infoData);
        
        const usageInfoElement = document.getElementById('ai-usage-info');
        if (!usageInfoElement) {
            console.log('Prompt Agent: 使用信息元素不存在，创建新的');
            this.createUsageInfoElement();
            return this.updateUsageDisplay(infoData); // 递归调用更新
        }

        // 格式化时间
        const formatTime = (seconds) => {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            
            if (hours > 0) {
                return `${hours}小时${minutes}分钟`;
            } else if (minutes > 0) {
                return `${minutes}分钟`;
            } else {
                return `${seconds}秒`;
            }
        };

        // 格式化日期时间
        const formatDateTime = (timestamp) => {
            const date = new Date(timestamp * 1000);
            return date.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        };

        // 创建多行显示内容
        const usageText = `使用量: ${infoData.current_period_usage}/${infoData.usage_limit}`;
        const resetText = `重置: ${formatTime(infoData.time_until_reset)}`;
        const expireText = `过期: ${formatDateTime(infoData.created_at + infoData.expiration_seconds)}`;

        // 更新显示内容，使用换行符分隔
        usageInfoElement.innerHTML = `
            <div style="line-height: 1.4;">
                <div>${usageText}</div>
                <div>${resetText}</div>
                <div>${expireText}</div>
            </div>
        `;
        usageInfoElement.style.display = 'block';
        
        console.log('Prompt Agent: 使用信息已更新:', { usageText, resetText, expireText });
    }

    // 创建使用信息显示元素
    createUsageInfoElement() {
        const container = document.getElementById('ai-floating-ui');
        if (!container) {
            console.error('Prompt Agent: 找不到浮动UI容器');
            return;
        }

        const content = document.getElementById('ai-content');
        if (!content) {
            console.error('Prompt Agent: 找不到内容容器');
            return;
        }

        // 创建使用信息元素
        const usageInfo = document.createElement('div');
        usageInfo.id = 'ai-usage-info';
        usageInfo.style.cssText = `
            background: #e3f2fd;
            border: 1px solid #2196f3;
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 10px;
            font-size: 11px;
            color: #1976d2;
            text-align: center;
            display: none;
            min-height: 60px;
        `;

        // 插入到API Key输入框之后
        const apiKeyDiv = content.querySelector('div');
        if (apiKeyDiv && apiKeyDiv.nextSibling) {
            content.insertBefore(usageInfo, apiKeyDiv.nextSibling.nextSibling);
        } else {
            content.insertBefore(usageInfo, content.firstChild);
        }

        console.log('Prompt Agent: 使用信息元素已创建');
    }

    // 启动使用信息查询定时器
    startUsageQueryTimer() {
        if (usageQueryTimer) {
            clearInterval(usageQueryTimer);
        }
        
        console.log('Prompt Agent: 启动API使用信息查询定时器');
        usageQueryTimer = setInterval(async () => {
            if (apiKey.trim()) {
                await this.getApiUsageInfo();
            }
        }, API_CONFIG.queryInterval);
    }

    // 停止使用信息查询定时器
    stopUsageQueryTimer() {
        if (usageQueryTimer) {
            clearInterval(usageQueryTimer);
            usageQueryTimer = null;
            console.log('Prompt Agent: 停止API使用信息查询定时器');
        }
    }

    async sendRequest(textarea) {
        if (!apiKey.trim()) {
            console.error('Prompt Agent: API Key未设置');
            MessageManager.error('API Key未设置');
            return;
        }

        isProcessing = true;
        console.log('Prompt Agent: 开始处理请求');
        uiManager.updateStatus('正在发送请求...');

        const userInput = this.inputManager.getTextContent(textarea).trim();

        try {
            const requestBody = {
                "model": API_CONFIG.model,
                "messages": [
                    { "role": "user", "content": userInput }
                ],
                "max_tokens": API_CONFIG.maxTokens,
                "temperature": API_CONFIG.temperature,
                "stream": true
            };
            
            // 只有启用prompts知识库时才添加相关参数
            if (enableRetrival) {
                requestBody.enable_retrival = true;
                requestBody.collection_name = collectionName;
            }

            const response = await fetch(API_CONFIG.endpoint, {
                method: 'POST',
                headers: {
                    "authorization": `Bearer ${apiKey}`,
                    "User-Agent": "Chrome Extension/1.0.0",
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                const errorText = await response.text().catch(() => '');
                throw new Error(`HTTP ${response.status}: ${response.statusText}${errorText ? ' - ' + errorText : ''}`);
            }

            uiManager.updateStatus('开始接收数据流...');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            let aiResponse = '';
            let isFirstContent = true;

            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    break;
                }

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const jsonStr = line.substring(6).trim();
                        if (jsonStr === '[DONE]') {
                            continue;
                        }

                        try {
                            const data = JSON.parse(jsonStr);
                            if (data.choices && data.choices[0] && data.choices[0].delta && data.choices[0].delta.content) {
                                const content = data.choices[0].delta.content;
                                aiResponse += content;

                                if (isFirstContent) {
                                    uiManager.updateStatus('开始接收响应...');
                                    // 清空输入框，对textarea使用.value
                                    if (textarea.tagName.toLowerCase() === 'textarea') {
                                        textarea.value = '';
                                        console.log('Prompt Agent: 清空textarea.value');
                                    } else {
                                        await this.inputManager.setTextContent(textarea, '');
                                    }
                                    isFirstContent = false;
                                }

                                try {
                                    // 对于textarea使用.value，对于其他元素使用textContent
                                    if (textarea.tagName.toLowerCase() === 'textarea') {
                                        textarea.value += content;
                                        console.log('Prompt Agent: 追加到textarea.value，长度:', textarea.value.length);
                                    } else {
                                        const currentText = textarea.textContent || '';
                                        textarea.textContent = currentText + content;
                                    }
                                    
                                    // 触发input事件
                                    const inputEvent = new Event('input', {
                                        bubbles: true,
                                        cancelable: true,
                                    });
                                    textarea.dispatchEvent(inputEvent);
                                    
                                    // 减少延迟，提高流式响应速度
                                    await new Promise(resolve => setTimeout(resolve, 20));

                                    // 自动滚动到底部
                                    if (textarea.tagName.toLowerCase() === 'textarea') {
                                        textarea.scrollTop = textarea.scrollHeight;
                                        // 设置光标到最后
                                        textarea.selectionStart = textarea.selectionEnd = textarea.value.length;
                                    } else if (textarea.scrollTop !== undefined) {
                                        textarea.scrollTop = textarea.scrollHeight;
                                    }
                                } catch (domError) {
                                    console.warn('Prompt Agent - DOM操作警告:', domError);
                                }
                            }
                        } catch (parseError) {
                            console.log('JSON解析错误:', parseError, jsonStr);
                        }
                    }
                }
            }

            console.log('Prompt Agent: 请求完成');
            MessageManager.success('请求完成!');

        } catch (error) {
            console.error('Prompt Agent - 请求错误:', error);
            let errorMessage = '未知错误';
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                errorMessage = '网络请求失败';
            } else if (error.message.includes('CORS')) {
                errorMessage = 'CORS跨域错误';
            } else {
                errorMessage = error.message;
            }
            MessageManager.error(`错误: ${errorMessage}`);
        } finally {
            isProcessing = false;
        }
    }

    async manualSend() {
        if (isProcessing) {
            MessageManager.warning('正在处理中，请稍后...');
            return { success: false, message: '正在处理中，请稍后...' };
        }

        // 检查API Key
        if (!apiKey.trim()) {
            MessageManager.error('请先输入API Key');
            return { success: false, message: '请先输入API Key' };
        }

        console.log('Prompt Agent: 开始查找输入框...');
        const textarea = this.inputManager.findActiveTextarea();
        
        if (!textarea) {
            console.error('Prompt Agent: 未找到输入框');
            MessageManager.error('未找到输入框');
            return { success: false, message: '未找到输入框' };
        }

        console.log('Prompt Agent: 找到输入框:', textarea.tagName, textarea.className);
        const content = this.inputManager.getTextContent(textarea);
        console.log('Prompt Agent: 输入内容:', content);
        
        if (!content.trim()) {
            MessageManager.warning('请先输入内容');
            return { success: false, message: '请先输入内容' };
        }

        // 立即更新状态并开始处理
        uiManager.updateStatus('开始处理请求...');
        console.log('Prompt Agent: 手动发送开始，API Key:', apiKey ? '已设置' : '未设置');
        console.log('Prompt Agent: 当前网站:', currentSiteConfig.name);
        console.log('Prompt Agent: 输入方法:', currentSiteConfig.textInputMethod);
        
        // 立即调用sendRequest
        try {
            console.log('Prompt Agent: 调用sendRequest，输入内容长度:', content.length);
            await this.sendRequest(textarea);
            console.log('Prompt Agent: sendRequest完成');
            return { success: true, message: '请求已发送' };
        } catch (error) {
            console.error('Prompt Agent: sendRequest失败:', error);
            MessageManager.error('发送失败: ' + error.message);
            return { success: false, message: '发送失败: ' + error.message };
        }
    }
}

// UI管理类
class UIManager {
    constructor() {
        this.container = null;
    }

    // 创建浮动UI
    createFloatingUI() {
        const container = document.createElement('div');
        container.id = 'ai-floating-ui';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            width: 280px;
            background: #ffffff;
            border: 1px solid #ddd;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            font-family: Arial, sans-serif;
            font-size: 14px;
        `;

        const siteName = currentSiteConfig ? currentSiteConfig.name : 'Unknown';
        
        this.createUIElements(container, siteName);

        document.body.appendChild(container);
        this.container = container;

        this.bindEvents();
    }

    // 创建UI元素
    createUIElements(container, siteName) {
        // 创建头部
        const header = document.createElement('div');
        header.style.cssText = 'background: #f5f5f5; padding: 12px; border-radius: 8px 8px 0 0; border-bottom: 1px solid #ddd;';
        
        const headerContent = document.createElement('div');
        headerContent.style.cssText = 'display: flex; justify-content: space-between; align-items: center;';
        
        const title = document.createElement('span');
        title.className = 'header-title';
        title.style.cssText = 'font-weight: bold; color: #333;';
        title.textContent = `Prompt Agent (${siteName})`;
        
        const minimizeBtn = document.createElement('button');
        minimizeBtn.id = 'ai-minimize';
        minimizeBtn.style.cssText = 'background: none; border: none; font-size: 16px; cursor: pointer; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center;';
        minimizeBtn.textContent = '−';
        
        headerContent.appendChild(title);
        headerContent.appendChild(minimizeBtn);
        header.appendChild(headerContent);
        
        // 创建内容区域
        const content = document.createElement('div');
        content.id = 'ai-content';
        content.style.cssText = 'padding: 15px;';
        
        // API Key输入区域
        const apiKeyDiv = document.createElement('div');
        apiKeyDiv.style.cssText = 'margin-bottom: 15px;';
        
        const apiKeyLabel = document.createElement('label');
        apiKeyLabel.style.cssText = 'display: block; margin-bottom: 5px; color: #555;';
        apiKeyLabel.textContent = 'API Key:';
        
        const apiKeyInput = document.createElement('input');
        apiKeyInput.type = 'text';
        apiKeyInput.id = 'ai-apikey';
        apiKeyInput.placeholder = 'Bearer token...';
        apiKeyInput.style.cssText = 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box;';
        
        // 确保API Key值是最新的
        StorageManager.getItem('apikey', '').then(savedApiKey => {
            apiKey = savedApiKey;
            apiKeyInput.value = this.formatApiKeyForDisplay(savedApiKey);
            apiKeyInput.dataset.realValue = savedApiKey; // 存储真实值
        });
        
        apiKeyDiv.appendChild(apiKeyLabel);
        apiKeyDiv.appendChild(apiKeyInput);
        
        // 启用开关区域
        const enableDiv = document.createElement('div');
        enableDiv.style.cssText = 'margin-bottom: 15px;';
        
        const enableLabel = document.createElement('label');
        enableLabel.style.cssText = 'display: flex; align-items: center; color: #555;';
        
        const enableCheckbox = document.createElement('input');
        enableCheckbox.type = 'checkbox';
        enableCheckbox.id = 'ai-enable';
        enableCheckbox.style.cssText = 'margin-right: 8px;';
        
        // 确保启用状态是最新的
        StorageManager.getItem('enabled', 'false').then(savedEnabled => {
            isEnabled = savedEnabled === 'true';
            enableCheckbox.checked = isEnabled;
        });
        
        const enableText = document.createElement('span');
        enableText.textContent = '启用AI响应';
        
        enableLabel.appendChild(enableCheckbox);
        enableLabel.appendChild(enableText);
        enableDiv.appendChild(enableLabel);
        
        // prompts知识库开关区域
        const retrivalDiv = document.createElement('div');
        retrivalDiv.style.cssText = 'margin-bottom: 15px;';
        
        const retrivalLabel = document.createElement('label');
        retrivalLabel.style.cssText = 'display: flex; align-items: center; color: #555;';
        
        const retrivalCheckbox = document.createElement('input');
        retrivalCheckbox.type = 'checkbox';
        retrivalCheckbox.id = 'ai-enable-retrival';
        retrivalCheckbox.style.cssText = 'margin-right: 8px;';
        
        // 确保prompts知识库状态是最新的
        StorageManager.getItem('enableRetrival', 'false').then(savedEnableRetrival => {
            enableRetrival = savedEnableRetrival === 'true';
            retrivalCheckbox.checked = enableRetrival;
        });
        
        const retrivalText = document.createElement('span');
        retrivalText.textContent = '启用prompts知识库';
        
        retrivalLabel.appendChild(retrivalCheckbox);
        retrivalLabel.appendChild(retrivalText);
        retrivalDiv.appendChild(retrivalLabel);
        
        // 知识库选择下拉框（仅在启用prompts知识库时显示）
        const collectionDiv = document.createElement('div');
        collectionDiv.id = 'ai-collection-container';
        collectionDiv.style.cssText = 'margin-bottom: 15px; margin-left: 24px; display: none;'; // 默认隐藏
        
        const collectionLabel = document.createElement('label');
        collectionLabel.style.cssText = 'display: block; margin-bottom: 5px; color: #555; font-size: 12px;';
        collectionLabel.textContent = '选择知识库:';
        
        const collectionSelect = document.createElement('select');
        collectionSelect.id = 'ai-collection-select';
        collectionSelect.style.cssText = 'width: 100%; padding: 6px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; font-size: 12px;';
        
        // 添加默认选项
        const defaultOption = document.createElement('option');
        defaultOption.value = 'default';
        defaultOption.textContent = 'default';
        defaultOption.selected = true;
        collectionSelect.appendChild(defaultOption);
        
        collectionDiv.appendChild(collectionLabel);
        collectionDiv.appendChild(collectionSelect);
        
        // 手动发送按钮
        const manualBtn = document.createElement('button');
        manualBtn.id = 'ai-manual-send';
        manualBtn.style.cssText = 'width: 100%; padding: 8px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; margin-bottom: 10px;';
        manualBtn.textContent = '⭐️优化输入';
        
        // 重置按钮
        const resetBtn = document.createElement('button');
        resetBtn.id = 'ai-reset';
        resetBtn.style.cssText = 'width: 100%; padding: 6px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; margin-bottom: 10px;';
        resetBtn.textContent = '重置';
        
        // 状态显示
        const status = document.createElement('div');
        status.id = 'ai-status';
        status.style.cssText = 'font-size: 12px; color: #666; text-align: center;';
        
        // 组装内容区域
        content.appendChild(apiKeyDiv);
        content.appendChild(enableDiv);
        content.appendChild(retrivalDiv);
        content.appendChild(collectionDiv);
        content.appendChild(manualBtn);
        content.appendChild(resetBtn);
        content.appendChild(status);
        
        // 组装整个容器
        container.appendChild(header);
        container.appendChild(content);
    }

    bindEvents() {
        document.getElementById('ai-minimize').addEventListener('click', () => this.toggleMinimize());
        document.getElementById('ai-enable').addEventListener('change', (e) => this.toggleEnable(e));
        document.getElementById('ai-enable-retrival').addEventListener('change', (e) => this.toggleEnableRetrival(e));
        document.getElementById('ai-collection-select').addEventListener('change', (e) => this.changeCollection(e));
        
        // API Key输入框事件处理
        const apiKeyInput = document.getElementById('ai-apikey');
        apiKeyInput.addEventListener('input', (e) => this.saveApiKey(e));
        apiKeyInput.addEventListener('focus', (e) => this.handleApiKeyFocus(e));
        apiKeyInput.addEventListener('blur', (e) => this.handleApiKeyBlur(e));
        
        document.getElementById('ai-manual-send').addEventListener('click', async () => {
            const button = document.getElementById('ai-manual-send');
            button.disabled = true;
            button.textContent = '发送中...';
            
            try {
                await aiAgent.manualSend();
            } finally {
                button.disabled = false;
                button.textContent = '⭐️优化输入';
            }
        });
        document.getElementById('ai-reset').addEventListener('click', () => this.resetSettings());
    }

    toggleMinimize() {
        const content = document.getElementById('ai-content');
        const button = document.getElementById('ai-minimize');
        const title = document.querySelector('#ai-floating-ui .header-title');
        const container = document.getElementById('ai-floating-ui');
        const header = container.querySelector('div'); // 头部div
        const headerContent = header.querySelector('div'); // headerContent div
        
        if (content.style.display === 'none') {
            // 展开状态
            content.style.display = 'block';
            button.textContent = '−';
            if (title) title.style.display = 'inline';
            if (container) {
                container.style.width = '280px';
                container.style.borderRadius = '8px';
            }
            if (header) {
                header.style.padding = '12px';
                header.style.borderRadius = '8px 8px 0 0';
                header.style.borderBottom = '1px solid #ddd';
            }
            if (headerContent) {
                headerContent.style.justifyContent = 'space-between';
            }
        } else {
            // 最小化状态
            content.style.display = 'none';
            button.textContent = '+';
            if (title) title.style.display = 'none';
            if (container) {
                container.style.width = 'auto';
                container.style.borderRadius = '50%';
            }
            if (header) {
                header.style.padding = '8px';
                header.style.borderRadius = '50%';
                header.style.borderBottom = 'none';
            }
            if (headerContent) {
                headerContent.style.justifyContent = 'center';
            }
        }
    }

    async toggleEnable(e) {
        isEnabled = e.target.checked;
        await StorageManager.setItem('enabled', isEnabled.toString());
        MessageManager.info(isEnabled ? '已启用 - 按Ctrl+Enter发送' : '已禁用');
    }

    async toggleEnableRetrival(e) {
        enableRetrival = e.target.checked;
        await StorageManager.setItem('enableRetrival', enableRetrival.toString());
        
        const collectionContainer = document.getElementById('ai-collection-container');
        
        if (enableRetrival) {
            // 显示知识库选择下拉框
            if (collectionContainer) {
                collectionContainer.style.display = 'block';
            }
            
            // 加载知识库列表
            MessageManager.info('正在加载知识库列表...');
            await this.loadCollectionsList();
            MessageManager.success('已启用prompts知识库');
        } else {
            // 隐藏知识库选择下拉框
            if (collectionContainer) {
                collectionContainer.style.display = 'none';
            }
            MessageManager.info('已禁用prompts知识库');
        }
    }

    async loadCollectionsList() {
        try {
            const collections = await aiAgent.getCollectionsList();
            const selectElement = document.getElementById('ai-collection-select');
            
            if (selectElement && collections) {
                // 清空现有选项
                selectElement.innerHTML = '';
                
                // 添加新选项
                collections.forEach(collection => {
                    const option = document.createElement('option');
                    option.value = collection;
                    option.textContent = collection;
                    if (collection === collectionName) {
                        option.selected = true;
                    }
                    selectElement.appendChild(option);
                });
                
                console.log('Prompt Agent: 知识库列表已更新:', collections);
            }
        } catch (error) {
            console.error('Prompt Agent: 加载知识库列表失败:', error);
        }
    }

    // 格式化API Key显示（中间用星号隐藏）
    formatApiKeyForDisplay(key) {
        if (!key || key.length <= 8) return key;
        const start = key.substring(0, 4);
        const end = key.substring(key.length - 4);
        const middle = '*'.repeat(Math.min(key.length - 8, 20));
        return start + middle + end;
    }

    // 处理API Key聚焦事件
    handleApiKeyFocus(e) {
        const realValue = e.target.dataset.realValue || '';
        e.target.value = realValue;
    }

    // 处理API Key失焦事件
    handleApiKeyBlur(e) {
        const realValue = e.target.dataset.realValue || '';
        e.target.value = this.formatApiKeyForDisplay(realValue);
    }

    async saveApiKey(e) {
        // 保存真实的API Key值
        apiKey = e.target.value;
        e.target.dataset.realValue = apiKey;
        await StorageManager.setItem('apikey', apiKey);
        
        console.log('Prompt Agent: API Key已更新:', apiKey ? '已设置' : '已清空');
        
        // 重启使用信息查询
        if (aiAgent) {
            aiAgent.stopUsageQueryTimer();
            if (apiKey.trim()) {
                await aiAgent.getApiUsageInfo();
                aiAgent.startUsageQueryTimer();
            } else {
                // 隐藏使用信息
                const usageInfoElement = document.getElementById('ai-usage-info');
                if (usageInfoElement) {
                    usageInfoElement.style.display = 'none';
                }
            }
        }
    }

    async resetSettings() {
        if (confirm('确定要重置所有设置吗？这将清除API Key和所有配置。')) {
            await StorageManager.removeItem('apikey');
            await StorageManager.removeItem('enabled');
            await StorageManager.removeItem('enableRetrival');
            
            apiKey = '';
            isEnabled = false;
            enableRetrival = false;
            
            const apiKeyInput = document.getElementById('ai-apikey');
            apiKeyInput.value = '';
            apiKeyInput.dataset.realValue = '';
            document.getElementById('ai-enable').checked = false;
            document.getElementById('ai-enable-retrival').checked = false;
            
            MessageManager.success('设置已重置');
        }
    }

    updateStatus(message, isError = false) {
        const status = document.getElementById('ai-status');
        if (status) {
            status.textContent = message;
            status.style.color = isError ? '#d32f2f' : '#666';
        }
    }

    async changeCollection(e) {
        collectionName = e.target.value;
        MessageManager.info(`已选择知识库: ${collectionName}`);
    }
}

// 全局实例
let inputManager, aiAgent, uiManager;

// 显示详细设置界面
function showDetailedSettingsUI() {
    // 确保UI管理器已初始化
    if (!uiManager) {
        console.log('Prompt Agent: UI管理器未初始化，无法显示详细设置');
        return;
    }

    // 添加CSS动画（如果还没有添加）
    if (!document.getElementById('prompt-agent-animations')) {
        const style = document.createElement('style');
        style.id = 'prompt-agent-animations';
        style.textContent = `
            @keyframes highlightPulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.02); }
                100% { transform: scale(1); }
            }
        `;
        document.head.appendChild(style);
    }

    // 确保浮动UI存在
    ensureUIExists();
    
    const floatingUI = document.getElementById('ai-floating-ui');
    if (floatingUI) {
        // 显示UI（如果被最小化了）
        const content = document.getElementById('ai-content');
        
        if (content && content.style.display === 'none') {
            // 展开UI
            uiManager.toggleMinimize();
        }
        
        // 滚动到UI位置
        floatingUI.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // 添加突出显示效果
        floatingUI.style.animation = 'highlightPulse 2s ease-in-out';
        floatingUI.style.boxShadow = '0 0 20px rgba(103, 126, 234, 0.6)';
        floatingUI.style.zIndex = '10001'; // 确保在最前面
        
        // 2秒后移除突出效果
        setTimeout(() => {
            floatingUI.style.animation = '';
            floatingUI.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
            floatingUI.style.zIndex = '10000';
        }, 2000);
        
        console.log('Prompt Agent: 详细设置界面已显示');
    } else {
        console.warn('Prompt Agent: 无法找到浮动UI元素');
    }
}

// 键盘事件监听
function handleKeyDown(e) {
    if (e.ctrlKey && e.key === 'Enter' && isEnabled && !isProcessing) {
        const textarea = inputManager.findActiveTextarea();
        if (textarea && inputManager.getTextContent(textarea).trim()) {
            e.preventDefault();
            aiAgent.sendRequest(textarea);
        }
    }
}

// 消息监听器
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    switch (request.action) {
        case 'updateApiKey':
            apiKey = request.apiKey;
            break;
        case 'updateEnabled':
            isEnabled = request.enabled;
            break;
        case 'updateEnableRetrival':
            enableRetrival = request.enableRetrival;
            break;
        case 'resetSettings':
            apiKey = '';
            isEnabled = false;
            enableRetrival = false;
            break;
        case 'manualSend':
            if (aiAgent) {
                aiAgent.manualSend().then(result => {
                    sendResponse(result);
                }).catch(error => {
                    sendResponse({ success: false, message: error.message });
                });
            } else {
                sendResponse({ success: false, message: '代理未初始化' });
            }
            break;
        case 'showDetailedSettings':
            // 显示详细设置界面（浮动UI）
            showDetailedSettingsUI();
            sendResponse({ success: true });
            break;
    }
    return true; // 保持消息通道开放
});

// UI状态监控和重建
function ensureUIExists() {
    const existingUI = document.getElementById('ai-floating-ui');
    if (!existingUI && uiManager) {
        console.log('Prompt Agent: UI丢失，正在重建...');
        try {
            uiManager.createFloatingUI();
            uiManager.updateStatus(`重建UI - ${currentSiteConfig.name} - Ctrl+Enter发送`);
        } catch (error) {
            console.error('Prompt Agent: UI重建失败:', error);
        }
    }
}

// 页面变化监听器 (针对SPA) - CSP兼容版本
function observePageChanges() {
    // 使用现代MutationObserver监听DOM变化，避免废弃的事件
    let uiCheckTimeout = null;
    
    const observer = new MutationObserver((mutations) => {
        let needsUICheck = false;
        let significantChange = false;
        
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList') {
                // 检查是否有UI相关的变化
                const hasSignificantChange = mutation.addedNodes.length > 5 || 
                                            mutation.removedNodes.length > 5;
                
                // 检查是否影响了我们的UI
                const affectsOurUI = Array.from(mutation.removedNodes).some(node => 
                    node.id === 'ai-floating-ui' || 
                    (node.querySelector && node.querySelector('#ai-floating-ui'))
                );
                
                if (hasSignificantChange || affectsOurUI) {
                    needsUICheck = true;
                    if (affectsOurUI) {
                        significantChange = true;
                    }
                }
            } else if (mutation.type === 'attributes') {
                // 检查是否影响页面结构
                if (mutation.attributeName === 'class' || mutation.attributeName === 'style') {
                    needsUICheck = true;
                }
            }
        });
        
        if (needsUICheck) {
            // 清除之前的超时
            if (uiCheckTimeout) {
                clearTimeout(uiCheckTimeout);
            }
            
            // 设置延迟检查，避免频繁操作
            const delay = significantChange ? 500 : 2000;
            uiCheckTimeout = setTimeout(() => {
                try {
                    ensureUIExists();
                } catch (error) {
                    console.warn('Prompt Agent: UI检查失败:', error);
                }
            }, delay);
        }
    });

    // 开始观察，使用更精确的配置
    try {
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['class', 'style', 'id']
        });
        
        console.log('Prompt Agent: MutationObserver已启动');
    } catch (error) {
        console.warn('Prompt Agent: MutationObserver启动失败:', error);
    }

    // 定期检查UI是否存在（备用方案，频率降低）
    setInterval(() => {
        try {
            ensureUIExists();
        } catch (error) {
            console.warn('Prompt Agent: 定期UI检查失败:', error);
        }
    }, 10000); // 改为10秒检查一次
}

// 初始化
async function init() {
    console.log('Prompt Agent: 开始初始化...', {
        url: window.location.href,
        readyState: document.readyState,
        userAgent: navigator.userAgent.includes('Chrome') ? 'Chrome' : 'Other'
    });
    
    try {
        if (!initSiteConfig()) {
            console.log('Prompt Agent: 当前网站不在AI聊天网站列表中，跳过初始化');
            return;
        }
        
        // 检查特殊网站兼容性
        const hostname = window.location.hostname;
        const isGemini = currentSiteConfig.name === 'Gemini';
        const isChatGPT = currentSiteConfig.name === 'ChatGPT';
        const isDoubao = currentSiteConfig.name === '豆包';
        const isGrok = currentSiteConfig.name === 'Grok';
        const isTongyi = currentSiteConfig.name === '千问';
        const isHunyuan = currentSiteConfig.name === '混元';
        
        if (isGemini) {
            console.log('Prompt Agent: 检测到Gemini网站，使用CSP兼容模式');
        } else if (isChatGPT) {
            console.log('Prompt Agent: 检测到ChatGPT网站，使用React兼容模式');
        } else if (isDoubao) {
            console.log('Prompt Agent: 检测到豆包网站，使用直接输入模式');
        } else if (isGrok) {
            console.log('Prompt Agent: 检测到Grok网站，使用直接输入模式');
        } else if (isTongyi) {
            console.log('Prompt Agent: 检测到千问网站，使用直接输入模式');
        } else if (isHunyuan) {
            console.log('Prompt Agent: 检测到混元网站，使用直接输入模式');
        }
        
        // 加载设置
        apiKey = await StorageManager.getItem('apikey', '');
        isEnabled = await StorageManager.getItem('enabled', 'false') === 'true';
        enableRetrival = await StorageManager.getItem('enableRetrival', 'false') === 'true';
        
        console.log('Prompt Agent: 设置已加载', { hasApiKey: !!apiKey, isEnabled, enableRetrival });

        // 创建管理器实例
        inputManager = new InputManager(currentSiteConfig);
        aiAgent = new AIAgent(inputManager);
        uiManager = new UIManager();

        // 创建浮动UI
        try {
            uiManager.createFloatingUI();
            let statusMessage = `就绪 - ${currentSiteConfig.name} - Ctrl+Enter发送`;
            
            if (isGemini) {
                statusMessage = `就绪(CSP兼容) - ${currentSiteConfig.name} - Ctrl+Enter发送`;
            } else if (isChatGPT) {
                statusMessage = `就绪(React兼容) - ${currentSiteConfig.name} - Ctrl+Enter发送`;
            } else if (isDoubao || isGrok || isTongyi || isHunyuan) {
                statusMessage = `就绪(直接输入) - ${currentSiteConfig.name} - Ctrl+Enter发送`;
            }
            
            uiManager.updateStatus(statusMessage);
        } catch (uiError) {
            console.error('Prompt Agent: UI创建失败', uiError);
            // 尝试简化版UI
            setTimeout(() => {
                try {
                    uiManager.createFloatingUI();
                } catch (retryError) {
                    console.error('Prompt Agent: UI重试创建失败', retryError);
                }
            }, 2000);
        }

        // 添加键盘事件监听
        try {
            document.addEventListener('keydown', handleKeyDown, { passive: true });
        } catch (eventError) {
            console.warn('Prompt Agent: 键盘事件监听器添加失败', eventError);
            // fallback
            document.addEventListener('keydown', handleKeyDown);
        }
        
        // 启动页面变化监听
        try {
            observePageChanges();
        } catch (observerError) {
            console.warn('Prompt Agent: 页面变化监听器启动失败', observerError);
        }
        
        console.log('Prompt Agent: 初始化完成 -', currentSiteConfig.name);
        
        // 如果有API Key，启动使用信息查询
        if (apiKey.trim()) {
            console.log('Prompt Agent: 检测到API Key，启动使用信息查询');
            setTimeout(async () => {
                if (aiAgent) {
                    await aiAgent.getApiUsageInfo();
                    aiAgent.startUsageQueryTimer();
                }
            }, 2000); // 延迟2秒启动，确保UI完全创建
        }
        
        // 如果启用了prompts知识库，显示下拉框并加载列表
        if (enableRetrival) {
            setTimeout(async () => {
                const collectionContainer = document.getElementById('ai-collection-container');
                if (collectionContainer) {
                    collectionContainer.style.display = 'block';
                    await uiManager.loadCollectionsList();
                }
            }, 1000);
        }
        
    } catch (error) {
        console.error('Prompt Agent: 初始化失败', error);
        
        // 即使初始化失败，也尝试提供基本功能
        setTimeout(() => {
            console.log('Prompt Agent: 尝试恢复基本功能...');
            try {
                if (!inputManager && currentSiteConfig) {
                    inputManager = new InputManager(currentSiteConfig);
                }
                if (!aiAgent && inputManager) {
                    aiAgent = new AIAgent(inputManager);
                }
            } catch (recoveryError) {
                console.error('Prompt Agent: 恢复失败', recoveryError);
            }
        }, 3000);
    }
}

// 启动初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}