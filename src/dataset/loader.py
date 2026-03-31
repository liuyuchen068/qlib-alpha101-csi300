from qlib.data.dataset.loader import QlibDataLoader


def create_data_loader(feature_cols: list[str]) -> QlibDataLoader:
    feature_names = [c.replace("$", "") for c in feature_cols]
    return QlibDataLoader(
        config={
            "feature": (feature_cols, feature_names),
            "label": (["Ref($close, -2)/Ref($close, -1) - 1"], ["LABEL"])
        }
    )