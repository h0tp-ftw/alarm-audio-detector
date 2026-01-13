/**
 * Visualizer - Handles drawing waveforms, spectrograms, and event timelines.
 * Updated with Catppuccin Mocha color palette for cohesive aesthetics.
 */

class Visualizer {
    constructor(waveformCanvas, spectrogramCanvas, eventsCanvas) {
        this.waveformCtx = waveformCanvas.getContext('2d');
        this.spectrogramCtx = spectrogramCanvas.getContext('2d');
        this.eventsCtx = eventsCanvas.getContext('2d');
        
        this.waveformCanvas = waveformCanvas;
        this.spectrogramCanvas = spectrogramCanvas;
        this.eventsCanvas = eventsCanvas;
        
        // Spectrogram history
        this.spectrogramHistory = [];
        this.maxHistoryLength = 200;
        
        // Detected events for display
        this.detectedEvents = [];
        
        // Catppuccin Mocha color palette
        this.colors = {
            // Canvas backgrounds
            bg: '#11111b',          // crust
            bgAlt: '#181825',       // mantle
            
            // Waveform
            waveform: '#cba6f7',    // mauve
            waveformGlow: 'rgba(203, 166, 247, 0.3)',
            
            // Spectrogram gradient
            spectrogramColors: [
                '#11111b',          // crust (low)
                '#313244',          // surface0
                '#585b70',          // surface2
                '#cba6f7',          // mauve
                '#f5c2e7'           // pink (high)
            ],
            
            // Events
            eventTone: '#a6e3a1',   // green
            eventToneAlt: '#94e2d5', // teal
            eventSilence: '#45475a', // surface1
            
            // Text and grid
            text: '#a6adc8',        // subtext0
            textBright: '#cdd6f4',  // text
            grid: '#45475a',        // surface1
            gridSubtle: '#313244',  // surface0
            
            // Accents
            accent: '#89b4fa',      // blue
            accentAlt: '#74c7ec',   // sapphire
            pink: '#f5c2e7',
            peach: '#fab387',
            yellow: '#f9e2af',
            red: '#f38ba8'
        };
    }

    drawWaveform(timeData, bufferLength) {
        const ctx = this.waveformCtx;
        const width = this.waveformCanvas.width;
        const height = this.waveformCanvas.height;
        
        // Clear with gradient background
        const bgGrad = ctx.createLinearGradient(0, 0, 0, height);
        bgGrad.addColorStop(0, this.colors.bg);
        bgGrad.addColorStop(1, this.colors.bgAlt);
        ctx.fillStyle = bgGrad;
        ctx.fillRect(0, 0, width, height);
        
        // Draw subtle grid lines
        ctx.strokeStyle = this.colors.gridSubtle;
        ctx.lineWidth = 1;
        for (let i = 0; i < 5; i++) {
            const y = (height / 4) * i;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
        
        // Draw center line (brighter)
        ctx.strokeStyle = this.colors.grid;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, height / 2);
        ctx.lineTo(width, height / 2);
        ctx.stroke();
        
        // Draw waveform with glow effect
        ctx.shadowColor = this.colors.waveformGlow;
        ctx.shadowBlur = 12;
        ctx.strokeStyle = this.colors.waveform;
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.beginPath();
        
        const sliceWidth = width / bufferLength;
        let x = 0;
        
        for (let i = 0; i < bufferLength; i++) {
            const v = timeData[i] / 128.0;
            const y = (v * height) / 2;
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
            x += sliceWidth;
        }
        
        ctx.stroke();
        ctx.shadowBlur = 0;
    }

