'use client'

import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'

interface Message {
  role: 'user' | 'assistant'
  content: string
  references?: string[]
}

interface Document {
  id: string
  source: string
  source_type: string
  rows?: number
  columns?: number
  sheet_name?: string
}

interface ChatInterfaceProps {
  selectedModel: {
    provider: 'OPENAI' | 'ANTHROPIC' | 'GEMINI'
    model: string
  }
  useRAG: boolean
  selectedDocuments?: string[]
}

export default function ChatInterface({ selectedModel, useRAG, selectedDocuments = [] }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedQueryDocument, setSelectedQueryDocument] = useState<string>('')
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Fetch available documents
  useEffect(() => {
    fetchDocuments()
    const interval = setInterval(fetchDocuments, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchDocuments = async () => {
    setDocumentsLoading(true)
    try {
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/documents`
      )
      setDocuments(response.data.documents || [])
    } catch (err) {
      // Silently handle errors
      console.log('Could not fetch documents')
      setDocuments([])
    } finally {
      setDocumentsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage: Message = {
      role: 'user',
      content: input
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      // Use selected query document if specified, otherwise use selectedDocuments from props
      const docsToUse = selectedQueryDocument 
        ? [selectedQueryDocument] 
        : (selectedDocuments && selectedDocuments.length > 0 ? selectedDocuments : null)

      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/query`,
        {
          query: input,
          llm_provider: selectedModel.provider,
          model: selectedModel.model,
          use_rag: useRAG,
          selected_documents: docsToUse,
          conversation_history: messages.map(m => ({
            role: m.role,
            content: m.content
          }))
        }
      )

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.response,
        references: response.data.references || []
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error: any) {
      const errorMessage: Message = {
        role: 'assistant',
        content: `Error: ${error.response?.data?.detail || error.message}`
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg h-[600px] flex flex-col">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 dark:text-gray-400 mt-8">
            <p className="text-lg mb-2">👋 Welcome!</p>
            <p>Start a conversation by asking a question or uploading a document.</p>
          </div>
        )}

        {messages.map((message, idx) => (
          <div
            key={idx}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-4 ${
                message.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
              }`}
            >
              {message.role === 'assistant' ? (
                <div>
                  <ReactMarkdown className="prose dark:prose-invert max-w-none">
                    {message.content}
                  </ReactMarkdown>
                      {message.references && message.references.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-gray-300 dark:border-gray-600">
                      <p className="text-sm font-semibold mb-2">References:</p>
                      <ul className="text-sm space-y-1">
                        {message.references.map((ref, refIdx) => (
                          <li key={refIdx} className="text-blue-600 dark:text-blue-400">
                            • {ref}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <p>{message.content}</p>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-700 rounded-lg p-4">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="border-t border-gray-200 dark:border-gray-700 p-4 space-y-3">
        {/* Document Selector Dropdown */}
        {documents.length > 0 && (
          <div className="flex items-center space-x-2">
            <label htmlFor="document-select" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              📄 Query Document:
            </label>
            <select
              id="document-select"
              value={selectedQueryDocument}
              onChange={(e) => setSelectedQueryDocument(e.target.value)}
              disabled={documentsLoading || loading}
              className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white text-sm"
            >
              <option value="">🔄 Use all selected documents</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.source_type === 'csv' || doc.source_type === 'excel' ? '📊' : '📄'} {doc.source}
                  {doc.sheet_name ? ` (${doc.sheet_name})` : ''}
                  {doc.rows ? ` [${doc.rows} rows]` : ''}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Input Field and Send Button */}
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}

