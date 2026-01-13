/**
 * Main Application - Ties together AudioEngine, Visualizer, and UI.
 */

class App {
    constructor() {
        this.audioEngine = new AudioEngine();
        this.visualizer = new Visualizer(
            document.getElementById('waveformCanvas'),
            document.getElementById('spectrogramCanvas'),
            document.getElementById('eventsCanvas')
        );
        
        this.segments = [];
        this.segmentIdCounter = 0;
        this.animationId = null;
        
        this.initUI();
        this.addDefaultSegments();
    }

    initUI() {
        // Recording controls
        document.getElementById('recordBtn').addEventListener('click', () => this.startRecording());
        document.getElementById('stopBtn').addEventListener('click', () => this.stopRecording());
        document.getElementById('playbackBtn').addEventListener('click', () => this.playRecording());
        
        // Segment controls
        document.getElementById('addSegmentBtn').addEventListener('click', () => this.addSegment());
        
        // Actions
        document.getElementById('generateSoundBtn').addEventListener('click', () => this.generateSound());
        document.getElementById('exportConfigBtn').addEventListener('click', () => this.exportConfig());
        document.getElementById('analyzeBtn').addEventListener('click', () => this.analyzeRecording());
        
        // Profile form listeners for auto-update
        document.getElementById('confirmCycles').addEventListener('input', () => {
            this.updatePreview();
            this.updateConfig();
        });
        document.getElementById('profileName').addEventListener('input', () => {
            this.updateConfig();
        });
    }

    addDefaultSegments() {
        // Add a sample pattern: Beep -> Silence -> Beep -> Silence
        this.addSegment('tone', 2900, 3100, 0.4, 0.6);
        this.addSegment('silence', 0, 0, 0.1, 0.3);
        this.addSegment('tone', 2900, 3100, 0.4, 0.6);
        this.addSegment('silence', 0, 0, 0.8, 1.2);
        
        this.updatePreview();
    }

    addSegment(type = 'tone', freqMin = 1000, freqMax = 1500, durationMin = 0.3, durationMax = 0.5) {
        const id = this.segmentIdCounter++;
        
        this.segments.push({
            id,
            type,
            freqMin,
            freqMax,
            durationMin,
            durationMax
        });
        
        this.renderSegments();
        this.updatePreview();
        this.updateConfig();
    }

    removeSegment(id) {
        this.segments = this.segments.filter(s => s.id !== id);
        this.renderSegments();
        this.updatePreview();
        this.updateConfig();
    }

    duplicateSegment(id) {
        const index = this.segments.findIndex(s => s.id === id);
        if (index === -1) return;
        
        const original = this.segments[index];
        const duplicate = {
            id: this.segmentIdCounter++,
            type: original.type,
            freqMin: original.freqMin,
            freqMax: original.freqMax,
            durationMin: original.durationMin,
            durationMax: original.durationMax
        };
        
        // Insert after the original
        this.segments.splice(index + 1, 0, duplicate);
        this.renderSegments();
        this.updatePreview();
        this.updateConfig();
    }

    moveSegment(id, direction) {
        const index = this.segments.findIndex(s => s.id === id);
        if (index === -1) return;
        
        const newIndex = index + direction;
        if (newIndex < 0 || newIndex >= this.segments.length) return;
        
        // Swap segments
        [this.segments[index], this.segments[newIndex]] = 
        [this.segments[newIndex], this.segments[index]];
        
        this.renderSegments();
        this.updatePreview();
        this.updateConfig();
        
        // Re-focus the moved segment's first input for continued keyboard navigation
        setTimeout(() => {
            const movedEl = document.querySelector(`.segment-item[data-id="${id}"] input`);
            if (movedEl) movedEl.focus();
        }, 50);
    }

    updateSegment(id, field, value) {
        const seg = this.segments.find(s => s.id === id);
        if (seg) {
            seg[field] = field === 'type' ? value : parseFloat(value);
            this.updatePreview();
            this.updateConfig();
        }
    }

