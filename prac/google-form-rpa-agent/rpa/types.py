from pydantic import BaseModel
from typing import List, Optional, Literal, Union
FieldType = Literal['text','paragraph','choice','checkbox','dropdown','date','time']
class FieldConfig(BaseModel):
    entry_id: Optional[str]=None
    question_label: Optional[str]=None
    type: FieldType
    value: Union[str, List[str]]
    option_hints: Optional[List[str]]=None
class FormConfig(BaseModel):
    form_url: str
    fields: List[FieldConfig]
