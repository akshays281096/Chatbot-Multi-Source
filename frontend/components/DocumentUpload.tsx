'use client'

import { useState } from 'react'
import axios from 'axios'

interface UploadProgress {
  [key: string]: number
}

export default function DocumentUpload() {
  const [uploading, setUploading] = useState(false)
  const [uploadType, setUploadType] = useState<'document' | 'web'>('document')
  const [url, setUrl] = useState('')
  const [crawlWebsite, setCrawlWebsite] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({})
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([])

  // File size constants (matching Next.js patterns)
  const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB
  const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB chunks for large files

  const allowedExtensions = ['.pdf', '.txt', '.md', '.markdown', '.docx', '.csv', '.xls', '.xlsx']

  const validateFile = (file: File): { valid: boolean; error?: string } => {
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase()

    if (!allowedExtensions.includes(fileExt)) {
      return {
        valid: false,
        error: `Unsupported file type. Allowed: ${allowedExtensions.join(', ')}`
      }
    }

    if (file.size > MAX_FILE_SIZE) {
      const sizeMB = Math.round(MAX_FILE_SIZE / (1024 * 1024))
      return {
        valid: false,
        error: `File size exceeds ${sizeMB}MB limit. Your file: ${Math.round(file.size / (1024 * 1024))}MB`
      }
    }

    return { valid: true }
  }

  const uploadLargeFile = async (file: File, endpoint: string): Promise<any> => {
    const fileId = file.name

    // For small files, upload directly
    if (file.size <= CHUNK_SIZE) {
      return uploadFile(file, endpoint, fileId)
    }

    // For large files, show chunked progress
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE)
    let uploadedChunks = 0

    // Upload file normally but with progress tracking
    const formData = new FormData()
    formData.append('file', file)

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()

      // Track upload progress
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = Math.round((e.loaded / e.total) * 100)
          setUploadProgress(prev => ({
            ...prev,
            [fileId]: percentComplete
          }))
        }
      })

      xhr.addEventListener('load', () => {
        if (xhr.status === 200 || xhr.status === 201) {
          resolve(JSON.parse(xhr.responseText))
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}`))
        }
      })

      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed'))
      })

      xhr.open('POST', `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${endpoint}`)
      xhr.send(formData)
    })
  }

  const uploadFile = async (file: File, endpoint: string, fileId: string): Promise<any> => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${endpoint}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const percentComplete = Math.round((progressEvent.loaded / progressEvent.total) * 100)
              setUploadProgress(prev => ({
                ...prev,
                [fileId]: percentComplete
              }))
            }
          }
        }
      )

      return response.data
    } catch (error) {
      throw error
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file
    const validation = validateFile(file)
    if (!validation.valid) {
      setMessage({
        type: 'error',
        text: validation.error || 'File validation failed'
      })
      return
    }

    setUploading(true)
    setMessage(null)

    try {
      const endpoint = '/api/ingest/document'

      // Use optimized upload with progress tracking
      const response = await uploadLargeFile(file, endpoint)

      setUploadedFiles(prev => [...prev, file.name])
      setMessage({
        type: 'success',
        text: 'Uploaded!'
      })

      // Clear progress after 2 seconds
      setTimeout(() => {
        setUploadProgress(prev => {
          const newProgress = { ...prev }
          delete newProgress[file.name]
          return newProgress
        })
        setMessage(null)
      }, 2000)
    } catch (error: any) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || error.message || 'Failed'
      })
    } finally {
      setUploading(false)
      // Reset file input
      if (e.target) {
        e.target.value = ''
      }
    }
  }

  const handleWebIngest = async () => {
    if (!url.trim()) return

    setUploading(true)
    setMessage(null)

    try {
      const formData = new FormData()
      formData.append('url', url)
      formData.append('crawl_website', crawlWebsite.toString())

      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/ingest/web`,
        formData
      )

      setMessage({
        type: 'success',
        text: 'Ingested!'
      })
      setUrl('')
      setTimeout(() => setMessage(null), 3000)
    } catch (error: any) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed'
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Upload Type Selector */}
      <div className="flex p-1 bg-gray-100 dark:bg-gray-700 rounded-lg">
        <button
          onClick={() => setUploadType('document')}
          className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${uploadType === 'document'
              ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
              : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
            }`}
        >
          File
        </button>
        <button
          onClick={() => setUploadType('web')}
          className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${uploadType === 'web'
              ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
              : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
            }`}
        >
          Web
        </button>
      </div>

      {/* File Upload */}
      {uploadType !== 'web' && (
        <div className="space-y-3">
          <div className="relative border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-4 hover:border-blue-400 dark:hover:border-blue-500 transition-colors cursor-pointer bg-gray-50 dark:bg-gray-800/50">
            <input
              type="file"
              onChange={handleFileUpload}
              disabled={uploading}
              accept=".pdf,.txt,.md,.markdown,.docx,.csv,.xls,.xlsx"
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="text-center">
              <svg className="mx-auto h-8 w-8 text-gray-400 dark:text-gray-500 mb-2" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                <path d="M28 8H12a4 4 0 00-4 4v20a4 4 0 004 4h24a4 4 0 004-4V20m-8-8l-4-4m0 0l-4 4m4-4v12" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p className="text-xs font-medium text-gray-700 dark:text-gray-300">
                {uploading ? 'Uploading...' : 'Click or drag file'}
              </p>
              <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-1">
                PDF, TXT, DOCX, CSV (Max 50MB)
              </p>
            </div>
          </div>

          {/* Progress bars */}
          {Object.keys(uploadProgress).length > 0 && (
            <div className="space-y-2">
              {Object.entries(uploadProgress).map(([fileId, progress]) => (
                <div key={fileId} className="text-xs">
                  <div className="flex justify-between mb-1">
                    <span className="truncate max-w-[150px]">{fileId}</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-1.5">
                    <div
                      className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Web URL Input */}
      {uploadType === 'web' && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="crawl"
              checked={crawlWebsite}
              onChange={(e) => setCrawlWebsite(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="crawl" className="text-xs text-gray-600 dark:text-gray-400">
              Crawl entire site
            </label>
          </div>

          <div className="flex gap-2">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="flex-1 px-3 py-1.5 text-xs border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              disabled={uploading}
            />
            <button
              onClick={handleWebIngest}
              disabled={uploading || !url.trim()}
              className="px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              Add
            </button>
          </div>
        </div>
      )}

      {/* Status Message */}
      {message && (
        <div
          className={`p-2 rounded-md text-xs border ${message.type === 'success'
              ? 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800'
              : 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800'
            }`}
        >
          {message.text}
        </div>
      )}
    </div>
  )
}

