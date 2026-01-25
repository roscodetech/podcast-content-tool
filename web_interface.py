#!/usr/bin/env python3
"""
Flask Web Interface for Podcast Content Automation
Simple web UI to submit podcast URLs and track processing
"""

from flask import Flask, render_template, request, jsonify, send_file
from pathlib import Path
import json
import threading
from datetime import datetime
from podcast_to_content_automation import (
    PodcastContentAutomation,
    ContentConfig
)

app = Flask(__name__)

# Store job status in memory (use Redis/database for production)
jobs = {}
job_counter = 0


class JobStatus:
    """Track job processing status"""
    def __init__(self, job_id: int, config: ContentConfig):
        self.job_id = job_id
        self.config = config
        self.status = 'queued'
        self.progress = 0
        self.message = 'Waiting to start...'
        self.results = None
        self.error = None
        self.created_at = datetime.now()
        self.completed_at = None


def process_job(job_id: int, config: ContentConfig):
    """Background job processor"""
    job = jobs[job_id]
    
    try:
        job.status = 'processing'
        job.message = 'Creating notebook...'
        job.progress = 10
        
        automation = PodcastContentAutomation()
        
        job.message = 'Processing podcast content...'
        job.progress = 30
        
        results = automation.process_episode(config)
        
        job.status = 'completed'
        job.progress = 100
        job.message = 'All content generated!'
        job.results = results
        job.completed_at = datetime.now()
        
    except Exception as e:
        job.status = 'failed'
        job.error = str(e)
        job.message = f'Error: {e}'
        job.completed_at = datetime.now()


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/submit', methods=['POST'])
def submit_job():
    """Submit a new processing job"""
    global job_counter
    
    data = request.json
    
    # Validate input
    if not data.get('episode_url'):
        return jsonify({'error': 'Episode URL is required'}), 400
    
    if not data.get('name'):
        return jsonify({'error': 'Episode name is required'}), 400
    
    # Create config
    config = ContentConfig(
        episode_url=data['episode_url'],
        notebook_name=data['name'],
        generate_slides=data.get('generate_slides', True),
        generate_blog=data.get('generate_blog', True),
        generate_social_images=data.get('generate_social_images', True),
        generate_soundbites=data.get('generate_soundbites', True),
        generate_summary=data.get('generate_summary', True),
        gdrive_folder_id=data.get('gdrive_folder_id')
    )
    
    # Create job
    job_counter += 1
    job_id = job_counter
    jobs[job_id] = JobStatus(job_id, config)
    
    # Start background processing
    thread = threading.Thread(target=process_job, args=(job_id, config))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'status': 'queued',
        'message': 'Job submitted successfully'
    })


@app.route('/api/status/<int:job_id>')
def job_status(job_id: int):
    """Get job status"""
    job = jobs.get(job_id)
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    response = {
        'job_id': job.job_id,
        'status': job.status,
        'progress': job.progress,
        'message': job.message,
        'created_at': job.created_at.isoformat(),
    }
    
    if job.completed_at:
        response['completed_at'] = job.completed_at.isoformat()
    
    if job.results:
        response['results'] = {
            'notebook_id': job.results['notebook_id'],
            'files': job.results['files'],
            'gdrive_links': job.results.get('gdrive_links', {})
        }
    
    if job.error:
        response['error'] = job.error
    
    return jsonify(response)


@app.route('/api/jobs')
def list_jobs():
    """List all jobs"""
    job_list = []
    
    for job in jobs.values():
        job_list.append({
            'job_id': job.job_id,
            'name': job.config.notebook_name,
            'status': job.status,
            'progress': job.progress,
            'created_at': job.created_at.isoformat()
        })
    
    # Sort by created_at descending
    job_list.sort(key=lambda x: x['created_at'], reverse=True)
    
    return jsonify(job_list)


