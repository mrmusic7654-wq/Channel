#!/usr/bin/env python3
"""Rebuild the 1080p story edit from the supplied MP3 and image archive.

Requirements: Pillow and imageio-ffmpeg. The source images receive slow, eased
Ken Burns moves; act changes dip briefly to black; the voice is leveled for web.
"""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path
from zipfile import ZipFile

from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "Oct 25 - 18_31.zip"
AUDIO = ROOT / "the_rain_in_the_nameless_valley_did_not_fall_it_w.mp3"
OUTPUT = ROOT / "rain-in-the-nameless-valley-explainer.mp4"
THUMBNAIL = ROOT / "rain-in-the-nameless-valley-thumbnail.jpg"
CHAPTERS = ROOT / "youtube-chapters.txt"
WORK = ROOT / ".video_work"
CLEAN_AUDIO = WORK / "narration_clean.wav"

WIDTH, HEIGHT, FPS = 1920, 1080, 30
DIP = 0.18
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

# Per-shot visible holds. Repeated landscape/character images reinforce key beats.
SEQUENCE: list[tuple[int, float]] = []
SEQUENCE += [(i, 6.0) for i in (19, 18, 20, 21)]
SEQUENCE += [(i, 9.0) for i in (12, 24, 23, 13, 14, 2, 6, 7, 3, 8)]
SEQUENCE += [(i, 8.6) for i in (15, 16, 17, 22, 25, 26, 11, 20, 21, 18)]
SEQUENCE += [(i, 5.0) for i in (29, 30, 28, 32, 36, 31, 27, 33, 34)]
SEQUENCE += [(i, 11.5) for i in (9, 10, 11, 0, 1, 4, 5, 35)]
SEQUENCE += [(7, 9.0), (14, 9.0), (15, 9.0), (19, 257 / FPS)]

SECTION_RANGES = [
    (0, 4, "opening"),
    (4, 14, "fall"),
    (14, 24, "world-shifts"),
    (24, 33, "hunter"),
    (33, 41, "counterstrike"),
    (41, 45, "aftermath"),
]
CHAPTERS_LIST = [
    ("01", "THE FALL"),
    ("02", "THE WORLD SHIFTS"),
    ("03", "THE HUNTER"),
    ("04", "THE COUNTERSTRIKE"),
    ("05", "THE AFTERMATH"),
]


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def fit_text(draw: ImageDraw.ImageDraw, text: str, font_obj: ImageFont.FreeTypeFont, max_width: int) -> str:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=font_obj)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\n".join(lines)


def make_title_overlay(path: Path) -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pixels = image.load()
    for y in range(545, HEIGHT):
        t = (y - 545) / (HEIGHT - 545)
        alpha = int(190 * (t ** 1.55))
        for x in range(WIDTH):
            pixels[x, y] = (4, 9, 15, alpha)
    draw = ImageDraw.Draw(image)
    gold = (220, 181, 111, 255)
    ivory = (246, 243, 234, 255)
    muted = (197, 206, 211, 255)
    draw.rounded_rectangle((112, 651, 123, 931), radius=5, fill=gold)
    draw.text((151, 655), "STORY EXPLAINED", font=font(FONT_SANS_BOLD, 22), fill=gold)
    title_font = font(FONT_SERIF_BOLD, 72)
    draw.text((148, 699), "THE RAIN IN THE", font=title_font, fill=ivory,
              stroke_width=2, stroke_fill=(0, 0, 0, 130))
    draw.text((148, 783), "NAMELESS VALLEY", font=title_font, fill=ivory,
              stroke_width=2, stroke_fill=(0, 0, 0, 130))
    draw.text((151, 889), "A tale of betrayal, sound, and survival", font=font(FONT_SANS, 27), fill=muted)
    image.save(path)


def make_chapter_overlay(path: Path, number: str, heading: str) -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((95, 100, 650, 224), radius=14,
                           fill=(5, 11, 18, 168), outline=(220, 181, 111, 105), width=2)
    draw.rounded_rectangle((95, 100, 103, 224), radius=4, fill=(220, 181, 111, 255))
    draw.text((132, 118), f"CHAPTER {number}", font=font(FONT_SANS_BOLD, 19), fill=(220, 181, 111, 255))
    heading_font = font(FONT_SANS_BOLD, 34 if len(heading) < 15 else 28)
    draw.multiline_text((132, 151), fit_text(draw, heading, heading_font, 470),
                        font=heading_font, fill=(247, 246, 240, 255), spacing=3)
    image.save(path)


