'use client'

import { useState } from 'react'
import axios from 'axios'

interface UploadProgress {
  [key: string]: number
}

export default function DocumentUpload() {
  const [uploading, setUploading] = useState(false)
  const [uploadType, setUploadType] = useState<'document' | 'web' | 'json'>('document')
  const [url, setUrl] = useState('')
  const [crawlWebsite, setCrawlWebsite] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({})
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([])

  // File size constants (matching Next.js patterns)
  const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB
  const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB chunks for large files
  
  const allowedExtensions = uploadType === 'json' 
    ? ['.json']
    : ['.pdf', '.txt', '.md', '.markdown', '.docx', '.csv', '.xls', '.xlsx']

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
      const endpoint = uploadType === 'json' 
        ? '/api/ingest/json'
        : '/api/ingest/document'

      // Use optimized upload with progress tracking
      const response = await uploadLargeFile(file, endpoint)

      setUploadedFiles(prev => [...prev, file.name])
      setMessage({
        type: 'success',
        text: response.message || 'File uploaded successfully!'
      })

      // Clear progress after 2 seconds
      setTimeout(() => {
        setUploadProgress(prev => {
          const newProgress = { ...prev }
          delete newProgress[file.name]
          return newProgress
        })
      }, 2000)
    } catch (error: any) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || error.message || 'Failed to upload file'
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

      const successMessage = crawlWebsite
        ? `Website crawled successfully! ${response.data.pages_crawled || 0} pages indexed.`
        : response.data.message || `Web page "${response.data.title || url}" ingested successfully!`

      setMessage({
        type: 'success',
        text: successMessage
      })
      setUrl('')
    } catch (error: any) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to ingest web page'
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
        Upload Documents
      </h2>

      {/* Upload Type Selector */}
      <div className="mb-4">
        <div className="flex space-x-2 mb-4">
          <button
            onClick={() => setUploadType('document')}
            className={`px-4 py-2 rounded-lg text-sm transition ${
              uploadType === 'document'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200'
            }`}
          >
            Document
          </button>
          <button
            onClick={() => setUploadType('web')}
            className={`px-4 py-2 rounded-lg text-sm transition ${
              uploadType === 'web'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200'
            }`}
          >
            Web Page
          </button>
          <button
            onClick={() => setUploadType('json')}
            className={`px-4 py-2 rounded-lg text-sm transition ${
              uploadType === 'json'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200'
            }`}
          >
            JSON
          </button>
        </div>
      </div>

      {/* File Upload */}
      {uploadType !== 'web' && (
        <div className="mb-4">
          <label className="block mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
            {uploadType === 'json' 
              ? 'Upload JSON File' 
              : 'Upload Document'}
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
            {uploadType === 'json' 
              ? 'JSON files only'
              : 'Supported: PDF, TXT, MD, DOCX, CSV, XLS, XLSX'} (Max: {Math.round(MAX_FILE_SIZE / (1024 * 1024))}MB)
          </p>
          
          {/* Drag and Drop Area */}
          <div className="relative border-2 border-dashed border-blue-300 rounded-lg p-8 bg-blue-50 dark:bg-gray-700 hover:bg-blue-100 dark:hover:bg-gray-600 transition cursor-pointer">
            <input
              type="file"
              onChange={handleFileUpload}
              disabled={uploading}
              accept={uploadType === 'json' 
                ? '.json' 
                : '.pdf,.txt,.md,.markdown,.docx,.csv,.xls,.xlsx'}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="pointer-events-none text-center">
              <svg className="mx-auto h-12 w-12 text-blue-400 mb-2" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                <path d="M28 8H12a4 4 0 00-4 4v20a4 4 0 004 4h24a4 4 0 004-4V20m-8-8l-4-4m0 0l-4 4m4-4v12" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p className="text-lg font-semibold text-gray-700 dark:text-gray-300">
                {uploading ? 'Uploading...' : 'Click to upload or drag and drop'}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                or select a file to upload
              </p>
            </div>
          </div>

          {/* Progress bars for uploading files */}
          {Object.keys(uploadProgress).length > 0 && (
            <div className="mt-4 space-y-3">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Upload Progress</p>
              {Object.entries(uploadProgress).map(([fileId, progress]) => (
                <div key={fileId}>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-600 dark:text-gray-400 truncate">{fileId}</span>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{progress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* List of uploaded files */}
          {uploadedFiles.length > 0 && (
            <div className="mt-4 bg-green-50 dark:bg-green-900/20 rounded-lg p-4 border border-green-200 dark:border-green-800">
              <p className="text-sm font-semibold text-green-700 dark:text-green-400 mb-3">
                ✓ Successfully Uploaded ({uploadedFiles.length})
              </p>
              <ul className="space-y-2">
                {uploadedFiles.map((fileName, idx) => (
                  <li key={idx} className="text-sm text-green-600 dark:text-green-400 flex items-center">
                    <span className="mr-2 text-green-500">✓</span> 
                    <span className="truncate">{fileName}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Web URL Input */}
      {uploadType === 'web' && (
        <div className="mb-4">
          <label className="block mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
            {crawlWebsite ? 'Website Homepage URL' : 'Web Page URL'}
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
            {crawlWebsite 
              ? 'Enter homepage URL to crawl entire website (up to 50 pages, 2 levels deep)'
              : 'Enter a single web page URL to ingest'}
          </p>
          
          {/* Crawl Website Toggle */}
          <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg mb-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Crawl Entire Website
              </label>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Crawl multiple pages from the website
              </p>
            </div>
            <button
              type="button"
              onClick={() => setCrawlWebsite(!crawlWebsite)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                crawlWebsite ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'
              }`}
              role="switch"
              aria-checked={crawlWebsite}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  crawlWebsite ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="flex space-x-2">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              disabled={uploading}
            />
            <button
              onClick={handleWebIngest}
              disabled={uploading || !url.trim()}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 transition"
            >
              {uploading ? (crawlWebsite ? 'Crawling...' : 'Ingesting...') : (crawlWebsite ? 'Crawl Website' : 'Ingest Page')}
            </button>
          </div>
        </div>
      )}

      {/* Status Message */}
      {message && (
        <div
          className={`p-4 rounded-lg text-sm border ${
            message.type === 'success'
              ? 'bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-400 border-green-200 dark:border-green-800'
              : 'bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-400 border-red-200 dark:border-red-800'
          } flex items-start gap-3`}
        >
          <span className="text-lg flex-shrink-0">{message.type === 'success' ? '✓' : '✕'}</span>
          <span>{message.text}</span>
        </div>
      )}

      {uploading && (
        <div className="mt-4 text-center">
          <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
        </div>
      )}
    </div>
  )
}

