/**
 * Audio Engine - Handles recording, playback, and sound generation.
 */

class AudioEngine {
    constructor() {
        this.audioContext = null;
        this.mediaStream = null;
        this.mediaRecorder = null;
        this.analyser = null;
        this.recordedChunks = [];
        this.recordedBuffer = null;
        this.isRecording = false;
        this.startTime = 0;
    }

    async init() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }

    async startRecording() {
        if (!this.audioContext) await this.init();
        
        // Resume context if suspended (browser autoplay policy)
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }

        this.recordedChunks = [];
        
        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Create analyser for visualization
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 2048;
            source.connect(this.analyser);
            
            // Setup MediaRecorder
            this.mediaRecorder = new MediaRecorder(this.mediaStream);
            this.mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    this.recordedChunks.push(e.data);
                }
            };
            
            this.mediaRecorder.onstop = async () => {
                const blob = new Blob(this.recordedChunks, { type: 'audio/webm' });
                const arrayBuffer = await blob.arrayBuffer();
                this.recordedBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
            };

            this.mediaRecorder.start(100); // Collect data every 100ms
            this.isRecording = true;
            this.startTime = Date.now();
            
            return true;
        } catch (err) {
            console.error('Error starting recording:', err);
            return false;
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.isRecording = false;
        }
    }

    playRecording() {
        if (!this.recordedBuffer) return;
        
        const source = this.audioContext.createBufferSource();
        source.buffer = this.recordedBuffer;
        source.connect(this.audioContext.destination);
        source.start();
    }

    getAnalyserData() {
        if (!this.analyser) return null;
        
        const bufferLength = this.analyser.frequencyBinCount;
        const timeData = new Uint8Array(bufferLength);
        const freqData = new Uint8Array(bufferLength);
        
        this.analyser.getByteTimeDomainData(timeData);
        this.analyser.getByteFrequencyData(freqData);
        
        return { timeData, freqData, bufferLength };
    }

    getRecordingDuration() {
        if (!this.isRecording) return 0;
        return (Date.now() - this.startTime) / 1000;
    }

    /**
     * Generate a sample sound based on an AlarmProfile definition.
     * @param {Array} segments - Array of segment objects
     * @param {number} cycles - Number of times to repeat the pattern
     */
    generateSound(segments, cycles = 1) {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        
        const sampleRate = this.audioContext.sampleRate;
        let totalDuration = 0;
        
        // Calculate total duration
        for (let c = 0; c < cycles; c++) {
            for (const seg of segments) {
                // Use midpoint of duration range
                const dur = (seg.durationMin + seg.durationMax) / 2;
                totalDuration += dur;
            }
        }
        
        // Create buffer
        const buffer = this.audioContext.createBuffer(1, Math.ceil(sampleRate * totalDuration), sampleRate);
        const data = buffer.getChannelData(0);
        
        let sampleIndex = 0;
        
        for (let c = 0; c < cycles; c++) {
            for (const seg of segments) {
                // Random duration within range
                const duration = seg.durationMin + Math.random() * (seg.durationMax - seg.durationMin);
                const numSamples = Math.floor(sampleRate * duration);
                
                if (seg.type === 'tone') {
                    // Random frequency within range
                    const freq = seg.freqMin + Math.random() * (seg.freqMax - seg.freqMin);
                    
                    for (let i = 0; i < numSamples && sampleIndex < data.length; i++) {
                        // Simple sine wave with envelope
                        const t = i / sampleRate;
                        const envelope = Math.min(1, Math.min(i / (sampleRate * 0.01), (numSamples - i) / (sampleRate * 0.01)));
                        data[sampleIndex++] = Math.sin(2 * Math.PI * freq * t) * 0.5 * envelope;
                    }
                } else {
                    // Silence
                    for (let i = 0; i < numSamples && sampleIndex < data.length; i++) {
                        data[sampleIndex++] = 0;
                    }
                }
            }
        }
        
        // Play the generated sound
        const source = this.audioContext.createBufferSource();
        source.buffer = buffer;
        source.connect(this.audioContext.destination);
        source.start();
        
        return buffer;
    }

    /**
     * Analyze recorded audio and extract segments for auto-tuning.
     * @returns {Object} Analysis result with detected segments
     */
    analyzeRecording() {
        if (!this.recordedBuffer) {
            return { segments: [], warnings: ['No recording available'] };
        }

        const audioData = this.recordedBuffer.getChannelData(0);
        const sampleRate = this.recordedBuffer.sampleRate;
        const chunkSize = 2048;
        
        // Parameters
        const silenceThreshold = 0.02;
        const minSegmentDuration = 0.05;
        
        const segments = [];
        let currentType = null;
        let segmentStart = 0;
        let freqHistory = [];
        
        // Process in chunks
        for (let i = 0; i < audioData.length - chunkSize; i += chunkSize) {
            const chunk = audioData.slice(i, i + chunkSize);
            const timestamp = i / sampleRate;
            
            // Calculate RMS
            let sum = 0;
            for (let j = 0; j < chunk.length; j++) {
                sum += chunk[j] * chunk[j];
            }
            const rms = Math.sqrt(sum / chunk.length);
            
            if (rms < silenceThreshold) {
                // Silence
                if (currentType === 'tone') {
                    const avgFreq = freqHistory.length > 0 
                        ? freqHistory.reduce((a, b) => a + b, 0) / freqHistory.length 
                        : 0;
                    segments.push({
                        type: 'tone',
                        startTime: segmentStart,
                        endTime: timestamp,
                        frequency: avgFreq,
                        duration: timestamp - segmentStart
                    });
                    freqHistory = [];
                    segmentStart = timestamp;
                    currentType = 'silence';
                } else if (currentType === null) {
                    currentType = 'silence';
                    segmentStart = timestamp;
                }
            } else {
                // Potential tone - estimate frequency using zero-crossing
                const freq = this._estimateFrequency(chunk, sampleRate);
                
                if (currentType === 'silence') {
                    segments.push({
                        type: 'silence',
                        startTime: segmentStart,
                        endTime: timestamp,
                        duration: timestamp - segmentStart
                    });
                    segmentStart = timestamp;
                    currentType = 'tone';
                    freqHistory = [freq];
                } else if (currentType === 'tone') {
                    freqHistory.push(freq);
                } else {
                    currentType = 'tone';
                    segmentStart = timestamp;
                    freqHistory = [freq];
                }
            }
        }
        
        // Close final segment
        const finalTime = audioData.length / sampleRate;
        if (currentType === 'tone' && freqHistory.length > 0) {
            const avgFreq = freqHistory.reduce((a, b) => a + b, 0) / freqHistory.length;
            segments.push({
                type: 'tone',
                startTime: segmentStart,
                endTime: finalTime,
                frequency: avgFreq,
                duration: finalTime - segmentStart
            });
        } else if (currentType === 'silence') {
            segments.push({
                type: 'silence',
                startTime: segmentStart,
                endTime: finalTime,
                duration: finalTime - segmentStart
            });
        }
        
        // Filter out very short segments
        const filtered = segments.filter(s => s.duration >= minSegmentDuration);
        
        // Generate proposed profile segments
        const proposedSegments = this._generateProfileFromSegments(filtered);
        
        return {
            rawSegments: filtered,
            proposedSegments: proposedSegments,
            totalDuration: finalTime,
            warnings: filtered.length < 2 ? ['Very few segments detected. Try recording a longer sample.'] : []
        };
    }

    _estimateFrequency(chunk, sampleRate) {
        // Simple zero-crossing frequency estimation
        let crossings = 0;
        for (let i = 1; i < chunk.length; i++) {
            if ((chunk[i] >= 0 && chunk[i - 1] < 0) || (chunk[i] < 0 && chunk[i - 1] >= 0)) {
                crossings++;
            }
        }
        return (crossings / 2) * (sampleRate / chunk.length);
    }

    _generateProfileFromSegments(segments) {
        const proposed = [];
        
        for (const seg of segments) {
            if (seg.type === 'tone') {
                proposed.push({
                    type: 'tone',
                    freqMin: Math.round(seg.frequency * 0.95),
                    freqMax: Math.round(seg.frequency * 1.05),
                    durationMin: Math.round(seg.duration * 0.8 * 100) / 100,
                    durationMax: Math.round(seg.duration * 1.2 * 100) / 100
                });
            } else {
                proposed.push({
                    type: 'silence',
                    freqMin: 0,
                    freqMax: 0,
                    durationMin: Math.round(seg.duration * 0.8 * 100) / 100,
                    durationMax: Math.round(seg.duration * 1.2 * 100) / 100
                });
            }
        }
        
        return proposed;
    }
}

// Export as global
window.AudioEngine = AudioEngine;
