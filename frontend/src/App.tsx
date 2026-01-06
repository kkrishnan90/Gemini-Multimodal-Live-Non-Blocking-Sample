import React, { useState, useRef } from 'react';
import { Mic, MicOff, Settings, Activity, Terminal, CheckCircle2, AlertCircle } from 'lucide-react';

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
  input_transcription?: { text: string, finished: boolean };
  output_transcription?: { text: string, finished: boolean };
}

const App: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [transcripts, setTranscripts] = useState<{ role: string, text: string }[]>([]);
  const [toolLogs, setToolLogs] = useState<{ name: string, args: Record<string, unknown> | undefined, time: string }[]>([]);
  const [status, setStatus] = useState('Disconnected');
  const [systemInstruction, setSystemInstruction] = useState(`You are Julia, an enthusiastic and complimentary travel assistant. 
Your tone is warm, inviting, and always positive. 
You love helping people plan their dream vacations and always find something nice to say about their choices.`);
  
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const isAiSpeakingRef = useRef(false);
  const audioQueueRef = useRef<Float32Array[]>([]);
  const isPlayingRef = useRef(false);

  // Initialize AudioContext only once
  const getAudioContext = () => {
    if (!audioContextRef.current) {
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      audioContextRef.current = new AudioContextClass({ sampleRate: 16000 });
    }
    return audioContextRef.current;
  };

  const processAudioQueue = async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;

    isPlayingRef.current = true;
    isAiSpeakingRef.current = true;
    const context = getAudioContext();
    
    // Get next chunk
    const float32Array = audioQueueRef.current.shift()!;
    const buffer = context.createBuffer(1, float32Array.length, 24000);
    buffer.getChannelData(0).set(float32Array);

    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);
    
    source.onended = () => {
      isPlayingRef.current = false;
      // Process next chunk immediately if available
      if (audioQueueRef.current.length > 0) {
        processAudioQueue();
      } else {
        // Small delay to ensure "speaking" state clears after final chunk
        setTimeout(() => {
           if (audioQueueRef.current.length === 0) {
             isAiSpeakingRef.current = false;
           }
        }, 100);
      }
    };
    
    source.start();
  };

  const updatePersona = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'update_persona',
        instruction: systemInstruction
      }));
      
      setTranscripts(prev => [...prev, { role: 'System', text: 'Updated Persona System Instructions' }]);
    }
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
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          mediaStreamRef.current = stream;
          
          const source = context.createMediaStreamSource(stream);
          const processor = context.createScriptProcessor(512, 1, 1);
          processorRef.current = processor;
          
          processor.onaudioprocess = (e) => {
            if (ws.readyState === WebSocket.OPEN && !isAiSpeakingRef.current) {
              const inputData = e.inputBuffer.getChannelData(0);
              // Convert Float32 to Int16
              const int16Data = new Int16Array(inputData.length);
              for (let i = 0; i < inputData.length; i++) {
                int16Data[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
              }
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
          const updateTranscript = (role: string, text: string) => {
            if (!text || !text.trim()) return;
            setTranscripts(prev => {
              if (prev.length === 0) return [{ role, text }];
              const last = prev[prev.length - 1];
              
              if (last.role === role) {
                // Check if the incoming text is a continuation/refinement
                // User transcriptions are often cumulative, Sophie (parts) are additive fragments
                if (text.startsWith(last.text)) {
                   // Cumulative update (already contains the previous text)
                   return [...prev.slice(0, -1), { role, text }];
                } else if (last.text.endsWith(text)) {
                   // Duplicate fragment at the end, ignore
                   return prev;
                } else {
                   // Additive fragment
                   return [...prev.slice(0, -1), { role, text: last.text + text }];
                }
              }
              // Role switch, start new bubble
              return [...prev, { role, text }];
            });
          };

          if (data.parts) {
            data.parts.forEach(part => {
              if (part.text) updateTranscript('Sophie', part.text);
              if (part.audio) playAudioBase64(part.audio);
            });
          }
          
          if (data.input_transcription?.text) {
             updateTranscript('User', data.input_transcription.text);
          }

          if (data.output_transcription?.text) {
             updateTranscript('Sophie', data.output_transcription.text);
          }

          if (data.interrupted) {
            audioQueueRef.current = [];
            isAiSpeakingRef.current = false;
          }
        } else if (data.type === 'tool_call') {
          setToolLogs(prev => [{
            name: data.name!,
            args: data.args,
            time: new Date().toLocaleTimeString()
          }, ...prev]);
        } else if (data.error) {
          setStatus(`Error: ${data.error}`);
        }
      };

      ws.onclose = () => {
        stopSession();
      };

    } catch (err) {
      console.error('Session start error:', err);
      setStatus('Connection Failed');
    }
  };

  const stopSession = () => {
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
          </div>
        </div>
        <div className="flex items-center gap-2">
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
          <button className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400">
            <Settings size={20} />
          </button>
        </div>
      </header>

      <main className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Transcription Area */}
        <div className="lg:col-span-2 flex flex-col bg-slate-900/30 rounded-3xl border border-slate-800 overflow-hidden">
          <div className="p-4 border-b border-slate-800 bg-slate-900/50 flex items-center gap-2">
            <Terminal size={16} className="text-indigo-400" />
            <span className="text-sm font-semibold uppercase tracking-wider text-slate-400">Live Transcript</span>
          </div>
          <div className="flex-1 p-6 overflow-y-auto flex flex-col gap-4">
            {transcripts.map((t, i) => (
              <div key={i} className={`flex flex-col ${t.role === 'User' ? 'items-end' : 'items-start'}`}>
                <span className="text-[10px] uppercase font-bold text-slate-600 mb-1 ml-1">{t.role}</span>
                <div className={`max-w-[80%] p-4 rounded-2xl ${
                  t.role === 'User' ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-slate-800 text-slate-200 rounded-tl-none'
                }`}>
                  {t.text}
                </div>
              </div>
            ))}
            {transcripts.length === 0 && (
              <div className="h-full flex items-center justify-center text-slate-600 italic">
                Start the session and speak to see the transcript...
              </div>
            )}
          </div>
        </div>

        {/* Side Panel: Tools & Stats */}
        <div className="flex flex-col gap-6">
          {/* System Instruction Editor */}
          <div className="bg-slate-900/30 rounded-3xl border border-slate-800 overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-800 bg-slate-900/50 flex items-center gap-2">
              <Settings size={16} className="text-purple-400" />
              <span className="text-sm font-semibold uppercase tracking-wider text-slate-400">System Instruction</span>
            </div>
            <div className="p-4 flex flex-col gap-3">
              <textarea
                value={systemInstruction}
                onChange={(e) => setSystemInstruction(e.target.value)}
                className="w-full h-32 bg-slate-800/50 border border-slate-700 rounded-xl p-3 text-xs text-slate-300 focus:outline-none focus:ring-2 focus:ring-purple-500/50 resize-none"
                placeholder="Enter system instruction..."
              />
              <button 
                onClick={updatePersona}
                disabled={!isConnected}
                className="bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-xl font-medium transition-all text-xs flex items-center justify-center gap-2"
              >
                Update Persona
              </button>
            </div>
          </div>

          <div className="flex-1 bg-slate-900/30 rounded-3xl border border-slate-800 overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-800 bg-slate-900/50 flex items-center gap-2">
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
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default App;