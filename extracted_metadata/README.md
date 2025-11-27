# Metadados Extraídos - DJI Mini 4 Pro

## 📋 Estrutura de Dados

Este diretório contém os metadados extraídos de todos os arquivos `.SRT` do projeto.

### Estrutura de Pastas

Cada vídeo tem sua própria pasta contendo:

- `*_metadata.csv` - Arquivo CSV com todos os frames e metadados
- `*_summary.txt` - Resumo dos dados extraídos

## 📊 Campos do CSV

Os arquivos CSV contêm as seguintes colunas:

| Campo | Descrição | Formato |
|-------|-----------|---------|
| `frame_index` | Número sequencial do frame | Inteiro |
| `timestamp` | Data e hora do frame | YYYY-MM-DD HH:MM:SS.mmm |
| `latitude` | Latitude GPS (WGS84) | Decimal |
| `longitude` | Longitude GPS (WGS84) | Decimal |
| `relative_altitude` | Altitude relativa (acima do ponto de decolagem) | metros |
| `absolute_altitude` | Altitude absoluta (acima do nível do mar) | metros |
| `iso` | Sensibilidade ISO da câmera | Inteiro |
| `shutter` | Velocidade do obturador | Fração (ex: 1/500.0) |
| `aperture` | Abertura do diafragma (fnum) | Decimal |
| `ev` | Valor de exposição | Inteiro |
| `color_mode` | Modo de cor | Texto |
| `focal_length` | Distância focal equivalente | mm |
| `color_temperature` | Temperatura de cor | Kelvin |

## 🗺️ Como Importar no QGIS

### Método 1: Camada de Texto Delimitado

1. Abra o QGIS
2. Vá em: **Layer** → **Add Layer** → **Add Delimited Text Layer**
3. Selecione o arquivo `*_metadata.csv`
4. Configure:
   - **File format**: CSV
   - **Geometry definition**: Point coordinates
   - **X field**: `longitude`
   - **Y field**: `latitude`
   - **Geometry CRS**: `EPSG:4326` (WGS84)
5. Clique em **Add**

### Método 2: Via Interface de Gerenciamento de Dados

1. **Browser Panel** → Navegue até o arquivo CSV
2. Arraste o arquivo para o mapa
3. Configure X/Y automaticamente quando solicitado

### Criar Heatmap no QGIS

Após importar os pontos:

1. Clique com botão direito na camada → **Properties**
2. Vá na aba **Symbology**
3. Selecione **Heatmap**
4. Configure a intensidade e raio do heatmap
5. Ajuste a coluna de peso se necessário

## 🗺️ Como Importar no ArcGIS

### Método 1: Adicionar Evento XY

1. Abra o ArcMap ou ArcGIS Pro
2. Vá em: **File** → **Add Data** → **Add XY Data** (ou **XY Table To Point** no Pro)
3. Selecione o arquivo CSV
4. Configure:
   - **X Field**: `longitude`
   - **Y Field**: `latitude`
   - **Coordinate System**: `WGS 1984` (EPSG:4326)
5. Clique em **OK**

### Método 2: Importar Tabela e Converter

1. **Add Data** → Selecione o CSV (será importado como tabela)
2. Clique com botão direito na tabela → **Display XY Data**
3. Configure X/Y e sistema de coordenadas
4. Clique em **OK**

### Criar Heatmap no ArcGIS

No ArcGIS Pro:

1. Selecione a camada de pontos
2. Vá em **Analysis** → **Tools**
3. Use **Kernel Density** ou **Hot Spot Analysis**
4. Configure os parâmetros e execute

## 📈 Estatísticas dos Arquivos Processados

| Arquivo | Frames | Status |
|---------|--------|--------|
| DJI_20251114091504_0053_D | 30 | ✅ |
| DJI_20251114091511_0054_D | 1,213 | ✅ |
| DJI_20251114093134_0057_D | 976 | ✅ |
| DJI_20251114094816_0058_D | 38 | ✅ |
| DJI_20251114094933_0059_D | 4,829 | ✅ |
| DJI_20251114100232_0060_D | 91 | ✅ |
| DJI_20251114100707_0061_D | 783 | ✅ |
| DJI_20251114101110_0062_D | 9,762 | ✅ |
| DJI_20251114101636_0063_D | 8,194 | ✅ |
| DJI_20251114105046_0064_D | 8,562 | ✅ |
| DJI_20251114105612_0065_D | 1,481 | ✅ |

**Total**: ~35,959 frames processados

## 🔄 Reprojeção para Coordenadas Métricas (UTM)

Se você precisa de coordenadas em metros para análises espaciais, pode reprojetar para UTM:

### QGIS

1. Clique com botão direito na camada → **Export** → **Save Features As**
2. Escolha o formato (CSV, Shapefile, etc.)
3. **CRS**: Selecione `EPSG:25832` (UTM Zone 32N - Alemanha) ou `EPSG:32632` (UTM Zone 32N - Hemisfério Norte)
4. Salve o arquivo

### ArcGIS

1. Use a ferramenta **Project** (Data Management)
2. **Output Coordinate System**: `WGS 1984 UTM Zone 32N` (EPSG:32632)

## 🐍 Uso em Python

Para carregar os dados em Python/Pandas:

```python
import pandas as pd

# Carregar um arquivo CSV
df = pd.read_csv('DJI_20251114091511_0054_D/DJI_20251114091511_0054_D_metadata.csv')

# Converter timestamps
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Converter coordenadas para float
df['latitude'] = df['latitude'].astype(float)
df['longitude'] = df['longitude'].astype(float)

# Visualizar primeiras linhas
print(df.head())
```

## 📝 Notas Importantes

- As coordenadas estão em **WGS84 (EPSG:4326)**
- Todos os timestamps estão no formato **UTC**
- As altitudes estão em **metros**
- A distância focal é equivalente a 24mm (formato full-frame)

## 🚀 Próximos Passos

1. **Mapeamento**: Importar os CSVs no QGIS/ArcGIS
2. **Análise**: Correlacionar com imagens RGB para análise de saúde da vegetação
3. **Visualização**: Criar heatmaps e mapas temáticos
4. **Modelagem**: Usar os dados para treinar modelos de classificação

## 📧 Suporte

Para dúvidas sobre os dados ou processamento, consulte o script `extract_srt_metadata.py` no diretório raiz do projeto.

