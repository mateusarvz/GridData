import os
import sys
import pandas as pd
from matplotlib.axes import Axes

sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), 'tests')))
from DADOS_PARA_LANGCHAIN.services.dashboard_service import desenhista, DEFAULT_BAR_COLOR

rec = []
orig = Axes.bar

def spy(self, x, height, *args, **kwargs):
    rec.append(kwargs.get('color'))
    return orig(self, x, height, *args, **kwargs)

Axes.bar = spy

df = pd.DataFrame({'categoria': ['A', 'B', 'C'], 'valor': [10, 20, 30]})
recipe = {
    'recipes': [
        {
            'id': 'df1',
            'chart_type': 'bar',
            'title': 'Bar chart',
            'description': 'Teste',
            'x': 'categoria',
            'y': ['valor'],
            'sql': 'SELECT 1',
        }
    ]
}

charts = desenhista(recipe, {'df1': df})
print(DEFAULT_BAR_COLOR)
print(charts[0]['chart_type'])
print(bool(charts[0]['image_base64']))
print(rec)
