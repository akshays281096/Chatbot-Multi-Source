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
    { name: 'claude-3-5-haiku-latest', label: 'Claude 3.5 Haiku Latest' },
    { name: 'claude-3-7-sonnet-latest', label: 'Claude 3.7 Sonnet Latest' },
    { name: 'claude-opus-4-20250514', label: 'Claude Opus 4' },
    { name: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
  ],
  GEMINI: [
    { name: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
    { name: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
  ],
}

const getDisplayLabel = (provider: string, model: string) => {
  const allModels = { ...MODELS }
  for (const [prov, modelList] of Object.entries(allModels)) {
    const found = modelList.find((m) => m.name === model)
    if (found) return `${prov} — ${found.label}`
  }
  return model
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
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
        LLM Model
      </h2>

      {/* Unified Model Selection */}
      <div className="mb-4">
        <label className="block mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
          Select Model
        </label>
        <select
          value={`${selectedModel.provider}|${selectedModel.model}`}
          onChange={handleModelChange}
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white bg-white text-gray-900"
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
      </div>

      {/* RAG Toggle */}
      <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Use RAG Pipeline
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Search uploaded documents for answers
          </p>
        </div>
        <button
          type="button"
          onClick={() => onUseRAGChange(!useRAG)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
            useRAG ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'
          }`}
          role="switch"
          aria-checked={useRAG}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              useRAG ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>
    </div>
  )
}

