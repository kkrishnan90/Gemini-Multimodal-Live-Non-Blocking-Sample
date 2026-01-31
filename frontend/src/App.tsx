import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Settings, Activity, Terminal, CheckCircle2, AlertCircle, X, Key, Cloud, Copy, Check } from 'lucide-react';

interface Part {
  text?: string;
  audio?: string;
}

interface ServerMessage {
  type: string;
  parts?: Part[];
  name?: string;
  args?: Record<string, unknown>;
  error?: string;
  interrupted?: boolean;
  turn_complete?: boolean;
  input_transcription?: { text: string, finished: boolean };
  output_transcription?: { text: string, finished: boolean };
  status?: string;
  message?: string;
  session_id?: string;
  tool_name?: string;
}

interface AuthConfig {
  auth_mode: 'AI_STUDIO' | 'VERTEX_AI';
  project_id: string;
  location: string;
  has_api_key: boolean;
}

const API_BASE_URL = 'http://localhost:8000';

const App: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [transcripts, setTranscripts] = useState<{ role: string, text: string, turnId: number }[]>([]);
  const [toolLogs, setToolLogs] = useState<{ name: string, args: Record<string, unknown> | undefined, time: string }[]>([]);
  const [status, setStatus] = useState('Disconnected');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [copiedSessionId, setCopiedSessionId] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [turnCompleteCount, setTurnCompleteCount] = useState(0);

  // Settings modal state
  const [showSettings, setShowSettings] = useState(false);
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null);
  const [pendingAuthMode, setPendingAuthMode] = useState<'AI_STUDIO' | 'VERTEX_AI'>('VERTEX_AI');
  const [isSavingConfig, setIsSavingConfig] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const isAiSpeakingRef = useRef(false);
  const audioQueueRef = useRef<Float32Array[]>([]);
  const isPlayingRef = useRef(false);  // True when actively playing through queue
  const currentSourceRef = useRef<AudioBufferSourceNode | null>(null);  // Current playing source
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const toolLogsEndRef = useRef<HTMLDivElement>(null);
  const turnIdRef = useRef(0);  // Track current turn for new bubbles on turn_complete

  // Initialize AudioContext only once - use native sample rate for proper mic capture
  const getAudioContext = () => {
    if (!audioContextRef.current) {
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      // Use default sample rate (usually 44100 or 48000) - we'll resample to 16kHz manually
      audioContextRef.current = new AudioContextClass();
    }
    return audioContextRef.current;
  };

  // Resample audio from source sample rate to 16kHz using linear interpolation
  const resampleTo16kHz = (inputData: Float32Array, inputSampleRate: number): Int16Array => {
    const ratio = inputSampleRate / 16000;
    const outputLength = Math.floor(inputData.length / ratio);
    const int16Data = new Int16Array(outputLength);

    for (let i = 0; i < outputLength; i++) {
      const srcIndexFloat = i * ratio;
      const srcIndex = Math.floor(srcIndexFloat);
      const nextIndex = Math.min(srcIndex + 1, inputData.length - 1);
      const frac = srcIndexFloat - srcIndex;

      // Linear interpolation for better quality
      const sample = inputData[srcIndex] * (1 - frac) + inputData[nextIndex] * frac;
      const clampedSample = Math.max(-1, Math.min(1, sample));
      int16Data[i] = clampedSample * 0x7FFF;
    }

    return int16Data;
  };

  // Fetch auth config on mount
  useEffect(() => {
    fetchAuthConfig();
  }, []);

  // Auto-scroll transcripts to bottom when new messages arrive
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcripts]);

  // Auto-scroll tool logs to bottom when new logs arrive
  useEffect(() => {
    toolLogsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [toolLogs]);

  const fetchAuthConfig = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/config`);
      if (response.ok) {
        const config: AuthConfig = await response.json();
        setAuthConfig(config);
        setPendingAuthMode(config.auth_mode);
      }
    } catch (error) {
      console.error('Failed to fetch auth config:', error);
    }
  };

  const saveAuthConfig = async () => {
    setIsSavingConfig(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          auth_mode: pendingAuthMode,
        }),
      });
      if (response.ok) {
        const config: AuthConfig = await response.json();
        setAuthConfig(config);
        setShowSettings(false);
      }
    } catch (error) {
      console.error('Failed to save auth config:', error);
    } finally {
      setIsSavingConfig(false);
    }
  };

  // Clear all pending and playing audio - used for interruptions
  const clearAudioPlayback = () => {
    // Stop current source if playing
    if (currentSourceRef.current) {
      try {
        currentSourceRef.current.stop();
      } catch {
        // Ignore errors if already stopped
      }
      currentSourceRef.current = null;
    }

    // Clear the queue
    audioQueueRef.current = [];

    // Reset flags
    isPlayingRef.current = false;
    isAiSpeakingRef.current = false;

    console.log('Audio playback cleared');
  };

  // Play the next chunk from the queue sequentially
  const playNextChunk = () => {
    // If nothing in queue, we're done
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      isAiSpeakingRef.current = false;
      currentSourceRef.current = null;
      return;
    }

    const context = getAudioContext();

    // Get next chunk - Gemini Live outputs at 24kHz
    const float32Array = audioQueueRef.current.shift()!;
    const buffer = context.createBuffer(1, float32Array.length, 24000);
    buffer.getChannelData(0).set(float32Array);

    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);

    currentSourceRef.current = source;

    // When this chunk ends, play the next one
    source.onended = () => {
      currentSourceRef.current = null;
      // Play next chunk (if any)
      playNextChunk();
    };

    // Start immediately
    source.start(0);
  };

  // Add audio to queue and start playing if not already
  const processAudioQueue = () => {
    // If already playing, the onended handler will pick up new chunks
    if (isPlayingRef.current) {
      return;
    }

    // Nothing to play
    if (audioQueueRef.current.length === 0) {
      return;
    }

    // Start playing
    isPlayingRef.current = true;
    isAiSpeakingRef.current = true;
    playNextChunk();
  };

  const startSession = async () => {
    try {
      const context = getAudioContext();
      if (context.state === 'suspended') {
        await context.resume();
      }

      setStatus('Connecting...');
      const ws = new WebSocket('ws://localhost:8000/ws/live');
      wsRef.current = ws;

      ws.onopen = async () => {
        setIsConnected(true);
        setStatus('Connected');
        
        // Start microphone
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
              sampleRate: { ideal: 48000 },
              channelCount: 1
            }
          });
          mediaStreamRef.current = stream;
          
          const source = context.createMediaStreamSource(stream);
          // Buffer size 2048 at 48kHz = ~42ms chunks - good balance of latency and quality
          const processor = context.createScriptProcessor(2048, 1, 1);
          processorRef.current = processor;

          const inputSampleRate = context.sampleRate;
          console.log(`Audio context sample rate: ${inputSampleRate}Hz, buffer will resample to 16kHz`);

          processor.onaudioprocess = (e) => {
            // Always send audio to server for VAD - even while AI is speaking
            // This enables barge-in/interruption functionality
            if (ws.readyState === WebSocket.OPEN) {
              const inputData = e.inputBuffer.getChannelData(0);
              // Resample from native rate (e.g., 44100/48000) to 16kHz and convert to Int16
              const int16Data = resampleTo16kHz(inputData, inputSampleRate);
              ws.send(int16Data.buffer);
            }
          };

          source.connect(processor);
          processor.connect(context.destination);
        } catch (err) {
          console.error('Mic error:', err);
          setStatus('Mic Error');
        }
      };

      ws.onmessage = (event) => {
        const data: ServerMessage = JSON.parse(event.data);
        
        if (data.type === 'server_content') {
          const updateTranscript = (role: string, text: string, turnId: number) => {
            if (!text || !text.trim()) return;
            setTranscripts(prev => {
              if (prev.length === 0) return [{ role, text, turnId }];
              const last = prev[prev.length - 1];

              // Same role AND same turn - merge text
              if (last.role === role && last.turnId === turnId) {
                // Check if the incoming text is a continuation/refinement
                // User transcriptions are often cumulative, Sophie (parts) are additive fragments
                if (text.startsWith(last.text)) {
                   // Cumulative update (already contains the previous text)
                   return [...prev.slice(0, -1), { role, text, turnId }];
                } else if (last.text.endsWith(text)) {
                   // Duplicate fragment at the end, ignore
                   return prev;
                } else {
                   // Additive fragment
                   return [...prev.slice(0, -1), { role, text: last.text + text, turnId }];
                }
              }
              // Role switch OR new turn, start new bubble
              return [...prev, { role, text, turnId }];
            });
          };

          if (data.parts) {
            data.parts.forEach(part => {
              if (part.text) updateTranscript('Sophie', part.text, turnIdRef.current);
              if (part.audio) playAudioBase64(part.audio);
            });
          }

          if (data.input_transcription?.text) {
             updateTranscript('User', data.input_transcription.text, turnIdRef.current);
          }

          if (data.output_transcription?.text) {
             updateTranscript('Sophie', data.output_transcription.text, turnIdRef.current);
          }

          if (data.interrupted) {
            // Clear all audio playback and reset state
            clearAudioPlayback();
            console.log('Audio interrupted by user speech');
            // Increment turn on interruption so next response is a new bubble
            turnIdRef.current += 1;
          }

          if (data.turn_complete) {
            const ts = new Date().toLocaleTimeString();
            console.log(`[${ts}] Turn complete - Turn #${turnIdRef.current + 1}`);
            // Increment turn ID so next messages start a new bubble
            turnIdRef.current += 1;
            setTurnCompleteCount(prev => prev + 1);
          }
        } else if (data.type === 'session_started') {
          console.log(`Session started: ${data.session_id}`);
          setSessionId(data.session_id || null);
        } else if (data.type === 'interim_response') {
          console.log(`Interim response: ${data.message}`);
          setToast(data.message || `Processing ${data.tool_name}...`);
          setTimeout(() => setToast(null), 3000);
        } else if (data.type === 'tool_call') {
          console.log(`Tool call: ${data.name}`);
          setToolLogs(prev => [{
            name: data.name!,
            args: data.args,
            time: new Date().toLocaleTimeString()
          }, ...prev]);
        } else if (data.error) {
          setStatus(`Error: ${data.error}`);
        }
      };

      ws.onclose = (event) => {
        console.log(`WebSocket closed: code=${event.code}, reason=${event.reason}, wasClean=${event.wasClean}`);
        stopSession();
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setStatus('WebSocket Error');
      };

    } catch (err) {
      console.error('Session start error:', err);
      setStatus('Connection Failed');
    }
  };

  const stopSession = () => {
    // Clear all audio playback first
    clearAudioPlayback();

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    setIsConnected(false);
    setStatus('Disconnected');
    setSessionId(null);
    // Reset turn tracking
    turnIdRef.current = 0;
    setTurnCompleteCount(0);
  };

  const playAudioBase64 = (base64Data: string) => {
    const binaryString = window.atob(base64Data);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    const int16Array = new Int16Array(bytes.buffer);
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    // Add to queue and try to process
    audioQueueRef.current.push(float32Array);
    processAudioQueue();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 flex flex-col gap-6">
      {/* Header */}
      <header className="flex justify-between items-center bg-slate-900/50 p-4 rounded-2xl border border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center">
            <Activity className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
              Sophie Live Demo
            </h1>
            <p className="text-xs text-slate-500 flex items-center gap-1">
              {isConnected ? <CheckCircle2 size={12} className="text-emerald-500" /> : <AlertCircle size={12} />}
              {status}
            </p>
            {sessionId && (
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="text-[10px] text-slate-600 font-mono">Session: {sessionId}</span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(sessionId);
                    setCopiedSessionId(true);
                    setTimeout(() => setCopiedSessionId(false), 2000);
                  }}
                  className="p-0.5 hover:bg-slate-800 rounded transition-colors"
                  title="Copy session ID"
                >
                  {copiedSessionId ? (
                    <Check size={10} className="text-emerald-400" />
                  ) : (
                    <Copy size={10} className="text-slate-500" />
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Auth mode indicator */}
          {authConfig && (
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium ${
              authConfig.auth_mode === 'AI_STUDIO'
                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
            }`}>
              {authConfig.auth_mode === 'AI_STUDIO' ? <Key size={12} /> : <Cloud size={12} />}
              {authConfig.auth_mode === 'AI_STUDIO' ? 'AI Studio' : 'Vertex AI'}
            </div>
          )}
          {!isConnected ? (
            <button
              onClick={startSession}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded-full font-medium transition-all flex items-center gap-2"
            >
              <Mic size={18} /> Start Session
            </button>
          ) : (
            <button
              onClick={stopSession}
              className="bg-rose-600 hover:bg-rose-500 text-white px-6 py-2 rounded-full font-medium transition-all flex items-center gap-2"
            >
              <MicOff size={18} /> Stop Session
            </button>
          )}
          <button
            onClick={() => setShowSettings(true)}
            className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400"
            title="Settings"
          >
            <Settings size={20} />
          </button>
        </div>
      </header>

      <main className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Transcription Area */}
        <div className="lg:col-span-2 flex flex-col bg-slate-900/30 rounded-3xl border border-slate-800 overflow-hidden h-[calc(100vh-200px)]">
          <div className="p-4 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <Terminal size={16} className="text-indigo-400" />
              <span className="text-sm font-semibold uppercase tracking-wider text-slate-400">Live Transcript</span>
            </div>
            {turnCompleteCount > 0 && (
              <div className="flex items-center gap-1.5 px-2 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
                <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                <span className="text-[10px] font-medium text-emerald-400">
                  {turnCompleteCount} turn{turnCompleteCount !== 1 ? 's' : ''} completed
                </span>
              </div>
            )}
          </div>
          <div className="flex-1 p-6 overflow-y-auto flex flex-col gap-4">
            {transcripts.map((t, i) => {
              // Check if this is a new turn (different turnId from previous)
              const isNewTurn = i > 0 && transcripts[i - 1].turnId !== t.turnId;

              return (
                <React.Fragment key={i}>
                  {isNewTurn && (
                    <div className="flex items-center gap-3 py-2">
                      <div className="flex-1 h-px bg-slate-700" />
                      <span className="text-[10px] text-slate-500 font-medium">Turn {t.turnId + 1}</span>
                      <div className="flex-1 h-px bg-slate-700" />
                    </div>
                  )}
                  <div className={`flex flex-col ${t.role === 'User' ? 'items-end' : 'items-start'}`}>
                    <span className="text-[10px] uppercase font-bold text-slate-600 mb-1 ml-1">{t.role}</span>
                    <div className={`max-w-[80%] p-4 rounded-2xl ${
                      t.role === 'User' ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-slate-800 text-slate-200 rounded-tl-none'
                    }`}>
                      {t.text}
                    </div>
                  </div>
                </React.Fragment>
              );
            })}
            {transcripts.length === 0 && (
              <div className="h-full flex items-center justify-center text-slate-600 italic">
                Start the session and speak to see the transcript...
              </div>
            )}
            <div ref={transcriptEndRef} />
          </div>
        </div>

        {/* Side Panel: Tools & Stats */}
        <div className="flex flex-col gap-6 h-[calc(100vh-200px)]">
          <div className="flex-1 bg-slate-900/30 rounded-3xl border border-slate-800 overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-800 bg-slate-900/50 flex items-center gap-2 shrink-0">
              <Activity size={16} className="text-emerald-400" />
              <span className="text-sm font-semibold uppercase tracking-wider text-slate-400">Tool Executions</span>
            </div>
            <div className="flex-1 p-4 overflow-y-auto flex flex-col gap-3">
              {toolLogs.map((log, i) => (
                <div key={i} className="bg-slate-800/50 p-3 rounded-xl border border-slate-700/50 animate-in fade-in slide-in-from-right-4 duration-300">
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-indigo-400 font-mono text-xs font-bold">{log.name}</span>
                    <span className="text-[10px] text-slate-500 font-mono">{log.time}</span>
                  </div>
                  <pre className="text-[10px] text-slate-400 overflow-x-auto">
                    {JSON.stringify(log.args, null, 2)}
                  </pre>
                </div>
              ))}
              {toolLogs.length === 0 && (
                <div className="h-full flex items-center justify-center text-slate-600 italic text-center p-10 text-sm">
                  Active tools used by Sophie will appear here...
                </div>
              )}
              <div ref={toolLogsEndRef} />
            </div>
          </div>
        </div>
      </main>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-6">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-3xl shadow-2xl max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-700 shrink-0">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Settings size={20} className="text-indigo-400" />
                Authentication Settings
              </h2>
              <button
                onClick={() => setShowSettings(false)}
                className="p-1 hover:bg-slate-700 rounded-lg transition-colors text-slate-400"
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6 overflow-y-auto flex-1">
              {/* Auth Mode Toggle */}
              <div className="space-y-3">
                <label className="text-sm font-medium text-slate-300">Authentication Mode</label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setPendingAuthMode('AI_STUDIO')}
                    className={`p-4 rounded-xl border-2 transition-all flex flex-col items-center gap-2 ${
                      pendingAuthMode === 'AI_STUDIO'
                        ? 'border-indigo-500 bg-indigo-500/10 text-indigo-300'
                        : 'border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    <Key size={24} />
                    <span className="text-sm font-medium">AI Studio</span>
                    <span className="text-[10px] text-slate-500">API Key</span>
                  </button>
                  <button
                    onClick={() => setPendingAuthMode('VERTEX_AI')}
                    className={`p-4 rounded-xl border-2 transition-all flex flex-col items-center gap-2 ${
                      pendingAuthMode === 'VERTEX_AI'
                        ? 'border-indigo-500 bg-indigo-500/10 text-indigo-300'
                        : 'border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    <Cloud size={24} />
                    <span className="text-sm font-medium">Vertex AI</span>
                    <span className="text-[10px] text-slate-500">Google Cloud</span>
                  </button>
                </div>
              </div>

              {/* Configuration info */}
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                <p className="text-xs text-slate-400">
                  {pendingAuthMode === 'AI_STUDIO' ? (
                    <>
                      Using API key from <code className="bg-slate-900 px-1.5 py-0.5 rounded text-indigo-300">.env</code> file
                      {authConfig?.has_api_key && (
                        <span className="ml-2 text-green-400">✓ Configured</span>
                      )}
                    </>
                  ) : (
                    <>
                      Using Application Default Credentials (ADC).
                      <br />
                      <span className="text-slate-500">
                        Run: <code className="bg-slate-900 px-1.5 py-0.5 rounded text-indigo-300">gcloud auth application-default login</code>
                      </span>
                    </>
                  )}
                </p>
              </div>

              {/* Configuration Preview */}
              <div className="space-y-3">
                <label className="text-sm font-medium text-slate-300">Configuration Preview</label>
                <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700 space-y-4">
                  {/* Model ID */}
                  <div className="space-y-2">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Model ID</span>
                    <code className="block text-xs text-indigo-300 bg-slate-900/50 p-2 rounded-lg font-mono">
                      {pendingAuthMode === 'AI_STUDIO'
                        ? 'gemini-2.5-flash-native-audio-preview-12-2025'
                        : 'gemini-live-2.5-flash-preview-native-audio-09-2025'}
                    </code>
                  </div>

                  {/* Function Call Config */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Function Calls</span>
                      <div className={`w-1.5 h-1.5 rounded-full ${pendingAuthMode === 'AI_STUDIO' ? 'bg-amber-400' : 'bg-emerald-400'}`} />
                      <span className="text-[10px] text-slate-400">
                        {pendingAuthMode === 'AI_STUDIO' ? 'Non-Blocking' : 'Standard'}
                      </span>
                    </div>
                    <pre className="text-[10px] text-slate-400 bg-slate-900/50 p-2 rounded-lg overflow-x-auto font-mono leading-relaxed">
{pendingAuthMode === 'AI_STUDIO'
  ? `declaration: { ..., "behavior": "NON_BLOCKING" }
response:    { ..., "scheduling": "INTERRUPT" }`
  : `declaration: { ... }
response:    { ... }`}
                    </pre>
                  </div>

                  <p className="text-[10px] text-slate-500">
                    {pendingAuthMode === 'AI_STUDIO'
                      ? 'AI Studio: NON_BLOCKING with scheduling (INTERRUPT, WHEN_IDLE, SILENT)'
                      : 'Vertex AI: Standard async execution'}
                  </p>
                </div>
              </div>

              {/* Current Config Info */}
              {authConfig && (
                <div className="bg-slate-800/50 rounded-xl p-3 border border-slate-700">
                  <p className="text-xs text-slate-400">
                    <span className="font-medium text-slate-300">Current: </span>
                    {authConfig.auth_mode === 'AI_STUDIO' ? (
                      <span className="text-indigo-300">
                        AI Studio {authConfig.has_api_key ? '(API key configured)' : '(no API key)'}
                      </span>
                    ) : (
                      <span className="text-emerald-300">
                        Vertex AI ({authConfig.project_id})
                      </span>
                    )}
                  </p>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="flex gap-3 p-4 border-t border-slate-700 shrink-0">
              <button
                onClick={() => setShowSettings(false)}
                className="flex-1 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={saveAuthConfig}
                disabled={isSavingConfig}
                className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSavingConfig ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast notification */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-indigo-600 text-white px-4 py-2 rounded-full shadow-lg animate-in fade-in slide-in-from-bottom-4 duration-300 flex items-center gap-2">
          <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
          <span className="text-sm font-medium">{toast}</span>
        </div>
      )}
    </div>
  );
};

export default App;