    drawSpectrogram(freqData, bufferLength) {
        const ctx = this.spectrogramCtx;
        const width = this.spectrogramCanvas.width;
        const height = this.spectrogramCanvas.height;
        
        // Add current frame to history
        this.spectrogramHistory.push(new Uint8Array(freqData));
        if (this.spectrogramHistory.length > this.maxHistoryLength) {
            this.spectrogramHistory.shift();
        }
        
        // Clear canvas
        ctx.fillStyle = this.colors.bg;
        ctx.fillRect(0, 0, width, height);
        
        const colWidth = width / this.maxHistoryLength;
        const rowHeight = height / 128; // Use lower half of frequency bins
        
        for (let col = 0; col < this.spectrogramHistory.length; col++) {
            const frame = this.spectrogramHistory[col];
            
            for (let row = 0; row < 128; row++) {
                const value = frame[row];
                const intensity = value / 255;
                
                // Catppuccin-inspired gradient: crust -> surface -> mauve -> pink
                let r, g, b;
                if (intensity < 0.25) {
                    // crust to surface0
                    const t = intensity / 0.25;
                    r = Math.floor(17 + (49 - 17) * t);
                    g = Math.floor(17 + (50 - 17) * t);
                    b = Math.floor(27 + (68 - 27) * t);
                } else if (intensity < 0.5) {
                    // surface0 to surface2
                    const t = (intensity - 0.25) / 0.25;
                    r = Math.floor(49 + (88 - 49) * t);
                    g = Math.floor(50 + (91 - 50) * t);
                    b = Math.floor(68 + (112 - 68) * t);
                } else if (intensity < 0.75) {
                    // surface2 to mauve
                    const t = (intensity - 0.5) / 0.25;
                    r = Math.floor(88 + (203 - 88) * t);
                    g = Math.floor(91 + (166 - 91) * t);
                    b = Math.floor(112 + (247 - 112) * t);
                } else {
                    // mauve to pink
                    const t = (intensity - 0.75) / 0.25;
                    r = Math.floor(203 + (245 - 203) * t);
                    g = Math.floor(166 + (194 - 166) * t);
                    b = Math.floor(247 + (231 - 247) * t);
                }
                
                ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
                ctx.fillRect(
                    col * colWidth,
                    height - (row + 1) * rowHeight,
                    colWidth + 1,
                    rowHeight + 1
                );
            }
        }
        
        // Draw frequency labels with better styling
        ctx.fillStyle = this.colors.text;
        ctx.font = '500 10px Inter, sans-serif';
        ctx.fillText('0Hz', 8, height - 8);
        ctx.fillText('10kHz', 8, 18);
    }

    drawEvents(events, duration) {
        const ctx = this.eventsCtx;
        const width = this.eventsCanvas.width;
        const height = this.eventsCanvas.height;
        
        // Reserve space for time axis
        const axisHeight = 18;
        const plotHeight = height - axisHeight;
        
        // Clear with gradient
        const bgGrad = ctx.createLinearGradient(0, 0, 0, height);
        bgGrad.addColorStop(0, this.colors.bg);
        bgGrad.addColorStop(1, this.colors.bgAlt);
        ctx.fillStyle = bgGrad;
        ctx.fillRect(0, 0, width, height);
        
        if (!events || events.length === 0 || duration === 0) {
            ctx.fillStyle = this.colors.text;
            ctx.font = '500 12px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('No events detected yet', width / 2, plotHeight / 2 + 4);
            return;
        }
        
        const pixelsPerSecond = width / duration;
        
        // Draw events
        for (const event of events) {
            const x = event.timestamp * pixelsPerSecond;
            const w = event.duration * pixelsPerSecond;
            
            if (event.type === 'tone') {
                // Draw tone event with rounded corners and glow
                ctx.shadowColor = 'rgba(166, 227, 161, 0.4)';
                ctx.shadowBlur = 8;
                ctx.fillStyle = this.colors.eventTone;
                this.roundRect(ctx, x, 6, Math.max(w - 2, 4), plotHeight - 12, 4);
                ctx.fill();
                ctx.shadowBlur = 0;
                
                // Frequency label
                ctx.fillStyle = this.colors.bg;
                ctx.font = '600 9px Inter, sans-serif';
                ctx.textAlign = 'center';
                if (w > 25) {
                    ctx.fillText(`${Math.round(event.frequency)}Hz`, x + w/2, plotHeight/2 + 2);
                }
            } else {
                ctx.fillStyle = this.colors.eventSilence;
                this.roundRect(ctx, x, 14, Math.max(w - 2, 4), plotHeight - 28, 4);
                ctx.fill();
            }
        }
        
        // Draw time axis
        this.drawTimeAxis(ctx, width, height, plotHeight, duration);
    }

