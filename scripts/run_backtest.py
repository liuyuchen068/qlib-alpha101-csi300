import logging
from src.pipelines.backtest_pipeline import BacktestExperiment

if __name__ == "__main__":
    experiment = BacktestExperiment()
    experiment.run()