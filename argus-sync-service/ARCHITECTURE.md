# ARGUS Architecture

## Objetivo

O ARGUS é uma Plataforma de Inteligência Empresarial.

O frontend não calcula indicadores.  
Toda regra de negócio fica no Python.

## Fluxo

ERP SQL Server
↓  
Extractors  
↓  
Transformers  
↓  
Pipelines  
↓  
Data Marts Supabase  
↓  
Lovable / Frontend  

## Camadas

### Connectors
Responsáveis por conexões externas:
- SQL Server
- Supabase

### Extractors
Extraem dados brutos do ERP.

### Transformers
Tratam e filtram dados.

### Features
Calculam indicadores e inteligência.

### Pipelines
Orquestram extração, transformação, cálculo e gravação.

### Data Marts
Tabelas prontas para consumo no Supabase.

## Regra principal

Nenhuma regra de negócio deve ficar no frontend.

O frontend apenas:
- consulta
- exibe
- filtra visualmente

## Pipelines atuais

- ExecutivePipeline
- SalesPipeline
- SalesMartPipeline
- CommercialIntelligencePipeline

## Intelligence atual

- Commercial Facts
- Commercial Summary
- Commercial Recommendations
- Commercial Alerts
- ABC Produtos
- ABC Clientes
- Concentration
- Customer Risk
- Product Risk
- Commercial Overview
- Commercial Scorecards