import React, { useState } from 'react';

// Define message structure
interface Message {
  sender: 'user' | 'bot';
  text: string;
}

const Chatbot: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input.trim();
    setMessages((prev) => [...prev, { sender: 'user', text: userMessage }]);
    setInput('');
    setIsLoading(true);

    try {
      // Adjust the port if your backend runs on a different one (e.g., 5000, 8080)
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // Adjust the payload structure based on your backend API requirements
        body: JSON.stringify({ message: userMessage }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      
      // Adjust 'data.reply' based on your actual backend response structure
      const botResponse = data.reply || data.response || data.message || "No response received.";
      
      setMessages((prev) => [...prev, { sender: 'bot', text: botResponse }]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages((prev) => [...prev, { sender: 'bot', text: 'Sorry, I encountered an error connecting to the server.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto', fontFamily: 'sans-serif' }}>
      <div style={{ border: '1px solid #ccc', borderRadius: '8px', padding: '16px', minHeight: '400px', display: 'flex', flexDirection: 'column' }}>
        
        {/* Chat Window */}
        <div style={{ flex: 1, overflowY: 'auto', marginBottom: '16px' }}>
          {messages.length === 0 ? (
            <p style={{ textAlign: 'center', color: '#888' }}>Start a conversation...</p>
          ) : (
            messages.map((msg, index) => (
              <div 
                key={index} 
                style={{ 
                  textAlign: msg.sender === 'user' ? 'right' : 'left',
                  margin: '8px 0' 
                }}
              >
                <span style={{
                  display: 'inline-block',
                  padding: '8px 12px',
                  borderRadius: '12px',
                  backgroundColor: msg.sender === 'user' ? '#007bff' : '#eee',
                  color: msg.sender === 'user' ? 'white' : 'black',
                  maxWidth: '80%'
                }}>
                  {msg.text}
                </span>
              </div>
            ))
          )}
          {isLoading && (
            <div style={{ textAlign: 'left', margin: '8px 0' }}>
              <span style={{ display: 'inline-block', padding: '8px 12px', borderRadius: '12px', backgroundColor: '#eee' }}>
                Typing...
              </span>
            </div>
          )}
        </div>

        {/* Input Area */}
        <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={isLoading}
            style={{ flex: 1, padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
          />
          <button 
            type="submit" 
            disabled={isLoading || !input.trim()}
            style={{ padding: '10px 20px', borderRadius: '4px', border: 'none', backgroundColor: '#007bff', color: 'white', cursor: 'pointer' }}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
};

export default Chatbot;