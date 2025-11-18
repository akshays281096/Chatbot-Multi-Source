'use client'

import { useState } from 'react'
import ChatInterface from '@/components/ChatInterface'
import DocumentUpload from '@/components/DocumentUpload'
import DocumentSelector from '@/components/DocumentSelector'
import ModelSelector from '@/components/ModelSelector'

export default function Home() {
  const [selectedModel, setSelectedModel] = useState<{
    provider: 'OPENAI' | 'ANTHROPIC' | 'GEMINI'
    model: string
  }>({
    provider: 'OPENAI',
    model: 'gpt-5'
  })
  const [useRAG, setUseRAG] = useState(true)
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([])

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          <header className="mb-8">
            <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
              Multi-Source Chatbot
            </h1>
            <p className="text-gray-600 dark:text-gray-300">
              Ask questions based on uploaded documents, web pages, and structured data
            </p>
          </header>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Sidebar - Upload & Settings */}
            <div className="lg:col-span-1 space-y-6">
              <ModelSelector
                selectedModel={selectedModel}
                onModelChange={setSelectedModel}
                useRAG={useRAG}
                onUseRAGChange={setUseRAG}
              />
              <DocumentUpload />
              <DocumentSelector
                selectedDocuments={selectedDocuments}
                onDocumentsChange={setSelectedDocuments}
              />
            </div>

            {/* Main Chat Area */}
            <div className="lg:col-span-2">
              <ChatInterface 
                selectedModel={selectedModel} 
                useRAG={useRAG}
                selectedDocuments={selectedDocuments}
              />
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

