const consoleStyles = {
    header: 'font-weight: bold; font-size: 16px; color: #667eea;',
    success: 'color: #48bb78;',
    info: 'color: #4299e1;',
    error: 'color: #f56565;'
};

class PageHandler {
    constructor() {
        this.loading = document.getElementById('loading');

        // Determine which page we're on
        if (document.getElementById('summarizeBtn')) {
            this.initStandardPage();
        }
        if (document.getElementById('mctsRunBtn')) {
            this.initMctsPage();
        }
    }

    // Standard page (index.html)
    initStandardPage() {
        this.textInput = document.getElementById('textInput');
        this.imageUpload = document.getElementById('imageUpload');
        this.videoUpload = document.getElementById('videoUpload');
        this.imagePreviews = document.getElementById('imagePreviews');
        this.videoPreview = document.getElementById('videoPreview');
        this.simulations = document.getElementById('simulations');
        this.simulationsValue = document.getElementById('simulationsValue');
        this.summarizeBtn = document.getElementById('summarizeBtn');
        this.resultDiv = document.getElementById('result');
        this.bestSummary = document.getElementById('bestSummary');
        this.selectedAgent = document.getElementById('selectedAgent');
        this.confidenceScore = document.getElementById('confidenceScore');

        this.files = { images: [], video: null };

        this.setupTabs('standardTabs');
        this.setupSlider(this.simulations, this.simulationsValue);
        this.setupFileHandlers();
        this.summarizeBtn.addEventListener('click', () => this.runStandard());
    }

    // MCTS page (explore.html)
    initMctsPage() {
        this.mctsQuestion = document.getElementById('mctsQuestion');
        this.mctsImageUpload = document.getElementById('mctsImageUpload');
        this.mctsVideoUpload = document.getElementById('mctsVideoUpload');
        this.mctsImagePreviews = document.getElementById('mctsImagePreviews');
        this.mctsVideoPreview = document.getElementById('mctsVideoPreview');
        this.mctsIterations = document.getElementById('mctsIterations');
        this.mctsIterationsValue = document.getElementById('mctsIterationsValue');
        this.mctsVariant = document.getElementById('mctsVariant');
        this.mctsRunBtn = document.getElementById('mctsRunBtn');

        // Result elements – only final answer remains
        this.mctsFinalResult = document.getElementById('mctsFinalResult');
        this.mctsFinalAnswer = document.getElementById('mctsFinalAnswer');
        this.mctsAgentInfo = document.getElementById('mctsAgentInfo');

        this.files = { images: [], video: null };

        this.setupTabs('mctsTabs');
        this.setupSlider(this.mctsIterations, this.mctsIterationsValue);
        this.setupFileHandlersMcts();
        this.mctsRunBtn.addEventListener('click', () => this.runMCTS());
    }

