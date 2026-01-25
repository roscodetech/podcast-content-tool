"""
YouTube Transcript Fetcher
Fetches full transcripts from any public YouTube video with captions.
"""

from youtube_transcript_api import YouTubeTranscriptApi
import re
import sys


def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'  # Direct video ID
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract video ID from: {url}")


def get_transcript(url: str, language_codes: list = None) -> dict:
    """
    Fetch transcript from a YouTube video.

    Args:
        url: YouTube URL or video ID
        language_codes: Preferred language codes (e.g., ['en', 'en-US'])

    Returns:
        dict with 'text' (formatted), 'segments' (timestamped), and 'video_id'
    """
    video_id = extract_video_id(url)

    if language_codes is None:
        language_codes = ['en', 'en-US', 'en-GB']

    # New API (v1.x): use fetch() method
    ytt_api = YouTubeTranscriptApi()

    try:
        # Fetch transcript - returns FetchedTranscript object
        transcript = ytt_api.fetch(video_id, languages=language_codes)
        segments = [{'text': snippet.text, 'start': snippet.start, 'duration': snippet.duration}
                    for snippet in transcript]
        print(f"Found transcript with {len(segments)} segments")
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        raise

    # Combine all text
    full_text = ' '.join(seg['text'] for seg in segments)

    return {
        'video_id': video_id,
        'text': full_text,
        'segments': segments
    }


def format_with_timestamps(segments: list) -> str:
    """Format transcript with timestamps."""
    lines = []
    for seg in segments:
        minutes = int(seg['start'] // 60)
        seconds = int(seg['start'] % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        lines.append(f"{timestamp} {seg['text']}")
    return '\n'.join(lines)


if __name__ == "__main__":
    # Test URL
    test_url = "https://www.youtube.com/watch?v=cmUbiG_R7n4"

    if len(sys.argv) > 1:
        test_url = sys.argv[1]

    print(f"Fetching transcript for: {test_url}\n")
    print("=" * 60)

    try:
        result = get_transcript(test_url)

        print(f"\nVideo ID: {result['video_id']}")
        print(f"Total segments: {len(result['segments'])}")
        print("\n" + "=" * 60)
        print("TRANSCRIPT WITH TIMESTAMPS:")
        print("=" * 60 + "\n")

        timestamped = format_with_timestamps(result['segments'])
        print(timestamped)

        # Save to file
        output_file = f"transcript_{result['video_id']}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Video: {test_url}\n")
            f.write(f"Video ID: {result['video_id']}\n")
            f.write("=" * 60 + "\n\n")
            f.write(timestamped)

        print(f"\n\nTranscript saved to: {output_file}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
