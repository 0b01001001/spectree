class SpecTreeException(Exception):
    pass


class SpecTreeValidationError(SpecTreeException):
    pass


class SpecTreeDuplicateField(SpecTreeException):
    def __init__(self, model_name: str, name: str) -> None:
        super().__init__(f"duplicate field `{name}` for model {model_name}")


class SpecTreeUnknownFields(SpecTreeException):
    def __init__(self, model_name: str, names: list[str]) -> None:
        super().__init__(f"unknown fields ({' '.join(names)}) for model {model_name}")
