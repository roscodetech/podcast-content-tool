# Podcast to Content Automation - Complete Guide

## 📁 Project Structure

```
podcast-content-automation/
├── podcast_to_content_automation.py  # Main automation script
├── web_interface.py                  # Flask web UI (optional)
├── batch_processor.py                # Batch processing from YAML
├── setup.sh                          # Quick setup script
├── requirements.txt                  # Python dependencies
├── batch_config.yaml                 # Sample batch configuration
├── README.md                         # Setup and usage guide
└── EXAMPLES.md                       # This file - detailed examples
```

## 🚀 Quick Start (3 Steps)

### 1. Run Setup Script

```bash
./setup.sh
```

This will:
- Install NotebookLM MCP server
- Authenticate with Google
- Set up Python environment
- Optionally configure Google Drive

### 2. Start MCP Server

```bash
notebooklm-mcp --transport http --port 8000
```

Keep this running in a terminal.

### 3. Process Your First Episode

**Option A: Command Line**
```bash
source venv/bin/activate
python podcast_to_content_automation.py \
  "https://www.youtube.com/watch?v=YOUR_VIDEO_ID" \
  --name "My First Episode"
```

**Option B: Web Interface**
```bash
source venv/bin/activate
python web_interface.py
```
Then open http://localhost:5000

## 📚 Detailed Examples

### Example 1: YouTube Podcast Episode

```bash
python podcast_to_content_automation.py \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --name "Fitness Science Episode 42" \
  --gdrive-folder "1ABC_YOUR_FOLDER_ID_xyz"
```

**What gets generated:**
- ✅ `summaries.json` - 3 formats (short, medium, social)
- ✅ `blog_post.md` - Full article with sections
- ✅ `soundbites.txt` - 5 quotable excerpts
- ✅ `slides.pptx` - PowerPoint presentation
- ✅ `social_landscape.png` - 1200x628px (Facebook, Twitter)
- ✅ `social_portrait.png` - 1080x1920px (Instagram Stories)
- ✅ `social_square.png` - 1080x1080px (Instagram Feed)

**Time estimate:** 15-20 minutes total

### Example 2: Spotify Podcast

```bash
python podcast_to_content_automation.py \
  "https://open.spotify.com/episode/ABC123XYZ" \
  --name "Recovery Strategies Episode 15"
```

**Note:** Spotify links work if the episode has a public transcript or if NotebookLM can access it.

### Example 3: Quick Text-Only Processing

Skip the time-consuming visual content generation:

```bash
python podcast_to_content_automation.py \
  "https://www.youtube.com/watch?v=ABC123" \
  --name "Quick Summary Test" \
  --no-slides \
  --no-social
```

**Time estimate:** 3-5 minutes

Generates only:
- Summaries
- Blog post
- Soundbites

Perfect for quick content repurposing when you don't need slides/images.

### Example 4: Blog Post Only for Website

```bash
python podcast_to_content_automation.py \
  "EPISODE_URL" \
  --name "Blog Post Only" \
  --no-slides \
  --no-social \
  --no-soundbites \
  --no-summary
```

Generates a single markdown file ready to publish.

### Example 5: Social Media Package

```bash
python podcast_to_content_automation.py \
  "EPISODE_URL" \
  --name "Social Media Pack" \
  --no-slides \
  --no-blog
```

Generates:
- Soundbites (quote cards text)
- Social media images (3 formats)
- Summaries (including social media post)

Perfect for creating a social media content bundle.

## 🎯 Use Cases for REPSWITHROSCOE

### Use Case 1: Weekly Podcast to Content Pipeline

**Scenario:** You release a podcast every Monday. By Tuesday morning, you want:
- Blog post on your website
- Instagram carousel (slides)
- 5 quote cards for the week
- Twitter thread (from summaries)

**Solution:**

```bash
# Monday evening, after podcast releases
python podcast_to_content_automation.py \
  "$PODCAST_URL" \
  --name "REPS Week $(date +%U)" \
  --gdrive-folder "YOUR_CONTENT_FOLDER_ID"
```

**Automation:** Set up a cron job or n8n workflow to trigger this when new episode RSS is detected.

### Use Case 2: Fitness Research to Instagram Carousels

**Scenario:** You have scientific papers saved as PDFs and want to create Instagram carousels explaining the research.

**Solution:**

```bash
# First, upload PDF to NotebookLM manually or via API
# Then generate slide deck
python -c "
from podcast_to_content_automation import PodcastContentAutomation, ContentConfig

automation = PodcastContentAutomation()
config = ContentConfig(
    episode_url='',  # Not needed for existing notebook
    notebook_name='Research Paper Analysis',
    generate_slides=True,
    generate_blog=False,
    generate_social_images=True,
    generate_soundbites=False,
    generate_summary=True
)
# Modify to use existing notebook_id
# results = automation.process_episode(config)
"
```

### Use Case 3: Batch Process Podcast Backlog

**Scenario:** You have 20 old podcast episodes you want to convert to blog posts.

**Solution:**

1. Create `my_backlog.yaml`:

```yaml
defaults:
  mcp_url: "http://localhost:8000"
  gdrive_folder_id: "YOUR_FOLDER_ID"
  generate_slides: false
  generate_blog: true
  generate_social_images: false
  generate_soundbites: true
  generate_summary: true

episodes:
  - name: "Episode 1: Mobility Training"
    url: "https://youtube.com/watch?v=ep1"
  - name: "Episode 2: Nutrition Basics"
    url: "https://youtube.com/watch?v=ep2"
  # ... add all 20 episodes

processing:
  delay_between_episodes: 120  # 2 minutes between episodes
  continue_on_error: true
```

2. Run batch processor:

```bash
python batch_processor.py my_backlog.yaml
```

