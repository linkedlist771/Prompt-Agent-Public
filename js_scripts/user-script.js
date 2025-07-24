// ==UserScript==
// @name         一个优化你使用AI时候的prompt智能体。
// @namespace    prompt-agent
// @version      0.0.7
// @description  prompt-agent
// @author       LLinkedList771
// @run-at       document-end 
// @match        https://chat.deepseek.com/*
// @match        https://chatgpt.com/*
// @match        https://claude.ai/*
// @match        https://gemini.google.com/*
// @grant        GM_setValue
// @grant        GM_getValue
// @homepageURL  https://github.com/linkedlist771/prompt-agent
// @supportURL   https://github.com/linkedlist771/prompt-agent/issues
// @license      MIT
// ==/UserScript==

(function() {
  'use strict';

  // 存储管理类 - 跨域名缓存
  class StorageManager {
      static setItem(key, value) {
          try {
              // 优先使用GM存储（跨域名）
              if (typeof GM_setValue !== 'undefined') {
                  GM_setValue(key, value);
              } else {
                  // 降级到localStorage
                  localStorage.setItem(`prompt-agent-${key}`, value);
              }
          } catch (error) {
              console.warn('存储失败:', error);
              // 最后降级方案
              localStorage.setItem(`prompt-agent-${key}`, value);
          }
      }

      static getItem(key, defaultValue = '') {
          try {
              // 优先使用GM存储（跨域名）
              if (typeof GM_getValue !== 'undefined') {
                  const value = GM_getValue(key, null);
                  return value !== null ? value : defaultValue;
              } else {
                  // 降级到localStorage
                  return localStorage.getItem(`prompt-agent-${key}`) || defaultValue;
              }
          } catch (error) {
              console.warn('读取存储失败:', error);
              // 最后降级方案
              return localStorage.getItem(`prompt-agent-${key}`) || defaultValue;
          }
      }

      static removeItem(key) {
          try {
              if (typeof GM_setValue !== 'undefined') {
                  GM_setValue(key, null);
              } else {
                  localStorage.removeItem(`prompt-agent-${key}`);
              }
          } catch (error) {
              console.warn('删除存储失败:', error);
              localStorage.removeItem(`prompt-agent-${key}`);
          }
      }
  }

  // 全局配置变量 - 从跨域名存储中加载
  let isEnabled = StorageManager.getItem('enabled', false) === 'true';
  let apiKey = StorageManager.getItem('apikey', '');
  let isProcessing = false;
  let currentSiteConfig = null;

  // 网站配置
  const SITE_CONFIGS = {
    'chat.deepseek.com': {
      name: 'DeepSeek',
      textareaSelectors: ['textarea'],
      sendButtonSelectors: [
        'button[type="submit"]',
        '[data-testid="send-button"]',
        '.send-button'
      ],
      textInputMethod: 'simulate' // 'simulate' or 'direct'
    },
    // not supported yet, because of the chatgpt's CSP constrain.
    'chatgpt.com': {
      name: 'ChatGPT',
      textareaSelectors: ['textarea', '[contenteditable="true"]'],
      sendButtonSelectors: [
        'button[data-testid="send-button"]',
        'button[aria-label*="Send"]',
        'button:has(svg)'
      ],
      textInputMethod: 'simulate'
    },
    'claude.ai': {
      name: 'Claude',
      textareaSelectors: ['div[contenteditable="true"]', 'textarea', '[contenteditable="true"]'],
      sendButtonSelectors: [
        'button[aria-label*="Send"]',
        'button:has(svg)',
        'button[type="submit"]'
      ],
      textInputMethod: 'simulate'
    },
    'gemini.google.com': {
      name: 'Gemini',
      textareaSelectors: ['div[contenteditable="true"]', 'textarea', '[contenteditable="true"]'],
      sendButtonSelectors: [
        'button[aria-label*="Send"]',
        'button:has(svg)',
        'button[type="submit"]',
        'button[data-testid="send-button"]'
      ],
      textInputMethod: 'simulate'
    }
  };

  // API配置
  const API_CONFIG = {
    endpoint: "http://127.0.0.1:3648/api/v1/chat/completions",
    model: "mock-gpt-model",
    maxTokens: 512,
    temperature: 0.1
  };

  // 初始化网站配置
  function initSiteConfig() {
      const hostname = window.location.hostname;
      currentSiteConfig = SITE_CONFIGS[hostname];
      
      if (!currentSiteConfig) {
          console.warn('Prompt Agent: 不支持的网站:', hostname);
          return false;
      }
      
      console.log('Prompt Agent: 已加载配置for', currentSiteConfig.name);
      return true;
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
          
          // 使用安全的DOM创建方法，避免innerHTML
          this.createUIElements(container, siteName);

          document.body.appendChild(container);
          this.container = container;

          // 绑定事件
          this.bindEvents();
      }

      // 安全创建UI元素的方法
      createUIElements(container, siteName) {
          // 创建头部
          const header = document.createElement('div');
          header.style.cssText = 'background: #f5f5f5; padding: 12px; border-radius: 8px 8px 0 0; border-bottom: 1px solid #ddd;';
          
          const headerContent = document.createElement('div');
          headerContent.style.cssText = 'display: flex; justify-content: space-between; align-items: center;';
          
          const title = document.createElement('span');
          title.style.cssText = 'font-weight: bold; color: #333;';
          title.textContent = `Prompt Agent (${siteName})`;
          
          const minimizeBtn = document.createElement('button');
          minimizeBtn.id = 'ai-minimize';
          minimizeBtn.style.cssText = 'background: none; border: none; font-size: 16px; cursor: pointer;';
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
          apiKeyInput.value = apiKey;
          
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
          enableCheckbox.checked = isEnabled;
          
          const enableText = document.createElement('span');
          enableText.textContent = '启用AI响应';
          
          enableLabel.appendChild(enableCheckbox);
          enableLabel.appendChild(enableText);
          enableDiv.appendChild(enableLabel);
          
          // 测试连接按钮
          const testBtn = document.createElement('button');
          testBtn.id = 'ai-test';
          testBtn.style.cssText = 'width: 100%; padding: 8px; background: #007cba; color: white; border: none; border-radius: 4px; cursor: pointer; margin-bottom: 10px;';
          testBtn.textContent = '测试连接';
          
          // 手动发送按钮
          const manualBtn = document.createElement('button');
          manualBtn.id = 'ai-manual-send';
          manualBtn.style.cssText = 'width: 100%; padding: 8px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; margin-bottom: 10px;';
          manualBtn.textContent = '手动发送';
          
          // 重置按钮
          const resetBtn = document.createElement('button');
          resetBtn.id = 'ai-reset';
          resetBtn.style.cssText = 'width: 100%; padding: 6px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; margin-bottom: 10px;';
          resetBtn.textContent = '重置所有设置';
          
          // 状态显示
          const status = document.createElement('div');
          status.id = 'ai-status';
          status.style.cssText = 'font-size: 12px; color: #666; text-align: center;';
          
          // 组装内容区域
          content.appendChild(apiKeyDiv);
          content.appendChild(enableDiv);
          content.appendChild(testBtn);
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
          document.getElementById('ai-apikey').addEventListener('input', (e) => this.saveApiKey(e));
          document.getElementById('ai-test').addEventListener('click', () => aiAgent.testConnection());
          document.getElementById('ai-manual-send').addEventListener('click', () => aiAgent.manualSend());
          document.getElementById('ai-reset').addEventListener('click', () => this.resetSettings());

          // 监听Ctrl+Enter组合键
          document.addEventListener('keydown', (e) => this.handleKeyDown(e));
      }

      toggleMinimize() {
          const content = document.getElementById('ai-content');
          const button = document.getElementById('ai-minimize');
          if (content.style.display === 'none') {
              content.style.display = 'block';
              button.textContent = '−';
          } else {
              content.style.display = 'none';
              button.textContent = '+';
          }
      }

      toggleEnable(e) {
          isEnabled = e.target.checked;
          StorageManager.setItem('enabled', isEnabled.toString());
          this.updateStatus(isEnabled ? '已启用 - 按Ctrl+Enter发送' : '已禁用');
      }

      saveApiKey(e) {
          apiKey = e.target.value;
          StorageManager.setItem('apikey', apiKey);
      }

      resetSettings() {
          if (confirm('确定要重置所有设置吗？这将清除API Key和所有配置。')) {
              // 清除所有存储的设置
              StorageManager.removeItem('apikey');
              StorageManager.removeItem('enabled');
              
              // 重置全局变量
              apiKey = '';
              isEnabled = false;
              
              // 更新UI
              document.getElementById('ai-apikey').value = '';
              document.getElementById('ai-enable').checked = false;
              
              this.updateStatus('设置已重置');
          }
      }

      updateStatus(message, isError = false) {
          const status = document.getElementById('ai-status');
          if (status) {
              status.textContent = message;
              status.style.color = isError ? '#d32f2f' : '#666';
          }
      }

      handleKeyDown(e) {
          if (e.ctrlKey && e.key === 'Enter' && isEnabled && !isProcessing) {
              const textarea = inputManager.findActiveTextarea();
              if (textarea && inputManager.getTextContent(textarea).trim()) {
                  e.preventDefault();
                  aiAgent.sendRequest(textarea);
              }
          }
      }
  }

  // 输入管理类
  class InputManager {
      constructor(siteConfig) {
          this.siteConfig = siteConfig;
      }

      // 查找当前活跃的输入框
      findActiveTextarea() {
          // 优先查找聚焦的输入框
          for (const selector of this.siteConfig.textareaSelectors) {
              const focused = document.querySelector(selector + ':focus');
              if (focused) return focused;
          }

          // 查找页面上的输入框
          for (const selector of this.siteConfig.textareaSelectors) {
              const elements = document.querySelectorAll(selector);
              if (elements.length > 0) {
                  return elements[elements.length - 1]; // 选择最后一个
              }
          }

          return null;
      }

      // 获取文本内容（兼容textarea和contenteditable）
      getTextContent(element) {
          if (element.tagName.toLowerCase() === 'textarea') {
              return element.value;
          } else if (element.contentEditable === 'true' || element.getAttribute('contenteditable') === 'true') {
              return element.textContent || element.innerText || '';
          }
          return '';
      }

      // 设置文本内容
      async setTextContent(element, text) {
          if (this.siteConfig.textInputMethod === 'simulate') {
              await this.simulateTextInput(element, text);
          } else {
              this.directSetText(element, text);
          }
      }

      // 模拟文字输入
      async simulateTextInput(element, text) {
          element.focus();
          await new Promise(resolve => setTimeout(resolve, 50));

          // 获取当前内容并清空
          const currentContent = this.getTextContent(element);
          if (currentContent.length > 0) {
              await this.clearContent(element);
          }

          // 逐字符输入
          for (let i = 0; i < text.length; i++) {
              const char = text[i];
              
              // 模拟按键事件
              this.simulateKeyboardEvent(element, 'keydown', char);
              this.simulateKeyboardEvent(element, 'keypress', char);
              
              // 更新内容
              if (element.tagName.toLowerCase() === 'textarea') {
                  element.value = text.substring(0, i + 1);
              } else {
                  element.textContent = text.substring(0, i + 1);
              }
              
              // 触发input事件
              const inputEvent = new Event('input', {
                  bubbles: true,
                  cancelable: true,
              });
              element.dispatchEvent(inputEvent);
              
              this.simulateKeyboardEvent(element, 'keyup', char);
              
              // 短暂延迟
              if (i % 5 === 0) {
                  await new Promise(resolve => setTimeout(resolve, 10));
              }
          }

          // 确保光标在最后
          if (element.tagName.toLowerCase() === 'textarea') {
              element.selectionStart = element.selectionEnd = element.value.length;
          }
      }

      // 清空内容
      async clearContent(element) {
          element.focus();
          await new Promise(resolve => setTimeout(resolve, 30));

          // 对于contenteditable元素，使用不同的选择方法
          if (element.tagName.toLowerCase() === 'textarea') {
              element.select();
          } else {
              // 对于contenteditable div，选择所有内容
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
                              // 避免使用innerHTML，改用安全的清空方法
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

      // 直接设置文本
      directSetText(element, text) {
          if (element.tagName.toLowerCase() === 'textarea') {
              element.value = text;
          } else {
              element.textContent = text;
          }
          
          const inputEvent = new Event('input', {
              bubbles: true,
              cancelable: true,
          });
          element.dispatchEvent(inputEvent);
      }

      // 模拟键盘事件
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

      // 查找发送按钮
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

          // 查找包含发送文本的按钮
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
      constructor(uiManager, inputManager) {
          this.uiManager = uiManager;
          this.inputManager = inputManager;
      }

      async testConnection() {
          if (!apiKey.trim()) {
              this.uiManager.updateStatus('请先输入API Key', true);
              return;
          }

          this.uiManager.updateStatus('测试连接中...');

          try {
              const response = await fetch(API_CONFIG.endpoint, {
                  method: 'POST',
                  mode: 'cors', // 明确指定CORS模式
                  headers: {
                      "authorization": `Bearer ${apiKey}`,
                      "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                      "Content-Type": "application/json"
                  },
                  body: JSON.stringify({
                      "model": API_CONFIG.model,
                      "messages": [
                          { "role": "user", "content": "test" }
                      ],
                      "max_tokens": 10,
                      "temperature": API_CONFIG.temperature,
                      "stream": false
                  })
              });

              if (response.ok) {
                  this.uiManager.updateStatus('连接成功!');
              } else {
                  const errorText = await response.text().catch(() => 'Unknown error');
                  this.uiManager.updateStatus(`连接失败: ${response.status} - ${errorText}`, true);
              }
          } catch (error) {
              // 更详细的错误信息
              if (error.name === 'TypeError' && error.message.includes('fetch')) {
                  this.uiManager.updateStatus('网络错误: 请检查API地址和网络连接', true);
              } else if (error.message.includes('CORS')) {
                  this.uiManager.updateStatus('CORS错误: 服务器未允许跨域请求', true);
              } else {
                  this.uiManager.updateStatus(`连接错误: ${error.message}`, true);
              }
              console.error('Prompt Agent - Connection test error:', error);
          }
      }

      manualSend() {
          if (isProcessing) {
              this.uiManager.updateStatus('正在处理中，请稍后...', true);
              return;
          }

          const textarea = this.inputManager.findActiveTextarea();
          
          if (!textarea) {
              this.uiManager.updateStatus('未找到输入框', true);
              return;
          }

          const content = this.inputManager.getTextContent(textarea);
          if (!content.trim()) {
              this.uiManager.updateStatus('请先输入内容', true);
              return;
          }

          this.sendRequest(textarea);
      }

      async sendRequest(textarea) {
          if (!apiKey.trim()) {
              this.uiManager.updateStatus('请先输入API Key', true);
              return;
          }

          isProcessing = true;
          this.uiManager.updateStatus('处理中...');

          const userInput = this.inputManager.getTextContent(textarea).trim();

          const myHeaders = new Headers();
          myHeaders.append("authorization", `Bearer ${apiKey}`);
          myHeaders.append("User-Agent", "Apifox/1.0.0 (https://apifox.com)");
          myHeaders.append("Content-Type", "application/json");

          const raw = JSON.stringify({
              "model": API_CONFIG.model,
              "messages": [
                  { "role": "user", "content": userInput }
              ],
              "max_tokens": API_CONFIG.maxTokens,
              "temperature": API_CONFIG.temperature,
              "stream": true
          });

          const requestOptions = {
              method: 'POST',
              mode: 'cors', // 明确指定CORS模式
              headers: myHeaders,
              body: raw,
              redirect: 'follow'
          };

          try {
              const response = await fetch(API_CONFIG.endpoint, requestOptions);

              if (!response.ok) {
                  throw new Error(`HTTP ${response.status}: ${response.statusText}`);
              }

              const reader = response.body.getReader();
              const decoder = new TextDecoder();

              this.uiManager.updateStatus('接收响应中...');

              let aiResponse = '';
              let isFirstContent = true; // 标记是否是第一次接收到内容

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

                                  // 如果是第一次接收到内容，先清空输入框
                                  if (isFirstContent) {
                                      this.uiManager.updateStatus('开始输出响应...');
                                      await this.inputManager.setTextContent(textarea, '');
                                      isFirstContent = false;
                                  }

                                  // 批量添加内容，减少频繁的DOM操作
                                  try {
                                      if (textarea.tagName.toLowerCase() === 'textarea') {
                                          textarea.value += content;
                                      } else {
                                          // 对于contenteditable元素，使用更安全的方式
                                          const currentText = textarea.textContent || '';
                                          textarea.textContent = currentText + content;
                                      }
                                      
                                      // 触发单次input事件
                                      const inputEvent = new Event('input', {
                                          bubbles: true,
                                          cancelable: true,
                                      });
                                      textarea.dispatchEvent(inputEvent);
                                      
                                      // 减少延迟，提高响应速度
                                      await new Promise(resolve => setTimeout(resolve, 50));

                                      // 滚动到底部
                                      if (textarea.scrollTop !== undefined) {
                                          textarea.scrollTop = textarea.scrollHeight;
                                      }
                                  } catch (domError) {
                                      console.warn('Prompt Agent - DOM操作警告:', domError);
                                      // 如果DOM操作失败，继续处理下一个chunk
                                  }
                              }
                          } catch (parseError) {
                              console.log('JSON解析错误:', parseError, jsonStr);
                          }
                      }
                  }
              }

              this.uiManager.updateStatus('完成!');

          } catch (error) {
              // 详细的错误分类和处理
              let errorMessage = '未知错误';
              if (error.name === 'TypeError' && error.message.includes('fetch')) {
                  errorMessage = '网络请求失败';
              } else if (error.message.includes('CORS')) {
                  errorMessage = 'CORS跨域错误';
              } else if (error.message.includes('HTTP')) {
                  errorMessage = `服务器错误: ${error.message}`;
              } else {
                  errorMessage = error.message;
              }
              
              this.uiManager.updateStatus(`错误: ${errorMessage}`, true);
              console.error('Prompt Agent - 请求错误详情:', {
                  error: error,
                  message: error.message,
                  stack: error.stack,
                  name: error.name
              });
          } finally {
              isProcessing = false;
          }
      }
  }

  // 全局实例
  let uiManager, inputManager, aiAgent;
  let uiCheckInterval = null;

  // UI状态监控和重建
  function ensureUIExists() {
      const existingUI = document.getElementById('ai-floating-ui');
      if (!existingUI && uiManager) {
          console.log('Prompt Agent: UI丢失，正在重建...');
          try {
              uiManager.createFloatingUI();
              const hasStorage = typeof GM_getValue !== 'undefined' ? '跨域名缓存已启用' : '本地缓存';
              uiManager.updateStatus(`重建UI - ${currentSiteConfig.name} - ${hasStorage} - Ctrl+Enter发送`);
          } catch (error) {
              console.error('Prompt Agent: UI重建失败:', error);
          }
      }
  }

  // 页面变化监听器 (针对SPA)
  function observePageChanges() {
      // 使用MutationObserver监听DOM变化
      const observer = new MutationObserver((mutations) => {
          let needsUICheck = false;
          mutations.forEach((mutation) => {
              if (mutation.type === 'childList') {
                  // 检查是否有大量节点变化（可能是页面路由切换）
                  if (mutation.addedNodes.length > 3 || mutation.removedNodes.length > 3) {
                      needsUICheck = true;
                  }
              }
          });
          
          if (needsUICheck) {
              // 延迟检查，避免频繁操作
              setTimeout(ensureUIExists, 1000);
          }
      });

      // 开始观察
      observer.observe(document.body, {
          childList: true,
          subtree: true
      });

      // 定期检查UI是否存在（备用方案）
      if (uiCheckInterval) {
          clearInterval(uiCheckInterval);
      }
      uiCheckInterval = setInterval(ensureUIExists, 5000);
  }

  // 改进的错误处理
  function safeExecute(func, context = 'Unknown') {
      try {
          return func();
      } catch (error) {
          console.error(`Prompt Agent Error in ${context}:`, error);
          if (uiManager && typeof uiManager.updateStatus === 'function') {
              uiManager.updateStatus(`错误: ${context}`, true);
          }
          return null;
      }
  }

  // 初始化
  function init() {
      console.log('Prompt Agent: 开始初始化...', {
          url: window.location.href,
          readyState: document.readyState,
          userAgent: navigator.userAgent.includes('Chrome') ? 'Chrome' : 'Other'
      });
      
      safeExecute(() => {
          // 检查是否支持当前网站
          if (!initSiteConfig()) {
              console.warn('Prompt Agent: 当前网站不受支持');
              return;
          }
          
          console.log('Prompt Agent: 网站配置加载成功', currentSiteConfig);

          // 创建管理器实例
          uiManager = new UIManager();
          inputManager = new InputManager(currentSiteConfig);
          aiAgent = new AIAgent(uiManager, inputManager);

          // 等待页面加载完成后创建UI
          if (document.readyState === 'loading') {
              document.addEventListener('DOMContentLoaded', () => {
                  safeExecute(() => {
                      uiManager.createFloatingUI();
                      const hasStorage = typeof GM_getValue !== 'undefined' ? '跨域名缓存已启用' : '本地缓存';
                      uiManager.updateStatus(`就绪 - ${currentSiteConfig.name} - ${hasStorage} - Ctrl+Enter发送`);
                      
                      // 启动页面变化监听
                      observePageChanges();
                  }, 'DOMContentLoaded');
              });
          } else {
              safeExecute(() => {
                  uiManager.createFloatingUI();
                  const hasStorage = typeof GM_getValue !== 'undefined' ? '跨域名缓存已启用' : '本地缓存';
                  uiManager.updateStatus(`就绪 - ${currentSiteConfig.name} - ${hasStorage} - Ctrl+Enter发送`);
                  
                  // 启动页面变化监听
                  observePageChanges();
              }, 'Direct Init');
          }
      }, 'Initialization');
  }

  // 页面卸载时清理
  window.addEventListener('beforeunload', () => {
      if (uiCheckInterval) {
          clearInterval(uiCheckInterval);
      }
  });

  init();
})();