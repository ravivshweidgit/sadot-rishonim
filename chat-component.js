/**
 * Chat with Yehuda - AI Chat Component
 * Floating chat UI for interacting with Yehuda Markovsky's AI persona
 */

class YehudaChat {
    constructor() {
        this.isOpen = false;
        this.conversationHistory = [];
        this.apiUrl = '/api/chat';
        this.storageKey = 'yehuda_chat_history';
        this.init();
    }

    init() {
        this.loadConversationHistory();
        this.createChatUI();
        this.attachEventListeners();
        this.restoreChatUI();
    }

    loadConversationHistory() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved) {
                this.conversationHistory = JSON.parse(saved);
            }
        } catch (e) {
            console.warn('Could not load conversation history:', e);
            this.conversationHistory = [];
        }
    }

    saveConversationHistory() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.conversationHistory));
        } catch (e) {
            console.warn('Could not save conversation history:', e);
        }
    }

    restoreChatUI() {
        // Restore messages from history (skip welcome message)
        if (this.conversationHistory.length > 0) {
            const messagesContainer = document.getElementById('chat-messages');
            // Hide welcome message if there's history
            const welcome = messagesContainer.querySelector('.chat-welcome');
            if (welcome) {
                welcome.style.display = 'none';
            }
            
            // Add all messages from history (skipWelcome = true since we already hid welcome)
            this.conversationHistory.forEach(msg => {
                this.addMessage(msg.role, msg.content, false, true);
            });
        }
    }

    createChatUI() {
        // Create chat container
        const chatContainer = document.createElement('div');
        chatContainer.id = 'yehuda-chat-container';
        chatContainer.className = 'yehuda-chat-container';
        chatContainer.innerHTML = `
            <div class="yehuda-chat-header" id="chat-header">
                <div class="chat-header-content">
                    <span class="chat-title">💬 שיחה עם יהודה</span>
                    <button class="chat-toggle-btn" id="chat-toggle" aria-label="סגור צ'אט">×</button>
                </div>
            </div>
            <div class="yehuda-chat-messages" id="chat-messages">
                <div class="chat-welcome">
                    <p>שלום! אני יהודה מרקובסקי. שאל אותי כל שאלה על חיי, על מטולה, על נהלל, או על כל דבר שסיפרתי בספרי "שדות ראשונים".</p>
                </div>
            </div>
            <div class="yehuda-chat-input-container">
                <textarea 
                    id="chat-input" 
                    class="yehuda-chat-input" 
                    placeholder="כתוב שאלה כאן..."
                    rows="2"
                ></textarea>
                <button id="chat-send-btn" class="yehuda-chat-send-btn">שלח</button>
            </div>
        `;
        document.body.appendChild(chatContainer);

        // Create floating button
        const chatButton = document.createElement('button');
        chatButton.id = 'yehuda-chat-button';
        chatButton.className = 'yehuda-chat-button';
        chatButton.innerHTML = '💬 שיחה עם יהודה';
        chatButton.setAttribute('aria-label', 'פתח שיחה עם יהודה');
        document.body.appendChild(chatButton);
    }

    attachEventListeners() {
        const chatButton = document.getElementById('yehuda-chat-button');
        const chatToggle = document.getElementById('chat-toggle');
        const sendBtn = document.getElementById('chat-send-btn');
        const chatInput = document.getElementById('chat-input');

        chatButton.addEventListener('click', () => this.toggleChat());
        chatToggle.addEventListener('click', () => this.toggleChat());
        sendBtn.addEventListener('click', () => this.sendMessage());
        
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    toggleChat() {
        const container = document.getElementById('yehuda-chat-container');
        const button = document.getElementById('yehuda-chat-button');
        
        this.isOpen = !this.isOpen;
        
        if (this.isOpen) {
            container.classList.add('chat-open');
            button.style.display = 'none';
            document.getElementById('chat-input').focus();
        } else {
            container.classList.remove('chat-open');
            button.style.display = 'flex';
        }
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Clear input
        input.value = '';
        input.disabled = true;
        
        // Add user message to UI
        this.addMessage('user', message);
        
        // Add to conversation history
        this.conversationHistory.push({ role: 'user', content: message });
        
        // Save to localStorage
        this.saveConversationHistory();
        
        // Show loading
        const loadingId = this.addMessage('assistant', 'כותב...', true);
        
        try {
            const response = await fetch(this.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    conversationHistory: this.conversationHistory.slice(-5) // Keep last 5 messages for context
                })
            });
            
            if (!response.ok) {
                // Try to get error details from response
                let errorMessage = `HTTP error! status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    if (errorData.error) {
                        errorMessage = errorData.error;
                        if (errorData.details) {
                            errorMessage += `: ${errorData.details}`;
                        }
                    }
                } catch (e) {
                    // If response is not JSON, use status text
                    errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            
            // Remove loading message
            const loadingEl = document.getElementById(loadingId);
            if (loadingEl) loadingEl.remove();
            
            // Add AI response
            this.addMessage('assistant', data.response);
            
            // Add to conversation history
            this.conversationHistory.push({ role: 'assistant', content: data.response });
            
            // Keep history manageable (last 10 messages)
            if (this.conversationHistory.length > 10) {
                this.conversationHistory = this.conversationHistory.slice(-10);
            }
            
            // Save to localStorage
            this.saveConversationHistory();
            
        } catch (error) {
            console.error('Error sending message:', error);
            
            // Remove loading message
            const loadingEl = document.getElementById(loadingId);
            if (loadingEl) loadingEl.remove();
            
            // Show error message with details
            let errorMessage = 'מצטער, אירעה שגיאה. אנא נסה שוב מאוחר יותר.';
            if (error.message) {
                console.error('Error details:', error.message);
                // Show helpful error messages (especially for API key issues)
                if (error.message.includes('GEMINI_API_KEY') || error.message.includes('AI service not configured')) {
                    errorMessage = 'שירות ה-AI לא מוגדר. אנא ודא שמשתנה הסביבה GEMINI_API_KEY מוגדר ב-Vercel.';
                } else if (error.message.includes('503') || error.message.includes('service not configured')) {
                    errorMessage = 'שירות ה-AI לא זמין כרגע. אנא נסה שוב מאוחר יותר או בדוק את הגדרות השרת.';
                } else {
                    // Show error details in development, generic message in production
                    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                        errorMessage += `\n\nשגיאה: ${error.message}`;
                    }
                }
            }
            this.addMessage('assistant', errorMessage);
        } finally {
            input.disabled = false;
            input.focus();
        }
    }

    addMessage(role, content, isLoading = false, skipWelcome = true) {
        const messagesContainer = document.getElementById('chat-messages');
        const messageId = `msg-${Date.now()}-${Math.random()}`;
        
        // Hide welcome message when first real message is added
        if (skipWelcome && this.conversationHistory.length > 0) {
            const welcome = messagesContainer.querySelector('.chat-welcome');
            if (welcome) {
                welcome.style.display = 'none';
            }
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.id = messageId;
        messageDiv.className = `chat-message chat-message-${role}`;
        
        if (isLoading) {
            messageDiv.innerHTML = `<div class="chat-loading">${content}</div>`;
        } else {
            messageDiv.innerHTML = `
                <div class="chat-message-content">${content}</div>
                <div class="chat-message-time">${new Date().toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' })}</div>
            `;
            
            // Attach click handlers to page links to ensure they open in new tab
            const pageLinks = messageDiv.querySelectorAll('.page-link');
            pageLinks.forEach(link => {
                link.setAttribute('target', '_blank');
                link.setAttribute('rel', 'noopener noreferrer');
            });
        }
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        return messageId;
    }
}

// Initialize chat when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.yehudaChat = new YehudaChat();
    });
} else {
    window.yehudaChat = new YehudaChat();
}

