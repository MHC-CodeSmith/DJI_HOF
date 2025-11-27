# Mapa Analítico - Índice de Saúde da Vegetação

## 📋 Visão Geral

Este mapa interativo foi desenvolvido especificamente para **análise e visualização científica** dos dados de voo do drone, com foco no mapeamento do índice de saúde da vegetação.

## 🎯 Características

### Visualizações Disponíveis

1. **Heatmap (Mapa de Calor)**
   - Visualização contínua da distribuição espacial do índice de saúde
   - Cores: Vermelho (baixa saúde) → Amarelo → Verde (alta saúde)
   - Ajustável: raio e intensidade

2. **Grid Interpolado**
   - Grade de células interpoladas usando IDW (Inverse Distance Weighting)
   - Estima valores de saúde entre pontos de medição
   - Permite identificar padrões espaciais e áreas com saúde estimada

3. **Pontos Originais**
   - Cada ponto representa um frame do drone
   - Popup com informações detalhadas ao clicar
   - Cor baseada no índice de saúde

### Camadas de Base

- **Mapa**: Visualização cartográfica (OpenStreetMap)
- **Satélite**: Imagens de satélite (Esri World Imagery) - ideal para ver a vegetação real

## 📊 Painel de Controle

O painel no canto superior direito mostra:

- **Total de Pontos**: Número total de frames analisados
- **Saúde Média**: Média aritmética do índice de saúde
- **Saúde Mín/Máx**: Valores extremos encontrados
- **Mediana**: Valor mediano do índice

### Controles Interativos

- ☑️ **Heatmap**: Liga/desliga o mapa de calor
- 🎚️ **Raio Heatmap**: Ajusta o tamanho da área de influência (10-50px)
- ☑️ **Grid Interpolado**: Liga/desliga a grade interpolada
- 🎚️ **Opacidade**: Ajusta transparência do grid (0-100%)
- ☑️ **Pontos Originais**: Mostra/oculta os pontos de medição originais

## 🔧 Como Usar

### Gerar o Índice de Saúde

Se você ainda não tem o arquivo com índice de saúde:

```bash
python3 add_health_index.py
```

Este script adiciona uma coluna `health_index` (0-100%) ao CSV consolidado usando padrões espaciais controlados.

### Gerar o Mapa Analítico

```bash
python3 generate_analytical_map.py
```

O mapa será salvo em: `maps/analytical_map.html`

### Atualizar com Dados Reais do Modelo

Quando você tiver resultados reais do modelo de saúde da vegetação:

1. Substitua a coluna `health_index` no arquivo `all_metadata_with_health.csv`
2. Execute novamente: `python3 generate_analytical_map.py`
3. O mapa será atualizado automaticamente

## 📈 Interpretação do Mapa

### Cores

- **🟢 Verde**: Saúde excelente (80-100%)
- **🟡 Amarelo**: Saúde moderada (50-80%)
- **🟠 Laranja**: Saúde baixa (25-50%)
- **🔴 Vermelho**: Saúde muito baixa (0-25%)

### Padrões a Observar

1. **Clusters de Alta Saúde**: Áreas verdes concentradas podem indicar:
   - Solo mais fértil
   - Melhor irrigação
   - Condições ambientais favoráveis

2. **Gradientes**: Transições suaves de cor podem indicar:
   - Mudanças graduais nas condições do solo
   - Efeitos de sombra/exposição solar
   - Variações de umidade

3. **Áreas Heterogêneas**: Mistura de cores pode indicar:
   - Diferentes tipos de vegetação
   - Presença de pragas ou doenças localizadas
   - Variações de manejo agrícola

## 🔬 Metodologia

### Interpolação IDW (Inverse Distance Weighting)

O grid interpolado usa a técnica IDW:

- **Potência**: 2.0 (quanto maior, mais localizada a interpolação)
- **Distância máxima**: ~111 metros (0.001 graus)
- **Resolução**: 80x80 células (6,400+ pontos interpolados)

### Cálculo do Heatmap

O heatmap usa a biblioteca Leaflet.heat:

- Intensidade baseada no índice de saúde
- Suavização gaussiana para visualização contínua
- Gradiente de cores configurável

## 📁 Arquivos

- `analytical_map.html` - Mapa interativo principal
- `all_metadata_with_health.csv` - Dados com índice de saúde
- `add_health_index.py` - Script para gerar índice dummy
- `generate_analytical_map.py` - Script gerador do mapa

## 🚀 Próximos Passos

### Integração com Modelo Real

1. **Treinar o modelo** usando características RGB das imagens
2. **Prever saúde** para cada frame
3. **Atualizar CSV** com valores reais
4. **Regenerar mapa** para visualizar resultados

### Melhorias Futuras

- [ ] Exportar dados para QGIS/ArcGIS
- [ ] Adicionar timeline temporal
- [ ] Comparação entre diferentes voos
- [ ] Estatísticas por região/zona
- [ ] Exportação de relatórios PDF

## 💡 Dicas

1. **Use a camada de Satélite** para correlacionar o índice com a vegetação visível
2. **Ajuste o raio do heatmap** para focar em padrões locais ou regionais
3. **Combine visualizações**: Use heatmap + grid para análise completa
4. **Clique nos pontos** para ver detalhes específicos de cada frame

## 🐛 Troubleshooting

### O mapa não carrega

- Verifique conexão com internet (requer CDN para Leaflet)
- Abra o console do navegador (F12) para ver erros

### Heatmap não aparece

- Verifique se a camada "Heatmap" está marcada
- Ajuste o zoom (funciona melhor em níveis 15-18)

### Performance lenta

- Reduza o tamanho do grid (altere `grid_size` no código)
- Desative algumas camadas simultaneamente

## 📧 Suporte

Para dúvidas ou problemas, consulte os scripts Python que têm comentários detalhados sobre cada funcionalidade.

