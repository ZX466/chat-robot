from pydantic import BaseModel, Field

from common.enumerator import BaseEnum
from common.utils.enum_util import enum_to_markdown
from pipeline.base.base_sync import AbstractPipelineConfig


##########
# ImgCap #
##########

class ImgCapModelIdEnum(BaseEnum):
    Blip = 'Salesforce/blip-image-captioning-large'
    DoubaoVision = 'DoubaoVision'


class DoubaoVisionConfig(BaseModel):
    api_key: str = Field(default="", description="The API key for Doubao Vision service.\n"
                                                  "Set via environment variable $ARK_API_KEY or directly here.")
    api_url: str = Field(default="https://ark.cn-beijing.volces.com/api/v3/responses",
                         description="The API URL for Doubao Vision service.")
    model: str = Field(default="doubao-seed-1-6-vision-250815",
                       description="Model name. Default: doubao-seed-1-6-vision-250815")


class ImgCapPipelineConfig(AbstractPipelineConfig):
    model_id: ImgCapModelIdEnum = Field(default=ImgCapModelIdEnum.Blip,
                                        description=f"The ID of the model used for image captioning. "
                                                    f"\n{enum_to_markdown(ImgCapModelIdEnum)}")
    predict_url: str = Field(default="http://127.0.0.1:11000/img-cap/predict",
                             description="The URL for image captioning prediction requests.")
    stream_predict_url: str = Field(default="http://127.0.0.1:11000/img-cap/stream-predict",
                                    description="The URL for streaming image captioning prediction requests.")
    doubao_vision_config: DoubaoVisionConfig = Field(default=DoubaoVisionConfig(),
                                                     description=f"Doubao Vision config. \n"
                                                                 f"Only edit it when you set `model_id` to `{ImgCapModelIdEnum.DoubaoVision.value}`.\n"
                                                                 f"For more details please see the [documents](https://www.volcengine.com/docs/82379/1399727).")
