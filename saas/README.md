# ADC SaaS Platform

This directory contains the planned SaaS productization of the ADC forex strategy archive and experimentation notebook.

The first pull request intentionally adds the project skeleton only: directories, placeholder modules, configuration examples, and documentation entry points. Feature code will be added incrementally in follow-up pull requests.

## High-level structure

```text
saas/
├── apps/
│   ├── api/        # Python backend API, domain services, jobs, DB access
│   └── web/        # Web application shell and frontend feature modules
├── packages/       # Shared contracts, UI primitives, and config
├── infra/          # Deployment, proxy, and infrastructure definitions
├── docs/           # Architecture decisions, API notes, runbooks
└── scripts/        # Developer and CI utility scripts
```

## Planned product areas

- User authentication and organization/team accounts
- Strategy archive and experiment tracking
- Market data ingestion and feature generation
- Backtesting, metrics, and risk dashboards
- Billing/subscription readiness
- Deployment-ready infrastructure templates
