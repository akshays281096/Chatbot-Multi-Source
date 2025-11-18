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
  const [deleteSuccess, setDeleteSuccess] = useState<string | null>(null)

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
    if (!window.confirm(`Are you sure you want to delete "${documentId}"? This action cannot be undone.`)) {
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
      
      setDeleteSuccess(`"${documentId}" deleted successfully`)
      setTimeout(() => setDeleteSuccess(null), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete document')
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

  const groupedDocuments = documents.reduce((acc, doc) => {
    const type = doc.source_type || 'unknown'
    if (!acc[type]) {
      acc[type] = []
    }
    acc[type].push(doc)
    return acc
  }, {} as Record<string, Document[]>)

  if (documents.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
          Documents for RAG
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No documents uploaded yet. Upload documents above to use them in your queries.
        </p>
      </div>
    )
  }

  const isAllSelected = documents.length > 0 && selectedDocuments.length === documents.length

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Documents for RAG
        </h2>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {selectedDocuments.length} of {documents.length} selected
        </span>
      </div>

      {/* Select All / Deselect All */}
      <div className="mb-4 flex items-center space-x-2">
        <input
          type="checkbox"
          id="select-all"
          checked={isAllSelected}
          onChange={handleSelectAll}
          className="w-4 h-4 cursor-pointer"
        />
        <label htmlFor="select-all" className="text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer">
          {isAllSelected ? 'Deselect All' : 'Select All'}
        </label>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-600 dark:text-red-400">❌ {error}</p>
        </div>
      )}

      {/* Success Message */}
      {deleteSuccess && (
        <div className="mb-4 p-3 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg">
          <p className="text-sm text-green-600 dark:text-green-400">✅ {deleteSuccess}</p>
        </div>
      )}

      {/* Documents List */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {Object.entries(groupedDocuments).map(([sourceType, docs]) => (
          <div key={sourceType}>
            <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mt-3 mb-2 px-2">
              {getSourceTypeIcon(sourceType)} {sourceType}
            </div>
            {docs.map((doc) => (
              <div
                key={doc.id}
                className="flex items-start space-x-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <input
                  type="checkbox"
                  id={doc.id}
                  checked={selectedDocuments.includes(doc.id)}
                  onChange={() => handleDocumentToggle(doc.id)}
                  disabled={deletingId === doc.id}
                  className="w-4 h-4 mt-0.5 cursor-pointer"
                />
                <div className="flex-1 min-w-0">
                  <label
                    htmlFor={doc.id}
                    className="text-sm font-medium text-gray-900 dark:text-white cursor-pointer block truncate"
                  >
                    {doc.source}
                  </label>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 flex flex-wrap gap-2">
                    {doc.sheet_name && (
                      <span className="bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                        Sheet: {doc.sheet_name}
                      </span>
                    )}
                    {doc.rows !== undefined && (
                      <span className="bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                        {doc.rows} rows
                      </span>
                    )}
                    {doc.columns !== undefined && (
                      <span className="bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                        {doc.columns} cols
                      </span>
                    )}
                    {doc.chunking_strategy && (
                      <span className="bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-0.5 rounded text-xs">
                        {doc.chunking_strategy}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteDocument(doc.id)}
                  disabled={deletingId === doc.id}
                  title="Delete document"
                  className="mt-0.5 p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {deletingId === doc.id ? (
                    <span className="text-sm">⏳</span>
                  ) : (
                    <span className="text-sm">🗑️</span>
                  )}
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Info Text */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          💡 <strong>Tip:</strong> If no documents are selected, all uploaded documents will be used for RAG queries by default.
        </p>
      </div>
    </div>
  )
}
