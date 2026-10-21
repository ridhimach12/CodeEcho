from pydantic import BaseModel, Field

class ASTFeatures(BaseModel):
    try_count: int = 0
    except_count: int = 0
    raise_count: int = 0
    none_check_count: int = 0
    if_count: int = 0
    return_count: int = 0
    loop_count: int = 0
    function_def_count: int = 0
    call_count: int = 0
    assign_count: int = 0
    assert_count: int = 0
    with_count: int = 0
    class_def_count: int = 0
    exception_types: list[str] = Field(default_factory=list)
    called_functions: list[str] = Field(default_factory=list)
    has_syntax_error: bool = False

    def to_vector(self) -> list[float]:
        """Returns 12-dimensional numerical vector of structural counts."""
        return [
            float(self.try_count),
            float(self.except_count),
            float(self.raise_count),
            float(self.none_check_count),
            float(self.if_count),
            float(self.return_count),
            float(self.loop_count),
            float(self.function_def_count),
            float(self.call_count),
            float(self.assign_count),
            float(self.assert_count),
            float(self.with_count),
        ]

class ASTDiffProfile(BaseModel):
    deleted_features: ASTFeatures
    added_features: ASTFeatures
    # Delta = added - deleted for each structural dimension
    delta_vector: list[float] = Field(default_factory=list)
    feature_names: list[str] = Field(default_factory=list)
    # High-level detected structural shifts
    detected_shifts: list[str] = Field(default_factory=list)
    parsed_successfully: bool = True
