import { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { ChatMessage, ChatRequest, ChatResponse } from '../types';
import { cn, formatRelativeTime } from '../utils/helpers';
import {
  Send,
  Loader2,
  Sparkles,
  Zap,
  Target,
  BookOpen,
  Route,
  User,
  Copy,
  Check,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const QUICK_ACTIONS = [
  { label: 'Analyze my goals', prompt: 'I want to become a machine learning engineer. I know Python basics and have done some data analysis. I can commit 15 hours per week and prefer project-based learning.', icon: Target },
  { label: 'Get recommendations', prompt: 'What courses do you recommend for me based on my profile?', icon: BookOpen },
  { label: 'Create learning path', prompt: 'Create a structured learning path for me to become a data scientist.', icon: Route },
  { label: 'Explain my path', prompt: 'Explain my current learning path and what I should do next.', icon: Sparkles },
];

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const sendMessageMutation = useMutation({
    mutationFn: (request: ChatRequest) => api.chat(request),
    onSuccess: (response: ChatResponse) => {
      setMessages((prev) => [...prev, { role: 'assistant', content: response.message }]);
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }
      if (response.tool_calls) {
        // Tool calls are handled in the response message
      }
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
    onError: (error) => {
      console.error('Chat error:', error);
      setMessages((prev) => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error. Please try again.' 
      }]);
    },
    onSettled: () => {
      setIsLoading(false);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    
    sendMessageMutation.mutate({
      message: input,
      conversation_id: conversationId || undefined,
    });
    
    setInput('');
  };

  const handleQuickAction = (prompt: string) => {
    setInput(prompt);
    handleSubmit(new Event('submit') as unknown as React.FormEvent);
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">AI Learning Coach</h1>
        <p className="text-gray-600 mt-1">
          Describe your learning goals, ask for recommendations, or get help with your learning path.
        </p>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-2 mb-4">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action.label}
            onClick={() => handleQuickAction(action.prompt)}
            disabled={isLoading}
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm border transition-colors',
              isLoading
                ? 'border-gray-200 text-gray-400 cursor-not-allowed'
                : 'border-gray-200 text-gray-700 hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700'
            )}
          >
            <action.icon className="w-4 h-4" />
            {action.label}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-2">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <Sparkles className="w-12 h-12 text-gray-300 mb-4" />
            <p className="text-lg font-medium">Start a conversation</p>
            <p className="text-sm mt-1">Tell me about your learning goals or ask a question</p>
          </div>
        )}
        
        {messages.map((message, index) => (
          <div
            key={index}
            className={cn(
              'flex gap-3 animate-in',
              message.role === 'user' ? 'flex-row-reverse' : ''
            )}
          >
            <div
              className={cn(
                'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                message.role === 'user'
                  ? 'bg-primary-100 text-primary-700'
                  : 'bg-gray-100 text-gray-700'
              )}
            >
              {message.role === 'user' ? (
                <User className="w-4 h-4" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
            </div>
            <div
              className={cn(
                'max-w-[70%] rounded-2xl px-4 py-3',
                message.role === 'user'
                  ? 'bg-primary-600 text-white rounded-tr-sm'
                  : 'bg-white text-gray-900 rounded-tl-sm border border-gray-200 shadow-sm'
              )}
            >
              <ReactMarkdown
                components={{
                  code: ({ children, ...props }) => (
                    <code
                      {...props}
                      className={cn(
                        'font-mono text-sm rounded px-1.5 py-0.5',
                        message.role === 'user'
                          ? 'bg-primary-700/30'
                          : 'bg-gray-100 text-primary-700'
                      )}
                    >
                      {children}
                    </code>
                  ),
                  pre: ({ children, ...props }) => (
                    <pre
                      {...props}
                      className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto text-sm my-2"
                    >
                      {children}
                    </pre>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3 animate-in">
            <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-4 h-4 text-gray-700 animate-pulse-soft" />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 max-w-[70%]">
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t border-gray-200 pt-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything about your learning journey..."
            className="flex-1 input"
            disabled={isLoading}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="btn-primary p-2"
            aria-label="Send message"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2 text-center">
          Press Enter to send, Shift+Enter for new line
        </p>
      </form>
    </div>
  );
}