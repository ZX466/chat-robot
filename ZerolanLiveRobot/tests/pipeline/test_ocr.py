import pytest
import os
from zerolan.data.pipeline.ocr import OCRQuery
from pipeline.ocr.config import OCRPipelineConfig, OCRModelIdEnum
from pipeline.ocr.deepseek_ocr import DeepSeekOCRPipeline

@pytest.mark.asyncio
async def test_deepseek_ocr():
    # Only run if API key is set
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if not api_key:
        pytest.skip("SILICONFLOW_API_KEY environment variable not set")
        
    config = OCRPipelineConfig(
        model_id=OCRModelIdEnum.DeepSeekOCR,
        api_key=api_key
    )
    
    pipeline = DeepSeekOCRPipeline(config)
    await pipeline.start()
    
    # Create a dummy image for testing if it doesn't exist
    test_image_path = "test_image.jpg"
    if not os.path.exists(test_image_path):
        from PIL import Image
        img = Image.new('RGB', (100, 30), color = (73, 109, 137))
        img.save(test_image_path)
        
    try:
        query = OCRQuery(image_path=test_image_path)
        result = await pipeline.predict(query)
        assert result is not None
        assert hasattr(result, 'region_results')
    finally:
        await pipeline.close()
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
