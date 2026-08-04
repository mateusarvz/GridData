import base64
import os
import pathlib
import sys
from io import BytesIO

sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), 'tests')))

import pandas as pd
from PIL import Image
import importlib
from DADOS_PARA_LANGCHAIN.services.dashboard_service import DEFAULT_BAR_COLOR, desenhista

svc = importlib.import_module('DADOS_PARA_LANGCHAIN.services.dashboard_service')
print('module path:', svc.__file__)
print('DEFAULT_BAR_COLOR:', DEFAULT_BAR_COLOR)

# generate a bar chart image

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
print('charts len:', len(charts))
print('chart_type:', charts[0]['chart_type'])
print('image_base64 length:', len(charts[0]['image_base64']))

png_bytes = base64.b64decode(charts[0]['image_base64'])
print('png header:', png_bytes[:8])
img = Image.open(BytesIO(png_bytes))
print('image size:', img.size, 'mode:', img.mode)

# sample pixels from the left/middle area
pixels = img.convert('RGB').load()
width, height = img.size
sample_coords = [(int(width * 0.2), int(height * 0.75)), (int(width * 0.5), int(height * 0.75)), (int(width * 0.8), int(height * 0.75))]
print('sample coords:', sample_coords)
for x, y in sample_coords:
    print('pixel', (x, y), pixels[x, y])

# search old color references in backend source
root = pathlib.Path(os.getcwd())
print('\nSearching for legacy blue references...')
for path in root.rglob('*.py'):
    if '.venv' in path.parts or 'node_modules' in path.parts:
        continue
    text = path.read_text(encoding='utf-8', errors='ignore')
    if '#7C3AED' in text:
        print('FOUND blue literal in', path)
    if 'color="#7C3AED"' in text or "color='#7C3AED'" in text:
        print('FOUND exact blue color string in', path)

print('done')