@app.route('/api/download/<int:job_id>/<file_type>')
def download_file(job_id: int, file_type: str):
    """Download a generated file"""
    job = jobs.get(job_id)
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if not job.results or file_type not in job.results['files']:
        return jsonify({'error': 'File not found'}), 404
    
    file_path = job.results['files'][file_type]
    
    if not Path(file_path).exists():
        return jsonify({'error': 'File not found on disk'}), 404
    
    return send_file(file_path, as_attachment=True)


# HTML Template
@app.route('/template')
def get_template():
    """Return the HTML template"""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Podcast Content Automation</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 2rem;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 2rem;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        
        h1 {
            color: #333;
            margin-bottom: 0.5rem;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 2rem;
        }
        
        .form-group {
            margin-bottom: 1.5rem;
        }
        
        label {
            display: block;
            margin-bottom: 0.5rem;
            color: #333;
            font-weight: 500;
        }
        
        input[type="text"],
        input[type="url"] {
            width: 100%;
            padding: 0.75rem;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.3s;
        }
        
        input[type="text"]:focus,
        input[type="url"]:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .checkbox-group {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        
        .checkbox-item {
            display: flex;
            align-items: center;
        }
        
        input[type="checkbox"] {
            margin-right: 0.5rem;
            width: 18px;
            height: 18px;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
            width: 100%;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .jobs-list {
            margin-top: 3rem;
        }
        
        .job-card {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border-left: 4px solid #667eea;
        }
        
        .job-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .job-name {
            font-weight: 600;
            color: #333;
        }
        
        .job-status {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        .status-queued { background: #ffd93d; color: #333; }
        .status-processing { background: #6bcf7f; color: white; }
        .status-completed { background: #4facfe; color: white; }
        .status-failed { background: #ff6b9d; color: white; }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 0.5rem;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
        }
        
        .job-message {
            color: #666;
            font-size: 0.875rem;
            margin-bottom: 1rem;
        }
        
        .file-links {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 0.5rem;
        }
        
        .file-link {
            display: inline-block;
            padding: 0.5rem 1rem;
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            text-decoration: none;
            color: #667eea;
            font-size: 0.875rem;
            text-align: center;
            transition: all 0.2s;
        }
        
        .file-link:hover {
            border-color: #667eea;
            background: #f0f4ff;
        }
        
        .empty-state {
            text-align: center;
            padding: 3rem;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ Podcast Content Automation</h1>
        <p class="subtitle">Transform podcast episodes into slides, blog posts, and social media content</p>
        
        <form id="submitForm">
            <div class="form-group">
                <label for="episodeUrl">Podcast Episode URL *</label>
                <input type="url" id="episodeUrl" required placeholder="https://www.youtube.com/watch?v=...">
            </div>
            
            <div class="form-group">
                <label for="episodeName">Episode Name *</label>
                <input type="text" id="episodeName" required placeholder="Episode 42: Fitness Science Deep Dive">
            </div>
            
            <div class="form-group">
                <label for="gdriveFolder">Google Drive Folder ID (optional)</label>
                <input type="text" id="gdriveFolder" placeholder="1ABC123xyz456">
            </div>
            
            <div class="form-group">
                <label>Content to Generate:</label>
                <div class="checkbox-group">
                    <div class="checkbox-item">
                        <input type="checkbox" id="genSummary" checked>
                        <label for="genSummary">Summaries</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" id="genBlog" checked>
                        <label for="genBlog">Blog Post</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" id="genSoundbites" checked>
                        <label for="genSoundbites">Soundbites</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" id="genSlides" checked>
                        <label for="genSlides">Slide Deck</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" id="genSocial" checked>
                        <label for="genSocial">Social Images</label>
                    </div>
                </div>
            </div>
            
            <button type="submit" class="btn" id="submitBtn">Start Processing</button>
        </form>
        
        <div class="jobs-list">
            <h2>Processing Jobs</h2>
            <div id="jobsList"></div>
        </div>
    </div>
    
    <script>
        let pollInterval;
        
        // Submit form
        document.getElementById('submitForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const btn = document.getElementById('submitBtn');
            btn.disabled = true;
            btn.textContent = 'Submitting...';
            
            const data = {
                episode_url: document.getElementById('episodeUrl').value,
                name: document.getElementById('episodeName').value,
                gdrive_folder_id: document.getElementById('gdriveFolder').value || null,
                generate_summary: document.getElementById('genSummary').checked,
                generate_blog: document.getElementById('genBlog').checked,
                generate_soundbites: document.getElementById('genSoundbites').checked,
                generate_slides: document.getElementById('genSlides').checked,
                generate_social_images: document.getElementById('genSocial').checked
            };
            
            try {
                const response = await fetch('/api/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert('Job submitted successfully! Job ID: ' + result.job_id);
                    document.getElementById('submitForm').reset();
                    loadJobs();
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (err) {
                alert('Error submitting job: ' + err.message);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Start Processing';
            }
        });
        
        // Load jobs list
        async function loadJobs() {
            try {
                const response = await fetch('/api/jobs');
                const jobs = await response.json();
                
                const jobsList = document.getElementById('jobsList');
                
                if (jobs.length === 0) {
                    jobsList.innerHTML = '<div class="empty-state">No jobs yet. Submit a podcast URL to get started!</div>';
                    return;
                }
                
                jobsList.innerHTML = jobs.map(job => `
                    <div class="job-card" data-job-id="${job.job_id}">
                        <div class="job-header">
                            <span class="job-name">${job.name}</span>
                            <span class="job-status status-${job.status}">${job.status.toUpperCase()}</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${job.progress}%"></div>
                        </div>
                        <div class="job-message" id="message-${job.job_id}">Loading...</div>
                        <div class="file-links" id="files-${job.job_id}"></div>
                    </div>
                `).join('');
                
                // Load detailed status for each job
                jobs.forEach(job => loadJobDetails(job.job_id));
                
            } catch (err) {
                console.error('Error loading jobs:', err);
            }
        }
        
        // Load job details
        async function loadJobDetails(jobId) {
            try {
                const response = await fetch(`/api/status/${jobId}`);
                const job = await response.json();
                
                // Update message
                const messageEl = document.getElementById(`message-${jobId}`);
                if (messageEl) {
                    messageEl.textContent = job.message;
                }
                
                // Update progress
                const progressEl = document.querySelector(`[data-job-id="${jobId}"] .progress-fill`);
                if (progressEl) {
                    progressEl.style.width = job.progress + '%';
                }
                
                // Update status
                const statusEl = document.querySelector(`[data-job-id="${jobId}"] .job-status`);
                if (statusEl) {
                    statusEl.className = `job-status status-${job.status}`;
                    statusEl.textContent = job.status.toUpperCase();
                }
                
                // Show file links if completed
                if (job.results && job.results.files) {
                    const filesEl = document.getElementById(`files-${jobId}`);
                    if (filesEl) {
                        const fileLinks = Object.entries(job.results.files).map(([type, path]) => {
                            // Use GDrive link if available, otherwise download link
                            const link = job.results.gdrive_links && job.results.gdrive_links[type] 
                                ? job.results.gdrive_links[type]
                                : `/api/download/${jobId}/${type}`;
                            
                            return `<a href="${link}" class="file-link" target="_blank">${type}</a>`;
                        }).join('');
                        
                        filesEl.innerHTML = fileLinks;
                    }
                }
            } catch (err) {
                console.error(`Error loading job ${jobId}:`, err);
            }
        }
        
        // Auto-refresh jobs
        loadJobs();
        pollInterval = setInterval(loadJobs, 5000);
    </script>
</body>
</html>
    '''


if __name__ == '__main__':
    # Create templates directory if needed
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)
    
    # Save HTML template
    with open(templates_dir / 'index.html', 'w') as f:
        f.write(app.test_client().get('/template').data.decode())
    
    print("Starting Podcast Content Automation Web Interface...")
    print("Open http://localhost:5000 in your browser")
    print("\nMake sure NotebookLM MCP server is running:")
    print("  notebooklm-mcp --transport http --port 8000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