    setupTabs(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        const buttons = container.querySelectorAll('.tab-button');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.getAttribute('data-tab');
                container.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
                container.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById(tabId).classList.add('active');
            });
        });
    }

    setupSlider(slider, display) {
        slider.addEventListener('input', () => {
            display.textContent = slider.value;
        });
    }

    setupFileHandlers() {
        this.imageUpload.addEventListener('change', (e) => {
            this.files.images = Array.from(e.target.files);
            this.previewImages(this.files.images, this.imagePreviews);
        });
        this.videoUpload.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.files.video = e.target.files[0];
                this.previewVideo(this.files.video, this.videoPreview);
            }
        });
    }

    setupFileHandlersMcts() {
        this.mctsImageUpload.addEventListener('change', (e) => {
            this.files.images = Array.from(e.target.files);
            this.previewImages(this.files.images, this.mctsImagePreviews);
        });
        this.mctsVideoUpload.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.files.video = e.target.files[0];
                this.previewVideo(this.files.video, this.mctsVideoPreview);
            }
        });
    }

    previewImages(files, container) {
        container.innerHTML = '';
        files.slice(0, 5).forEach(file => {
            const url = URL.createObjectURL(file);
            const div = document.createElement('div');
            div.className = 'image-preview';
            div.innerHTML = `<img src="${url}"><div class="file-info">${file.name}</div>`;
            container.appendChild(div);
        });
    }

    previewVideo(file, container) {
        const url = URL.createObjectURL(file);
        container.innerHTML = `
            <div class="video-preview">
                <video controls><source src="${url}" type="${file.type}"></video>
                <div class="file-info">${file.name}</div>
            </div>
        `;
    }

    async runStandard() {
        const text = this.textInput.value.trim();
        const hasMedia = this.files.video || this.files.images.length > 0;

        if (!text && !hasMedia) {
            alert('Please enter text or upload media.');
            return;
        }

        this.showLoading();
        this.resultDiv.classList.add('hidden');

        try {
            let mediaAnalyses = [];
            let summaryData;

            if (hasMedia) {
                const uploadResult = await this.uploadFiles(text);
                mediaAnalyses = uploadResult.media_analyses || [];
                summaryData = await this.runSimpleSummarization(uploadResult.text, mediaAnalyses);
            } else {
                summaryData = await this.runSimpleSummarization(text, []);
            }

            this.displaySimpleResult(summaryData);
        } catch (error) {
            console.error(error);
            alert('Error: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async runSimpleSummarization(text, mediaAnalyses) {
        const resp = await fetch('/summarize_simple', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, media_analyses: mediaAnalyses })
        });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);
        return data;
    }

    displaySimpleResult(data) {
        this.bestSummary.textContent = data.summary || 'No summary generated';
        this.confidenceScore.textContent = data.confidence || '0';
        this.selectedAgent.textContent = data.agent_name || 'Default Agent';
        this.resultDiv.classList.remove('hidden');
    }

    async runMCTS() {
        const question = this.mctsQuestion.value.trim();
        const hasMedia = this.files.video || this.files.images.length > 0;

        if (!question && !hasMedia) {
            alert('Please enter a question or upload media.');
            return;
        }

        this.showLoading();
        // Hide previous final result
        if (this.mctsFinalResult) this.mctsFinalResult.style.display = 'none';

        try {
            const iterations = parseInt(this.mctsIterations.value);
            const variant = this.mctsVariant.value;

            let mediaAnalyses = [];
            if (hasMedia) {
                const uploadResult = await this.uploadFiles(question);
                mediaAnalyses = uploadResult.media_analyses || [];
            }

            const payload = {
                question: question,
                media_analyses: mediaAnalyses,
                iterations: iterations,
                variant: variant
            };

            const resp = await fetch('/reasoning_explore', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (data.error) throw new Error(data.error);

            this.displayMCTSResults(data);
        } catch (error) {
            console.error(error);
            alert('MCTS exploration failed: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async uploadFiles(text) {
        const formData = new FormData();
        formData.append('text', text);
        if (this.files.video) formData.append('video', this.files.video);
        this.files.images.forEach(img => formData.append('images', img));

        const resp = await fetch('/upload', { method: 'POST', body: formData });
        const data = await resp.json();
        if (!data.success) throw new Error(data.message || 'Upload failed');
        return data;
    }

    // The following methods are kept for standard page; they are not used on explore page
    async runMultimodalAgents(uploadResult) {
        const resp = await fetch('/summarize_multimodal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: uploadResult.text,
                media_analyses: uploadResult.media_analyses || []
            })
        });
        const data = await resp.json();
        return data.agent_results;
    }

    async runTextAgents(text) {
        return this.runMultimodalAgents({ text, media_analyses: [] });
    }

    async executeMCTSOptimization(agentResults, hasMedia, simulations, variant, originalText, mediaAnalyses) {
        const useReflection = variant === 'reflective';
        const useRag = variant === 'rag';
        const useWorld = variant === 'world';

        const payload = {
            agent_results: agentResults,
            has_multimedia: hasMedia,
            simulations: simulations,
            use_reflection: useReflection,
            use_rag: useRag,
            use_world: useWorld,
            original_text: originalText,
            media_analyses: mediaAnalyses
        };

        const resp = await fetch('/mcts_optimize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        return await resp.json();
    }

    displayMCTSResults(data) {
        // Final answer
        if (this.mctsFinalResult && this.mctsFinalAnswer) {
            this.mctsFinalAnswer.textContent = data.final_answer || 'No answer generated.';
            let bestAgent = 'Unknown';
            // We can get the agent name from the last element of optimal_path if available
            if (data.optimal_path && data.optimal_path.length) {
                bestAgent = data.optimal_path[data.optimal_path.length - 1];
            } else if (data.winning_agent_name) {
                bestAgent = data.winning_agent_name;
            }
            const confidencePercent = Math.round((data.confidence || 0) * 100);
            this.mctsAgentInfo.textContent = `Selected by: ${bestAgent} | Confidence: ${confidencePercent}%`;
            this.mctsFinalResult.style.display = 'block';
        }
    }

    showLoading() {
        this.loading.classList.remove('hidden');
    }

    hideLoading() {
        this.loading.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new PageHandler();
});