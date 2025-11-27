# Mapas Interativos dos Voos

## Conteúdo

- `flight_map.html`: mapa interativo com todos os trajetos e pontos capturados.
- Gerado pelo script `generate_flight_map.py` localizado na raiz do projeto.

## Como gerar/atualizar o mapa

1. Certifique-se de que o arquivo `extracted_metadata/all_metadata_consolidated.csv` está atualizado.
2. Execute:
   ```
   cd /home/mhc/Germany/Drone
   python3 generate_flight_map.py
   ```
3. O arquivo `maps/flight_map.html` será recriado automaticamente.

## Como visualizar

- Abra o arquivo `maps/flight_map.html` em qualquer navegador moderno.
- O mapa usa Leaflet + OpenStreetMap (não requer instalação extra).

## Camadas disponíveis

- **Colorir por voo**: cada voo recebe uma cor distinta.
- **Colorir por altitude**: pontos coloridos conforme a altitude relativa (gradiente azul → vermelho). Útil para verificar variações de altura rapidamente.

Use o controle no canto superior direito do mapa para alternar entre as camadas.

## Personalização

- Atualize o script `generate_flight_map.py` para adicionar novos indicadores (por exemplo, índice de saúde previsto pelo modelo) e inclua-os no popup/cores.
- O script lê todos os metadados diretamente do CSV consolidado, então qualquer nova coluna pode ser adicionada ao mapa sem alterar o pipeline de extração.