def make_end_card(source: Image.Image, path: Path) -> None:
    bg = ImageOps.fit(source.convert("RGB"), (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(12))
    bg = Image.alpha_composite(bg.convert("RGBA"), Image.new("RGBA", (WIDTH, HEIGHT), (3, 9, 16, 190)))
    draw = ImageDraw.Draw(bg)
    gold = (220, 181, 111, 255)
    ivory = (246, 243, 234, 255)
    muted = (195, 205, 212, 255)
    draw.rounded_rectangle((322, 257, 1598, 824), radius=30,
                           fill=(5, 12, 19, 154), outline=(220, 181, 111, 92), width=2)
    draw.text((WIDTH // 2, 342), "THE SYMPHONY OF DEATH", anchor="mm",
              font=font(FONT_SANS_BOLD, 25), fill=gold)
    title_font = font(FONT_SERIF_BOLD, 63)
    draw.text((WIDTH // 2, 431), "THE RAIN IN THE", anchor="mm", font=title_font, fill=ivory)
    draw.text((WIDTH // 2, 512), "NAMELESS VALLEY", anchor="mm", font=title_font, fill=ivory)
    draw.rounded_rectangle((774, 578, 1146, 582), radius=2, fill=gold)
    draw.text((WIDTH // 2, 643), "THEY THOUGHT THEY HAD BLINDED HIM.", anchor="mm",
              font=font(FONT_SANS_BOLD, 22), fill=muted)
    draw.text((WIDTH // 2, 685), "THEY TAUGHT HIM TO LISTEN.", anchor="mm",
              font=font(FONT_SANS_BOLD, 22), fill=ivory)
    draw.text((WIDTH // 2, 765), "LIKE  ·  SUBSCRIBE  ·  SHARE", anchor="mm",
              font=font(FONT_SANS_BOLD, 18), fill=gold)
    bg.convert("RGB").save(path, quality=95)


def make_thumbnail(source: Image.Image, path: Path) -> None:
    width, height = 1280, 720
    thumb = ImageOps.fit(source.convert("RGB"), (width, height), method=Image.Resampling.LANCZOS)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pix = overlay.load()
    for x in range(width):
        t = max(0.0, 1.0 - x / 920)
        alpha = int(222 * (t ** 1.2))
        for y in range(height):
            pix[x, y] = (4, 9, 15, alpha)
    thumb = Image.alpha_composite(thumb.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(thumb)
    gold = (231, 183, 98, 255)
    ivory = (250, 247, 238, 255)
    draw.rounded_rectangle((64, 93, 75, 597), radius=5, fill=gold)
    draw.text((104, 110), "A DARK FANTASY STORY", font=font(FONT_SANS_BOLD, 21), fill=gold)
    draw.text((98, 212), "HE COULD", font=font(FONT_SANS_BOLD, 74), fill=ivory,
              stroke_width=3, stroke_fill=(0, 0, 0, 170))
    draw.text((98, 300), "HEAR THE", font=font(FONT_SANS_BOLD, 74), fill=ivory,
              stroke_width=3, stroke_fill=(0, 0, 0, 170))
    draw.text((98, 388), "WOLF.", font=font(FONT_SANS_BOLD, 94), fill=gold,
              stroke_width=4, stroke_fill=(0, 0, 0, 190))
    draw.text((104, 529), "THE NAMELESS VALLEY", font=font(FONT_SANS_BOLD, 19), fill=(211, 219, 221, 255))
    thumb.convert("RGB").save(path, quality=93, optimize=True)


def composite_asset(base: Image.Image, overlay_path: Path, output_path: Path) -> Path:
    base = base.convert("RGBA")
    overlay = Image.open(overlay_path).convert("RGBA").resize(base.size, Image.Resampling.LANCZOS)
    Image.alpha_composite(base, overlay).convert("RGB").save(output_path, quality=95)
    return output_path


def run(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode:
        raise SystemExit(result.returncode)


def prepare_audio(ffmpeg: str) -> float:
    # The provided MP3 has malformed tail frames; decode the valid audio once to PCM.
    run([
        ffmpeg, "-hide_banner", "-loglevel", "fatal", "-y",
        "-fflags", "+discardcorrupt", "-err_detect", "ignore_err",
        "-i", str(AUDIO), "-vn", "-ac", "1", "-ar", "48000",
        "-c:a", "pcm_s16le", str(CLEAN_AUDIO),
    ])
    with wave.open(str(CLEAN_AUDIO), "rb") as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


def render_shot(ffmpeg: str, source: Path, hold: float, output: Path, shot_index: int,
                fade_in: float = 0.0, fade_out: float = 0.0) -> int:
    frames = int(round(hold * FPS))
    ease = f"(0.5-0.5*cos(PI*on/{frames}))"
    if shot_index % 2 == 0:
        zoom = f"1.025+0.05*{ease}"
        x = f"(iw-iw/zoom)*(0.36+0.28*{ease})"
        y = f"(ih-ih/zoom)*(0.40+0.20*{ease})"
    else:
        zoom = f"1.075-0.05*{ease}"
        x = f"(iw-iw/zoom)*(0.64-0.28*{ease})"
        y = f"(ih-ih/zoom)*(0.60-0.20*{ease})"
    filters = [
        f"zoompan=z='{zoom}':x='{x}':y='{y}':d=1:s={WIDTH}x{HEIGHT}:fps={FPS}",
        f"trim=end_frame={frames}",
        "setpts=PTS-STARTPTS",
        "eq=contrast=1.035:saturation=0.96:brightness=-0.004",
        f"fps={FPS}", "setsar=1", "format=yuv420p",
    ]
    if fade_in > 0:
        filters.append(f"fade=t=in:st=0:d={fade_in:.3f}")
    if fade_out > 0:
        filters.append(f"fade=t=out:st={max(0.0, frames/FPS-fade_out):.6f}:d={fade_out:.3f}")
    run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-framerate", str(FPS), "-i", str(source),
        "-vf", ",".join(filters), "-frames:v", str(frames), "-an",
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "animation", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", str(FPS * 2), "-sc_threshold", "0",
        "-video_track_timescale", "90000", str(output),
    ])
    return frames


def concat_video(ffmpeg: str, clips: list[Path], list_path: Path, output: Path) -> None:
    entries = ["ffconcat version 1.0"]
    entries.extend(f"file '{clip.as_posix()}'" for clip in clips)
    list_path.write_text("\n".join(entries) + "\n", encoding="utf-8")
    run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-c", "copy", "-video_track_timescale", "90000", str(output),
    ])


def render_final(ffmpeg: str, storyboard: Path, audio_duration: float) -> None:
    graph = (
        f"[0:v]fps={FPS},setsar=1,format=yuv420p,settb=1/{FPS},setpts=PTS-STARTPTS,"
        f"fade=t=out:st={max(0.0, audio_duration-1.05):.6f}:d=1.05,format=yuv420p[vout];"
        f"[1:a]highpass=f=75,lowpass=f=10500,loudnorm=I=-16:TP=-1.5:LRA=11,"
        f"aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,"
        f"atrim=duration={audio_duration:.6f},"
        f"afade=t=out:st={max(0.0, audio_duration-1.35):.6f}:d=1.30,asetpts=PTS-STARTPTS[aout]"
    )
    run([
        ffmpeg, "-hide_banner", "-loglevel", "warning", "-filter_complex_threads", "2", "-y",
        "-i", str(storyboard), "-i", str(CLEAN_AUDIO), "-filter_complex", graph,
        "-map", "[vout]", "-map", "[aout]", "-t", f"{audio_duration:.6f}",
        "-c:v", "libx264", "-preset", "medium", "-tune", "animation",
        "-b:v", "1750k", "-maxrate", "2400k", "-bufsize", "4800k",
        "-profile:v", "high", "-level:v", "4.1", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-g", str(FPS * 2),
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart",
        "-metadata", "title=The Rain in the Nameless Valley | Story Explained",
        "-metadata", "comment=Edited from user-provided narration and artwork",
        str(OUTPUT),
    ])


def main() -> None:
    for path in (ARCHIVE, AUDIO):
        if not path.is_file():
            raise FileNotFoundError(path)
    WORK.mkdir(exist_ok=True)
    ffmpeg = get_ffmpeg_exe()
    audio_duration = prepare_audio(ffmpeg)
    story_duration = sum(round(hold * FPS) for _, hold in SEQUENCE) / FPS

    with ZipFile(ARCHIVE) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith((".jpg", ".jpeg", ".png"))]
        if len(names) != 37:
            raise RuntimeError(f"Expected 37 supplied stills, found {len(names)}")
        extracted: list[Path] = []
        originals: list[Image.Image] = []
        for index, name in enumerate(names):
            path = WORK / f"source_{index:02d}.jpg"
            path.write_bytes(archive.read(name))
            extracted.append(path)
            originals.append(Image.open(path).convert("RGB"))

    render_sources = [extracted[image_index] for image_index, _ in SEQUENCE]
    title_overlay = WORK / "title.png"
    make_title_overlay(title_overlay)
    render_sources[0] = composite_asset(originals[SEQUENCE[0][0]], title_overlay, WORK / "title_frame.jpg")
    chapter_clip_indices = [4, 14, 24, 33, 41]
    for i, (clip_index, (number, heading)) in enumerate(zip(chapter_clip_indices, CHAPTERS_LIST), 1):
        overlay = WORK / f"chapter_{i:02d}.png"
        make_chapter_overlay(overlay, number, heading)
        image_index = SEQUENCE[clip_index][0]
        render_sources[clip_index] = composite_asset(originals[image_index], overlay, WORK / f"chapter_{i:02d}_frame.jpg")

    end_card_path = WORK / "end_card.jpg"
    make_end_card(originals[19], end_card_path)
    make_thumbnail(originals[34], THUMBNAIL)

    clips_dir = WORK / "clips"
    clips_dir.mkdir(exist_ok=True)
    clips: list[Path] = []
    section_starts = {0} | {start for start, _, _ in SECTION_RANGES[1:]}
    section_ends = {end - 1 for _, end, _ in SECTION_RANGES}
    for i, (_, hold) in enumerate(SEQUENCE):
        clip = clips_dir / f"shot_{i:02d}.mp4"
        fade_in = 0.8 if i == 0 else (DIP if i in section_starts else 0.0)
        fade_out = DIP if i in section_ends else 0.0
        render_shot(ffmpeg, render_sources[i], hold, clip, i, fade_in, fade_out)
        clips.append(clip)
        if (i + 1) % 5 == 0 or i + 1 == len(SEQUENCE):
            print(f"Rendered shot {i+1}/{len(SEQUENCE)}", flush=True)

    end_frames = max(1, round((audio_duration - story_duration) * FPS))
    end_clip = clips_dir / "end_card.mp4"
    render_shot(ffmpeg, end_card_path, end_frames / FPS, end_clip, len(SEQUENCE), DIP, 0.0)
    storyboard = WORK / "storyboard.mp4"
    concat_video(ffmpeg, clips + [end_clip], WORK / "storyboard.ffconcat", storyboard)
    print(f"Encoding the 1080p master ({audio_duration:.2f}s)…", flush=True)
    render_final(ffmpeg, storyboard, audio_duration)

    chapters = [
        "00:00 The Nameless Valley",
        "00:24 The Fall",
        "01:54 The World Shifts",
        "03:20 The Hunter",
        "04:05 The Counterstrike",
        "05:37 The Aftermath",
        "06:12 The Symphony of Death",
    ]
    CHAPTERS.write_text("\n".join(chapters) + "\n", encoding="utf-8")
    size = OUTPUT.stat().st_size
    print(f"Done: {OUTPUT.name} ({size/1_000_000:.1f} MB, {audio_duration:.2f}s)")
    print(f"Thumbnail: {THUMBNAIL.name}; chapter list: {CHAPTERS.name}")


if __name__ == "__main__":
    main()
