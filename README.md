
## Estrutura do Projeto

```
src/vgb/
├── __init__.py
├── __main__.py
├── interface_cli.py                 # Entry point CLI
│
├── domain/
│   ├── entities.py                  # Edition, Occurrence, Analysis, SearchTarget
│   ├── enums.py                     # ActType, AnalysisModel, EditionStatus, OccurrenceType
│   ├── exceptions.py                # Exceções de domínio
│   └── value_objects.py             # Nome, Cargo, HashSHA256
│
├── application/
│   ├── ports/
│   │   ├── ai_analyzer.py           # Contrato PDFAnalyzer
│   │   ├── notifier.py              # Contrato Notifier
│   │   ├── repository.py            # Contratos Repository
│   │   └── source.py                # Contrato DocumentSource
│   └── use_cases/
│       └── monitor_diario.py        # Orquestração principal
│
└── infrastructure/
    ├── ai/
    │   ├── composite_analyzer.py    # Fallback chain
    │   ├── gemini_analyzer.py       # Google Gemini 2.5 Flash
    │   ├── openrouter_analyzer.py   # OpenRouter (deepseek-v4-flash:free)
    │   └── ocr_analyzer.py          # PyMuPDF + fuzzy matching
    ├── config/
    │   └── settings.py              # Pydantic Settings
    ├── http/
    │   └── resilient_client.py      # HTTP client com retry
    ├── notifications/
    │   ├── telegram_notifier.py     # Notificações normais + resumo
    │   └── emergency_notifier.py    # Dead Man's Switch
    ├── storage/
    │   ├── database.py              # SQLAlchemy + aiosqlite
    │   ├── models.py                # ORM models
    │   └── repositories.py          # Repositórios concretos
    └── web/
        └── web_source.py            # Scraper de PDFs
```