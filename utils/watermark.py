import asyncio
import subprocess
import os
from pathlib import Path
import tempfile
from aiogram.types import BufferedInputFile
import logging

logger = logging.getLogger(__name__)


class WatermarkProcessor:
    """Video watermark processor using FFmpeg"""

    def __init__(self, logo_path: str = None):
        self.logo_path = logo_path or "assets/logo.png"
        self.temp_dir = tempfile.gettempdir()

    async def add_watermark(self, video_path: str, output_path: str = None) -> str:
        """
        Add watermark to video using FFmpeg

        Args:
            video_path: Path to input video file
            output_path: Path to output video file (optional)

        Returns:
            Path to watermarked video file
        """
        if not os.path.exists(self.logo_path):
            logger.warning(f"Logo file not found: {self.logo_path}")
            return video_path

        if output_path is None:
            output_path = os.path.join(
                self.temp_dir,
                f"watermarked_{os.path.basename(video_path)}"
            )

        try:
            # FFmpeg command to add watermark
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-i', self.logo_path,
                '-filter_complex',
                '[1:v]scale=100:100[logo];[0:v][logo]overlay=10:10',
                '-c:a', 'copy',
                '-y',
                output_path
            ]

            # Run FFmpeg command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"FFmpeg error: {stderr.decode()}")
                return video_path

            if os.path.exists(output_path):
                logger.info(f"Watermark added successfully: {output_path}")
                return output_path
            else:
                logger.warning("Watermark failed, returning original video")
                return video_path

        except Exception as e:
            logger.error(f"Watermark processing error: {e}")
            return video_path

    async def add_text_watermark(self, video_path: str, text: str = "@uzkinobaza_bot", output_path: str = None) -> str:
        """
        Add text watermark to video using FFmpeg

        Args:
            video_path: Path to input video file
            text: Text to add as watermark
            output_path: Path to output video file (optional)

        Returns:
            Path to watermarked video file
        """
        if output_path is None:
            output_path = os.path.join(
                self.temp_dir,
                f"text_watermarked_{os.path.basename(video_path)}"
            )

        try:
            # FFmpeg command to add text watermark
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf',
                f"drawtext=text='{text}':fontcolor=white:fontsize=24:x=10:y=10",
                '-c:a', 'copy',
                '-y',
                output_path
            ]

            # Run FFmpeg command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"FFmpeg error: {stderr.decode()}")
                return video_path

            if os.path.exists(output_path):
                logger.info(f"Text watermark added successfully: {output_path}")
                return output_path
            else:
                logger.warning("Text watermark failed, returning original video")
                return video_path

        except Exception as e:
            logger.error(f"Text watermark processing error: {e}")
            return video_path


# Global watermark processor instance
watermark_processor = WatermarkProcessor()


async def process_video_with_watermark(video_file: bytes, text: str = "@uzkinobaza_bot") -> bytes:
    """
    Process video file with watermark

    Args:
        video_file: Video file bytes
        text: Text to add as watermark

    Returns:
        Processed video file bytes
    """
    # Create temporary files
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as input_file:
        input_file.write(video_file)
        input_path = input_file.name

    try:
        # Add watermark
        output_path = await watermark_processor.add_text_watermark(input_path, text)

        # Read output file
        with open(output_path, 'rb') as f:
            processed_video = f.read()

        # Clean up temporary files
        os.unlink(input_path)
        if output_path != input_path:
            os.unlink(output_path)

        return processed_video

    except Exception as e:
        logger.error(f"Video processing error: {e}")
        # Clean up input file
        if os.path.exists(input_path):
            os.unlink(input_path)
        return video_file
