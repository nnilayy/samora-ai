import React, { useState, useEffect, useRef } from 'react';
import './Settings.css';

// Provider options with logos
const LLM_PROVIDERS = [
  { value: 'google', label: 'Google Gemini 2.5 Flash', logo: 'https://img.logo.dev/google.com?token=pk_buX28YqpQXOAIi11qHiUog' },
  { value: 'openai', label: 'OpenAI GPT-4o-mini', logo: 'https://img.logo.dev/openai.com?token=pk_buX28YqpQXOAIi11qHiUog' },
  { value: 'cerebras', label: 'Cerebras Llama-4-Scout', logo: 'https://img.logo.dev/cerebras.ai?token=pk_buX28YqpQXOAIi11qHiUog' },
  { value: 'groq', label: 'Groq Llama-3.3-70B', logo: 'https://img.logo.dev/groq.com?token=pk_buX28YqpQXOAIi11qHiUog', warning: '⚠️ Requires paid tier (free tier has 8k token limit)' },
];

const STT_PROVIDERS = [
  { value: 'elevenlabs', label: 'ElevenLabs Scribe v2', logo: 'https://img.logo.dev/elevenlabs.io?token=pk_buX28YqpQXOAIi11qHiUog', note: '✓ Multilingual STT supported' },
  { value: 'deepgram', label: 'Deepgram Nova-3', logo: 'https://img.logo.dev/deepgram.com?token=pk_buX28YqpQXOAIi11qHiUog', note: '✓ Multilingual STT supported' },
];

const TTS_PROVIDERS = [
  { value: 'deepgram', label: 'Deepgram Aura-2 Theia', logo: 'https://img.logo.dev/deepgram.com?token=pk_buX28YqpQXOAIi11qHiUog', warning: '⚠️ Multilingual TTS not supported' },
  { value: 'cartesia', label: 'Cartesia', logo: 'https://img.logo.dev/cartesia.ai?token=pk_buX28YqpQXOAIi11qHiUog', note: '✓ Multilingual TTS supported' },
];

// API Key providers with logos
const API_KEY_PROVIDERS = {
  google_api_key: { label: 'Google', logo: 'https://img.logo.dev/google.com?token=pk_buX28YqpQXOAIi11qHiUog' },
  openai_api_key: { label: 'OpenAI', logo: 'https://img.logo.dev/openai.com?token=pk_buX28YqpQXOAIi11qHiUog' },
  cerebras_api_key: { label: 'Cerebras', logo: 'https://img.logo.dev/cerebras.ai?token=pk_buX28YqpQXOAIi11qHiUog' },
  groq_api_key: { label: 'Groq', logo: 'https://img.logo.dev/groq.com?token=pk_buX28YqpQXOAIi11qHiUog' },
  elevenlabs_api_key: { label: 'ElevenLabs', logo: 'https://img.logo.dev/elevenlabs.io?token=pk_buX28YqpQXOAIi11qHiUog' },
  deepgram_api_key: { label: 'Deepgram', logo: 'https://img.logo.dev/deepgram.com?token=pk_buX28YqpQXOAIi11qHiUog' },
  cartesia_api_key: { label: 'Cartesia', logo: 'https://img.logo.dev/cartesia.ai?token=pk_buX28YqpQXOAIi11qHiUog' },
};