**Time estimate:** ~10-15 min per episode = 3-5 hours total (runs unattended)

## 🔄 Integration with Your Existing Workflows

### Integration with n8n

Create an n8n workflow:

1. **Trigger:** RSS Feed (new podcast episode)
2. **Execute Command:**
   ```bash
   cd /path/to/automation
   source venv/bin/activate
   python podcast_to_content_automation.py \
     "{{ $json.episode_url }}" \
     --name "{{ $json.title }}" \
     --gdrive-folder "YOUR_FOLDER_ID"
   ```
3. **Read File:** Parse `~/podcast_content_outputs/latest_results.json`
4. **Post to Instagram:** Use social images
5. **Publish Blog:** Upload markdown to your CMS
6. **Send Notification:** Slack/Email when complete

### Integration with Zapier/Make

Similar concept:
1. Trigger: New episode in podcast RSS
2. Webhook: Call your Flask web interface API
3. Poll: Check job status endpoint
4. Action: Use generated content URLs

### Local Script Integration

```python
from podcast_to_content_automation import PodcastContentAutomation, ContentConfig

def process_new_episode(url: str, title: str):
    """Your custom function"""
    automation = PodcastContentAutomation()
    
    config = ContentConfig(
        episode_url=url,
        notebook_name=title,
        gdrive_folder_id="YOUR_FOLDER_ID"
    )
    
    results = automation.process_episode(config)
    
    # Your custom post-processing
    blog_path = results['files']['blog']
    # ... upload to your CMS
    
    return results

# Use it
results = process_new_episode(
    "https://youtube.com/watch?v=abc",
    "My New Episode"
)
```

## 💡 Pro Tips

### Tip 1: Pre-Process Transcripts Locally

For very long podcasts (2+ hours), consider:
1. Download audio locally
2. Transcribe with Whisper locally
3. Add transcript as text source to NotebookLM
4. Process with automation

This can be faster and more accurate than YouTube auto-captions.

### Tip 2: Customize NotebookLM Query Prompts

Edit `podcast_to_content_automation.py` to customize the questions asked:

```python
# Line ~250-260 in ContentGenerator.generate_blog_post()
takeaways = self.client.query_notebook(
    notebook_id,
    "List the 5-7 most important key takeaways from this episode "
    "specifically focused on actionable fitness advice."  # Customize this
)
```

### Tip 3: Create Episode Templates

For consistent formatting, create template markdown files and merge with generated content.

### Tip 4: Monitor NotebookLM Rate Limits

Free tier: ~50 queries/day
- Each episode uses ~15-20 queries
- Process max 2-3 episodes per day
- For more, consider NotebookLM Pro

### Tip 5: Google Drive Organization

Create a folder structure:
```
Podcast Content/
├── 2026/
│   ├── January/
│   │   ├── Episode_1_TIMESTAMP/
│   │   └── Episode_2_TIMESTAMP/
│   └── February/
└── Templates/
```

Automate folder creation:

```python
# Before processing
month_folder = automation.gdrive.create_folder(
    datetime.now().strftime("%B"),
    parent_id="YOUR_2026_FOLDER_ID"
)

config.gdrive_folder_id = month_folder
```

## 🐛 Troubleshooting Common Issues

### Issue: "Module 'yaml' not found"

```bash
pip install pyyaml
```

### Issue: Slides/Images Take Too Long

This is normal. Studio content generation takes 5-10 minutes per item.

**Solutions:**
- Process overnight
- Skip slides/images for quick turnaround
- Use batch processing to queue multiple episodes

### Issue: Google Drive Upload Fails

1. Check credentials file exists
2. Verify folder ID is correct
3. Ensure you have write permissions
4. Re-run OAuth flow:
   ```bash
   rm ~/.podcast_automation/token.pickle
   # Next run will prompt for re-auth
   ```

### Issue: NotebookLM Returns Empty/Poor Results

**Possible causes:**
- Audio quality is poor
- No transcript available
- Episode is too short (<5 minutes)

**Solutions:**
- Use episodes with good audio quality
- Verify captions exist for YouTube videos
- Try adding transcript manually first

## 📈 Performance Benchmarks

Based on typical 30-60 minute podcast episodes:

| Content Type | Generation Time | File Size |
|--------------|----------------|-----------|
| Summaries | 1-2 min | ~5 KB |
| Blog Post | 3-5 min | ~10-20 KB |
| Soundbites | 1-2 min | ~2 KB |
| Slide Deck | 5-10 min | ~500 KB - 2 MB |
| Social Images (3) | 15-20 min | ~1-3 MB each |

**Total for full pipeline:** 25-40 minutes per episode

## 🔐 Security Best Practices

1. **Never commit credentials:**
   ```bash
   echo "*.json" >> .gitignore
   echo ".env" >> .gitignore
   echo "venv/" >> .gitignore
   ```

2. **Use environment variables:**
   ```bash
   export GOOGLE_CREDENTIALS_PATH=~/.podcast_automation/credentials.json
   ```

3. **Restrict Google Drive folder permissions:**
   - Only give access to specific folder
   - Don't use full Google Drive scope

4. **Secure your NotebookLM cookies:**
   - They're stored in `~/.notebooklm-mcp`
   - Don't share this directory

## 📞 Support Resources

- **NotebookLM MCP Issues:** https://github.com/jacob-bd/notebooklm-mcp/issues
- **Google Drive API Docs:** https://developers.google.com/drive
- **Flask Documentation:** https://flask.palletsprojects.com/

## 🎉 Success Stories

Share your automation wins! Tag @REPSWITHROSCOE when you:
- Publish blog posts generated from podcasts
- Create Instagram carousels from research papers
- Build automated content pipelines

Happy automating! 🚀
