import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// Renderiza markdown muy simple: **negrita**, listas con •, saltos de línea.
function renderInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) {
      return (
        <strong key={i} className="font-semibold">
          {p.slice(2, -2)}
        </strong>
      );
    }
    return <React.Fragment key={i}>{p}</React.Fragment>;
  });
}

function MessageBody({ text }) {
  const lines = text.split('\n');
  return (
    <div className="leading-snug">
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-2" />;
        if (line.trim().startsWith('•')) {
          return (
            <div key={i} className="ml-2 my-0.5">
              {renderInline(line)}
            </div>
          );
        }
        return <div key={i}>{renderInline(line)}</div>;
      })}
    </div>
  );
}

export default function ChatWidget({
  open,
  messages,
  inputBuffer,
  botTyping,
  contexto,
  showOnboarding,
  selectedTitulacion,
}) {
  const scrollRef = useRef(null);

  // Autoscroll al fondo cuando entra mensaje
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, botTyping, showOnboarding]);

  return (
    <>
      {/* Botón flotante (esquina inferior derecha del escenario) */}
      <motion.button
        initial={false}
        animate={{ scale: open ? 0.92 : 1 }}
        className="absolute w-16 h-16 rounded-full shadow-2xl flex items-center justify-center text-white text-2xl"
        style={{
          background: '#9e1c3f',
          boxShadow: '0 8px 24px rgba(158,28,63,0.4)',
          right: 30,
          bottom: 30,
        }}
      >
        <i className="fa-solid fa-comment-dots" />
      </motion.button>

      {/* Ventana del chat */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.95 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
            className="absolute w-[400px] h-[600px] rounded-xl overflow-hidden flex flex-col"
            style={{
              background: '#fff',
              boxShadow: '0 12px 40px rgba(158,28,63,0.3)',
              border: '1px solid rgba(158,28,63,0.2)',
              right: 30,
              bottom: 110,
            }}
          >
            {/* Header */}
            <div
              className="px-4 py-3 flex items-center gap-3 text-white"
              style={{ background: '#9e1c3f' }}
            >
              <div className="w-9 h-9 rounded-full bg-white flex items-center justify-center overflow-hidden">
                <img
                  src="/linceUS-logo.png"
                  alt="Linceus"
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="flex-1">
                <div className="font-semibold text-[15px] leading-tight">Linceus Assistant</div>
                <div className="text-[11px] opacity-90 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                  Conectado · {contexto}
                </div>
              </div>
            </div>

            {/* Mensajes */}
            <div
              ref={scrollRef}
              className="flex-1 overflow-y-auto px-4 py-3 space-y-3"
              style={{ background: '#f5f5f5' }}
            >
              {/* Mensaje de bienvenida con selector de titulación */}
              {(showOnboarding || selectedTitulacion) && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                  className="self-start mr-auto rounded-2xl rounded-bl-sm text-gray-800 bg-white shadow-sm px-3.5 py-2.5 text-[13.5px] max-w-[92%]"
                >
                  <div className="leading-snug">
                    ¡Hola! Soy <strong>Linceus</strong>, el asistente virtual de la ETSII (Universidad de Sevilla). ¿En qué puedo ayudarte hoy?
                  </div>
                  <div className="leading-snug mt-2">
                    Antes de empezar, por favor indícame tu titulación:
                  </div>
                  <div className="flex flex-col gap-1.5 mt-2.5">
                    {[
                      { id: 'GII-IS', label: 'Ingeniería del Software (GII-IS)' },
                      { id: 'GII-TI', label: 'Tecnologías Informáticas (GII-TI)' },
                      { id: 'GII-IC', label: 'Ingeniería de Computadores (GII-IC)' },
                    ].map((opt) => {
                      const selected = selectedTitulacion === opt.id;
                      return (
                        <button
                          key={opt.id}
                          className="text-left px-3 py-1.5 rounded-full text-[12.5px] border transition-colors"
                          style={
                            selected
                              ? {
                                  background: '#9e1c3f',
                                  color: '#fff',
                                  borderColor: '#9e1c3f',
                                }
                              : {
                                  background: '#fff',
                                  color: '#9e1c3f',
                                  borderColor: '#9e1c3f',
                                }
                          }
                        >
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                </motion.div>
              )}

              {messages.map((m, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                  className={`max-w-[85%] px-3.5 py-2.5 text-[13.5px] ${
                    m.from === 'user'
                      ? 'self-end ml-auto rounded-2xl rounded-br-sm text-white'
                      : 'self-start mr-auto rounded-2xl rounded-bl-sm text-gray-800 bg-white shadow-sm'
                  }`}
                  style={
                    m.from === 'user'
                      ? { background: '#9e1c3f' }
                      : undefined
                  }
                >
                  <MessageBody text={m.text} />
                </motion.div>
              ))}

              {/* Burbuja "borrador" del usuario mientras teclea (antes de enviar) */}
              {inputBuffer && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                  className="self-end ml-auto rounded-2xl rounded-br-sm text-white max-w-[85%] px-3.5 py-2.5 text-[13.5px]"
                  style={{ background: '#9e1c3f', opacity: 0.78 }}
                >
                  <span>{inputBuffer}</span>
                  <span className="inline-block w-0.5 h-4 bg-white/85 ml-0.5 animate-pulse align-middle" />
                </motion.div>
              )}

              {botTyping && (
                <div className="self-start mr-auto rounded-2xl rounded-bl-sm bg-white shadow-sm px-3.5 py-3 flex gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:-0.3s]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:-0.15s]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" />
                </div>
              )}
            </div>

            {/* Input */}
            <div className="px-3 py-2.5 border-t border-gray-200 bg-white flex items-center gap-2">
              <div className="flex-1 px-3 py-2 rounded-full bg-gray-100 text-[13px] text-gray-800 min-h-[36px] flex items-center">
                {inputBuffer || (
                  <span className="text-gray-400">Escribe tu pregunta…</span>
                )}
                {inputBuffer && (
                  <span className="inline-block w-0.5 h-4 bg-[#9e1c3f] ml-0.5 animate-pulse" />
                )}
              </div>
              <button
                className="w-9 h-9 rounded-full flex items-center justify-center text-white"
                style={{ background: '#9e1c3f' }}
              >
                <i className="fa-solid fa-paper-plane text-sm" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
