
## Estrutura do Projeto

```
src/vgb/
├── __init__.py
├── __main__.py
├── interface_cli.py                 # Entry point CLI
│
├── domain/
│   ├── __init__.py
│   ├── entities.py                  # Edition, Occurrence, Analysis, SearchTarget
│   ├── enums.py                     # AnalysisModel, EditionStatus, OccurrenceType
│   ├── exceptions.py                # Exceções de domínio
│   └── value_objects.py             # Nome, Cargo, HashSHA256
│
├── application/
│   ├── __init__.py
│   ├── ports/
│   │   ├── __init__.py
│   │   ├── ai_analyzer.py           # Contrato PDFAnalyzer
│   │   ├── notifier.py              # Contrato Notifier
│   │   ├── repository.py            # Contratos Repository
│   │   └── source.py                # Contrato DocumentSource
│   └── use_cases/
│       ├── __init__.py
│       └── monitor_diario.py        # Orquestração principal
│
└── infrastructure/
    ├── __init__.py
    ├── ai/
    │   ├── __init__.py
    │   ├── composite_analyzer.py    # Fallback chain
    │   ├── gemini_analyzer.py       # Google Gemini 2.5 Flash
    │   ├── openrouter_analyzer.py   # OpenRouter (deepseek-v4-flash:free)
    │   └── ocr_analyzer.py          # PyMuPDF + fuzzy matching
    ├── config/
    │   ├── __init__.py
    │   └── settings.py              # Pydantic Settings
    ├── http/
    │   ├── __init__.py
    │   └── resilient_client.py      # HTTP client com retry
    ├── notifications/
    │   ├── __init__.py
    │   ├── telegram_notifier.py     # Notificações normais + resumo
    │   └── emergency_notifier.py    # Dead Man's Switch
    ├── storage/
    │   ├── __init__.py
    │   ├── database.py              # SQLAlchemy + aiosqlite
    │   ├── models.py                # ORM models
    │   └── repositories.py          # Repositórios concretos
    └── web/
        ├── __init__.py
        └── web_source.py            # Scraper de PDFs

tests/
├── __init__.py
├── integration/
│   ├── __init__.py
│   └── test_source.py              # Testes de integração com a fonte web
└── unit/
    ├── __init__.py
    ├── test_composite_analyzer.py  # Testes do fallback chain de IA
    ├── test_domain.py              # Testes de entidades e value objects
    ├── test_emergency_notifier.py  # Testes do Dead Man's Switch
    ├── test_monitor_diario.py      # Testes do fluxo principal de orquestração
    └── test_telegram_notifier.py   # Testes de formatação de mensagens Telegram
```