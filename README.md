# alcantara-social

Fila de posts e stories do Instagram **@alcantarainvestimentos**.

## Como funciona

1. As tarefas agendadas do Claude geram as artes e colocam cada uma na fila como **rascunho** (`scripts/enqueue.py`).
2. O Kaynander recebe a prévia no celular e responde **"aprovo"** (ou pede ajuste / recusa). O agente marca os itens como **aprovado** (`scripts/approve.py`).
3. O GitHub Actions (`.github/workflows/publish.yml`) roda a cada 15 min e publica **1 item aprovado por vez**, quando o horário chega, pela API oficial do Instagram.

## Horários

| Story | Horário |
|---|---|
| Radar | 08:00 |
| Notícia | 11:00 |
| Você sabia? | 14:00 |
| Pergunta | 19:30 |

Feed: seg, qua e sex às 12:00.

Itens aprovados com mais de 6 h de atraso viram **expirado** e não são publicados (para não postar notícia velha).

## Segredo necessário

`Settings → Secrets and variables → Actions → New repository secret`
- Nome: `IG_TOKEN`
- Valor: o token gerado no app **Alcantara Agente Social** (Meta for Developers).

O token **nunca** vai para arquivo do repositório.

## Ver a fila

`python3 scripts/approve.py --list`
