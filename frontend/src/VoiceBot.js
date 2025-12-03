import React from 'react';
import { useRTVIClientEvent } from '@pipecat-ai/client-react';

function VoiceBot({ onDisconnect }) {
  const [isListening, setIsListening] = React.useState(false);
  const [isSpeaking, setIsSpeaking] = React.useState(false);
  const [transcript, setTranscript] = React.useState('');

  // Listen for bot events
  useRTVIClientEvent('userStartedSpeaking', () => {
    setIsListening(true);
  });

  useRTVIClientEvent('userStoppedSpeaking', () => {
    setIsListening(false);
  });

  useRTVIClientEvent('botStartedSpeaking', () => {
    setIsSpeaking(true);
  });

  useRTVIClientEvent('botStoppedSpeaking', () => {
    setIsSpeaking(false);
  });

  useRTVIClientEvent('userTranscript', (data) => {
    if (data.final) {
      setTranscript(prev => prev + '\n👤 You: ' + data.text);
    }
  });

  useRTVIClientEvent('botTranscript', (data) => {
    setTranscript(prev => prev + '\n🤖 Samora: ' + data.text);
  });

  return (
    <div className="voice-bot">
      <div className="status-indicator">
        {isListening && <div className="status listening">🎤 Listening...</div>}
        {isSpeaking && <div className="status speaking">🔊 Samora is speaking...</div>}
        {!isListening && !isSpeaking && <div className="status idle">💬 Ready to chat</div>}
      </div>

      <div className="audio-visualizer">
        <div className={`pulse-circle ${isListening ? 'listening' : ''} ${isSpeaking ? 'speaking' : ''}`}>
          🎙️
        </div>
      </div>

      <div className="transcript-box">
        <h3>Conversation</h3>
        <pre>{transcript || 'Start speaking to begin...'}</pre>
      </div>

      <button className="disconnect-btn" onClick={onDisconnect}>
        ❌ End Conversation
      </button>
    </div>
  );
}

export default VoiceBot;