// API Key Input Component with eye toggle and save/delete
function ApiKeyInput({ keyName, value, savedValue, onChange, onSave, onDelete }) {
  const [showPassword, setShowPassword] = useState(false);
  const [inputValue, setInputValue] = useState(savedValue || '');
  const provider = API_KEY_PROVIDERS[keyName];
  
  // Sync inputValue when savedValue changes (e.g., after reset)
  useEffect(() => {
    setInputValue(savedValue || '');
  }, [savedValue]);
  
  const isSaved = savedValue && savedValue.length > 0;
  const hasUnsavedChanges = inputValue !== (savedValue || '');
  
  const handleInputChange = (e) => {
    setInputValue(e.target.value);
    onChange(e.target.value);
  };
  
  const handleSave = () => {
    onSave(keyName, inputValue);
  };
  
  const handleDelete = () => {
    setInputValue('');
    onDelete(keyName);
  };

  return (
    <div className="api-key-group">
      <label className="settings-label">
        <img src={provider.logo} alt={provider.label} className="provider-icon" />
        <span className="provider-name">{provider.label} API Key</span>
        {isSaved && !hasUnsavedChanges && (
          <span className="api-key-saved-badge">Saved</span>
        )}
      </label>
      <div className="api-key-input-wrapper">
        <input
          type={showPassword ? 'text' : 'password'}
          value={inputValue}
          onChange={handleInputChange}
          placeholder={`Enter ${provider.label} API key...`}
          className={`api-key-input ${isSaved && !hasUnsavedChanges ? 'saved' : ''}`}
          disabled={isSaved && !hasUnsavedChanges}
        />
        <button 
          type="button"
          className="api-key-toggle"
          onClick={() => setShowPassword(!showPassword)}
          aria-label={showPassword ? 'Hide password' : 'Show password'}
        >
          {showPassword ? (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
              <line x1="1" y1="1" x2="23" y2="23"/>
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          )}
        </button>
        {/* Show Save button if there are unsaved changes */}
        {hasUnsavedChanges && inputValue.length > 0 && (
          <button 
            type="button"
            className="api-key-action save"
            onClick={handleSave}
            aria-label="Save API key"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </button>
        )}
        {/* Show Delete button if key is saved */}
        {isSaved && !hasUnsavedChanges && (
          <button 
            type="button"
            className="api-key-action delete"
            onClick={handleDelete}
            aria-label="Delete API key"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}

// Custom Dropdown Component
function CustomDropdown({ options, value, onChange, label }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  
  const selectedOption = options.find(opt => opt.value === value) || options[0];
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="settings-group">
      <label className="settings-label">{label}</label>
      <div className="custom-dropdown" ref={dropdownRef}>
        <button 
          type="button"
          className={`dropdown-trigger ${isOpen ? 'open' : ''}`}
          onClick={() => setIsOpen(!isOpen)}
        >
          <div className="dropdown-selected">
            <img src={selectedOption.logo} alt="" className="dropdown-logo" />
            <span>{selectedOption.label}</span>
          </div>
          <svg className="dropdown-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
        
        {isOpen && (
          <div className="dropdown-menu">
            {options.map((option) => (
              <button
                key={option.value}
                type="button"
                className={`dropdown-option ${option.value === value ? 'selected' : ''}`}
                onClick={() => {
                  onChange(option.value);
                  setIsOpen(false);
                }}
              >
                <div className="dropdown-option-content">
                  <div className="dropdown-option-main">
                    <img src={option.logo} alt="" className="dropdown-logo" />
                    <span>{option.label}</span>
                  </div>
                  {option.warning && (
                    <span className="dropdown-option-warning">{option.warning}</span>
                  )}
                  {option.note && (
                    <span className="dropdown-option-note">{option.note}</span>
                  )}
                </div>
                {option.value === value && (
                  <svg className="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Default values
const DEFAULT_CONFIG = {
  // Model providers
  llm_provider: 'google',
  stt_provider: 'deepgram',
  tts_provider: 'deepgram',
  // Context management
  context_threshold: 100,
  context_keep_recent: 20,
  // API keys (empty by default - will use server env vars)
  openai_api_key: '',
  google_api_key: '',
  cerebras_api_key: '',
  groq_api_key: '',
  elevenlabs_api_key: '',
  deepgram_api_key: '',
  cartesia_api_key: '',
};

// Load from localStorage
const loadConfig = () => {
  try {
    const saved = localStorage.getItem('samora_config');
    if (saved) {
      return { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
    }
  } catch (e) {
    console.error('Failed to load config:', e);
  }
  return DEFAULT_CONFIG;
};

// Save to localStorage
const saveConfig = (config) => {
  try {
    localStorage.setItem('samora_config', JSON.stringify(config));
  } catch (e) {
    console.error('Failed to save config:', e);
  }
};

function Settings({ isOpen, onClose, onConfigChange, onSaveAndApply }) {
  const [activeTab, setActiveTab] = useState('models');
  const [config, setConfig] = useState(loadConfig);
  const [savedConfig, setSavedConfig] = useState(loadConfig);

  // Notify parent of config changes
  useEffect(() => {
    if (onConfigChange) {
      onConfigChange(savedConfig);
    }
  }, [savedConfig, onConfigChange]);

  // Check if model config has unsaved changes
  const hasModelChanges = 
    config.llm_provider !== savedConfig.llm_provider ||
    config.stt_provider !== savedConfig.stt_provider ||
    config.tts_provider !== savedConfig.tts_provider ||
    config.context_threshold !== savedConfig.context_threshold ||
    config.context_keep_recent !== savedConfig.context_keep_recent;

  const handleChange = (key, value) => {
    const newConfig = { ...config, [key]: value };
    setConfig(newConfig);
    // Don't auto-save model changes - wait for Save & Apply
  };

  const handleSaveAndApply = () => {
    saveConfig(config);
    setSavedConfig(config);
    if (onSaveAndApply) {
      onSaveAndApply(config);
    }
    onClose();
  };

  // Get provider info for pills
  const getProviderInfo = (type, value) => {
    const providers = type === 'llm' ? LLM_PROVIDERS : type === 'stt' ? STT_PROVIDERS : TTS_PROVIDERS;
    return providers.find(p => p.value === value) || { label: value, logo: '' };
  };

  const handleApiKeyChange = (key, value) => {
    // Just update local state, don't save yet
    setConfig({ ...config, [key]: value });
  };

  const handleApiKeySave = (key, value) => {
    const newConfig = { ...config, [key]: value };
    setConfig(newConfig);
    saveConfig(newConfig);
    setSavedConfig(newConfig);
  };

  const handleApiKeyDelete = (key) => {
    const newConfig = { ...config, [key]: '' };
    setConfig(newConfig);
    saveConfig(newConfig);
    setSavedConfig(newConfig);
  };

  if (!isOpen) return null;

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="settings-header">
          <h2>Settings</h2>
          <button className="settings-close" onClick={onClose}>×</button>
        </div>

        {/* Tabs */}
        <div className="settings-tabs">
          <button 
            className={`settings-tab ${activeTab === 'models' ? 'active' : ''}`}
            onClick={() => setActiveTab('models')}
          >
            <svg className="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
            Models
          </button>
          <button 
            className={`settings-tab ${activeTab === 'apikeys' ? 'active' : ''}`}
            onClick={() => setActiveTab('apikeys')}
          >
            <svg className="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
            </svg>
            API Keys
          </button>
          <button 
            className={`settings-tab ${activeTab === 'context' ? 'active' : ''}`}
            onClick={() => setActiveTab('context')}
          >
            <svg className="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            Context
          </button>
        </div>

        {/* Content */}
        <div className="settings-content">
          {activeTab === 'models' && (
            <div className="settings-section">
              <h3>Model Selection</h3>
              <p className="settings-description">
                Choose which AI providers to use for each component.
              </p>

              {/* LLM Provider */}
              <CustomDropdown
                label="LLM Provider"
                options={LLM_PROVIDERS}
                value={config.llm_provider}
                onChange={(value) => handleChange('llm_provider', value)}
              />

              {/* STT Provider */}
              <CustomDropdown
                label="Speech-to-Text (STT)"
                options={STT_PROVIDERS}
                value={config.stt_provider}
                onChange={(value) => handleChange('stt_provider', value)}
              />

              {/* TTS Provider */}
              <CustomDropdown
                label="Text-to-Speech (TTS)"
                options={TTS_PROVIDERS}
                value={config.tts_provider}
                onChange={(value) => handleChange('tts_provider', value)}
              />

              {/* Current Config Preview */}
              <div className="config-preview">
                <div className="config-preview-label">Your Voice Agent Config:</div>
                <div className="config-pills">
                  <div className="config-pill">
                    <img src={getProviderInfo('llm', config.llm_provider).logo} alt="" className="pill-logo" />
                    <span className="pill-type">LLM</span>
                    <span className="pill-value">{getProviderInfo('llm', config.llm_provider).label.split(' ')[0]}</span>
                  </div>
                  <div className="config-pill">
                    <img src={getProviderInfo('stt', config.stt_provider).logo} alt="" className="pill-logo" />
                    <span className="pill-type">STT</span>
                    <span className="pill-value">{getProviderInfo('stt', config.stt_provider).label.split(' ')[0]}</span>
                  </div>
                  <div className="config-pill">
                    <img src={getProviderInfo('tts', config.tts_provider).logo} alt="" className="pill-logo" />
                    <span className="pill-type">TTS</span>
                    <span className="pill-value">{getProviderInfo('tts', config.tts_provider).label.split(' ')[0]}</span>
                  </div>
                </div>
                <button 
                  className={`save-apply-btn ${hasModelChanges ? 'has-changes' : ''}`}
                  onClick={handleSaveAndApply}
                  disabled={!hasModelChanges}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                  {hasModelChanges ? 'Save & Apply' : 'No Changes'}
                </button>
              </div>
            </div>
          )}

          {activeTab === 'apikeys' && (
            <div className="settings-section">
              <h3>API Keys</h3>
              <p className="settings-description">
                Optional: Provide your own API keys. Leave empty to use default server keys.
              </p>

              {/* LLM Keys */}
              <div className="settings-category">
                <h4>LLM Providers</h4>
                <p className="settings-category-desc">Provide your own API key to use your preferred LLM model.</p>
                
                <ApiKeyInput
                  keyName="google_api_key"
                  value={config.google_api_key}
                  savedValue={savedConfig.google_api_key}
                  onChange={(value) => handleApiKeyChange('google_api_key', value)}
                  onSave={handleApiKeySave}
                  onDelete={handleApiKeyDelete}
                />

                <ApiKeyInput
                  keyName="openai_api_key"
                  value={config.openai_api_key}
                  savedValue={savedConfig.openai_api_key}
                  onChange={(value) => handleApiKeyChange('openai_api_key', value)}
                  onSave={handleApiKeySave}
                  onDelete={handleApiKeyDelete}
                />

                <ApiKeyInput
                  keyName="cerebras_api_key"
                  value={config.cerebras_api_key}
                  savedValue={savedConfig.cerebras_api_key}
                  onChange={(value) => handleApiKeyChange('cerebras_api_key', value)}
                  onSave={handleApiKeySave}
                  onDelete={handleApiKeyDelete}
                />

                <ApiKeyInput
                  keyName="groq_api_key"
                  value={config.groq_api_key}
                  savedValue={savedConfig.groq_api_key}
                  onChange={(value) => handleApiKeyChange('groq_api_key', value)}
                  onSave={handleApiKeySave}
                  onDelete={handleApiKeyDelete}
                />
              </div>

              {/* STT/TTS Keys */}
              <div className="settings-category no-border">
                <h4>Speech Providers</h4>
                <p className="settings-category-desc">Provide API keys for your preferred STT and TTS services.</p>
                
                <ApiKeyInput
                  keyName="elevenlabs_api_key"
                  value={config.elevenlabs_api_key}
                  savedValue={savedConfig.elevenlabs_api_key}
                  onChange={(value) => handleApiKeyChange('elevenlabs_api_key', value)}
                  onSave={handleApiKeySave}
                  onDelete={handleApiKeyDelete}
                />

                <ApiKeyInput
                  keyName="deepgram_api_key"
                  value={config.deepgram_api_key}
                  savedValue={savedConfig.deepgram_api_key}
                  onChange={(value) => handleApiKeyChange('deepgram_api_key', value)}
                  onSave={handleApiKeySave}
                  onDelete={handleApiKeyDelete}
                />

                <ApiKeyInput
                  keyName="cartesia_api_key"
                  value={config.cartesia_api_key}
                  savedValue={savedConfig.cartesia_api_key}
                  onChange={(value) => handleApiKeyChange('cartesia_api_key', value)}
                  onSave={handleApiKeySave}
                  onDelete={handleApiKeyDelete}
                />
              </div>

              <div className="settings-info warning no-border">
                <svg className="info-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                <span>API keys are stored locally in your browser.</span>
              </div>
            </div>
          )}

          {activeTab === 'context' && (
            <div className="settings-section">
              <h3>Context Management</h3>
              <p className="settings-description">
                Configure how the conversation context is managed to prevent token overflow.
              </p>

              <div className="settings-group">
                <label className="settings-label">Threshold</label>
                <p className="settings-input-desc">Number of messages before summarization triggers</p>
                <input
                  type="number"
                  min="10"
                  max="500"
                  value={config.context_threshold}
                  onChange={(e) => handleChange('context_threshold', parseInt(e.target.value) || 100)}
                  className="settings-number-input"
                />
              </div>

              <div className="settings-group">
                <label className="settings-label">Keep Recent</label>
                <p className="settings-input-desc">Number of recent messages to preserve after summarization</p>
                <input
                  type="number"
                  min="5"
                  max="100"
                  value={config.context_keep_recent}
                  onChange={(e) => handleChange('context_keep_recent', parseInt(e.target.value) || 20)}
                  className="settings-number-input"
                />
              </div>

              <div className="config-preview">
                <button 
                  className={`save-apply-btn ${hasModelChanges ? 'has-changes' : ''}`}
                  onClick={handleSaveAndApply}
                  disabled={!hasModelChanges}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                  {hasModelChanges ? 'Save & Apply' : 'No Changes'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Voice Agent Config Pill Component
export function VoiceAgentConfigPill({ config, onModifyClick }) {
  const llm = LLM_PROVIDERS.find(p => p.value === config.llm_provider) || LLM_PROVIDERS[0];
  const stt = STT_PROVIDERS.find(p => p.value === config.stt_provider) || STT_PROVIDERS[0];
  const tts = TTS_PROVIDERS.find(p => p.value === config.tts_provider) || TTS_PROVIDERS[0];

  // Get short names
  const getLLMShortName = (provider) => {
    if (provider.value === 'google') return 'Gemini';
    if (provider.value === 'openai') return 'OpenAI';
    if (provider.value === 'cerebras') return 'Cerebras';
    if (provider.value === 'groq') return 'Groq';
    return provider.label;
  };

  const getSTTShortName = (provider) => {
    if (provider.value === 'elevenlabs') return 'ElevenLabs';
    if (provider.value === 'deepgram') return 'Deepgram';
    return provider.label;
  };

  const getTTSShortName = (provider) => {
    if (provider.value === 'deepgram') return 'Deepgram';
    if (provider.value === 'cartesia') return 'Cartesia';
    return provider.label;
  };

  return (
    <div className="voice-agent-config-pill">
      <div className="config-pill-header">
        <span className="config-pill-title">YOUR VOICE AGENT CONFIG:</span>
      </div>
      <div className="config-pill-providers">
        <div className="config-provider-chip">
          <img src={llm.logo} alt={llm.label} className="config-chip-logo" />
          <span className="config-chip-type">LLM</span>
          <span className="config-chip-name">{getLLMShortName(llm)}</span>
        </div>
        <div className="config-provider-chip">
          <img src={stt.logo} alt={stt.label} className="config-chip-logo" />
          <span className="config-chip-type">STT</span>
          <span className="config-chip-name">{getSTTShortName(stt)}</span>
        </div>
        <div className="config-provider-chip">
          <img src={tts.logo} alt={tts.label} className="config-chip-logo" />
          <span className="config-chip-type">TTS</span>
          <span className="config-chip-name">{getTTSShortName(tts)}</span>
        </div>
      </div>
      <button className="config-modify-link" onClick={onModifyClick}>
        Modify Settings →
      </button>
    </div>
  );
}

// Export helper to get current config
export const getConfig = loadConfig;

export default Settings;
