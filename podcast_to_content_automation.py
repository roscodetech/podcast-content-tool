#!/usr/bin/env python3
"""
Podcast to Content Automation
Takes a podcast episode URL, processes it through NotebookLM, and generates:
- Slide decks
- Blog posts
- Social media images
- Soundbites
- Summaries
All saved to Google Drive
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import requests
from datetime import datetime

# Configure logging - set to DEBUG to see MCP communication
logging.basicConfig(
    level=logging.DEBUG,  # Change to INFO for less verbose output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ContentConfig:
    """Configuration for content generation"""
    episode_url: str
    notebook_name: str
    generate_slides: bool = True
    generate_blog: bool = True
    generate_social_images: bool = True
    generate_soundbites: bool = True
    generate_summary: bool = True
    # Default Google Drive folder for podcast content uploads
    gdrive_folder_id: Optional[str] = "1B2QpuUeXxiq-aKuM3jkfb9aBK3eBObkb"


class NotebookLMClient:
    """Client for interacting with NotebookLM MCP server via subprocess"""

    def __init__(self):
        import subprocess
        import json
        import uuid

        self.process = None
        self.request_id = 0
        self._auth_cookies = None

    def _load_auth_cookies(self) -> Dict[str, str]:
        """Load authentication cookies from the MCP auth file"""
        if self._auth_cookies is not None:
            return self._auth_cookies

        auth_file = Path.home() / '.notebooklm-mcp' / 'auth.json'
        if not auth_file.exists():
            logger.warning("NotebookLM auth file not found - downloads may fail")
            return {}

        try:
            with open(auth_file, 'r') as f:
                auth_data = json.load(f)

            # Extract cookies from auth data
            cookies = {}
            if 'cookies' in auth_data:
                # Parse cookie string if it's a string
                cookie_str = auth_data['cookies']
                if isinstance(cookie_str, str):
                    for part in cookie_str.split(';'):
                        part = part.strip()
                        if '=' in part:
                            key, value = part.split('=', 1)
                            cookies[key.strip()] = value.strip()
                elif isinstance(cookie_str, dict):
                    cookies = cookie_str

            self._auth_cookies = cookies
            logger.debug(f"Loaded {len(cookies)} auth cookies")
            return cookies
        except Exception as e:
            logger.error(f"Error loading auth cookies: {e}")
            return {}

    def download_artifact(self, url: str, output_path: Path) -> bool:
        """Download an artifact using Playwright with authenticated browser profile.

        Both PDFs and images from NotebookLM trigger browser downloads,
        so we use expect_download for all artifact types.
        """
        try:
            from playwright.sync_api import sync_playwright

            # Use persistent profile for authentication
            profile_dir = Path.home() / '.notebooklm-mcp' / 'playwright_profile'

            if not profile_dir.exists():
                logger.error("Download auth not set up. Run: python setup_download_auth.py")
                return False

            with sync_playwright() as p:
                # Use persistent context with saved auth
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled'],
                    accept_downloads=True
                )

                page = context.new_page()

                # All NotebookLM artifact URLs trigger downloads
                try:
                    with page.expect_download(timeout=120000) as download_info:
                        try:
                            page.goto(url)
                        except Exception as e:
                            # "Download is starting" error is expected and means it's working
                            if 'Download is starting' not in str(e):
                                raise

                    download = download_info.value
                    logger.info(f"Downloading: {download.suggested_filename}")
                    download.save_as(str(output_path))

                    # Verify download
                    if output_path.exists():
                        size = output_path.stat().st_size
                        logger.info(f"Downloaded: {output_path} ({size} bytes)")
                        context.close()
                        return True
                    else:
                        logger.error("Download completed but file not found")
                        context.close()
                        return False

                except Exception as e:
                    # Check if we were redirected to login
                    if 'accounts.google.com' in page.url:
                        logger.error("Redirected to login - run setup_download_auth.py to re-authenticate")
                    else:
                        logger.error(f"Download failed: {e}")
                    context.close()
                    return False

        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return False
        except Exception as e:
            logger.error(f"Error downloading artifact: {e}")
            return False
        
    def _ensure_process(self):
        """Start the MCP server process if not already running"""
        if self.process is None:
            import subprocess
            self.process = subprocess.Popen(
                ['notebooklm-mcp'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            # Perform MCP initialization handshake
            self._initialize_mcp()

    def _initialize_mcp(self):
        """Perform MCP protocol initialization handshake"""
        import json

        # Step 1: Send initialize request
        self.request_id += 1
        init_request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "podcast-content-automation",
                    "version": "1.0.0"
                }
            }
        }

        request_str = json.dumps(init_request) + '\n'
        self.process.stdin.write(request_str)
        self.process.stdin.flush()

        # Read initialize response
        response_str = self.process.stdout.readline()
        if not response_str:
            raise Exception("No response from MCP server during initialization")

        response = json.loads(response_str)
        if "error" in response:
            raise Exception(f"MCP initialization error: {response['error']}")

        logger.info(f"MCP server initialized: {response.get('result', {}).get('serverInfo', {})}")

        # Step 2: Send initialized notification (no response expected)
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }

        notif_str = json.dumps(initialized_notification) + '\n'
        self.process.stdin.write(notif_str)
        self.process.stdin.flush()

        # Give server a moment to process
        time.sleep(0.5)

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool via stdio"""
        try:
            self._ensure_process()

            # Create MCP request
            self.request_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            # Send request
            request_str = json.dumps(request) + '\n'
            logger.debug(f"Sending MCP request: {request_str.strip()}")
            self.process.stdin.write(request_str)
            self.process.stdin.flush()

            # Read response - keep reading until we get our response
            while True:
                response_str = self.process.stdout.readline()
                if not response_str:
                    # Check if process is still alive
                    if self.process.poll() is not None:
                        stderr_output = self.process.stderr.read()
                        raise Exception(f"MCP server process died. stderr: {stderr_output}")
                    continue

                logger.debug(f"Received MCP response: {response_str.strip()}")

                try:
                    response = json.loads(response_str)
                except json.JSONDecodeError:
                    logger.warning(f"Non-JSON response from MCP: {response_str}")
                    continue

                # Check if this is our response (matching ID)
                if response.get("id") == self.request_id:
                    break
                # Skip notifications or other messages
                logger.debug(f"Skipping message with id {response.get('id')}")

            if "error" in response:
                raise Exception(f"MCP Error: {response['error']}")

            # Extract result from MCP response
            result = response.get("result", {})

            # Handle different response formats
            if "content" in result:
                # Extract text content from MCP response
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    if "text" in content[0]:
                        # Parse the text as JSON if it's a structured response
                        text = content[0]["text"]
                        try:
                            parsed = json.loads(text)
                            logger.debug(f"Parsed tool result: {parsed}")
                            return parsed
                        except:
                            return {"result": text}
                return result

            return result

        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise
    
    def __del__(self):
        """Clean up subprocess"""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
    
    def create_notebook(self, title: str) -> str:
        """Create a new notebook"""
        logger.info(f"Creating notebook: {title}")
        result = self.call_tool("notebook_create", {"title": title})

        # Check for errors
        if result.get("status") == "error":
            raise Exception(f"Failed to create notebook: {result.get('error')}")

        # The notebook info is nested in the result
        notebook = result.get("notebook", {})
        logger.debug(f"Notebook result: {notebook}")

        notebook_id = notebook.get("id") if isinstance(notebook, dict) else result.get("notebook_id")

        if not notebook_id:
            raise Exception(f"Failed to get notebook ID from response: {result}")

        notebook_url = notebook.get("url", "") if isinstance(notebook, dict) else ""
        logger.info(f"Created notebook with ID: {notebook_id}")
        if notebook_url:
            logger.info(f"Notebook URL: {notebook_url}")

        return notebook_id
    
    def add_url_source(self, notebook_id: str, url: str, display_name: str = None) -> str:
        """Add a URL source to the notebook"""
        logger.info(f"Adding URL source: {url}")
        result = self.call_tool("notebook_add_url", {
            "notebook_id": notebook_id,
            "url": url
        })

        # Check for errors
        if result.get("status") == "error":
            raise Exception(f"Failed to add URL source: {result.get('error')}")

        # The source info is nested in the result
        source = result.get("source", {})
        logger.debug(f"Source result: {source}")

        # Handle different response structures
        if isinstance(source, dict):
            source_id = source.get("id") or source.get("source_id")
        elif isinstance(source, str):
            source_id = source
        else:
            source_id = result.get("source_id")

        if not source_id:
            logger.warning(f"Could not extract source_id from response: {result}")

        logger.info(f"Added source with ID: {source_id}")
        return source_id
    
    def query_notebook(self, notebook_id: str, question: str) -> Dict[str, Any]:
        """Query the notebook with a question"""
        logger.info(f"Querying notebook: {question}")
        result = self.call_tool("notebook_query", {
            "notebook_id": notebook_id,
            "query": question  # MCP server uses 'query' not 'question'
        })
        return result
    
    def create_slide_deck(self, notebook_id: str) -> str:
        """Generate a slide deck from the notebook"""
        logger.info("Creating slide deck...")
        result = self.call_tool("slide_deck_create", {
            "notebook_id": notebook_id,
            "confirm": True  # Required to actually create the artifact
        })
        artifact_id = result.get("artifact_id")
        logger.info(f"Slide deck creation initiated: {artifact_id}")
        return artifact_id
    
    def create_infographic(self, notebook_id: str, orientation: str = "landscape") -> str:
        """Generate an infographic from the notebook"""
        logger.info(f"Creating infographic ({orientation})...")
        result = self.call_tool("infographic_create", {
            "notebook_id": notebook_id,
            "orientation": orientation,
            "confirm": True  # Required to actually create the artifact
        })
        artifact_id = result.get("artifact_id")
        logger.info(f"Infographic creation initiated: {artifact_id}")
        return artifact_id
    
    def create_audio_overview(self, notebook_id: str, format: str = "deep_dive") -> str:
        """Generate an audio overview from the notebook"""
        logger.info(f"Creating audio overview ({format})...")
        result = self.call_tool("audio_overview_create", {
            "notebook_id": notebook_id,
            "format": format,  # Note: MCP server uses 'format' not 'style'
            "confirm": True  # Required to actually create the artifact
        })
        artifact_id = result.get("artifact_id")
        logger.info(f"Audio overview creation initiated: {artifact_id}")
        return artifact_id
    
    def check_studio_status(self, notebook_id: str, artifact_id: str = None) -> Dict[str, Any]:
        """Check the status of studio artifacts.

        Args:
            notebook_id: The notebook ID
            artifact_id: Optional specific artifact to find in the results
        """
        result = self.call_tool("studio_status", {
            "notebook_id": notebook_id
        })

        # If a specific artifact_id is requested, find it in the artifacts list
        if artifact_id and "artifacts" in result:
            for artifact in result["artifacts"]:
                if artifact.get("artifact_id") == artifact_id:
                    return artifact
            # Artifact not found yet, return pending status
            return {"status": "in_progress", "artifact_id": artifact_id}

        return result
    
    def wait_for_artifact(self, notebook_id: str, artifact_id: str, timeout: int = 600) -> str:
        """Wait for an artifact to be ready and return download URL"""
        logger.info(f"Waiting for artifact {artifact_id} to be ready...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.check_studio_status(notebook_id, artifact_id)

            if status.get("status") == "completed":
                # Check various URL fields based on artifact type
                download_url = (
                    status.get("slide_deck_url") or
                    status.get("audio_url") or
                    status.get("video_url") or
                    status.get("infographic_url") or
                    status.get("download_url")
                )
                logger.info(f"Artifact ready: {download_url}")
                return download_url
            elif status.get("status") == "failed":
                raise Exception(f"Artifact generation failed: {status.get('error')}")

            time.sleep(10)  # Check every 10 seconds

        raise TimeoutError(f"Artifact {artifact_id} not ready after {timeout} seconds")


class ContentGenerator:
    """Generate various content types from NotebookLM"""
    
    def __init__(self, client: NotebookLMClient):
        self.client = client
    
    def generate_blog_post(self, notebook_id: str) -> str:
        """Generate a blog post from the notebook"""
        logger.info("Generating blog post...")
        
        # Query for blog post structure
        sections = []
        
        # Get summary
        summary = self.client.query_notebook(
            notebook_id,
            "Provide a comprehensive summary of this podcast episode in 2-3 paragraphs."
        )
        sections.append(f"## Summary\n\n{summary.get('answer', '')}\n\n")
        
        # Get key takeaways
        takeaways = self.client.query_notebook(
            notebook_id,
            "List the 5-7 most important key takeaways from this episode as bullet points."
        )
        sections.append(f"## Key Takeaways\n\n{takeaways.get('answer', '')}\n\n")
        
        # Get main topics
        topics = self.client.query_notebook(
            notebook_id,
            "What are the main topics discussed in this episode? Provide detailed explanations for each."
        )
        sections.append(f"## Main Topics\n\n{topics.get('answer', '')}\n\n")
        
        # Get actionable insights
        insights = self.client.query_notebook(
            notebook_id,
            "What are the actionable insights or practical applications from this episode?"
        )
        sections.append(f"## Actionable Insights\n\n{insights.get('answer', '')}\n\n")
        
        blog_post = "\n".join(sections)
        logger.info("Blog post generated")
        return blog_post
    
    def generate_summary(self, notebook_id: str) -> Dict[str, str]:
        """Generate multiple summary formats"""
        logger.info("Generating summaries...")
        
        summaries = {}
        
        # Short summary (1 paragraph)
        short = self.client.query_notebook(
            notebook_id,
            "Provide a one-paragraph summary of this episode."
        )
        summaries['short'] = short.get('answer', '')
        
        # Medium summary (3-5 bullets)
        medium = self.client.query_notebook(
            notebook_id,
            "Summarize this episode in 3-5 key bullet points."
        )
        summaries['medium'] = medium.get('answer', '')
        
        # Social media summary (280 characters)
        social = self.client.query_notebook(
            notebook_id,
            "Create a compelling 280-character social media post about this episode."
        )
        summaries['social'] = social.get('answer', '')
        
        logger.info("Summaries generated")
        return summaries
    
    def generate_soundbites(self, notebook_id: str, num_bites: int = 5) -> List[str]:
        """Extract quotable soundbites from the episode"""
        logger.info(f"Generating {num_bites} soundbites...")
        
        result = self.client.query_notebook(
            notebook_id,
            f"Extract {num_bites} powerful, quotable soundbites from this episode. "
            f"Each should be 1-2 sentences maximum and work well as standalone quotes for social media."
        )
        
        soundbites_text = result.get('answer', '')
        # Parse soundbites (assuming they're numbered or bulleted)
        soundbites = [line.strip() for line in soundbites_text.split('\n') if line.strip() and any(c.isalpha() for c in line)]
        
        logger.info(f"Generated {len(soundbites)} soundbites")
        return soundbites[:num_bites]


class GoogleDriveUploader:
    """Upload files to Google Drive"""
    
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or os.getenv('GOOGLE_CREDENTIALS_PATH')
        self.service = self._get_service()
    
    def _get_service(self):
        """Initialize Google Drive service"""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import pickle
            
            SCOPES = ['https://www.googleapis.com/auth/drive.file']
            creds = None
            token_path = Path.home() / '.podcast_automation' / 'token.pickle'
            
            if token_path.exists():
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not self.credentials_path or not Path(self.credentials_path).exists():
                        logger.warning("Google Drive credentials not found. Files will be saved locally only.")
                        return None
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            
            return build('drive', 'v3', credentials=creds)
        
        except ImportError:
            logger.warning("Google Drive API libraries not installed. Files will be saved locally only.")
            return None
        except Exception as e:
            logger.error(f"Error initializing Google Drive service: {e}")
            return None
    
    def upload_file(self, file_path: str, folder_id: Optional[str] = None, mime_type: Optional[str] = None) -> Optional[str]:
        """Upload a file to Google Drive"""
        if not self.service:
            logger.warning(f"Cannot upload {file_path} - Google Drive not configured")
            return None
        
        try:
            from googleapiclient.http import MediaFileUpload
            
            file_metadata = {
                'name': Path(file_path).name
            }
            
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            logger.info(f"Uploaded {file_path} to Google Drive: {file.get('webViewLink')}")
            return file.get('webViewLink')
        
        except Exception as e:
            logger.error(f"Error uploading file to Google Drive: {e}")
            return None
    
    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """Create a folder in Google Drive"""
        if not self.service:
            return None
        
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id, webViewLink'
            ).execute()
            
            logger.info(f"Created folder {folder_name}: {folder.get('webViewLink')}")
            return folder.get('id')
        
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return None


