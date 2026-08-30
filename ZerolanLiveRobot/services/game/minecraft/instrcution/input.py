from dataclasses import dataclass
from typing import Optional, Union

from pydantic import create_model, Field, BaseModel


def ts_type_to_py_type(t: str) -> type:
    if t == 'number':
        return Union[float, int]
    elif t == 'string':
        return str
    elif t == 'boolean':
        return bool
    else:
        raise ValueError(f"Not a valid type: {t}")

@dataclass
class FieldMetadata:
    name: str
    type: str
    description: str
    required: bool


def generate_model_from_args(class_name: str, args_list: list[FieldMetadata]):
    fields = {}
    for arg in args_list:
        name = arg.name
        if not isinstance(name, str):
            raise TypeError(f"Expected str for name, got {type(name)}")
        field_type = arg.type
        if not isinstance(field_type, str):
            raise TypeError(f"Expected str for field_type, got {type(field_type)}")
        field_type = ts_type_to_py_type(field_type)
        required = arg.required
        if not isinstance(required, bool):
            raise TypeError(f"Expected bool for required, got {type(required)}")
        description = arg.description
        if not isinstance(description, str):
            raise TypeError(f"Expected str for description, got {type(description)}")

        if required:
            fields[name] = (field_type, Field(default=None, description=description))
        else:
            fields[name] = (Optional[field_type], Field(default=None, description=description))

    model = create_model(class_name, **fields)
    if not issubclass(model, BaseModel):
        raise TypeError("model must be a subclass of BaseModel")
    return model

