from pydantic import BaseModel, Field, ConfigDict
from typing import Tuple
from datetime import datetime
from typing import Optional


class BaseSchema(BaseModel):
    model_config: ConfigDict = ConfigDict(from_attributes=True, extra="forbid")

    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_deleted: Optional[bool] = None