class PodcastContentAutomation:
    """Main automation orchestrator"""
    
    def __init__(self):
        self.notebooklm = NotebookLMClient()
        self.content_gen = ContentGenerator(self.notebooklm)
        self.gdrive = GoogleDriveUploader()
        self.output_dir = Path.home() / 'podcast_content_outputs'
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_episode(self, config: ContentConfig) -> Dict[str, Any]:
        """Process a podcast episode and generate all content"""
        logger.info(f"Processing episode: {config.episode_url}")
        
        results = {
            'notebook_id': None,
            'files': {},
            'gdrive_links': {}
        }
        
        try:
            # Create notebook
            notebook_id = self.notebooklm.create_notebook(config.notebook_name)
            results['notebook_id'] = notebook_id
            
            # Add episode as source
            self.notebooklm.add_url_source(
                notebook_id,
                config.episode_url,
                f"Episode: {config.notebook_name}"
            )
            
            # Wait for processing
            logger.info("Waiting for source to be processed...")
            time.sleep(30)  # Give NotebookLM time to process
            
            # Create episode folder with format: [notebook_name]_[yyyy-mm-dd]
            timestamp = datetime.now().strftime("%Y-%m-%d")
            episode_folder = self.output_dir / f"{config.notebook_name}_{timestamp}"
            episode_folder.mkdir(parents=True, exist_ok=True)
            
            # Create Google Drive subfolder for this episode
            gdrive_folder_id = None
            if config.gdrive_folder_id and self.gdrive.service:
                folder_name = f"{config.notebook_name}_{timestamp}"
                gdrive_folder_id = self.gdrive.create_folder(
                    folder_name,
                    config.gdrive_folder_id
                )
                if gdrive_folder_id:
                    logger.info(f"Created Google Drive folder: {folder_name}")
            
            # Generate summaries
            if config.generate_summary:
                summaries = self.content_gen.generate_summary(notebook_id)
                summaries_file = episode_folder / 'summaries.json'
                with open(summaries_file, 'w') as f:
                    json.dump(summaries, f, indent=2)
                results['files']['summaries'] = str(summaries_file)
                
                # Upload to Google Drive
                if gdrive_folder_id:
                    link = self.gdrive.upload_file(str(summaries_file), gdrive_folder_id, 'application/json')
                    if link:
                        results['gdrive_links']['summaries'] = link
            
            # Generate blog post
            if config.generate_blog:
                blog_post = self.content_gen.generate_blog_post(notebook_id)
                blog_file = episode_folder / 'blog_post.md'
                with open(blog_file, 'w') as f:
                    f.write(f"# {config.notebook_name}\n\n")
                    f.write(blog_post)
                results['files']['blog'] = str(blog_file)
                
                # Upload to Google Drive
                if gdrive_folder_id:
                    link = self.gdrive.upload_file(str(blog_file), gdrive_folder_id, 'text/markdown')
                    if link:
                        results['gdrive_links']['blog'] = link
            
            # Generate soundbites
            if config.generate_soundbites:
                soundbites = self.content_gen.generate_soundbites(notebook_id)
                soundbites_file = episode_folder / 'soundbites.txt'
                with open(soundbites_file, 'w') as f:
                    for i, bite in enumerate(soundbites, 1):
                        f.write(f"{i}. {bite}\n\n")
                results['files']['soundbites'] = str(soundbites_file)
                
                # Upload to Google Drive
                if gdrive_folder_id:
                    link = self.gdrive.upload_file(str(soundbites_file), gdrive_folder_id, 'text/plain')
                    if link:
                        results['gdrive_links']['soundbites'] = link
            
            # Initialize artifact URLs dict for manual download fallback
            results['artifact_urls'] = {}

            # Generate slide deck
            if config.generate_slides:
                artifact_id = self.notebooklm.create_slide_deck(notebook_id)
                download_url = self.notebooklm.wait_for_artifact(notebook_id, artifact_id)

                # Save URL for manual download
                results['artifact_urls']['slides'] = download_url

                # Try downloading the file using authenticated session (NotebookLM returns PDF format)
                slides_file = episode_folder / 'slides.pdf'
                if self.notebooklm.download_artifact(download_url, slides_file):
                    results['files']['slides'] = str(slides_file)

                    # Upload to Google Drive
                    if gdrive_folder_id:
                        link = self.gdrive.upload_file(
                            str(slides_file),
                            gdrive_folder_id,
                            'application/pdf'
                        )
                        if link:
                            results['gdrive_links']['slides'] = link
                else:
                    logger.warning("Auto-download failed - URL saved for manual download")

            # Generate social media images (infographics)
            if config.generate_social_images:
                for orientation in ['landscape', 'portrait', 'square']:
                    artifact_id = self.notebooklm.create_infographic(notebook_id, orientation)
                    download_url = self.notebooklm.wait_for_artifact(notebook_id, artifact_id)

                    # Save URL for manual download
                    results['artifact_urls'][f'social_{orientation}'] = download_url

                    # Try downloading the file using authenticated session
                    image_file = episode_folder / f'social_{orientation}.png'
                    if self.notebooklm.download_artifact(download_url, image_file):
                        results['files'][f'social_{orientation}'] = str(image_file)

                        # Upload to Google Drive
                        if gdrive_folder_id:
                            link = self.gdrive.upload_file(str(image_file), gdrive_folder_id, 'image/png')
                            if link:
                                results['gdrive_links'][f'social_{orientation}'] = link
                    else:
                        logger.warning(f"Auto-download failed for {orientation} - URL saved for manual download")
            
            logger.info("Content generation complete!")
            logger.info(f"Local files saved to: {episode_folder}")

            # Save artifact URLs for manual download if automated download failed
            if results.get('artifact_urls'):
                urls_file = episode_folder / 'artifact_urls.txt'
                with open(urls_file, 'w') as f:
                    f.write("# Open these URLs in your browser to download artifacts\n")
                    f.write(f"# (You must be logged into NotebookLM)\n\n")
                    for name, url in results['artifact_urls'].items():
                        f.write(f"{name}:\n{url}\n\n")
                logger.info(f"Artifact URLs saved to: {urls_file}")
                logger.info("Open these URLs in your browser to download manually")

            if results['gdrive_links']:
                logger.info("Google Drive links:")
                for name, link in results['gdrive_links'].items():
                    logger.info(f"  {name}: {link}")
            
            return results
        
        except Exception as e:
            logger.error(f"Error processing episode: {e}")
            raise


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Podcast to Content Automation')
    parser.add_argument('episode_url', help='URL of the podcast episode')
    parser.add_argument('--name', required=True, help='Name for the notebook')
    parser.add_argument('--gdrive-folder', help='Google Drive folder ID for uploads (default: podcast content folder)')
    parser.add_argument('--no-gdrive', action='store_true', help='Skip Google Drive upload')
    parser.add_argument('--no-slides', action='store_true', help='Skip slide generation')
    parser.add_argument('--no-blog', action='store_true', help='Skip blog post generation')
    parser.add_argument('--no-social', action='store_true', help='Skip social media images')
    parser.add_argument('--no-soundbites', action='store_true', help='Skip soundbites')
    parser.add_argument('--no-summary', action='store_true', help='Skip summaries')

    args = parser.parse_args()

    # Determine Google Drive folder: use provided, default, or None if disabled
    if args.no_gdrive:
        gdrive_folder = None
    elif args.gdrive_folder:
        gdrive_folder = args.gdrive_folder
    else:
        gdrive_folder = "1B2QpuUeXxiq-aKuM3jkfb9aBK3eBObkb"  # Default folder

    config = ContentConfig(
        episode_url=args.episode_url,
        notebook_name=args.name,
        generate_slides=not args.no_slides,
        generate_blog=not args.no_blog,
        generate_social_images=not args.no_social,
        generate_soundbites=not args.no_soundbites,
        generate_summary=not args.no_summary,
        gdrive_folder_id=gdrive_folder
    )
    
    automation = PodcastContentAutomation()
    results = automation.process_episode(config)
    
    # Save results summary
    results_file = Path.home() / 'podcast_content_outputs' / 'latest_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")


if __name__ == '__main__':
    main()