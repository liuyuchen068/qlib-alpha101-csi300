import logging
from src.pipelines.data_pipeline import DataPipeline

if __name__ == "__main__":
    pipeline = DataPipeline(config_path="config.yaml")
    pipeline.run()