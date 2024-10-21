from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EvalConfig(BaseSettings):
    evaluation_strategy_name: str = Field("jp v1.2.0-beta", description="Will be shown in evaluation page, and be used for just visibility")
    eval_dataset: str = Field(
        "weave:///wandbot/wandbot-eval-jp/object/wandbot_eval_data_jp:oCWifIAtEVCkSjushP0bOEc5GnhsMUYXURwQznBeKLA"
        ,description="Dataset reference for evaluation"
    )
    # en evaluation dataset: "weave:///wandbot/wandbot-eval/object/wandbot_eval_data:eCQQ0GjM077wi4ykTWYhLPRpuGIaXbMwUGEB7IyHlFU"
    # jp evaluation dataset: "weave:///wandbot/wandbot-eval-jp/object/wandbot_eval_data_jp:oCWifIAtEVCkSjushP0bOEc5GnhsMUYXURwQznBeKLA" 
    # jp small evaluation dataset: "weave:///wandbot/wandbot-eval-jp/object/wandbot_eval_data_jp_test:Qp5qAlNYhzLJSfDZONaBNDzjhEmlfOTXNI1NvYhELKQ"

    language: str = Field("ja", description="language for application (en or ja)")

    eval_judge_model: str = Field(
        "gpt-4-1106-preview",
        env="EVAL_JUDGE_MODEL",
        validation_alias="eval_judge_model",
    )
    wandb_entity: str = Field("wandbot", env="WANDB_ENTITY")
    wandb_project: str = Field("wandbot-eval-jp", env="WANDB_PROJECT")