    renderSegments() {
        const container = document.getElementById('segmentList');
        container.innerHTML = '';
        
        this.segments.forEach((seg, index) => {
            const el = document.createElement('div');
            el.className = `segment-item segment-${seg.type}`;
            el.dataset.id = seg.id;
            el.tabIndex = 0; // Make focusable for keyboard navigation
            
            const isFirst = index === 0;
            const isLast = index === this.segments.length - 1;
            
            el.innerHTML = `
                <div class="segment-header">
                    <span class="segment-type">
                        <span class="segment-indicator">${seg.type === 'tone' ? '♪' : '⏸'}</span>
                        <span class="segment-number">#${index + 1}</span>
                        <select data-id="${seg.id}" data-field="type">
                            <option value="tone" ${seg.type === 'tone' ? 'selected' : ''}>Tone</option>
                            <option value="silence" ${seg.type === 'silence' ? 'selected' : ''}>Silence</option>
                        </select>
                    </span>
                    <div class="segment-actions">
                        <button class="segment-action-btn move-up" data-id="${seg.id}" title="Move up (Shift+↑)" ${isFirst ? 'disabled' : ''}>↑</button>
                        <button class="segment-action-btn move-down" data-id="${seg.id}" title="Move down (Shift+↓)" ${isLast ? 'disabled' : ''}>↓</button>
                        <button class="segment-action-btn duplicate" data-id="${seg.id}" title="Duplicate">⧉</button>
                        <button class="segment-action-btn remove-btn" data-id="${seg.id}" title="Remove">×</button>
                    </div>
                </div>
                <div class="segment-fields">
                    ${seg.type === 'tone' ? `
                        <label>
                            Freq Min (Hz)
                            <input type="number" value="${seg.freqMin}" data-id="${seg.id}" data-field="freqMin" />
                        </label>
                        <label>
                            Freq Max (Hz)
                            <input type="number" value="${seg.freqMax}" data-id="${seg.id}" data-field="freqMax" />
                        </label>
                    ` : ''}
                    <label>
                        Duration Min (s)
                        <input type="number" step="0.1" value="${seg.durationMin}" data-id="${seg.id}" data-field="durationMin" />
                    </label>
                    <label>
                        Duration Max (s)
                        <input type="number" step="0.1" value="${seg.durationMax}" data-id="${seg.id}" data-field="durationMax" />
                    </label>
                </div>
            `;
            container.appendChild(el);
        });
        
        // Attach event listeners for inputs and selects
        container.querySelectorAll('input, select').forEach(input => {
            input.addEventListener('change', (e) => {
                const id = parseInt(e.target.dataset.id);
                const field = e.target.dataset.field;
                this.updateSegment(id, field, e.target.value);
                
                // Re-render if type changed
                if (field === 'type') {
                    this.renderSegments();
                }
            });
            
            // Keyboard shortcuts for reordering
            input.addEventListener('keydown', (e) => {
                if (e.shiftKey) {
                    const id = parseInt(e.target.dataset.id);
                    if (e.key === 'ArrowUp') {
                        e.preventDefault();
                        this.moveSegment(id, -1);
                    } else if (e.key === 'ArrowDown') {
                        e.preventDefault();
                        this.moveSegment(id, 1);
                    }
                }
            });
        });
        
        // Move up buttons
        container.querySelectorAll('.move-up').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.dataset.id);
                this.moveSegment(id, -1);
            });
        });
        
        // Move down buttons
        container.querySelectorAll('.move-down').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.dataset.id);
                this.moveSegment(id, 1);
            });
        });
        
        // Duplicate buttons
        container.querySelectorAll('.duplicate').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.dataset.id);
                this.duplicateSegment(id);
            });
        });
        
        // Remove buttons
        container.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.dataset.id);
                this.removeSegment(id);
            });
        });
    }

    updatePreview() {
        const cycles = parseInt(document.getElementById('confirmCycles').value) || 1;
        this.visualizer.drawSegmentPreview(this.segments, cycles);
    }

    updateConfig() {
        const name = document.getElementById('profileName').value || 'NewAlarm';
        const cycles = parseInt(document.getElementById('confirmCycles').value) || 1;
        
        let yaml = `# Alarm Profile: ${name}\n`;
        yaml += `name: "${name}"\n`;
        yaml += `confirmation_cycles: ${cycles}\n`;
        yaml += `segments:\n`;
        
        this.segments.forEach((seg, i) => {
            yaml += `  - type: "${seg.type}"\n`;
            if (seg.type === 'tone') {
                yaml += `    frequency:\n`;
                yaml += `      min: ${seg.freqMin}\n`;
                yaml += `      max: ${seg.freqMax}\n`;
            }
            yaml += `    duration:\n`;
            yaml += `      min: ${seg.durationMin}\n`;
            yaml += `      max: ${seg.durationMax}\n`;
        });
        
        document.getElementById('configOutput').textContent = yaml;
    }

    async startRecording() {
        const success = await this.audioEngine.startRecording();
        if (success) {
            document.getElementById('recordBtn').classList.add('recording');
            document.getElementById('recordBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('playbackBtn').disabled = true;
            document.getElementById('statusText').textContent = 'Recording...';
            
            this.visualizer.clear();
            this.startVisualization();
        }
    }

    stopRecording() {
        this.audioEngine.stopRecording();
        this.stopVisualization();
        
        document.getElementById('recordBtn').classList.remove('recording');
        document.getElementById('recordBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
        document.getElementById('playbackBtn').disabled = false;
        document.getElementById('analyzeBtn').disabled = false;
        document.getElementById('statusText').textContent = 'Recording stopped - Click Auto-Tune to analyze';
    }

    playRecording() {
        this.audioEngine.playRecording();
        document.getElementById('statusText').textContent = 'Playing back...';
    }

    startVisualization() {
        const draw = () => {
            const data = this.audioEngine.getAnalyserData();
            if (data) {
                this.visualizer.drawWaveform(data.timeData, data.bufferLength);
                this.visualizer.drawSpectrogram(data.freqData, data.bufferLength);
            }
            
            const duration = this.audioEngine.getRecordingDuration();
            document.getElementById('durationText').textContent = duration.toFixed(1) + 's';
            
            this.animationId = requestAnimationFrame(draw);
        };
        draw();
    }

    stopVisualization() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    generateSound() {
        if (this.segments.length === 0) {
            alert('Add at least one segment to generate sound!');
            return;
        }
        
        const cycles = parseInt(document.getElementById('confirmCycles').value) || 1;
        
        // Calculate total duration for playhead
        let totalDuration = 0;
        for (let c = 0; c < cycles; c++) {
            for (const seg of this.segments) {
                totalDuration += (seg.durationMin + seg.durationMax) / 2;
            }
        }
        
        // Generate and play the sound
        const buffer = this.audioEngine.generateSound(this.segments, cycles);
        
        // Start playhead animation
        this.startPlayheadAnimation(totalDuration);
        
        document.getElementById('statusText').textContent = 'Playing generated sound...';
    }

    /**
     * Animate a playhead bar across the Detected Events canvas during playback
     */
    startPlayheadAnimation(duration) {
        const startTime = performance.now();
        const durationMs = duration * 1000;
        
        // Stop any existing animation
        if (this.playheadAnimationId) {
            cancelAnimationFrame(this.playheadAnimationId);
        }
        
        const animate = () => {
            const elapsed = performance.now() - startTime;
            const progress = Math.min(elapsed / durationMs, 1);
            const currentTime = progress * duration;
            
            // Update duration display
            document.getElementById('durationText').textContent = currentTime.toFixed(1) + 's';
            
            // Redraw segments with playhead
            const cycles = parseInt(document.getElementById('confirmCycles').value) || 1;
            this.visualizer.drawSegmentPreview(this.segments, cycles, progress);
            
            if (progress < 1) {
                this.playheadAnimationId = requestAnimationFrame(animate);
            } else {
                // Playback finished
                document.getElementById('statusText').textContent = `Playback complete (${duration.toFixed(1)}s)`;
                this.playheadAnimationId = null;
                
                // Redraw without playhead after a short delay
                setTimeout(() => {
                    this.visualizer.drawSegmentPreview(this.segments, cycles);
                }, 500);
            }
        };
        
        animate();
    }

    exportConfig() {
        const yamlContent = document.getElementById('configOutput').textContent;
        const blob = new Blob([yamlContent], { type: 'text/yaml' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `${document.getElementById('profileName').value || 'alarm'}_profile.yaml`;
        a.click();
        
        URL.revokeObjectURL(url);
        document.getElementById('statusText').textContent = 'Config exported!';
    }

    analyzeRecording() {
        const result = this.audioEngine.analyzeRecording();
        
        if (result.warnings && result.warnings.length > 0) {
            console.warn('Analysis warnings:', result.warnings);
        }
        
        if (result.proposedSegments && result.proposedSegments.length > 0) {
            // Clear existing segments and load proposed ones
            this.segments = [];
            this.segmentIdCounter = 0;
            
            for (const seg of result.proposedSegments) {
                this.addSegment(
                    seg.type,
                    seg.freqMin || 0,
                    seg.freqMax || 0,
                    seg.durationMin,
                    seg.durationMax
                );
            }
            
            document.getElementById('statusText').textContent = 
                `Auto-tuned! Extracted ${result.proposedSegments.length} segments from ${result.totalDuration.toFixed(1)}s audio`;
            
            // Visualize raw segments
            this.visualizer.drawEvents(
                result.rawSegments.map(s => ({
                    type: s.type,
                    timestamp: s.startTime,
                    duration: s.duration,
                    frequency: s.frequency || 0
                })),
                result.totalDuration
            );
        } else {
            document.getElementById('statusText').textContent = 'No patterns detected. Try a longer recording.';
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
