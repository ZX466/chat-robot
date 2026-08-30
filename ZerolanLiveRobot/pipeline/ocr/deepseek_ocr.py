from typing import Literal
import os
import base64
import json
import asyncio
import aiohttp

from typeguard import typechecked
from zerolan.data.pipeline.ocr import OCRQuery, OCRPrediction, RegionResult, Position, Vector2D

from pipeline.base.base_async import BaseAsyncPipeline
from pipeline.ocr.config import OCRPipelineConfig

class DeepSeekOCRPipeline(BaseAsyncPipeline):
    def __init__(self, config: OCRPipelineConfig):
        # We handle the url dynamically.
        super().__init__(base_url="https://api.siliconflow.cn/v1/")
        self._model_id = "deepseek-ai/DeepSeek-OCR"  # Adjust as needed based on actual API
        self._api_key = config.api_key if hasattr(config, "api_key") else os.environ.get("SILICONFLOW_API_KEY", "")
        self._predict_endpoint = "chat/completions"

    @typechecked
    async def predict(self, query: OCRQuery) -> OCRPrediction:
        # Convert image to base64
        with open(query.img_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self._model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all the text from this image precisely."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}}
                    ]
                }
            ],
            "max_tokens": 1024,
            "temperature": 0.1
        }
        
        async with self.session.post(self._predict_endpoint, headers=headers, json=payload) as resp:
            resp_data = await resp.json()
            if "choices" in resp_data and len(resp_data["choices"]) > 0:
                text_content = resp_data["choices"][0]["message"]["content"]
                
                # Create default dummy position
                dummy_pos = Position(
                    lu=Vector2D(x=0, y=0),
                    ru=Vector2D(x=0, y=0),
                    rd=Vector2D(x=0, y=0),
                    ld=Vector2D(x=0, y=0)
                )
                
                region = RegionResult(
                    content=text_content,
                    confidence=1.0, 
                    position=dummy_pos
                )
                return OCRPrediction(region_results=[region])
            else:
                return OCRPrediction(region_results=[])
