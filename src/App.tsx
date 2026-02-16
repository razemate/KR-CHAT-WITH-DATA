import { useState } from 'react';
import axios from 'axios';
import { Send, Bot, User, Loader2, LogIn } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  type?: 'text' | 'sql' | 'data';
}

interface ChatStreamChunk {
  type: string;
  simple?: {
    text?: string;
    // Add other fields as needed based on Vanna's response
  };
}

interface ChatResponse {
  conversation_id: string;
  chunks: ChatStreamChunk[];
}

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hello! I am your data assistant. Ask me anything about your database.' }
  ]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('auth_token'));
  const [showLogin, setShowLogin] = useState(!localStorage.getItem('auth_token'));

  const [tokenInput, setTokenInput] = useState('');

  const handleLogin = (e: React.FormEvent) => {
      e.preventDefault();
      if (tokenInput.trim()) {
          setToken(tokenInput.trim());
          localStorage.setItem('auth_token', tokenInput.trim());
          setShowLogin(false);
          setTokenInput('');
      }
  };

  const sendMessage = async () => {
    if (!input.trim()) return;
    if (!token) {
        setMessages(prev => [...prev, { role: 'assistant', content: "Please sign in to continue." }]);
        setShowLogin(true);
        return;
    }

    const userMessage = { role: 'user' as const, content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post<ChatResponse>('/api/vanna/v2/chat_poll', {
        message: input,
        conversation_id: conversationId
      }, {
        headers: {
            Authorization: `Bearer ${token}`
        }
      });

      const data = response.data;
      
      // Update conversation ID
      if (data.conversation_id) {
          setConversationId(data.conversation_id);
      }

      // Process chunks
      let fullText = "";
      if (data.chunks && data.chunks.length > 0) {
          // Extract text from chunks
          // This logic depends on how Vanna returns chunks. 
          // Usually it's a list of components. We'll try to find text components.
          const textChunks = data.chunks
              .map(chunk => chunk.simple?.text)
              .filter(Boolean);
          
          if (textChunks.length > 0) {
              fullText = textChunks.join("\n\n");
          } else {
              fullText = "Response received (rich UI not yet rendered).";
          }
      } else {
          fullText = "No response content received.";
      }
      
      setMessages(prev => [...prev, { role: 'assistant', content: fullText }]);
    } catch (error) {
      console.error(error);
      let errorMessage = "Sorry, I encountered an error connecting to the AI.";
      
      if (axios.isAxiosError(error)) {
          if (error.response?.status === 401) {
              errorMessage = "Please sign in again (Session expired).";
              setToken(null);
              localStorage.removeItem('auth_token');
              setShowLogin(true);
          } else if (error.response?.status === 500) {
              errorMessage = "The AI service encountered an internal error.";
          } else if (error.response?.status === 429) {
              errorMessage = "You are sending requests too quickly. Please wait a moment.";
          }
      }
      
      setMessages(prev => [...prev, { role: 'assistant', content: errorMessage }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 text-gray-900 font-sans">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center">
            <Bot className="w-8 h-8 text-blue-600 mr-3" />
            <h1 className="text-xl font-bold text-gray-800">KR Chat with Data</h1>
        </div>
        <div>
            {token ? (
                <button 
                    onClick={() => {
                        setToken(null);
                        localStorage.removeItem('auth_token');
                        setShowLogin(true);
                    }}
                    className="text-sm text-gray-600 hover:text-red-600"
                >
                    Sign Out
                </button>
            ) : (
                <button 
                    onClick={() => setShowLogin(true)}
                    className="text-sm text-blue-600 hover:underline"
                >
                    Sign In
                </button>
            )}
        </div>
      </header>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-blue-600 ml-3' : 'bg-gray-200 mr-3'}`}>
                {msg.role === 'user' ? <User className="w-5 h-5 text-white" /> : <Bot className="w-5 h-5 text-gray-600" />}
              </div>
              <div className={`p-4 rounded-2xl shadow-sm ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white text-gray-800 border'}`}>
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
             <div className="flex flex-row">
              <div className="w-8 h-8 rounded-full bg-gray-200 mr-3 flex items-center justify-center">
                <Bot className="w-5 h-5 text-gray-600" />
              </div>
              <div className="bg-white p-4 rounded-2xl border shadow-sm flex items-center">
                <Loader2 className="w-5 h-5 text-blue-600 animate-spin mr-2" />
                <span className="text-gray-500 text-sm">Thinking...</span>
              </div>
            </div>
          </div>
        )}
        
        {/* Login Modal Overlay */}
        {showLogin && !token && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div className="bg-white p-8 rounded-xl shadow-xl max-w-md w-full">
                    <div className="flex flex-col items-center mb-6">
                        <Bot className="w-12 h-12 text-blue-600 mb-2" />
                        <h2 className="text-2xl font-bold">Welcome Back</h2>
                        <p className="text-gray-500 text-center">Please enter your access token to continue</p>
                    </div>
                    <form onSubmit={handleLogin} className="space-y-4">
                        <input 
                            type="password"
                            value={tokenInput}
                            onChange={(e) => setTokenInput(e.target.value)}
                            placeholder="Enter Bearer Token"
                            className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition-all"
                            required
                        />
                        <button 
                            type="submit"
                            className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors flex items-center justify-center"
                        >
                            <LogIn className="w-4 h-4 mr-2" />
                            Enter Token
                        </button>
                    </form>
                </div>
            </div>
        )}
      </main>

      {/* Input Area */}
      <div className="bg-white border-t p-4">
        <div className="max-w-4xl mx-auto relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Ask a question about your data..."
            className="w-full pl-4 pr-12 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition-all"
            disabled={loading || !token}
          />
          <button 
            onClick={sendMessage}
            disabled={!input.trim() || loading || !token}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        <p className="text-center text-xs text-gray-400 mt-2">
          Powered by Vanna AI & Gemini 2.5 Flash
        </p>
      </div>
    </div>
  )
}

export default App
