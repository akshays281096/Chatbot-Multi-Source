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
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900 overflow-hidden">
      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed md:static inset-y-0 left-0 z-50 w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transform transition-transform duration-200 ease-in-out
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        md:translate-x-0 flex flex-col
      `}>
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
            Multi-Source AI
          </h1>
          <button 
            onClick={() => setIsSidebarOpen(false)}
            className="md:hidden text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-8 scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600">
          <section>
            <h2 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-4">Model Settings</h2>
            <ModelSelector
              selectedModel={selectedModel}
              onModelChange={setSelectedModel}
              useRAG={useRAG}
              onUseRAGChange={setUseRAG}
            />
          </section>

          <section>
            <h2 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-4">Knowledge Base</h2>
            <div className="space-y-6">
              <DocumentUpload />
              <DocumentSelector
                selectedDocuments={selectedDocuments}
                onDocumentsChange={setSelectedDocuments}
              />
            </div>
          </section>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 bg-gray-50 dark:bg-gray-900">
        {/* Mobile Header */}
        <header className="md:hidden bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 flex items-center shadow-sm">
          <button 
            onClick={() => setIsSidebarOpen(true)}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 mr-4"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Chat</h1>
        </header>

        {/* Chat Area */}
        <div className="flex-1 relative">
          <div className="absolute inset-0 p-0 md:p-0">
            <ChatInterface 
              selectedModel={selectedModel} 
              useRAG={useRAG}
              selectedDocuments={selectedDocuments}
            />
          </div>
        </div>
      </main>
    </div>
  )
}

