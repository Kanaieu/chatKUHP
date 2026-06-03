from typing import Tuple, Dict
from pydantic import BaseModel, RootModel, Field

class VisualInferenceSchema(BaseModel):
    health_bar: str = Field(alias="health bar")
    food_bar: str = Field(alias="food bar")
    hotbar: str
    environment: str

class GoalInferenceSchema(BaseModel):
    goal_inference: str = Field(alias="goal inference")
    visual_inference: VisualInferenceSchema = Field(alias="visual inference")

class StepSchema(BaseModel):
    task: str
    goal: Tuple[str, int]

class PlanSchema(RootModel):
    root: Dict[str, StepSchema]