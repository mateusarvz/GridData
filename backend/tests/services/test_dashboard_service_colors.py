import os
import sys

import pandas as pd

import matplotlib
from matplotlib.axes import Axes

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from DADOS_PARA_LANGCHAIN.services.dashboard_service import DEFAULT_BAR_COLOR, desenhista

matplotlib.use("Agg")


def test_desenhista_bar_and_column_use_orange_color(monkeypatch):
    recorded_colors: list[str] = []
    original_bar = Axes.bar

    def spy_bar(self, x, height, *args, **kwargs):
        recorded_colors.append(kwargs.get("color"))
        return original_bar(self, x, height, *args, **kwargs)

    monkeypatch.setattr(Axes, "bar", spy_bar)

    df = pd.DataFrame({
        "categoria": ["A", "B", "C"],
        "valor": [10, 20, 30],
    })
    recipe = {
        "recipes": [
            {
                "id": "df1",
                "chart_type": "bar",
                "title": "Bar chart",
                "description": "Teste de cor bar",
                "x": "categoria",
                "y": ["valor"],
                "sql": "SELECT categoria, valor FROM tabela",
            },
            {
                "id": "df2",
                "chart_type": "column",
                "title": "Column chart",
                "description": "Teste de cor column",
                "x": "categoria",
                "y": ["valor"],
                "sql": "SELECT categoria, valor FROM tabela",
            },
        ]
    }

    charts = desenhista(recipe, {"df1": df, "df2": df})

    assert len(charts) == 2
    assert all(chart["chart_type"] in {"bar", "column"} for chart in charts)
    assert recorded_colors == [DEFAULT_BAR_COLOR, DEFAULT_BAR_COLOR]


def test_bar_color_constant_is_orange():
    assert DEFAULT_BAR_COLOR == "#F97316"
