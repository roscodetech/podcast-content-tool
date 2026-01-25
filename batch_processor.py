#!/usr/bin/env python3
"""
Batch Podcast Processing
Process multiple podcast episodes from a YAML configuration file
"""

import yaml
import time
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import json

from podcast_to_content_automation import (
    PodcastContentAutomation,
    ContentConfig
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BatchProcessor:
    """Process multiple episodes from configuration"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.automation = PodcastContentAutomation(
            mcp_url=self.config['defaults']['mcp_url']
        )
        self.results = []
    
    def _load_config(self) -> Dict:
        """Load YAML configuration"""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _merge_config(self, episode: Dict) -> ContentConfig:
        """Merge episode config with defaults"""
        defaults = self.config['defaults']
        
        return ContentConfig(
            episode_url=episode['url'],
            notebook_name=episode['name'],
            generate_slides=episode.get('generate_slides', defaults['generate_slides']),
            generate_blog=episode.get('generate_blog', defaults['generate_blog']),
            generate_social_images=episode.get('generate_social_images', defaults['generate_social_images']),
            generate_soundbites=episode.get('generate_soundbites', defaults['generate_soundbites']),
            generate_summary=episode.get('generate_summary', defaults['generate_summary']),
            gdrive_folder_id=episode.get('gdrive_folder_id', defaults['gdrive_folder_id'])
        )
    
    def process_all(self):
        """Process all episodes in configuration"""
        episodes = self.config['episodes']
        processing_opts = self.config.get('processing', {})
        
        total = len(episodes)
        logger.info(f"Starting batch processing of {total} episodes...")
        
        for i, episode in enumerate(episodes, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing episode {i}/{total}: {episode['name']}")
            logger.info(f"{'='*60}\n")
            
            try:
                # Merge with defaults
                config = self._merge_config(episode)
                
                # Process episode
                start_time = time.time()
                result = self.automation.process_episode(config)
                elapsed = time.time() - start_time
                
                # Store result
                self.results.append({
                    'episode': episode['name'],
                    'status': 'success',
                    'elapsed_seconds': elapsed,
                    'notebook_id': result['notebook_id'],
                    'files': result['files'],
                    'gdrive_links': result.get('gdrive_links', {})
                })
                
                logger.info(f"✅ Completed in {elapsed:.1f} seconds")
                
            except Exception as e:
                logger.error(f"❌ Failed: {e}")
                
                self.results.append({
                    'episode': episode['name'],
                    'status': 'failed',
                    'error': str(e)
                })
                
                # Continue or abort?
                if not processing_opts.get('continue_on_error', True):
                    logger.error("Aborting batch processing due to error")
                    break
            
            # Delay between episodes
            if i < total:
                delay = processing_opts.get('delay_between_episodes', 60)
                logger.info(f"Waiting {delay} seconds before next episode...")
                time.sleep(delay)
        
        logger.info(f"\n{'='*60}")
        logger.info("Batch processing complete!")
        logger.info(f"{'='*60}\n")
        
        # Generate summary
        self._generate_summary()
    
    def _generate_summary(self):
        """Generate processing summary report"""
        output_opts = self.config.get('output', {})
        
        # Count successes and failures
        successful = sum(1 for r in self.results if r['status'] == 'success')
        failed = sum(1 for r in self.results if r['status'] == 'failed')
        
        # Calculate total time
        total_time = sum(r.get('elapsed_seconds', 0) for r in self.results if r['status'] == 'success')
        
        # Create summary
        summary = {
            'batch_run': datetime.now().isoformat(),
            'total_episodes': len(self.results),
            'successful': successful,
            'failed': failed,
            'total_processing_time_seconds': total_time,
            'results': self.results
        }
        
        # Save summary
        if output_opts.get('create_summary_report', True):
            summary_file = Path.home() / 'podcast_content_outputs' / f'batch_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            summary_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Summary saved to: {summary_file}")
            
            # Upload to Google Drive if configured
            if output_opts.get('upload_summary_to_gdrive', False):
                gdrive_folder = self.config['defaults'].get('gdrive_folder_id')
                if gdrive_folder and self.automation.gdrive.service:
                    link = self.automation.gdrive.upload_file(
                        str(summary_file),
                        gdrive_folder,
                        'application/json'
                    )
                    if link:
                        logger.info(f"Summary uploaded to Google Drive: {link}")
        
        # Print summary to console
        print("\n" + "="*60)
        print("BATCH PROCESSING SUMMARY")
        print("="*60)
        print(f"Total Episodes: {len(self.results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total Time: {total_time/60:.1f} minutes")
        print("\nResults:")
        
        for result in self.results:
            status_icon = "✅" if result['status'] == 'success' else "❌"
            print(f"  {status_icon} {result['episode']}")
            
            if result['status'] == 'success':
                print(f"     Time: {result.get('elapsed_seconds', 0)/60:.1f} min")
                if result.get('gdrive_links'):
                    print(f"     Files: {len(result['gdrive_links'])} uploaded to Google Drive")
            else:
                print(f"     Error: {result.get('error', 'Unknown error')}")
        
        print("="*60 + "\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch Podcast Processing')
    parser.add_argument(
        'config',
        nargs='?',
        default='batch_config.yaml',
        help='Path to YAML configuration file (default: batch_config.yaml)'
    )
    
    args = parser.parse_args()
    
    config_path = Path(args.config)
    
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        print("\nCreate a configuration file based on batch_config.yaml example")
        return 1
    
    try:
        processor = BatchProcessor(args.config)
        processor.process_all()
        return 0
    
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
