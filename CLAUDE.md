# CLAUDE.md — Plataforma de Inteligência em Licitações (GovTech SaaS)

## Visão do produto
SaaS B2B que monitora Diários Oficiais e portais de compras públicas, usa LLM
para identificar editais relevantes (não busca por palavra-chave, e sim por
intenção/contexto) e avisa clientes via WhatsApp/email antes da concorrência.

## Problema que resolve
- Diários Oficiais são descentralizados, mal formatados, em PDF/OCR.
- Busca por keyword gera falso positivo (ex: "trator" pega trator de brinquedo).
- Empresas perdem prazo de licitação por triagem manual lenta.

## Nicho do MVP (não generalizar ainda)
Setor: maquinário pesado/agrícola — tratores, linha amarela, motores industriais,
peças e manutenção de frota (ecossistema Caterpillar, Komatsu, John Deere).
Região: Piracicaba e polos de agronegócio/industrial adjacentes.
Motivo: ticket médio alto, contratos públicos recorrentes, 1 contrato paga anos de SaaS.

## Pilares técnicos
1. **Ingestão**: scraping de ComprasNet (API estruturada) + Diários Oficiais
   municipais (PDF, exige OCR).
2. **Processamento**: OCR (se necessário) → LLM classifica objeto do edital
   como relevante/irrelevante + extrai dados-chave (valor, data, município, link).
3. **Distribuição**: alerta direto (WhatsApp/email) + painel web simples.

## Stack
- Scraper: Python (Scrapy ou Playwright)
- OCR: Tesseract (MVP) — migrar pra AWS Textract se precisão insuficiente
- Classificação: LLM via API Anthropic
- Backend/DB: Node + Next.js + Postgres (Supabase)
- Notificação: WhatsApp Business API
- Infra: Docker Compose (Postgres local pro dev)

## Schema inicial (criar como migration)
- `municipios` (id, nome, uf, portal_url, ativo)
- `editais` (id, municipio_id, fonte, numero_processo, objeto_raw, objeto_resumo,
  valor_estimado, data_abertura, link_original, pdf_hash UNIQUE, classificacao,
  confianca, status, created_at)
- `clientes` (id, nome, whatsapp, email, filtros JSONB, ativo)
- `alertas_enviados` (id, edital_id, cliente_id, canal, enviado_em)

## Regras de classificação do LLM
Incluir: tratores, retroescavadeiras, motoniveladoras, motores diesel industriais,
peças/manutenção frota pesada, locação maquinário agrícola.
Excluir: brinquedos/miniaturas, maquinário escolar, TI, alimentação, serviços
não-mecânicos.
Confiança <0.6 → não disparar alerta automático, marcar para revisão manual.
Output esperado: JSON {relevante: bool, categoria: string, confianca: float, motivo: string}

## Ordem de execução (seguir nessa sequência, commit por etapa)
1. Estrutura de pastas + docker-compose (Postgres)
2. Migration SQL com schema acima
3. Scraper ComprasNet (API estruturada, sem OCR) → validar pipeline simples antes de OCR
4. Pipeline de classificação: objeto_raw → LLM → grava resultado no banco
5. Scraper Diário Oficial de 3 municípios de Piracicaba (PDF) + OCR
6. Cron diário + dedupe via hash do PDF
7. Notificador WhatsApp (só dispara se relevante=true e confianca>0.6)
8. Painel web simples (lista de editais + filtro por status)

## Convenções de trabalho
- Commits pequenos, um por etapa da ordem acima.
- Testar cada módulo isolado antes de integrar no pipeline.
- Nunca expor API keys no código — usar .env (criar .env.example).
- Priorizar pipeline end-to-end funcional (mesmo simples) antes de otimizar OCR/UI.
- Se travar em decisão de arquitetura, escolher a opção mais simples que funcione
  para o MVP, não a mais "correta" a longo prazo.

## Primeira tarefa
Criar estrutura de pastas, docker-compose com Postgres, migration do schema
acima, e um scraper básico do ComprasNet que imprime JSON estruturado no console.