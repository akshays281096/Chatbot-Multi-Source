'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

interface Document {
  id: string
  source: string
  source_type: string
  rows?: number
  columns?: number
  sheet_name?: string
  chunking_strategy?: string
}

interface DocumentSelectorProps {
  selectedDocuments: string[]
  onDocumentsChange: (documentIds: string[]) => void
}

export default function DocumentSelector({ selectedDocuments, onDocumentsChange }: DocumentSelectorProps) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // Fetch documents on component mount
  useEffect(() => {
    fetchDocuments()
    // Refresh documents every 5 seconds
    const interval = setInterval(fetchDocuments, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/documents`
      )
      setDocuments(response.data.documents || [])
      setError(null)
    } catch (err: any) {
      // Silently handle errors - documents endpoint might not exist yet
      console.log('Could not fetch documents:', err.message)
      setDocuments([])
    }
  }

  const handleDeleteDocument = async (documentId: string) => {
    if (!window.confirm(`Delete "${documentId}"?`)) {
      return
    }

    setDeletingId(documentId)
    try {
      await axios.delete(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/documents/${encodeURIComponent(documentId)}`
      )

      // Remove from selected documents if it was selected
      if (selectedDocuments.includes(documentId)) {
        onDocumentsChange(selectedDocuments.filter(id => id !== documentId))
      }

      // Refresh documents list
      await fetchDocuments()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete')
      setTimeout(() => setError(null), 3000)
    } finally {
      setDeletingId(null)
    }
  }

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      onDocumentsChange(documents.map(doc => doc.id))
    } else {
      onDocumentsChange([])
    }
  }

  const handleDocumentToggle = (docId: string) => {
    if (selectedDocuments.includes(docId)) {
      onDocumentsChange(selectedDocuments.filter(id => id !== docId))
    } else {
      onDocumentsChange([...selectedDocuments, docId])
    }
  }

  const getSourceTypeIcon = (sourceType: string) => {
    const icons: Record<string, string> = {
      pdf: '📄',
      txt: '📝',
      markdown: '📋',
      md: '📋',
      docx: '📘',
      csv: '📊',
      excel: '📊',
      xls: '📊',
      xlsx: '📊',
      json: '{}',
      web: '🌐',
    }
    return icons[sourceType.toLowerCase()] || '📎'
  }

  if (documents.length === 0) {
    return (
      <div className="text-xs text-gray-500 dark:text-gray-400 text-center py-4 border border-dashed border-gray-300 dark:border-gray-700 rounded-lg">
        No documents yet
      </div>
    )
  }

  const isAllSelected = documents.length > 0 && selectedDocuments.length === documents.length

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="select-all"
            checked={isAllSelected}
            onChange={handleSelectAll}
            className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <label htmlFor="select-all" className="text-xs font-medium text-gray-700 dark:text-gray-300 cursor-pointer">
            Select All
          </label>
        </div>
        <span className="text-[10px] text-gray-500 dark:text-gray-400">
          {selectedDocuments.length}/{documents.length}
        </span>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-2 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded text-xs text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Documents List */}
      <div className="space-y-1 max-h-[300px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="group flex items-center gap-2 p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <input
              type="checkbox"
              id={doc.id}
              checked={selectedDocuments.includes(doc.id)}
              onChange={() => handleDocumentToggle(doc.id)}
              disabled={deletingId === doc.id}
              className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 flex-shrink-0"
            />
            <div className="flex-1 min-w-0 overflow-hidden">
              <label
                htmlFor={doc.id}
                className="text-xs text-gray-700 dark:text-gray-200 cursor-pointer block truncate"
                title={doc.source}
              >
                {getSourceTypeIcon(doc.source_type)} {doc.source}
              </label>
            </div>
            <button
              onClick={() => handleDeleteDocument(doc.id)}
              disabled={deletingId === doc.id}
              className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-all"
              title="Delete"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
