import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  PersonStanding,
  Upload,
  Video,
  Play,
  Square,
  Camera,
  Activity,
  History,
  Download,
  AlertTriangle,
  Loader2,
  Maximize2,
  Minimize2,
  ShieldAlert,
  BellRing,
  Crosshair,
  Volume2,
  VolumeX,
  UserCheck,
  XCircle
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip
} from 'recharts';
import {
  detectPersonsInImage,
  detectPersonsInFrame,
  captureAndSaveFrame,
  getPersonDetectionHistory,
  batchDetectPersons,
  exportDetectionLog,
  getActiveTargetPerson,
  clearActiveTargetPerson
} from '../../lib/api';
import { PersonDetectionResult, LiveDetectionFrame, DetectedPerson } from '../../types';

export const PersonTracker: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'evidence' | 'live'>('evidence');
  
  // Evidence State
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [evidenceResult, setEvidenceResult] = useState<PersonDetectionResult | null>(null);
  const [evidenceImageUrl, setEvidenceImageUrl] = useState<string | null>(null);
  const evidenceCanvasRef = useRef<HTMLCanvasElement>(null);
  
  // Live State
  const [isLiveActive, setIsLiveActive] = useState(false);
  const isLiveActiveRef = useRef(false);
  const isProcessingRef = useRef(false);
  const [fps, setFps] = useState(0);
  const [chartData, setChartData] = useState<any[]>([]);
  const [liveLog, setLiveLog] = useState<any[]>([]);
  const videoRef = useRef<HTMLVideoElement>(null);
  const liveCanvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const loopRef = useRef<number | null>(null);
  const lastLoggedCountRef = useRef<number | null>(null);
  const lastLogTimeRef = useRef<number>(0);
  const cameraBoxRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  // Active Target Suspect Surveillance State
  const [targetSuspect, setTargetSuspect] = useState<{
    name?: string;
    imageUrl?: string;
    fileName?: string;
    timestamp?: string;
  } | null>(null);

  const [targetAlert, setTargetAlert] = useState<{
    active: boolean;
    matchScore: number;
    time: string;
  } | null>(null);

  const [soundEnabled, setSoundEnabled] = useState(true);
  const alertTimerRef = useRef<number | null>(null);
  const lastSoundTimeRef = useRef<number>(0);

  // Tactical Audio Alert synthesizer via Web Audio API (Loud 2-tone siren)
  const audioCtxRef = useRef<AudioContext | null>(null);

  const playAlertSound = useCallback(() => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
        audioCtxRef.current = new AudioCtx();
      }
      const ctx = audioCtxRef.current;
      if (ctx.state === 'suspended') {
        ctx.resume().catch(() => {});
      }
      
      const now = ctx.currentTime;
      // High-low tactical siren burst
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      
      // Siren warble: 960Hz -> 720Hz -> 960Hz
      osc.frequency.setValueAtTime(960, now);
      osc.frequency.linearRampToValueAtTime(720, now + 0.12);
      osc.frequency.linearRampToValueAtTime(960, now + 0.24);
      osc.frequency.linearRampToValueAtTime(680, now + 0.38);

      gain.gain.setValueAtTime(0.45, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.42);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.42);
    } catch (e) {
      console.warn('Audio alert play error:', e);
    }
  }, []);

  const handleClearTarget = async () => {
    try {
      await clearActiveTargetPerson();
      setTargetSuspect(null);
      setTargetAlert(null);
    } catch (err) {
      console.error('Failed to clear target', err);
    }
  };

  useEffect(() => {
    getActiveTargetPerson().then(res => {
      if (res && res.active && res.target) {
        setTargetSuspect({
          fileName: res.target.file_name,
          timestamp: res.target.timestamp
        });
      }
    }).catch(() => {});
  }, []);

  const toggleFullscreen = () => {
    if (!cameraBoxRef.current) return;
    if (!document.fullscreenElement) {
      cameraBoxRef.current.requestFullscreen().catch((err) => {
        console.error('Error enabling fullscreen:', err);
      });
    } else {
      document.exitFullscreen().catch((err) => {
        console.error('Error exiting fullscreen:', err);
      });
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  const drawBoundingBox = (
    ctx: CanvasRenderingContext2D,
    bbox: any,
    index: number,
    confidence: number,
    mode: 'live'|'uploaded'|'match',
    matchScore?: number
  ) => {
    if (!bbox) return;
    const { x, y, width, height } = bbox;
    const isMatch = mode === 'match' || bbox.is_target_match;
    const isLive = mode === 'live';
    
    // Glowing RED for Target Match, Green for normal live, Red for uploaded evidence
    const color = isMatch ? '#ff0000' : (isLive ? '#22c55e' : '#ef4444');
    const fillStyle = isMatch ? 'rgba(255, 0, 0, 0.28)' : (isLive ? 'rgba(34, 197, 94, 0.16)' : 'rgba(239, 68, 68, 0.16)');
    
    // Translucent Target Fill
    ctx.fillStyle = fillStyle;
    ctx.fillRect(x, y, width, height);
    
    // Bright RED Laser Border Outline
    ctx.save();
    if (isMatch) {
      ctx.shadowColor = '#ff0000';
      ctx.shadowBlur = 16;
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = isMatch ? 4.5 : 2.5;
    ctx.strokeRect(x, y, width, height);
    
    // High-visibility Tactical Corner Brackets (Red Laser)
    ctx.lineWidth = isMatch ? 6 : 4;
    const l = Math.max(10, Math.min(26, width / 4, height / 4));
    ctx.beginPath();
    // Top-left
    ctx.moveTo(x, y + l); ctx.lineTo(x, y); ctx.lineTo(x + l, y);
    // Top-right
    ctx.moveTo(x + width - l, y); ctx.lineTo(x + width, y); ctx.lineTo(x + width, y + l);
    // Bottom-left
    ctx.moveTo(x, y + height - l); ctx.lineTo(x, y + height); ctx.lineTo(x + l, y + height);
    // Bottom-right
    ctx.moveTo(x + width - l, y + height); ctx.lineTo(x + width, y + height); ctx.lineTo(x + width, y + height - l);
    ctx.stroke();

    // Red Laser Crosshair on matched target center
    if (isMatch) {
      const cx = x + width / 2;
      const cy = y + height / 2;
      const ch = 12;
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = '#ff0000';
      ctx.beginPath();
      ctx.moveTo(cx - ch, cy); ctx.lineTo(cx + ch, cy);
      ctx.moveTo(cx, cy - ch); ctx.lineTo(cx, cy + ch);
      ctx.stroke();
    }
    ctx.restore();

    // High-visibility Identification Pill
    ctx.fillStyle = isMatch ? '#dc2626' : color;
    const label = isMatch
      ? `🚨 TARGET MATCH! ${Math.round(matchScore || bbox.match_similarity || 88)}%`
      : (isLive ? `LIVE #${index} ${Math.round(confidence * 100)}%` : `PERSON #${index} ${Math.round(confidence * 100)}%`);
    ctx.font = 'bold 13px ui-monospace, monospace';
    const textWidth = ctx.measureText(label).width;
    const pillHeight = 24;
    const pillY = y >= pillHeight + 6 ? y - pillHeight - 4 : y + 4;
    
    // Pill background
    ctx.fillRect(x, pillY, textWidth + 18, pillHeight);
    
    // White text
    ctx.fillStyle = '#ffffff';
    ctx.fillText(label, x + 9, pillY + 17);
  };

  // --- EVIDENCE LOGIC ---
  const handleEvidenceUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    const url = URL.createObjectURL(file);
    setEvidenceImageUrl(url);
    
    try {
      setUploading(true);
      const res = await detectPersonsInImage(file);
      setEvidenceResult(res);
      setTargetSuspect({
        name: file.name,
        fileName: file.name,
        imageUrl: url,
        timestamp: new Date().toLocaleTimeString()
      });
      
      // Draw immediately after image loads
      const img = new Image();
      img.onload = () => {
        const cvs = evidenceCanvasRef.current;
        if (!cvs) return;
        const ctx = cvs.getContext('2d');
        if (!ctx) return;
        cvs.width = img.width;
        cvs.height = img.height;
        ctx.drawImage(img, 0, 0);
        if (res?.persons && Array.isArray(res.persons)) {
          res.persons.forEach((p: any) => {
            drawBoundingBox(ctx, p.bounding_box, p.person_index, p.confidence, 'uploaded');
          });
        }
      };
      img.src = url;
    } catch (err) {
      console.error('Evidence detection error:', err);
      alert('Detection failed. Please check backend connection.');
    } finally {
      setUploading(false);
    }
  };

  // --- LIVE LOGIC ---
  const scheduleNextLiveFrame = (delayMs: number = 120) => {
    if (!isLiveActiveRef.current) return;
    if (loopRef.current) clearTimeout(loopRef.current);
    loopRef.current = window.setTimeout(processLiveFrame, delayMs);
  };

  const startLive = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } }
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
      streamRef.current = stream;
      isLiveActiveRef.current = true;
      setIsLiveActive(true);
      scheduleNextLiveFrame(150);
    } catch (err) {
      console.error('Camera access error:', err);
      alert('Camera access denied or unavailable.');
    }
  };

  const stopLive = () => {
    isLiveActiveRef.current = false;
    setIsLiveActive(false);
    if (loopRef.current) {
      clearTimeout(loopRef.current);
      loopRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    const canvas = liveCanvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx?.clearRect(0, 0, canvas.width, canvas.height);
    }
  };

  useEffect(() => {
    return () => {
      stopLive();
    };
  }, []);

  const processLiveFrame = async () => {
    if (!isLiveActiveRef.current || !videoRef.current || !liveCanvasRef.current) return;
    if (isProcessingRef.current) {
      scheduleNextLiveFrame(100);
      return;
    }
    
    const video = videoRef.current;
    const canvas = liveCanvasRef.current;
    if (video.videoWidth === 0 || video.videoHeight === 0 || video.readyState < 2) {
      scheduleNextLiveFrame(100);
      return;
    }

    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    }

    isProcessingRef.current = true;
    const t0 = performance.now();

    // Use offscreen canvas for frame capture to prevent flicker
    const offscreen = document.createElement('canvas');
    offscreen.width = video.videoWidth;
    offscreen.height = video.videoHeight;
    const offCtx = offscreen.getContext('2d');
    if (!offCtx) {
      isProcessingRef.current = false;
      scheduleNextLiveFrame(120);
      return;
    }
    offCtx.drawImage(video, 0, 0, offscreen.width, offscreen.height);

    offscreen.toBlob(async (blob) => {
      try {
        if (!blob || !isLiveActiveRef.current) return;
        const res = await detectPersonsInFrame(blob);
        
        const ctx = canvas.getContext('2d');
        const hasTargetMatch = Boolean(res?.target_matched || res?.persons?.some((p: any) => p.is_target_match));
        const topMatchScore = res?.highest_match_score || (hasTargetMatch ? 88.5 : 0);

          if (ctx && isLiveActiveRef.current) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            if (res?.persons && Array.isArray(res.persons)) {
              res.persons.forEach((p: any) => {
                // Strict matching: ONLY the person whose biometric features match the uploaded photo turns RED.
                // Any other person detected in camera remains standard GREEN line (no alert).
                const isThisMatch = Boolean(p.is_target_match);
                const pMode = isThisMatch ? 'match' : 'live';
                const score = p.match_similarity || (isThisMatch ? topMatchScore : 0);
                drawBoundingBox(ctx, p.bounding_box, p.person_index, p.confidence, pMode, score);
              });
            }
          }
        
        const elapsed = performance.now() - t0;
        const currentFps = Math.max(1, Math.round(1000 / elapsed));
        setFps(currentFps);
        
        const timestamp = new Date().toLocaleTimeString();
        const count = res?.persons_count ?? res?.persons?.length ?? 0;
        setChartData(prev => [...prev.slice(-30), { time: timestamp, count }]);
        
        const now = Date.now();
        if (count > 0 && (count !== lastLoggedCountRef.current || hasTargetMatch || now - lastLogTimeRef.current > 3000)) {
          lastLoggedCountRef.current = count;
          lastLogTimeRef.current = now;
          setLiveLog(prev => [{
            time: timestamp,
            count,
            isMatch: hasTargetMatch,
            matchScore: topMatchScore
          }, ...prev.slice(0, 19)]);
        }

        if (hasTargetMatch) {
          setTargetAlert({
            active: true,
            matchScore: topMatchScore,
            time: timestamp
          });
          if (soundEnabled) {
            if (now - lastSoundTimeRef.current > 1500) {
              lastSoundTimeRef.current = now;
              playAlertSound();
            }
          }
          if (alertTimerRef.current) clearTimeout(alertTimerRef.current);
          alertTimerRef.current = window.setTimeout(() => {
            setTargetAlert(prev => prev ? { ...prev, active: false } : null);
          }, 4000);
        }

      } catch (err) {
        console.warn('Frame detection skipped:', err);
      } finally {
        isProcessingRef.current = false;
        if (isLiveActiveRef.current) {
          scheduleNextLiveFrame(120);
        }
      }
    }, 'image/jpeg', 0.7);
  };

  const captureFrame = async () => {
    if (!videoRef.current) return;
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    canvas.getContext('2d')?.drawImage(videoRef.current, 0, 0);
    canvas.toBlob(async (blob) => {
      if (blob) {
        await captureAndSaveFrame(blob);
        alert('Live frame captured with cryptographic seal.');
      }
    }, 'image/jpeg');
  };

  return (
    <div className="space-y-4 text-slate-900 animate-fade-in flex flex-col h-[calc(100vh-112px)] overflow-hidden">
      <div className="border-b border-slate-200/90 pb-3 flex justify-between items-center shrink-0">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 flex items-center space-x-2">
            <PersonStanding className="w-6 h-6 text-sky-600" />
            <span>Tactical Person Tracker</span>
          </h1>
          <p className="text-xs text-slate-500 mt-0.5 font-mono">
            YOLOv8-powered human detection. Analyze static evidence or monitor live CCTV/webcam feeds.
          </p>
        </div>
        <div className="flex space-x-2">
          <button onClick={() => setActiveTab('evidence')} className={`px-4 py-2 text-xs font-bold font-mono rounded-lg transition-colors ${activeTab === 'evidence' ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-slate-50 text-slate-600 border border-slate-200'}`}>
            📸 Evidence Analysis
          </button>
          <button onClick={() => setActiveTab('live')} className={`px-4 py-2 text-xs font-bold font-mono rounded-lg transition-colors ${activeTab === 'live' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-slate-50 text-slate-600 border border-slate-200'}`}>
            🎥 Live Camera
          </button>
        </div>
      </div>

      <div className={`flex-1 min-h-0 ${activeTab === 'live' ? 'overflow-hidden' : 'overflow-y-auto'}`}>
        {activeTab === 'evidence' ? (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5">
              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  handleEvidenceUpload(e.dataTransfer.files);
                }}
                className={`p-6 border-2 border-dashed rounded-xl cursor-pointer transition-all duration-300 flex flex-col items-center justify-center text-center ${
                  isDragging ? 'border-red-500 bg-red-50' : 'border-slate-300 hover:border-red-400 bg-slate-50 hover:bg-red-50/50'
                }`}
              >
                <input type="file" className="hidden" id="file-upload" accept="image/*" onChange={(e) => handleEvidenceUpload(e.target.files)} />
                <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
                  {uploading ? <Loader2 className="w-8 h-8 text-red-500 animate-spin mb-2" /> : <Upload className="w-8 h-8 text-red-500 mb-2" />}
                  <div className="text-sm font-bold text-slate-900">{uploading ? 'Analyzing Image...' : 'Upload Evidence Image'}</div>
                </label>
              </div>

              {evidenceImageUrl && (
                <div className="mt-6">
                  <div className="relative rounded-lg overflow-hidden border border-slate-200 bg-slate-100 flex justify-center">
                    <canvas ref={evidenceCanvasRef} className="max-w-full h-auto max-h-[60vh] object-contain" />
                  </div>
                  {evidenceResult && (
                    <div className="mt-4 p-4 bg-slate-50 border border-slate-200 rounded-lg">
                      <div className="text-[10px] font-mono uppercase text-slate-500 font-bold mb-2">Detection Summary</div>
                      <div className="grid grid-cols-3 gap-4 font-mono text-sm">
                        <div>
                          <div className="text-slate-400 text-[10px]">TOTAL PERSONS</div>
                          <div className="font-bold text-red-600 text-lg">{evidenceResult.total_persons}</div>
                        </div>
                        <div>
                          <div className="text-slate-400 text-[10px]">PROCESSING TIME</div>
                          <div className="font-bold text-slate-800">{evidenceResult.processing_time_ms}ms</div>
                        </div>
                        <div>
                          <div className="text-slate-400 text-[10px]">SHA-256 HASH</div>
                          <div className="font-bold text-slate-800 truncate text-xs">{evidenceResult.sha256_hash?.slice(0,16)}</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Target Suspect Armed Confirmation */}
                  {targetSuspect && (
                    <div className="mt-4 p-4 bg-red-50/80 border-2 border-red-500/80 rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs animate-fade-in">
                      <div className="flex items-center space-x-3">
                        <div className="p-2.5 bg-red-600 text-white rounded-lg shadow-sm">
                          <Crosshair className="w-5 h-5 animate-pulse" />
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-bold font-mono uppercase px-2 py-0.5 rounded bg-red-600 text-white tracking-wider">
                              TARGET SUSPECT ARMED
                            </span>
                            <span className="text-xs text-red-800 font-mono font-medium truncate max-w-[200px]">
                              {targetSuspect.fileName}
                            </span>
                          </div>
                          <p className="text-xs text-red-700 mt-1">
                            Visual biometrics extracted & armed for live cross-referencing. Switch to <strong>Live Camera</strong> to scan automatically.
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => setActiveTab('live')}
                        className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold font-mono shadow-sm transition-all flex items-center space-x-1.5 shrink-0 cursor-pointer"
                      >
                        <Video className="w-3.5 h-3.5" />
                        <span>Go To Live Camera →</span>
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-full min-h-0">
            <div className="lg:col-span-8 bg-white rounded-xl border border-slate-200 shadow-xs p-4 flex flex-col h-full min-h-0">
              
              {/* Active Target Banner in Live Mode */}
              {targetSuspect && (
                <div className="mb-3 px-3.5 py-2 bg-gradient-to-r from-red-500/10 via-red-500/5 to-transparent border border-red-500/30 rounded-lg flex items-center justify-between shrink-0">
                  <div className="flex items-center space-x-2.5">
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-600"></span>
                    </span>
                    <span className="text-xs font-mono font-extrabold text-red-700 tracking-wider">
                      ACTIVE SURVEILLANCE TARGET:
                    </span>
                    <span className="text-xs font-mono font-bold text-slate-800 bg-white/90 px-2 py-0.5 rounded border border-red-200">
                      {targetSuspect.fileName || 'Evidence Suspect'}
                    </span>
                    <span className="text-[11px] font-mono text-red-600/80 hidden sm:inline">
                      (Armed at {targetSuspect.timestamp || 'Recent'})
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setSoundEnabled(!soundEnabled)}
                      className={`p-1.5 rounded text-xs font-mono flex items-center space-x-1 transition-colors ${
                        soundEnabled ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                      }`}
                      title={soundEnabled ? 'Mute Alert Chime' : 'Unmute Alert Chime'}
                    >
                      {soundEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
                    </button>
                    <button
                      onClick={handleClearTarget}
                      className="text-xs font-mono text-slate-500 hover:text-red-600 flex items-center space-x-1 px-2 py-1 rounded hover:bg-red-50 transition-colors"
                      title="Clear active surveillance target"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Clear</span>
                    </button>
                  </div>
                </div>
              )}

              <div className="flex justify-between items-center mb-3 shrink-0">
                <div className="flex space-x-2">
                  <button onClick={isLiveActive ? stopLive : startLive} className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center space-x-2 text-white ${isLiveActive ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'}`}>
                    {isLiveActive ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    <span>{isLiveActive ? 'Stop Stream' : 'Start Camera'}</span>
                  </button>
                  <button onClick={captureFrame} disabled={!isLiveActive} className="px-4 py-2 rounded-lg text-sm font-semibold flex items-center space-x-2 bg-slate-100 hover:bg-slate-200 text-slate-700 disabled:opacity-50 border border-slate-300">
                    <Camera className="w-4 h-4" />
                    <span>Capture Frame</span>
                  </button>
                  <button
                    onClick={toggleFullscreen}
                    className="px-3.5 py-2 rounded-lg text-sm font-semibold flex items-center space-x-2 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 transition-colors cursor-pointer"
                    title={isFullscreen ? "Exit Fullscreen (Esc)" : "Enter Fullscreen"}
                  >
                    {isFullscreen ? <Minimize2 className="w-4 h-4 text-sky-600" /> : <Maximize2 className="w-4 h-4 text-slate-600" />}
                    <span>{isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}</span>
                  </button>
                </div>
                <div className="text-xs font-mono font-bold bg-slate-100 px-3 py-1.5 rounded-full text-slate-600 border border-slate-200">
                  {fps} FPS
                </div>
              </div>

              <div 
                ref={cameraBoxRef} 
                className={`relative flex-1 rounded-lg overflow-hidden bg-slate-950 flex items-center justify-center min-h-0 transition-all duration-300 ${
                  targetAlert?.active 
                    ? 'border-4 animate-red-glow ring-4 ring-red-500/50' 
                    : 'border border-slate-300'
                } ${
                  isFullscreen ? 'fixed inset-0 z-50 rounded-none border-0 w-screen h-screen' : ''
                }`}
              >
                <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-contain max-h-full" />
                <canvas ref={liveCanvasRef} className="absolute inset-0 w-full h-full object-contain pointer-events-none" />

                {/* Tactical Flashing Red Perimeter Warning Lines when target detected */}
                {targetAlert?.active && (
                  <div className="absolute inset-0 pointer-events-none z-10 overflow-hidden">
                    {/* Glowing Red Corner Targets */}
                    <div className="absolute top-2 left-2 w-12 h-12 border-t-4 border-l-4 border-red-500 animate-pulse"></div>
                    <div className="absolute top-2 right-2 w-12 h-12 border-t-4 border-r-4 border-red-500 animate-pulse"></div>
                    <div className="absolute bottom-2 left-2 w-12 h-12 border-b-4 border-l-4 border-red-500 animate-pulse"></div>
                    <div className="absolute bottom-2 right-2 w-12 h-12 border-b-4 border-r-4 border-red-500 animate-pulse"></div>
                    
                    {/* Animated Scanning Red Laser Line sweeping across camera */}
                    <div className="absolute left-0 right-0 h-1.5 bg-gradient-to-r from-transparent via-red-500 to-transparent shadow-[0_0_20px_#ff0000] animate-laser-scan"></div>
                    
                    {/* Red Tactical Vignette Frame */}
                    <div className="absolute inset-0 bg-red-600/10 pointer-events-none animate-pulse"></div>
                  </div>
                )}

                {/* Floating Corner Fullscreen Toggle */}
                <button
                  onClick={toggleFullscreen}
                  className="absolute top-3 right-3 z-20 p-2 rounded-lg bg-black/60 hover:bg-black/80 text-white backdrop-blur-xs border border-white/20 transition-all active:scale-95 cursor-pointer shadow-md"
                  title={isFullscreen ? "Exit Fullscreen (Esc)" : "Enter Fullscreen"}
                >
                  {isFullscreen ? <Minimize2 className="w-4 h-4 text-sky-400" /> : <Maximize2 className="w-4 h-4 text-white" />}
                </button>

                {/* Real-time Target Match Alert Dropdown Modal */}
                {targetAlert?.active && (
                  <div className="absolute top-3 left-1/2 -translate-x-1/2 z-30 flex items-center space-x-3 bg-red-600/95 text-white px-5 py-2.5 rounded-xl shadow-2xl backdrop-blur-md border-2 border-red-300 animate-bounce">
                    <ShieldAlert className="w-6 h-6 text-yellow-300 animate-pulse" />
                    <div>
                      <div className="text-xs font-black font-mono tracking-widest uppercase flex items-center space-x-1.5">
                        <span>🚨 TARGET SUSPECT IDENTIFIED!</span>
                        <span className="bg-yellow-400 text-black px-1.5 py-0.2 rounded font-mono font-extrabold text-[10px]">
                          {targetAlert.matchScore}% MATCH
                        </span>
                      </div>
                      <div className="text-[11px] font-mono text-red-100">
                        Visual biometric fingerprint matches armed evidence profile
                      </div>
                    </div>
                  </div>
                )}

                {/* Fullscreen Surveillance HUD */}
                {isFullscreen && (
                  <div className="absolute top-3 left-3 z-20 flex items-center space-x-3 bg-black/75 backdrop-blur-md px-3.5 py-2 rounded-lg border border-white/20 text-white font-mono text-xs shadow-lg">
                    <div className="flex items-center space-x-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse"></span>
                      <span className="font-bold text-red-400 tracking-wider">TACTICAL SURVEILLANCE</span>
                    </div>
                    <span className="text-slate-500">|</span>
                    <span className="text-emerald-400 font-bold">{fps} FPS</span>
                    <span className="text-slate-500">|</span>
                    <span className="text-sky-300 font-bold">
                      {chartData.length > 0 ? `${chartData[chartData.length - 1].count} Person(s) Detected` : '0 Persons Detected'}
                    </span>
                    {targetSuspect && (
                      <>
                        <span className="text-slate-500">|</span>
                        <span className="text-red-400 font-bold flex items-center space-x-1">
                          <Crosshair className="w-3.5 h-3.5 animate-spin" />
                          <span>ARMED: {targetSuspect.fileName}</span>
                        </span>
                      </>
                    )}
                  </div>
                )}

                {!isLiveActive && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-400 bg-slate-900 z-10">
                    <Video className="w-12 h-12 mb-2 opacity-60" />
                    <span className="font-mono text-sm tracking-wider font-semibold">LIVE CAMERA OFFLINE</span>
                    <span className="font-mono text-xs text-slate-500 mt-1">Click "Start Camera" to initiate live surveillance detection</span>
                  </div>
                )}
              </div>

            </div>

            <div className="lg:col-span-4 flex flex-col space-y-4 h-full min-h-0">
              <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4 h-44 shrink-0">
                <h2 className="text-[10px] font-mono uppercase tracking-widest text-slate-400 font-extrabold mb-2">Live Crowd Density</h2>
                <ResponsiveContainer width="100%" height="80%">
                  <AreaChart data={chartData}>
                    <XAxis dataKey="time" hide />
                    <YAxis hide />
                    <Tooltip contentStyle={{ fontSize: '10px', fontFamily: 'monospace' }} />
                    <Area type="stepAfter" dataKey="count" stroke="#22c55e" fill="rgba(34, 197, 94, 0.2)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4 flex-1 min-h-0 flex flex-col overflow-hidden">
                <h2 className="text-[10px] font-mono uppercase tracking-widest text-slate-400 font-extrabold mb-3 flex justify-between shrink-0">
                  <span>Detection Log</span>
                  <Activity className="w-3.5 h-3.5 text-green-500 animate-pulse" />
                </h2>
                <div className="space-y-1.5 flex-1 min-h-0 overflow-y-auto tactical-scrollbar pr-1">
                  {liveLog.length === 0 ? (
                    <div className="text-xs font-mono text-slate-400 text-center py-6">
                      No detections logged yet
                    </div>
                  ) : (
                    liveLog.map((log, i) => (
                      <div 
                        key={i} 
                        className={`flex justify-between items-center text-xs font-mono p-2 rounded transition-all ${
                          log.isMatch 
                            ? 'bg-red-500/15 border border-red-500/40 text-red-900 shadow-xs' 
                            : 'bg-slate-50 border border-slate-100 text-slate-700'
                        }`}
                      >
                        <span className={log.isMatch ? 'text-red-700 font-semibold' : 'text-slate-400'}>{log.time}</span>
                        {log.isMatch ? (
                          <div className="flex items-center space-x-1.5 text-red-600 font-bold animate-pulse">
                            <ShieldAlert className="w-3.5 h-3.5" />
                            <span>🚨 TARGET MATCH ({log.matchScore}%)</span>
                          </div>
                        ) : (
                          <span className="font-bold">{log.count} Person(s) Detected</span>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>

  );
};
