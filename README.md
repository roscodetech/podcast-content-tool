# Podcast to Content Automation - Setup Guide

Complete automation pipeline that takes a podcast episode URL and generates slides, blog posts, social media images, soundbites, and summaries using NotebookLM MCP.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Examples](#examples)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### 1. Install NotebookLM MCP Server

```bash
# Install using uv (recommended)
uv tool install notebooklm-mcp-server

# Or using pip
pip install notebooklm-mcp-server

# Or using pipx
pipx install notebooklm-mcp-server
```

### 2. Authenticate with NotebookLM

```bash
# Run the authentication helper (auto mode - recommended)
notebooklm-mcp-auth

# This will:
# - Launch Chrome in a dedicated profile
# - Prompt you to log in to Google
# - Automatically extract and save your cookies
```

### 3. Python Requirements

- Python 3.8 or higher
- pip or uv for package management

## Installation

### Step 1: Clone or Download Files

Save these files to a directory:
- `podcast_to_content_automation.py` - Main automation script
- `requirements.txt` - Python dependencies
- `README.md` - This file

### Step 2: Install Python Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Set Up Google Drive (Optional)

If you want to automatically upload files to Google Drive:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API
4. Create OAuth 2.0 credentials:
   - Application type: Desktop app
   - Download the credentials JSON file
5. Save the credentials file and note the path

**Note:** On first run, you'll be prompted to authorize the application in your browser.

## Configuration

### Option 1: Run NotebookLM MCP as HTTP Server

For the automation to work, NotebookLM MCP needs to run as an HTTP server:

```bash
# Start the MCP server in HTTP mode
notebooklm-mcp --transport http --port 8000
```

Keep this running in a terminal window.

### Option 2: Environment Variables (Optional)

Create a `.env` file in the same directory:

```env
# Google Drive credentials (optional)
GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json

# MCP server URL (optional, defaults to http://localhost:8000)
MCP_SERVER_URL=http://localhost:8000
```

## Usage

### Basic Usage

```bash
python podcast_to_content_automation.py \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  --name "Episode Title"
```

### Full Options

```bash
python podcast_to_content_automation.py \
  "EPISODE_URL" \
  --name "Episode Name" \
  --mcp-url "http://localhost:8000" \
  --gdrive-folder "FOLDER_ID" \
  [--no-slides] \
  [--no-blog] \
  [--no-social] \
  [--no-soundbites] \
  [--no-summary]
```

### Arguments

- `episode_url` (required): URL of the podcast episode (YouTube, Spotify, or any supported URL)
- `--name` (required): Name for the notebook and output files
- `--mcp-url`: URL of NotebookLM MCP server (default: http://localhost:8000)
- `--gdrive-folder`: Google Drive folder ID for uploads (optional)
- `--no-slides`: Skip slide deck generation
- `--no-blog`: Skip blog post generation
- `--no-social`: Skip social media images generation
- `--no-soundbites`: Skip soundbites extraction
- `--no-summary`: Skip summary generation

## Examples

### Example 1: Process YouTube Podcast with All Features

```bash
# Make sure MCP server is running first
notebooklm-mcp --transport http --port 8000

# In another terminal, run the automation
python podcast_to_content_automation.py \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --name "Fitness Science Deep Dive Ep 42"
```

**Output:**
- `~/podcast_content_outputs/Fitness_Science_Deep_Dive_Ep_42_20260125_143022/`
  - `summaries.json` - Short, medium, and social media summaries
  - `blog_post.md` - Full blog post with sections
  - `soundbites.txt` - 5 quotable soundbites
  - `slides.pptx` - PowerPoint presentation
  - `social_landscape.png` - Landscape infographic
  - `social_portrait.png` - Portrait infographic (Instagram Stories)
  - `social_square.png` - Square infographic (Instagram Feed)

### Example 2: With Google Drive Upload

```bash
python podcast_to_content_automation.py \
  "https://spotify.link/podcast123" \
  --name "Recovery Strategies Episode 15" \
  --gdrive-folder "1ABC123xyz456"
```

This will:
1. Generate all content locally
2. Create a timestamped folder in Google Drive
3. Upload all files to that folder
4. Print Google Drive links for sharing

### Example 3: Quick Summary Only (No Studio Content)

```bash
python podcast_to_content_automation.py \
  "https://www.youtube.com/watch?v=ABC123" \
  --name "Quick Episode Summary" \
  --no-slides \
  --no-social
```

This skips the time-consuming slide and infographic generation, focusing on text content only.

### Example 4: Blog Post and Social Media Only

```bash
python podcast_to_content_automation.py \
  "https://podcast.example.com/episode" \
  --name "Nutrition Myths Debunked" \
  --no-slides \
  --no-soundbites
```

## Output Files

All files are saved to `~/podcast_content_outputs/NOTEBOOK_NAME_TIMESTAMP/`:

| File | Description | Use Case |
|------|-------------|----------|
| `summaries.json` | Short, medium, and social summaries | Copy/paste for various platforms |
| `blog_post.md` | Full markdown blog post | Publish to website/Medium |
| `soundbites.txt` | 5 quotable excerpts | Social media quote cards |
| `slides.pptx` | PowerPoint presentation | Repurpose episode content for talks |
| `social_landscape.png` | Landscape infographic (1200x628) | Facebook, LinkedIn, Twitter |
| `social_portrait.png` | Portrait infographic (1080x1920) | Instagram Stories, TikTok |
| `social_square.png` | Square infographic (1080x1080) | Instagram Feed |

Additionally, `latest_results.json` contains all file paths and Google Drive links.

## Workflow Integration

### Integration with n8n

You can trigger this automation from n8n:

1. **Webhook Trigger**: Receive podcast URL from RSS feed or manual input
2. **Execute Command Node**: Run the Python script
3. **Process Results**: Parse `latest_results.json` for Google Drive links
4. **Post to Social Media**: Use the generated images and summaries

### Integration with Make.com

Similar workflow possible with Make.com's HTTP and Shell command modules.

## Troubleshooting

### Error: "Connection refused" or "Cannot connect to MCP server"

**Solution:** Make sure the NotebookLM MCP server is running in HTTP mode:

```bash
notebooklm-mcp --transport http --port 8000
```

### Error: "Authentication failed" or "Invalid cookies"

**Solution:** Re-run the authentication:

```bash
notebooklm-mcp-auth
```

### Error: "Timeout waiting for artifact"

**Cause:** NotebookLM is taking longer than expected to generate slides/infographics.

**Solution:** The default timeout is 600 seconds (10 minutes). For very long episodes, you might need to wait longer or check the NotebookLM web interface manually.

### Google Drive Upload Not Working

**Solutions:**
1. Verify credentials file path is correct
2. Make sure Google Drive API is enabled in your Google Cloud project
3. Check that you've completed the OAuth flow (browser authorization)
4. Verify the folder ID is correct and you have write permissions

### Generated Content Quality Issues

**Tips:**
- Ensure the podcast audio is clear and well-transcribed
- For YouTube videos, make sure captions are available
- NotebookLM works best with structured, professional content
- Very long episodes (3+ hours) may need to be split into parts

## Advanced Usage

### Programmatic Usage

You can also import and use the automation in your own Python scripts:

```python
from podcast_to_content_automation import (
    PodcastContentAutomation,
    ContentConfig
)

# Configure
config = ContentConfig(
    episode_url="https://youtube.com/watch?v=xyz",
    notebook_name="My Episode",
    generate_slides=True,
    generate_blog=True,
    gdrive_folder_id="your-folder-id"
)

# Run automation
automation = PodcastContentAutomation(mcp_url="http://localhost:8000")
results = automation.process_episode(config)

# Access results
print(f"Notebook ID: {results['notebook_id']}")
print(f"Blog post: {results['files']['blog']}")
print(f"GDrive blog link: {results['gdrive_links']['blog']}")
```

### Batch Processing Multiple Episodes

Create a simple bash script:

```bash
#!/bin/bash

# episodes.txt contains one URL per line
while IFS= read -r url; do
  echo "Processing: $url"
  
  # Extract episode number or title (customize this)
  episode_name=$(echo "$url" | grep -oP 'v=\K[^&]+' || echo "Episode")
  
  python podcast_to_content_automation.py "$url" \
    --name "Episode $episode_name" \
    --gdrive-folder "YOUR_FOLDER_ID"
  
  # Wait between episodes to avoid rate limits
  sleep 60
done < episodes.txt
```

## Rate Limits

NotebookLM has rate limits:
- **Free tier**: ~50 queries per day
- **Studio content generation**: Takes 3-10 minutes per item
- **Recommendation**: Process 3-5 episodes per day maximum

## Support

For issues with:
- **NotebookLM MCP Server**: Check the [official repo](https://github.com/jacob-bd/notebooklm-mcp)
- **This automation script**: Feel free to modify or extend as needed
- **Google Drive API**: Refer to [Google's documentation](https://developers.google.com/drive)

## License

This automation script is provided as-is for your use with NotebookLM MCP.

## Credits

Built with:
- [NotebookLM MCP Server](https://github.com/jacob-bd/notebooklm-mcp) by jacob-bd
- Google's NotebookLM
- Google Drive API
