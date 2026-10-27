# The Rain in the Nameless Valley

A complete edited YouTube story explainer assembled from the narration and still images in this repository. The finished master is in the repository root as `rain-in-the-nameless-valley-explainer.mp4`.

## Deliverables

- `rain-in-the-nameless-valley-explainer.mp4` — 1080p, 30 fps, H.264 video with stereo AAC narration.
- `rain-in-the-nameless-valley-thumbnail.jpg` — YouTube thumbnail.
- `youtube-chapters.txt` — chapter timestamps for the description.

## Rebuild

Python 3.10+ is required. Install the video-rendering dependencies in a virtual environment, then run the renderer:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-video.txt
.venv/bin/python render_youtube_video.py
```

The renderer extracts the supplied images into `.video_work/`, creates the overlays and end slate, and uses the bundled FFmpeg from `imageio-ffmpeg`. The source narration has a damaged tail; the renderer decodes its valid audio portion and keeps picture and sound in sync.
