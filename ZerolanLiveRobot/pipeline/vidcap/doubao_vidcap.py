import os
import base64
import json
import subprocess
import tempfile
from typing import List

from typeguard import typechecked
from zerolan.data.pipeline.vid_cap import VidCapQuery, VidCapPrediction
from pipeline.base.base_async import BaseAsyncPipeline
from pipeline.vidcap.config import VidCapPipelineConfig

class DoubaoVidCapPipeline(BaseAsyncPipeline):
    def __init__(self, config: VidCapPipelineConfig):
        super().__init__(base_url="https://ark.cn-beijing.volces.com/api/v3/")
        self._model_id = "doubao-1.5-vision-pro-250328"
        self._api_key = config.api_key if hasattr(config, "api_key") else os.environ.get("ARK_API_KEY", "")
        self._predict_endpoint = "chat/completions"

    async def _extract_frames(self, video_path: str, num_frames: int = 4) -> List[str]:
        """Extracts evenly spaced frames from a video and returns them as base64 strings."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        # Get video duration using ffprobe
        probe_cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', video_path
        ]
        
        try:
            # Note: in a real async environment we should use asyncio.create_subprocess_exec
            # For simplicity in this implementation we'll use subprocess
            duration_str = subprocess.check_output(probe_cmd, stderr=subprocess.STDOUT).decode('utf-8').strip()
            duration = float(duration_str)
        except (subprocess.CalledProcessError, ValueError):
            # Fallback if duration extraction fails
            duration = 10.0
            
        base64_frames = []
        
        # Calculate timestamps for evenly spaced frames
        timestamps = [duration * i / (num_frames + 1) for i in range(1, num_frames + 1)]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            for i, ts in enumerate(timestamps):
                out_path = os.path.join(temp_dir, f"frame_{i}.jpg")
                
                # Extract frame using ffmpeg
                ffmpeg_cmd = [
                    'ffmpeg', '-y', '-ss', str(ts), '-i', video_path,
                    '-vframes', '1', '-q:v', '2', out_path
                ]
                
                try:
                    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    
                    if os.path.exists(out_path):
                        with open(out_path, "rb") as image_file:
                            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                            base64_frames.append(encoded_string)
                except subprocess.CalledProcessError:
                    continue
                    
        return base64_frames

    @typechecked
    async def predict(self, query: VidCapQuery) -> VidCapPrediction:
        # Since Doubao Vision is an image-based model, we extract frames from the video
        # and send them as multiple images in the context
        
        frames = await self._extract_frames(query.vid_path, num_frames=3)
        
        if not frames:
            return VidCapPrediction(caption="Failed to extract frames from video.")
            
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }
        
        # Build multi-image content payload
        content = []
        for frame in frames:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{frame}"}
            })
            
        content.append({
            "type": "text",
            "text": "These are sequentially extracted frames from a video. Describe what is happening in the video. Answer in Chinese."
        })
        
        payload = {
            "model": self._model_id,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "max_tokens": 1024,
            "temperature": 0.3
        }
        
        async with self.session.post(self._predict_endpoint, headers=headers, json=payload) as resp:
            resp_data = await resp.json()
            if "choices" in resp_data and len(resp_data["choices"]) > 0:
                caption = resp_data["choices"][0]["message"]["content"]
                return VidCapPrediction(caption=caption, lang="zh")
            else:
                return VidCapPrediction(caption="Failed to generate caption.")

    @typechecked
    async def stream_predict(self, query: VidCapQuery, chunk_size: int | None = None):
        prediction = await self.predict(query)
        yield prediction
