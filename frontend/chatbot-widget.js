// Linceus Chat Widget - Universidad de Sevilla
(function() {
    // Estilos del widget
    const styles = `
        .linceus-chat-widget {
            --chat--color-primary: #9e1c3f;
            --chat--color-secondary: #7a1631;
            --chat--color-background: #ffffff;
            --chat--color-font: #333333;
            --chat--color-header: #9e1c3f;
            font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }

        .linceus-chat-widget .chat-container {
            position: fixed;
            bottom: 80px;
            right: 20px;
            z-index: 1000;
            display: none;
            width: 340px;
            height: 480px;
            background: var(--chat--color-background);
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(158, 28, 63, 0.25);
            border: 1px solid rgba(158, 28, 63, 0.2);
            overflow: hidden;
            font-family: inherit;
        }

        .linceus-chat-widget .chat-container.open {
            display: flex;
            flex-direction: column;
        }

        /* Header */
        .linceus-chat-widget .chat-header {
            padding: 16px;
            display: flex;
            align-items: center;
            gap: 12px;
            background: var(--chat--color-header);
            color: white;
            position: relative;
        }

        .linceus-chat-widget .chat-header img {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: white;
            padding: 4px;
        }

        .linceus-chat-widget .chat-header-info {
            flex: 1;
        }

        .linceus-chat-widget .chat-header-title {
            font-size: 16px;
            font-weight: 600;
            margin: 0;
        }

        .linceus-chat-widget .chat-header-subtitle {
            font-size: 12px;
            opacity: 0.9;
            margin: 0;
        }

        .linceus-chat-widget .close-button {
            background: none;
            border: none;
            color: white;
            cursor: pointer;
            padding: 4px 8px;
            font-size: 24px;
            opacity: 0.8;
            transition: opacity 0.2s;
        }

        .linceus-chat-widget .close-button:hover {
            opacity: 1;
        }

        /* Mensajes */
        .linceus-chat-widget .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            background: #f5f5f5;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .linceus-chat-widget .chat-message {
            padding: 12px 16px;
            border-radius: 12px;
            max-width: 85%;
            word-wrap: break-word;
            font-size: 14px;
            line-height: 1.5;
        }

        .linceus-chat-widget .chat-message.user {
            background: var(--chat--color-primary);
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }

        .linceus-chat-widget .chat-message.bot {
            background: white;
            color: var(--chat--color-font);
            align-self: flex-start;
            border-bottom-left-radius: 4px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }

        .linceus-chat-widget .chat-message.bot ul {
            margin: 8px 0;
            padding-left: 20px;
        }

        .linceus-chat-widget .chat-message.bot li {
            margin: 4px 0;
        }

        .linceus-chat-widget .typewriter-cursor {
            font-weight: 100;
            color: #9e1c3f;
            animation: blink 0.7s step-end infinite;
        }

        @keyframes blink {
            50% { opacity: 0; }
        }

        .linceus-chat-widget .chat-message.bot a {
            color: #9e1c3f;
            text-decoration: underline;
            word-break: break-all;
        }

        .linceus-chat-widget .chat-message.bot a:hover {
            color: #7a1631;
        }

        .linceus-chat-widget .typing-indicator {
            display: none;
            padding: 12px 16px;
            background: white;
            border-radius: 12px;
            align-self: flex-start;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }

        .linceus-chat-widget .typing-indicator.visible {
            display: block;
        }

        .linceus-chat-widget .typing-indicator span {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #999;
            border-radius: 50%;
            margin-right: 4px;
            animation: typing 1s infinite;
        }

        .linceus-chat-widget .typing-indicator span:nth-child(2) {
            animation-delay: 0.2s;
        }

        .linceus-chat-widget .typing-indicator span:nth-child(3) {
            animation-delay: 0.4s;
            margin-right: 0;
        }

        @keyframes typing {
            0%, 100% { opacity: 0.3; transform: translateY(0); }
            50% { opacity: 1; transform: translateY(-4px); }
        }

        /* Input */
        .linceus-chat-widget .chat-input {
            padding: 12px;
            background: white;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 8px;
        }

        .linceus-chat-widget .chat-input textarea {
            flex: 1;
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 20px;
            background: #f9f9f9;
            color: var(--chat--color-font);
            resize: none;
            font-family: inherit;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }

        .linceus-chat-widget .chat-input textarea:focus {
            border-color: var(--chat--color-primary);
        }

        .linceus-chat-widget .chat-input textarea::placeholder {
            color: #999;
        }

        .linceus-chat-widget .chat-input button {
            background: var(--chat--color-primary);
            color: white;
            border: none;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            cursor: pointer;
            transition: background 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .linceus-chat-widget .chat-input button:hover {
            background: var(--chat--color-secondary);
        }

        .linceus-chat-widget .chat-input button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }

        .linceus-chat-widget .chat-input button svg {
            width: 20px;
            height: 20px;
        }

        /* Botón flotante */
        .linceus-chat-widget .chat-toggle {
            position: fixed;
            bottom: 16px;
            right: 16px;
            width: 54px;
            height: 54px;
            border-radius: 50%;
            background: var(--chat--color-primary);
            color: white;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(158, 28, 63, 0.4);
            z-index: 999;
            transition: transform 0.3s, background 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .linceus-chat-widget .chat-toggle:hover {
            transform: scale(1.05);
            background: var(--chat--color-secondary);
        }

        .linceus-chat-widget .chat-toggle svg {
            width: 24px;
            height: 24px;
        }

        /* Footer */
        .linceus-chat-widget .chat-footer {
            padding: 8px;
            text-align: center;
            background: white;
            border-top: 1px solid #eee;
            font-size: 11px;
            color: #999;
        }
    `;

    // Inyectar estilos
    const styleSheet = document.createElement('style');
    styleSheet.textContent = styles;
    document.head.appendChild(styleSheet);

    // Configuración por defecto
    const defaultConfig = {
        rasaServer: 'http://localhost:5005',
        branding: {
            logo: 'logo-us.png',
            name: 'Linceus',
            subtitle: 'Asistente Universidad de Sevilla'
        }
    };

    // Combinar con configuración del usuario si existe
    const config = window.LinceusChatConfig ? 
        { ...defaultConfig, ...window.LinceusChatConfig } : defaultConfig;

    // Prevenir múltiples inicializaciones
    if (window.LinceusChatInitialized) return;
    window.LinceusChatInitialized = true;

    // Crear el widget
    const widgetContainer = document.createElement('div');
    widgetContainer.className = 'linceus-chat-widget';

    // HTML del chat
    widgetContainer.innerHTML = `
        <div class="chat-container">
            <div class="chat-header">
                <img src="${config.branding.logo}" alt="Linceus">
                <div class="chat-header-info">
                    <p class="chat-header-title">${config.branding.name}</p>
                    <p class="chat-header-subtitle">${config.branding.subtitle}</p>
                </div>
                <button class="close-button">×</button>
            </div>
            <div class="chat-messages">
                <div class="chat-message bot">
                    ¡Hola! Soy <strong>Linceus</strong>, el asistente virtual de la Universidad de Sevilla. 
                    ¿En qué puedo ayudarte hoy?
                </div>
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
            <div class="chat-input">
                <textarea placeholder="Escribe tu mensaje..." rows="1"></textarea>
                <button type="submit">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                    </svg>
                </button>
            </div>
            <div class="chat-footer">
                Universidad de Sevilla · TFG 2025-26
            </div>
        </div>
        <button class="chat-toggle">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/>
                <path d="M7 9h10v2H7zm0-3h10v2H7z"/>
            </svg>
        </button>
    `;

    document.body.appendChild(widgetContainer);

    // Referencias a elementos
    const chatContainer = widgetContainer.querySelector('.chat-container');
    const messagesContainer = widgetContainer.querySelector('.chat-messages');
    const typingIndicator = widgetContainer.querySelector('.typing-indicator');
    const textarea = widgetContainer.querySelector('textarea');
    const sendButton = widgetContainer.querySelector('button[type="submit"]');
    const toggleButton = widgetContainer.querySelector('.chat-toggle');
    const closeButton = widgetContainer.querySelector('.close-button');

    // Enviar mensaje a Rasa
    async function sendMessage(message) {
        if (!message.trim()) return;

        // Mostrar mensaje del usuario
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'chat-message user';
        userMessageDiv.textContent = message;
        messagesContainer.insertBefore(userMessageDiv, typingIndicator);

        // Limpiar input
        textarea.value = '';
        textarea.disabled = true;
        sendButton.disabled = true;

        // Mostrar indicador de escritura
        typingIndicator.classList.add('visible');
        scrollToBottom();

        try {
            const response = await fetch(`${config.rasaServer}/webhooks/rest/webhook`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sender: 'user',
                    message: message
                })
            });

            const data = await response.json();

            // Ocultar indicador
            typingIndicator.classList.remove('visible');

            // Mostrar respuestas del bot (agrupadas, efecto typewriter)
            if (data && data.length > 0) {
                const combinedText = data
                    .filter(msg => msg.text)
                    .map(msg => msg.text)
                    .join('\n\n');
                if (combinedText) {
                    const botMessageDiv = document.createElement('div');
                    botMessageDiv.className = 'chat-message bot';
                    messagesContainer.insertBefore(botMessageDiv, typingIndicator);
                    await typewriterEffect(botMessageDiv, combinedText);
                }
            } else {
                // Respuesta vacía
                const botMessageDiv = document.createElement('div');
                botMessageDiv.className = 'chat-message bot';
                botMessageDiv.textContent = 'Lo siento, no he podido procesar tu mensaje. ¿Puedes reformularlo?';
                messagesContainer.insertBefore(botMessageDiv, typingIndicator);
            }

        } catch (error) {
            console.error('Error al comunicarse con Rasa:', error);
            typingIndicator.classList.remove('visible');

            const errorDiv = document.createElement('div');
            errorDiv.className = 'chat-message bot';
            errorDiv.textContent = '⚠️ Error de conexión. Asegúrate de que el servidor Rasa esté ejecutándose.';
            messagesContainer.insertBefore(errorDiv, typingIndicator);
        }

        textarea.disabled = false;
        sendButton.disabled = false;
        textarea.focus();
        scrollToBottom();
    }

    // Efecto typewriter: revela palabra por palabra
    function typewriterEffect(element, text) {
        return new Promise(resolve => {
            const words = text.split(/(\s+)/); // conservar espacios
            let current = '';
            let i = 0;
            const speed = 30; // ms entre palabras

            function nextWord() {
                if (i < words.length) {
                    current += words[i];
                    element.innerHTML = formatMessage(current) + '<span class="typewriter-cursor">|</span>';
                    scrollToBottom();
                    i++;
                    setTimeout(nextWord, words[i - 1].trim() ? speed : 0);
                } else {
                    // Terminado: render final sin cursor
                    element.innerHTML = formatMessage(current);
                    scrollToBottom();
                    resolve();
                }
            }
            nextWord();
        });
    }

    // Formatear mensaje (convertir saltos de línea, listas y enlaces)
    function formatMessage(text) {
        // Escapar HTML
        let formatted = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // Convertir enlaces Markdown [texto](url)
        formatted = formatted.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
            '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

        // Convertir URLs sueltas que no estén ya dentro de un <a>
        formatted = formatted.replace(/(?<!href="|">)(https?:\/\/[^\s<]+)/g,
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');

        // Convertir **texto** a <strong>
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Convertir _texto_ a <em> (cursiva)
        formatted = formatted.replace(/(?<!\w)_(.*?)_(?!\w)/g, '<em>$1</em>');
        
        // Convertir listas con viñetas (• o -)
        const lines = formatted.split('\n');
        let inList = false;
        let result = [];
        
        lines.forEach(line => {
            if (line.match(/^[\-•]\s/)) {
                if (!inList) {
                    result.push('<ul>');
                    inList = true;
                }
                result.push(`<li>${line.replace(/^[\-•]\s/, '')}</li>`);
            } else {
                if (inList) {
                    result.push('</ul>');
                    inList = false;
                }
                if (line.trim()) {
                    result.push(line);
                }
            }
        });
        
        if (inList) result.push('</ul>');
        
        return result.join('<br>').replace(/<br><ul>/g, '<ul>').replace(/<\/ul><br>/g, '</ul>');
    }

    // Scroll al final
    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Event listeners
    sendButton.addEventListener('click', () => {
        sendMessage(textarea.value);
    });

    textarea.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage(textarea.value);
        }
    });

    toggleButton.addEventListener('click', () => {
        chatContainer.classList.toggle('open');
        if (chatContainer.classList.contains('open')) {
            textarea.focus();
        }
    });

    closeButton.addEventListener('click', () => {
        chatContainer.classList.remove('open');
    });

})();