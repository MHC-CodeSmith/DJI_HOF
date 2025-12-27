# 📊 Scripts de Validação do Modelo de Saúde da Vegetação

Este diretório contém scripts para **validação visual** do modelo de saúde da vegetação, permitindo verificar se o modelo está funcionando corretamente antes de gerar os mapas finais.

---

## 🔍 Scripts Disponíveis

### 1. `validate_health_image.py`
**Validação visual de uma imagem única**

Compara lado a lado:
- **Esquerda**: Imagem original
- **Direita**: Mapa de saúde gerado pelo modelo
  - 🟢 Verde = Áreas saudáveis
  - 🔴 Vermelho = Áreas não saudáveis

**Uso:**
```bash
source venv/bin/activate
python3 validate_health_image.py
```

**O que verificar:**
- ✅ Áreas verdes aparecem marcadas como saudáveis
- ✅ Concreto/asfalto aparecem como não saudáveis
- ✅ Sombras não distorcem muito os resultados
- ✅ Vegetação estressada/amarelada aparece mais vermelha
- ✅ O modelo está sendo interpretável

---

### 2. `validate_health_video.py`
**Validação temporal completa de um vídeo**

Mostra:
- 🎥 Stream em tempo real do mapa de saúde sobreposto ao vídeo
- 📈 Gráfico final com a evolução da saúde ao longo do tempo
- 📊 Estatísticas (mín, máx, média, mediana)

**Uso:**
```bash
source venv/bin/activate

# Vídeo aleatório
python3 validate_health_video.py

# Vídeo específico
python3 validate_health_video.py DJI_20251114091511_0054_D
```

**Controles durante a visualização:**
- Pressione `q` para pular para o gráfico
- Aguarde o vídeo terminar para ver o gráfico completo

**O que verificar:**
- ✅ Estabilidade: O modelo não oscila demais entre frames
- ✅ Resposta ao terreno: Muda adequadamente quando o drone voa sobre diferentes áreas
- ✅ Valores razoáveis: Percentual de saúde entre 0-100%
- ✅ Padrões espaciais: Áreas específicas mantêm valores consistentes

---

## 📋 Pré-requisitos

1. **Modelo treinado**: Execute primeiro `add_health_index.py` ou `process_all_videos.py` para garantir que o modelo existe em `models/health_model.pkl`

2. **Dependências instaladas**:
   ```bash
   source venv/bin/activate
   pip install opencv-python numpy scikit-learn joblib matplotlib
   ```

3. **Dataset disponível** (para `validate_health_image.py`):
   - Pasta `Dataset_Hipolito_drone/` com imagens

4. **Vídeos disponíveis** (para `validate_health_video.py`):
   - Pasta `DJI_20251114105612_0065_D/` com arquivos MP4

---

## 🎯 Interpretação dos Resultados

### ✅ **Indicadores de Bom Funcionamento**

1. **Consistência Visual**
   - Áreas claramente verdes aparecem como saudáveis
   - Solo exposto, concreto aparecem como não saudáveis
   - Transições são suaves e lógicas

2. **Estabilidade Temporal**
   - Valores não oscilam drasticamente entre frames próximos
   - Mudanças refletem mudanças reais no terreno
   - Gráfico mostra padrões reconhecíveis (não ruído aleatório)

3. **Valores Razonáveis**
   - Saúde média entre 40-90% para áreas com vegetação
   - Mínimos próximos de 0% para áreas sem vegetação
   - Máximos próximos de 100% para vegetação muito saudável

### ⚠️ **Possíveis Problemas**

1. **Muito vermelho em áreas verdes**
   - Modelo pode estar muito conservador
   - Pode precisar re-treinar com mais exemplos

2. **Oscilações muito grandes**
   - Iluminação variando muito entre frames
   - Modelo muito sensível
   - Considere ajustar parâmetros ou adicionar suavização

3. **Tudo verde ou tudo vermelho**
   - Modelo não está diferenciando bem
   - Dataset de treino pode estar desbalanceado
   - Re-treine o modelo

---

## 🔧 Troubleshooting

### Erro: "Model not found"
```bash
# Treine o modelo primeiro
source venv/bin/activate
python3 add_health_index.py
```

### Erro: "No images found"
- Verifique se a pasta `Dataset_Hipolito_drone/` existe e contém imagens JPG/PNG

### Erro: "No videos found"
- Verifique se a pasta `DJI_20251114105612_0065_D/` existe e contém arquivos MP4

### Janela não abre / Vídeo não reproduz
- Verifique se está usando ambiente com suporte a GUI (não SSH sem X11)
- Para servidores remotos, considere salvar imagens em vez de mostrar

### Matplotlib não funciona
```bash
source venv/bin/activate
pip install matplotlib
```

---

## 📸 Exemplos de Saída

### `validate_health_image.py`
```
🔍 Validação Visual - Imagem Original vs Mapa de Saúde
================================================================================
🤖 Carregando modelo...
✅ Modelo carregado!

📷 Carregando imagem aleatória do dataset...
   ✅ Imagem: DJI_20251107114851_0041_D.JPG

🧮 Calculando mapa de saúde...

🖼️  Abrindo janela de visualização...
   Pressione qualquer tecla para fechar
```

### `validate_health_video.py`
```
🔍 Validação Visual - Saúde ao Longo do Tempo (Vídeo)
================================================================================
🤖 Carregando modelo...
✅ Modelo carregado!

📹 Carregando vídeo aleatório...
   ✅ Vídeo: DJI_20251114091511_0054_D.MP4
   📊 Total de frames: 1213
   ⏱️  FPS: 30.00
   ⏱️  Duração: 40.4 segundos

🎬 Processando vídeo...
   Pressione 'q' durante a visualização para pular para o gráfico

📊 Estatísticas:
   Total de amostras: 243
   Saúde mínima: 45.23%
   Saúde máxima: 92.15%
   Saúde média: 72.48%
   Desvio padrão: 8.32%

📈 Gerando gráfico...
```

---

## 🚀 Próximos Passos

Após validar o modelo:

1. ✅ Se tudo estiver OK: Gere os mapas analíticos com `generate_analytical_map.py`
2. ⚠️ Se houver problemas: Ajuste o modelo ou re-treine com mais dados
3. 📊 Combine validações: Use ambos scripts para ter certeza completa

---

## 📝 Notas

- Os scripts são **independentes** e podem ser executados em qualquer ordem
- Eles **não modificam** os dados existentes, apenas visualizam
- Podem ser executados **múltiplas vezes** sem problemas
- Úteis para **debug** e **apresentações** de resultados