    /**
     * Draw a time axis at the bottom of the canvas
     */
    drawTimeAxis(ctx, width, height, plotHeight, duration) {
        const axisY = plotHeight + 2;
        
        // Axis line
        ctx.strokeStyle = this.colors.grid;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, axisY);
        ctx.lineTo(width, axisY);
        ctx.stroke();
        
        // Calculate nice tick intervals
        const targetTicks = 8;
        const rawInterval = duration / targetTicks;
        const niceIntervals = [0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10];
        const interval = niceIntervals.find(i => i >= rawInterval) || rawInterval;
        
        ctx.fillStyle = this.colors.text;
        ctx.font = '500 9px Inter, sans-serif';
        ctx.textAlign = 'center';
        
        const pixelsPerSecond = width / duration;
        
        for (let t = 0; t <= duration; t += interval) {
            const x = t * pixelsPerSecond;
            
            // Tick mark
            ctx.strokeStyle = this.colors.grid;
            ctx.beginPath();
            ctx.moveTo(x, axisY);
            ctx.lineTo(x, axisY + 4);
            ctx.stroke();
            
            // Time label
            const label = t < 1 ? `${(t * 1000).toFixed(0)}ms` : `${t.toFixed(1)}s`;
            ctx.fillText(label, x, height - 2);
        }
    }

    /**
     * Draw a visual representation of segments from the ruleset.
     * @param {Array} segments - Array of segment objects
     * @param {number} cycles - Number of times to repeat the pattern
     * @param {number} playheadProgress - Optional 0-1 value for playhead position
     */
    drawSegmentPreview(segments, cycles = 1, playheadProgress = null) {
        const ctx = this.eventsCtx;
        const width = this.eventsCanvas.width;
        const height = this.eventsCanvas.height;
        
        // Reserve space for time axis
        const axisHeight = 18;
        const plotHeight = height - axisHeight;
        
        // Clear with gradient
        const bgGrad = ctx.createLinearGradient(0, 0, 0, height);
        bgGrad.addColorStop(0, this.colors.bg);
        bgGrad.addColorStop(1, this.colors.bgAlt);
        ctx.fillStyle = bgGrad;
        ctx.fillRect(0, 0, width, height);
        
        if (!segments || segments.length === 0) {
            ctx.fillStyle = this.colors.text;
            ctx.font = '500 12px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Add segments to preview pattern', width / 2, plotHeight / 2 + 4);
            return;
        }
        
        // Calculate total duration
        let totalDuration = 0;
        for (let c = 0; c < cycles; c++) {
            for (const seg of segments) {
                totalDuration += (seg.durationMin + seg.durationMax) / 2;
            }
        }
        
        const pixelsPerSecond = width / totalDuration;
        let x = 0;
        let toneIndex = 0;
        
        // Define Catppuccin tone colors for variety (only for tones)
        const toneColors = [
            { fill: this.colors.eventTone, glow: 'rgba(166, 227, 161, 0.4)' },    // green
            { fill: this.colors.accentAlt, glow: 'rgba(116, 199, 236, 0.4)' },    // sapphire
            { fill: this.colors.peach, glow: 'rgba(250, 179, 135, 0.4)' },        // peach
            { fill: this.colors.pink, glow: 'rgba(245, 194, 231, 0.4)' }          // pink
        ];
        
        for (let c = 0; c < cycles; c++) {
            for (const seg of segments) {
                const duration = (seg.durationMin + seg.durationMax) / 2;
                const w = duration * pixelsPerSecond;
                
                if (seg.type === 'tone') {
                    const avgFreq = (seg.freqMin + seg.freqMax) / 2;
                    const colorIndex = toneIndex % toneColors.length;
                    const color = toneColors[colorIndex];
                    toneIndex++;
                    
                    // Draw with glow
                    ctx.shadowColor = color.glow;
                    ctx.shadowBlur = 10;
                    ctx.fillStyle = color.fill;
                    this.roundRect(ctx, x + 1, 6, w - 4, plotHeight - 12, 6);
                    ctx.fill();
                    ctx.shadowBlur = 0;
                    
                    // Frequency label
                    ctx.fillStyle = this.colors.bg;
                    ctx.font = '600 9px Inter, sans-serif';
                    ctx.textAlign = 'center';
                    if (w > 35) {
                        ctx.fillText(`${Math.round(avgFreq)}Hz`, x + w/2, plotHeight/2);
                    }
                } else {
                    // Silence - distinct muted style
                    ctx.fillStyle = this.colors.eventSilence;
                    this.roundRect(ctx, x + 1, 16, w - 4, plotHeight - 32, 4);
                    ctx.fill();
                    
                    // Optional: Draw pause icon in center for larger silences
                    if (w > 20) {
                        ctx.fillStyle = this.colors.text;
                        ctx.font = '500 10px Inter, sans-serif';
                        ctx.textAlign = 'center';
                        ctx.fillText('⏸', x + w/2, plotHeight/2 + 2);
                    }
                }
                
                x += w;
            }
        }
        
        // Cycle markers with subtle styling
        ctx.strokeStyle = 'rgba(205, 214, 244, 0.2)';
        ctx.setLineDash([6, 6]);
        ctx.lineWidth = 1;
        x = 0;
        for (let c = 0; c < cycles; c++) {
            for (const seg of segments) {
                x += ((seg.durationMin + seg.durationMax) / 2) * pixelsPerSecond;
            }
            if (c < cycles - 1) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, plotHeight);
                ctx.stroke();
            }
        }
        ctx.setLineDash([]);
        
        // Draw time axis
        this.drawTimeAxis(ctx, width, height, plotHeight, totalDuration);
        
        // Draw playhead if progress is provided
        if (playheadProgress !== null && playheadProgress >= 0 && playheadProgress <= 1) {
            const playheadX = playheadProgress * width;
            
            // Glowing playhead line
            ctx.shadowColor = 'rgba(243, 139, 168, 0.8)';
            ctx.shadowBlur = 12;
            ctx.strokeStyle = this.colors.red;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(playheadX, 0);
            ctx.lineTo(playheadX, plotHeight);
            ctx.stroke();
            ctx.shadowBlur = 0;
            
            // Playhead triangle indicator at top
            ctx.fillStyle = this.colors.red;
            ctx.beginPath();
            ctx.moveTo(playheadX - 5, 0);
            ctx.lineTo(playheadX + 5, 0);
            ctx.lineTo(playheadX, 8);
            ctx.closePath();
            ctx.fill();
        }
    }
    
    /**
     * Helper to draw rounded rectangles
     */
    roundRect(ctx, x, y, width, height, radius) {
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + width - radius, y);
        ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
        ctx.lineTo(x + width, y + height - radius);
        ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
        ctx.lineTo(x + radius, y + height);
        ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
        ctx.lineTo(x, y + radius);
        ctx.quadraticCurveTo(x, y, x + radius, y);
        ctx.closePath();
    }

    clear() {
        this.spectrogramHistory = [];
        this.detectedEvents = [];
        
        [this.waveformCanvas, this.spectrogramCanvas, this.eventsCanvas].forEach(canvas => {
            const ctx = canvas.getContext('2d');
            const bgGrad = ctx.createLinearGradient(0, 0, 0, canvas.height);
            bgGrad.addColorStop(0, this.colors.bg);
            bgGrad.addColorStop(1, this.colors.bgAlt);
            ctx.fillStyle = bgGrad;
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        });
    }
}

window.Visualizer = Visualizer;
