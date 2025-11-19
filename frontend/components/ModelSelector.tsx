'use client'

interface ModelSelectorProps {
  selectedModel: {
    provider: 'OPENAI' | 'ANTHROPIC' | 'GEMINI'
    model: string
  }
  onModelChange: (model: { provider: 'OPENAI' | 'ANTHROPIC' | 'GEMINI', model: string }) => void
  useRAG: boolean
  onUseRAGChange: (useRAG: boolean) => void
}

const MODELS = {
  OPENAI: [
    { name: 'gpt-5', label: 'GPT-5' },
    { name: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  ],
  ANTHROPIC: [
    { name: 'claude-3-5-haiku-latest', label: 'Claude 3.5 Haiku' },
    { name: 'claude-3-7-sonnet-latest', label: 'Claude 3.7 Sonnet' },
    { name: 'claude-opus-4-20250514', label: 'Claude Opus 4' },
    { name: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
  ],
  GEMINI: [
    { name: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
    { name: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
  ],
}

export default function ModelSelector({ selectedModel, onModelChange, useRAG, onUseRAGChange }: ModelSelectorProps) {
  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    const [provider, modelName] = value.split('|')
    onModelChange({
      provider: provider as 'OPENAI' | 'ANTHROPIC' | 'GEMINI',
      model: modelName,
    })
  }

  return (
    <div className="space-y-4">
      {/* Unified Model Selection */}
      <div>
        <label className="block mb-1.5 text-xs font-medium text-gray-700 dark:text-gray-300">
          LLM Model
        </label>
        <div className="relative">
          <select
            value={`${selectedModel.provider}|${selectedModel.model}`}
            onChange={handleModelChange}
            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white bg-white text-gray-900 appearance-none"
          >
            {/* OpenAI Models */}
            <optgroup label="OpenAI">
              {MODELS.OPENAI.map((model) => (
                <option key={model.name} value={`OPENAI|${model.name}`}>
                  {model.label}
                </option>
              ))}
            </optgroup>

            {/* Anthropic Models */}
            <optgroup label="Anthropic">
              {MODELS.ANTHROPIC.map((model) => (
                <option key={model.name} value={`ANTHROPIC|${model.name}`}>
                  {model.label}
                </option>
              ))}
            </optgroup>

            {/* Google Gemini Models */}
            <optgroup label="Google Gemini">
              {MODELS.GEMINI.map((model) => (
                <option key={model.name} value={`GEMINI|${model.name}`}>
                  {model.label}
                </option>
              ))}
            </optgroup>
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700 dark:text-gray-300">
            <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
              <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
            </svg>
          </div>
        </div>
      </div>

      {/* RAG Toggle */}
      <div className="flex items-center justify-between p-2 bg-gray-100 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
        <div className="flex-1">
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
            RAG Pipeline
          </label>
          <p className="text-[10px] text-gray-500 dark:text-gray-400">
            Search uploaded docs
          </p>
        </div>
        <button
          type="button"
          onClick={() => onUseRAGChange(!useRAG)}
          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${useRAG ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
            }`}
          role="switch"
          aria-checked={useRAG}
        >
          <span
            className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${useRAG ? 'translate-x-4' : 'translate-x-1'
              }`}
          />
        </button>
      </div>
    </div>
  )
}

