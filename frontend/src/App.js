import React, { useState, useCallback, useRef, useEffect } from 'react';
import { PipecatClient, RTVIEvent } from '@pipecat-ai/client-js';
import { DailyTransport } from '@pipecat-ai/daily-transport';
import SiriWave from 'siriwave';
import { QRCodeSVG } from 'qrcode.react';
import SyncWave from './SyncWave';
import Settings, { getConfig, VoiceAgentConfigPill } from './Settings';
import './App.css';

// Twilio phone number for calling the agent (E.164 format)
const PHONE_NUMBER = '+15206521762';
const PHONE_DISPLAY = '+1 (520) 652-1762';

// Pipecat Cloud config
const PIPECAT_API_URL = 'https://api.pipecat.daily.co/v1/public/samora-agent/start';
const PUBLIC_API_KEY = 'pk_7d0bfa89-4493-4a92-89a3-7df391f0ef8d';

function App() {
  const [status, setStatus] = useState('idle'); // idle, connecting, active
  const [isBotSpeaking, setIsBotSpeaking] = useState(false);
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [waveAmplitude, setWaveAmplitude] = useState(0.5);
  const [waveSpeed, setWaveSpeed] = useState(0.01);
  
  const [showQRModal, setShowQRModal] = useState(false);
  const [showMongoInfo, setShowMongoInfo] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [config, setConfig] = useState(getConfig);
  
  const clientRef = useRef(null);
  const audioRef = useRef(null);
  const siriWaveRef = useRef(null);
  const siriWaveContainerRef = useRef(null);
  const isBotSpeakingRef = useRef(false);
  const isUserSpeakingRef = useRef(false);
  const userIdleTimeoutRef = useRef(null);
  const botIdleTimeoutRef = useRef(null);
  
  // Web Audio API refs for real-time analysis
  const audioContextRef = useRef(null);
  const localAnalyserRef = useRef(null);
  const remoteAnalyserRef = useRef(null);
  const animationFrameRef = useRef(null);

  // Check if anyone is speaking (for switching between wave types)
  const isSpeaking = isBotSpeaking || isUserSpeaking;
  const isConnected = status === 'active';

  // Initialize/update SiriWave when connected (for speaking AND pauses)
  useEffect(() => {
    if (!isConnected) {
      // Destroy siriwave when not connected
      if (siriWaveRef.current) {
        siriWaveRef.current.dispose();
        siriWaveRef.current = null;
      }
      return;
    }

    // Create siriwave when connected (stays active during pauses too)
    if (siriWaveContainerRef.current && !siriWaveRef.current) {
      siriWaveRef.current = new SiriWave({
        container: siriWaveContainerRef.current,
        style: 'ios9',
        width: 300,
        height: 150,
        autostart: true,
        amplitude: 0.3,
        speed: 0.03,
        lerpSpeed: 0.1,
        curveDefinition: [
          { color: '255, 255, 255', supportLine: true },
          { color: '200, 200, 200' },
          { color: '180, 180, 180' },
          { color: '160, 160, 160' },
        ],
      });
    }
  }, [isConnected]);

  // Update siriwave colors when speaker changes
  useEffect(() => {
    if (!siriWaveRef.current || !siriWaveContainerRef.current || !isConnected) return;
    
    // Dispose and recreate with new colors
    siriWaveRef.current.dispose();
    
    let curveDefinition;
    let amplitude = 0.3;
    let speed = 0.03;
    
    if (isBotSpeaking) {
      curveDefinition = [
        { color: '255, 255, 255', supportLine: true },
        { color: '255, 200, 50' },   // yellow
        { color: '255, 150, 0' },    // orange
        { color: '255, 100, 50' },   // red-orange
      ];
      amplitude = 1.0;
      speed = 0.1;
    } else if (isUserSpeaking) {
      curveDefinition = [
        { color: '255, 255, 255', supportLine: true },
        { color: '50, 255, 150' },   // green
        { color: '0, 200, 255' },    // cyan
        { color: '50, 200, 255' },   // blue
      ];
      amplitude = 1.0;
      speed = 0.1;
    } else {
      // Pause/silence - silver/gray waves
      curveDefinition = [
        { color: '255, 255, 255', supportLine: true },
        { color: '200, 200, 200' },
        { color: '180, 180, 180' },
        { color: '160, 160, 160' },
      ];
      amplitude = 0.3;
      speed = 0.03;
    }

    siriWaveRef.current = new SiriWave({
      container: siriWaveContainerRef.current,
      style: 'ios9',
      width: 300,
      height: 150,
      autostart: true,
      amplitude,
      speed,
      lerpSpeed: 0.1,
      curveDefinition,
    });
  }, [isBotSpeaking, isUserSpeaking, isConnected]);

  // Real-time audio analysis loop
  const startAudioAnalysis = useCallback(() => {
    const analyze = () => {
      // For idle SyncWave animation
      let amplitude = 0.5;
      let speed = 0.01;

      // Analyze local (user) audio - update siriwave
      if (isUserSpeakingRef.current && localAnalyserRef.current && siriWaveRef.current) {
        const dataArray = new Uint8Array(localAnalyserRef.current.frequencyBinCount);
        localAnalyserRef.current.getByteFrequencyData(dataArray);
        
        // Calculate RMS (root mean square) for more accurate loudness
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i] * dataArray[i];
        }
        const rms = Math.sqrt(sum / dataArray.length) / 255;
        
        // Apply non-linear scaling for better visual response
        const scaledLevel = Math.pow(rms, 0.7) * 1.5;
        const siriAmplitude = 0.3 + scaledLevel * 3.5;
        const siriSpeed = 0.05 + scaledLevel * 0.2;
        
        siriWaveRef.current.setAmplitude(siriAmplitude);
        siriWaveRef.current.setSpeed(siriSpeed);
      }
      
      // Analyze remote (bot) audio - update siriwave
      if (isBotSpeakingRef.current && remoteAnalyserRef.current && siriWaveRef.current) {
        const dataArray = new Uint8Array(remoteAnalyserRef.current.frequencyBinCount);
        remoteAnalyserRef.current.getByteFrequencyData(dataArray);
        
        // Calculate RMS
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i] * dataArray[i];
        }
        const rms = Math.sqrt(sum / dataArray.length) / 255;
        
        // Apply non-linear scaling
        const scaledLevel = Math.pow(rms, 0.7) * 1.5;
        const siriAmplitude = 0.3 + scaledLevel * 3.5;
        const siriSpeed = 0.05 + scaledLevel * 0.2;
        
        siriWaveRef.current.setAmplitude(siriAmplitude);
        siriWaveRef.current.setSpeed(siriSpeed);
      }

      // Update idle wave state (for when not speaking)
      setWaveAmplitude(amplitude);
      setWaveSpeed(speed);
      
      animationFrameRef.current = requestAnimationFrame(analyze);
    };
    
    analyze();
  }, []);

  // Stop audio analysis
  const stopAudioAnalysis = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
  }, []);

  // Setup audio analyser for a track
  const setupAnalyser = useCallback((track, isLocal) => {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
    }
    
    const audioContext = audioContextRef.current;
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 256; // Smaller = faster, more responsive
    analyser.smoothingTimeConstant = 0.3; // Less smoothing = more reactive
    
    const source = audioContext.createMediaStreamSource(new MediaStream([track]));
    source.connect(analyser);
    
    if (isLocal) {
      localAnalyserRef.current = analyser;
    } else {
      remoteAnalyserRef.current = analyser;
      // Also connect to destination for playback
      if (audioRef.current) {
        audioRef.current.srcObject = new MediaStream([track]);
      }
    }
    
    console.log(`${isLocal ? 'Local' : 'Remote'} audio analyser set up`);
  }, []);

  const setupAudio = useCallback(() => {
    if (clientRef.current && audioRef.current) {
      const tracks = clientRef.current.tracks();
      if (tracks?.bot?.audio) {
        setupAnalyser(tracks.bot.audio, false);
      }
    }
  }, [setupAnalyser]);

  // Initialize Pipecat client
  useEffect(() => {
    const client = new PipecatClient({
      transport: new DailyTransport(),
      enableMic: true,
      enableCam: false,
      callbacks: {
        onConnected: () => {
          console.log('Connected!');
          setStatus('active');
          startAudioAnalysis(); // Start real-time audio analysis
        },
        onDisconnected: () => {
          console.log('Disconnected');
          setStatus('idle');
          setIsBotSpeaking(false);
          setIsUserSpeaking(false);
          isBotSpeakingRef.current = false;
          isUserSpeakingRef.current = false;
          stopAudioAnalysis(); // Stop analysis
          setWaveAmplitude(0.5);
          setWaveSpeed(0.01);
        },
        onTransportStateChanged: (state) => {
          console.log('Transport state:', state);
          if (state === 'ready') {
            setupAudio();
          }
        },
        onBotReady: () => {
          console.log('Bot is ready!');
          setupAudio();
        },
        onBotDisconnected: () => {
          console.log('Bot disconnected gracefully');
          if (clientRef.current) {
            clientRef.current.disconnect();
          }
        },
        onBotStartedSpeaking: () => {
          setIsBotSpeaking(true);
          isBotSpeakingRef.current = true;
        },
        onBotStoppedSpeaking: () => {
          setIsBotSpeaking(false);
          isBotSpeakingRef.current = false;
        },
        onUserStartedSpeaking: () => {
          // User interrupts bot - stop bot instantly
          if (isBotSpeakingRef.current) {
            setIsBotSpeaking(false);
            isBotSpeakingRef.current = false;
          }
          setIsUserSpeaking(true);
          isUserSpeakingRef.current = true;
        },
        onUserStoppedSpeaking: () => {
          setIsUserSpeaking(false);
          isUserSpeakingRef.current = false;
        },
        // Fallback: Use audio levels to detect speaking (client-side)
        onLocalAudioLevel: (level) => {
          if (level > 0.05) {
            // Cancel any pending idle timeout
            if (userIdleTimeoutRef.current) {
              clearTimeout(userIdleTimeoutRef.current);
              userIdleTimeoutRef.current = null;
            }
            if (!isUserSpeakingRef.current) {
              // User starts speaking - stop bot instantly (interruption)
              if (isBotSpeakingRef.current) {
                setIsBotSpeaking(false);
                isBotSpeakingRef.current = false;
              }
              setIsUserSpeaking(true);
              isUserSpeakingRef.current = true;
            }
          } else if (level <= 0 && isUserSpeakingRef.current && !userIdleTimeoutRef.current) {
            // User stops speaking - wait 1.2s before changing animation
            userIdleTimeoutRef.current = setTimeout(() => {
              setIsUserSpeaking(false);
              isUserSpeakingRef.current = false;
              userIdleTimeoutRef.current = null;
            }, 1200);
          }
        },
        onRemoteAudioLevel: (level) => {
          if (level > 0.05) {
            // Cancel any pending idle timeout
            if (botIdleTimeoutRef.current) {
              clearTimeout(botIdleTimeoutRef.current);
              botIdleTimeoutRef.current = null;
            }
            if (!isBotSpeakingRef.current) {
              setIsBotSpeaking(true);
              isBotSpeakingRef.current = true;
            }
          } else if (level <= 0 && isBotSpeakingRef.current && !botIdleTimeoutRef.current) {
            // Bot stops speaking - wait 1.2s before changing animation
            botIdleTimeoutRef.current = setTimeout(() => {
              setIsBotSpeaking(false);
              isBotSpeakingRef.current = false;
              botIdleTimeoutRef.current = null;
            }, 1200);
          }
        },
        onError: (err) => {
          console.error('Client error:', err);
          setStatus('idle');
          stopAudioAnalysis();
        },
      },
    });

    client.on(RTVIEvent.TrackStarted, (track, participant) => {
      if (!participant?.local && track.kind === 'audio') {
        console.log('Bot audio track started');
        setupAnalyser(track, false); // Set up analyser for bot audio
      } else if (participant?.local && track.kind === 'audio') {
        console.log('Local audio track started');
        setupAnalyser(track, true); // Set up analyser for user audio
      }
    });

    clientRef.current = client;

    return () => {
      stopAudioAnalysis();
      if (clientRef.current) {
        clientRef.current.disconnect();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleClick = useCallback(async () => {
    if (!clientRef.current) return;
    
    if (status === 'active') {
      await clientRef.current.disconnect();
    } else if (status === 'idle') {
      setStatus('connecting');
      setWaveAmplitude(0.7);
      setWaveSpeed(0.015);

      try {
        // Build body with provider selections and optional API keys
        const body = {
          llm_provider: config.llm_provider,
          stt_provider: config.stt_provider,
          tts_provider: config.tts_provider,
          context_threshold: config.context_threshold,
          context_keep_recent: config.context_keep_recent,
        };
        
        // Add API keys only if provided (non-empty)
        if (config.openai_api_key) body.openai_api_key = config.openai_api_key;
        if (config.google_api_key) body.google_api_key = config.google_api_key;
        if (config.cerebras_api_key) body.cerebras_api_key = config.cerebras_api_key;
        if (config.groq_api_key) body.groq_api_key = config.groq_api_key;
        if (config.elevenlabs_api_key) body.elevenlabs_api_key = config.elevenlabs_api_key;
        if (config.deepgram_api_key) body.deepgram_api_key = config.deepgram_api_key;
        if (config.cartesia_api_key) body.cartesia_api_key = config.cartesia_api_key;

        // Wrap in requestData with body field for Pipecat Cloud API
        const requestData = {
          createDailyRoom: true,
          body,
        };

        await clientRef.current.startBotAndConnect({
          endpoint: PIPECAT_API_URL,
          headers: new Headers({
            'Authorization': `Bearer ${PUBLIC_API_KEY}`,
          }),
          requestData,
          timeout: 30000,
        });
      } catch (err) {
        console.error('Failed to connect:', err);
        setStatus('idle');
      }
    }
  }, [status, config]);

  // Handle Save & Apply from Settings - reconnects with new config
  const handleSaveAndApply = useCallback(async (newConfig) => {
    setConfig(newConfig);
    
    // If currently connected, disconnect and reconnect with new config
    if (clientRef.current && status === 'active') {
      await clientRef.current.disconnect();
      // Small delay to ensure clean disconnect
      setTimeout(async () => {
        if (clientRef.current) {
          setStatus('connecting');
          setWaveAmplitude(0.7);
          setWaveSpeed(0.015);
          
          try {
            // Build body with provider selections and optional API keys
            const body = {
              llm_provider: newConfig.llm_provider,
              stt_provider: newConfig.stt_provider,
              tts_provider: newConfig.tts_provider,
              context_threshold: newConfig.context_threshold,
              context_keep_recent: newConfig.context_keep_recent,
            };
            
            if (newConfig.openai_api_key) body.openai_api_key = newConfig.openai_api_key;
            if (newConfig.google_api_key) body.google_api_key = newConfig.google_api_key;
            if (newConfig.cerebras_api_key) body.cerebras_api_key = newConfig.cerebras_api_key;
            if (newConfig.groq_api_key) body.groq_api_key = newConfig.groq_api_key;
            if (newConfig.elevenlabs_api_key) body.elevenlabs_api_key = newConfig.elevenlabs_api_key;
            if (newConfig.deepgram_api_key) body.deepgram_api_key = newConfig.deepgram_api_key;
            if (newConfig.cartesia_api_key) body.cartesia_api_key = newConfig.cartesia_api_key;

            // Wrap in requestData with body field for Pipecat Cloud API
            const requestData = {
              createDailyRoom: true,
              body,
            };

            await clientRef.current.startBotAndConnect({
              endpoint: PIPECAT_API_URL,
              headers: new Headers({
                'Authorization': `Bearer ${PUBLIC_API_KEY}`,
              }),
              requestData,
              timeout: 30000,
            });
          } catch (err) {
            console.error('Failed to reconnect:', err);
            setStatus('idle');
          }
        }
      }, 500);
    }
  }, [status]);

  return (
    <div className="App">
      <audio ref={audioRef} autoPlay playsInline />
      
      {/* Settings Icon */}
      <button 
        className="settings-icon-btn" 
        onClick={() => setShowSettings(true)}
        aria-label="Settings"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
      </button>
      
      {/* Settings Modal */}
      <Settings 
        isOpen={showSettings} 
        onClose={() => setShowSettings(false)}
        onConfigChange={setConfig}
        onSaveAndApply={handleSaveAndApply}
      />
      
      {/* Hero Header */}
      <div className="hero-header">
        <h1 className="hero-title">
          <span className="hero-highlight">Meet Samora-Extended</span>
        </h1>
        <ul className="hero-features">
          <li>Rolling Summarization Context Window Support</li>
          <li>Put on Hold and Return Back</li>
          <li>Improved Call Ending</li>
          <li>Improved Multilingual Support</li>
        </ul>
      </div>
      
      {/* Tagline */}
      <div className="agent-tagline">
        <p>AI Voice Agent for Hotel Grand Vista</p>
        <div className="mongodb-badge">
          <img 
            src="https://www.mongodb.com/assets/images/global/favicon.ico" 
            alt="MongoDB" 
            className="mongodb-logo"
          />
          <span>Samora is Connected to MongoDB</span>
          <div className="ping-dot-container">
            <div className="ping-ring"></div>
            <div className="ping-ring ping-ring-2"></div>
            <div className="ping-dot"></div>
          </div>
          <button 
            className="info-icon" 
            onClick={() => setShowMongoInfo(true)}
            aria-label="More info"
          >
            i
          </button>
        </div>
      </div>
      
      <div className="options-container">
        {/* Web Agent Option */}
        <div className="option-section">
          <p className="option-label">Use Web Agent</p>
          <div className="wave-container" onClick={handleClick}>
            <div className="wave-circle">
              <div className="siriwave-wrapper">
                {/* Show SyncWave only before connected (idle/connecting) */}
                {!isConnected && (
                  <SyncWave 
                    width={300}
                    height={150}
                    amplitude={waveAmplitude}
                    speed={waveSpeed}
                    colorScheme="idle"
                  />
                )}
                {/* Container for siriwave when connected (speaking + pauses) */}
                <div 
                  ref={siriWaveContainerRef} 
                  style={{ display: isConnected ? 'block' : 'none' }}
                />
              </div>
            </div>
          </div>
          <p className="hint">
            {status === 'idle' && 'Tap to start'}
            {status === 'connecting' && 'Connecting...'}
            {status === 'active' && 'Tap to end'}
          </p>
        </div>

        {/* Divider */}
        <div className="option-divider">
          <div className="divider-line"></div>
          <span className="divider-text">OR</span>
          <div className="divider-line"></div>
        </div>

        {/* Call Agent Option */}
        <div className="option-section">
          <p className="option-label">Call Agent</p>
          <button 
            className="call-button"
            onClick={() => setShowQRModal(true)}
          >
            <svg className="twilio-logo" viewBox="0 0 256 256" fill="none">
              <circle cx="128" cy="128" r="112" stroke="#F22F46" strokeWidth="24" fill="none"/>
              <circle cx="96" cy="96" r="24" fill="#F22F46"/>
              <circle cx="160" cy="96" r="24" fill="#F22F46"/>
              <circle cx="96" cy="160" r="24" fill="#F22F46"/>
              <circle cx="160" cy="160" r="24" fill="#F22F46"/>
            </svg>
            <span className="button-text">
              <span className="button-title">Call Samora Agent</span>
              <span className="button-subtitle">Powered by <span className="twilio-text">twilio</span></span>
            </span>
          </button>
          <p className="hint">Scan QR to call</p>
        </div>
      </div>

      {/* Voice Agent Config Pill */}
      <VoiceAgentConfigPill 
        config={config} 
        onModifyClick={() => setShowSettings(true)} 
      />

      {/* QR Code Modal */}
      {showQRModal && (
        <div className="qr-modal-overlay" onClick={() => setShowQRModal(false)}>
          <div className="qr-modal" onClick={(e) => e.stopPropagation()}>
            <button className="qr-close" onClick={() => setShowQRModal(false)}>
              ×
            </button>
            <div className="qr-twilio-header">
              <svg className="qr-twilio-logo" viewBox="0 0 256 256" fill="none">
                <circle cx="128" cy="128" r="112" stroke="#F22F46" strokeWidth="24" fill="none"/>
                <circle cx="96" cy="96" r="24" fill="#F22F46"/>
                <circle cx="160" cy="96" r="24" fill="#F22F46"/>
                <circle cx="96" cy="160" r="24" fill="#F22F46"/>
                <circle cx="160" cy="160" r="24" fill="#F22F46"/>
              </svg>
              <span className="qr-twilio-text">twilio</span>
            </div>
            <h3>Scan to Call</h3>
            <div className="qr-code-container">
              <QRCodeSVG 
                value={PHONE_NUMBER}
                size={200}
                bgColor="#ffffff"
                fgColor="#F22F46"
                level="M"
              />
            </div>
            <p className="phone-number">{PHONE_DISPLAY}</p>
            <p className="qr-hint">Scan with your phone camera to call Samora</p>
          </div>
        </div>
      )}

      {/* MongoDB Info Modal */}
      {showMongoInfo && (
        <div className="qr-modal-overlay" onClick={() => setShowMongoInfo(false)}>
          <div className="mongo-modal" onClick={(e) => e.stopPropagation()}>
            <button className="qr-close" onClick={() => setShowMongoInfo(false)}>
              ×
            </button>
            <div className="mongo-header">
              <img 
                src="https://www.mongodb.com/assets/images/global/favicon.ico" 
                alt="MongoDB" 
                className="mongo-modal-logo"
              />
              <span className="mongo-title">MongoDB</span>
            </div>
            <h3 className="mongo-status">Samora is Connected</h3>
            <p className="mongo-db-name">Database: Hotel Grand Vista</p>
            <div className="mongo-info-content">
              <p className="mongo-subtitle">You can ask Samora to:</p>
              <ul className="mongo-list">
                <li>Book rooms and check availability</li>
                <li>Look up or cancel bookings</li>
                <li>Update reservations</li>
                <li>Check pricing and amenities</li>
                <li>Add special requests</li>
              </ul>
            </div>
            <p className="mongo-realtime">All changes are updated in the database in real-time!</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
