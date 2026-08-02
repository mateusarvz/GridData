import pandas as pd

from DADOS_PARA_LANGCHAIN.services.dashboard_service import _prepare_axis_labels


def test_prepare_axis_labels_preserves_full_text_values():
    values = pd.Series(["63.345.345", "1000", "valor com espaço"])

    positions, labels = _prepare_axis_labels(values)

    assert positions == [0, 1, 2]
    assert labels == ["63.345.345", "1000", "valor com espaço"]
