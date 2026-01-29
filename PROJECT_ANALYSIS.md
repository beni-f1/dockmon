# DockMon Project Analysis Report

**Generated:** January 28, 2026  
**Version:** 2.2.8-2  
**License:** Business Source License 1.1

---

## Executive Summary

DockMon is a comprehensive, self-hosted Docker container monitoring and management platform. It provides real-time monitoring, intelligent auto-restart capabilities, multi-channel alerting, and complete event logging across multiple Docker hosts—both local and remote.

---

## Technology Stack

### Languages & Frameworks

| Component | Technology | Version |
|-----------|------------|---------|
| **Backend API** | Python + FastAPI | 3.13 |
| **Frontend** | React + TypeScript | 18.3 |
| **Stats Service** | Go | 1.24 |
| **Compose Service** | Go | 1.24 |
| **Remote Agent** | Go | 1.24 |
| **Database** | SQLAlchemy + SQLite | 2.0 |
| **Build Tool** | Vite | 7.x |
| **Container Base** | Alpine Linux | 3.x |

### Key Dependencies

#### Backend (Python)
- **FastAPI** (0.123.5) - Async web framework
- **SQLAlchemy** (2.0.36) - ORM with async support
- **Alembic** (1.13.1) - Database migrations
- **Docker SDK** (7.1.0) - Docker API integration
- **aiohttp/httpx** - Async HTTP clients
- **Pydantic** (2.10.6) - Data validation
- **bcrypt/argon2-cffi** - Password hashing
- **cryptography** (46.0.3) - mTLS and encryption

#### Frontend (TypeScript/React)
- **React** (18.3.1) - UI framework
- **TanStack Query** (5.90.5) - Server state management
- **TanStack Table** (8.21.3) - Data tables
- **React Grid Layout** (1.5.2) - Drag-and-drop dashboard
- **Tailwind CSS** (3.4.18) - Styling
- **Radix UI** - Accessible components
- **xterm.js** - Terminal emulation
- **CodeMirror** - YAML/JSON editing
- **Zod** (4.1.12) - Schema validation

#### Go Services
- **Docker SDK** (v28.5.2) - Container management
- **Docker Compose** (v2.40.2) - Stack operations
- **gorilla/websocket** - WebSocket connections
- **logrus** - Structured logging

---

## Project Structure

```
dockmon/
├── agent/                    # Go-based remote monitoring agent
│   ├── cmd/agent/           # Agent entrypoint
│   ├── internal/            # Internal packages
│   │   ├── client/          # WebSocket client
│   │   ├── config/          # Configuration
│   │   ├── docker/          # Docker operations
│   │   ├── handlers/        # Message handlers
│   │   └── protocol/        # Communication protocol
│   └── pkg/types/           # Shared types
│
├── backend/                  # Python FastAPI backend
│   ├── agent/               # Agent connection handling
│   ├── alerts/              # Alert engine & rules
│   ├── api/v2/              # v2 API endpoints
│   ├── auth/                # Authentication (sessions, API keys)
│   ├── config/              # Application configuration
│   ├── deployment/          # Stack deployment engine
│   ├── docker_monitor/      # Container monitoring
│   ├── health_check/        # HTTP health checks
│   ├── models/              # Pydantic models
│   ├── security/            # Rate limiting, audit
│   ├── tests/               # Unit & integration tests
│   ├── updates/             # Container update logic
│   ├── utils/               # Shared utilities
│   └── websocket/           # WebSocket connections
│
├── compose-service/          # Go service for Compose operations
│   ├── cmd/                 # Service entrypoint
│   └── internal/            # Business logic
│
├── docker/                   # Docker build files
│   ├── Dockerfile           # Multi-stage build
│   ├── nginx.conf           # Nginx configuration
│   └── supervisord.conf     # Process manager config
│
├── shared/                   # Shared Go modules
│   ├── compose/             # Compose utilities
│   ├── docker/              # Docker utilities
│   └── update/              # Update utilities
│
├── stats-service/            # Go real-time stats streaming
│   ├── aggregator.go        # Stats aggregation
│   ├── cache.go             # Caching layer
│   ├── event_*.go           # Event management
│   └── streamer.go          # WebSocket streaming
│
├── ui/                       # React TypeScript frontend
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── features/        # Feature modules
│   │   │   ├── agents/      # Agent management
│   │   │   ├── alerts/      # Alert configuration
│   │   │   ├── auth/        # Authentication
│   │   │   ├── containers/  # Container views
│   │   │   ├── dashboard/   # Dashboard widgets
│   │   │   ├── deployments/ # Stack deployments
│   │   │   ├── events/      # Event viewer
│   │   │   ├── hosts/       # Host management
│   │   │   ├── logs/        # Log viewer
│   │   │   └── settings/    # User settings
│   │   ├── hooks/           # Custom React hooks
│   │   ├── lib/             # Utilities
│   │   ├── providers/       # Context providers
│   │   └── types/           # TypeScript types
│   └── tests/               # E2E & unit tests
│
└── scripts/                  # Deployment & utility scripts
```

---

## Codebase Metrics

| Metric | Count |
|--------|-------|
| **Python Files** | 221 |
| **Go Files** | 51 |
| **TypeScript Files (.ts)** | 85 |
| **React Files (.tsx)** | 179 |
| **Total Lines of Code** | ~162,000 |
| **Backend Main File** | 5,969 lines |

---

## Architecture Overview

### Multi-Service Container

DockMon runs as a single Docker container with multiple internal services managed by Supervisor:

```
┌─────────────────────────────────────────────────────────────┐
│                     DockMon Container                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Nginx   │  │ Stats Service│  │   Compose Service      │ │
│  │  (443)   │  │   (Go 8081)  │  │      (Go 8082)         │ │
│  └────┬─────┘  └──────────────┘  └────────────────────────┘ │
│       │                                                      │
│       ▼                                                      │
│  ┌──────────────────────────────────────────────────────────┐│
│  │            FastAPI Backend (Python 8080)                 ││
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  ││
│  │  │REST API │ │WebSocket │ │Monitoring│ │   Alerts     │  ││
│  │  └─────────┘ └──────────┘ └──────────┘ └──────────────┘  ││
│  └──────────────────────────────────────────────────────────┘│
│                              │                               │
│                    ┌─────────┴─────────┐                     │
│                    │   SQLite Database │                     │
│                    └───────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### Remote Agent Architecture

```
┌─────────────────────┐         ┌─────────────────────┐
│   Remote Host 1     │         │   Remote Host 2     │
│  ┌───────────────┐  │         │  ┌───────────────┐  │
│  │ DockMon Agent │  │         │  │ DockMon Agent │  │
│  └───────┬───────┘  │         │  └───────┬───────┘  │
│          │          │         │          │          │
│  ┌───────┴───────┐  │         │  ┌───────┴───────┐  │
│  │ Docker Daemon │  │         │  │ Docker Daemon │  │
│  └───────────────┘  │         │  └───────────────┘  │
└──────────┬──────────┘         └──────────┬──────────┘
           │                               │
           │      WebSocket (Outbound)     │
           └───────────────┬───────────────┘
                           ▼
                ┌─────────────────────┐
                │   DockMon Server    │
                │  (Central Instance) │
                └─────────────────────┘
```

---

## Key Features

### 1. Multi-Host Monitoring
- Local Docker via socket mount
- Remote hosts via mTLS or Agent
- Unlimited host connections

### 2. Real-Time Dashboard
- Customizable drag-and-drop widgets
- WebSocket-powered live updates
- CPU, memory, network metrics

### 3. Container Management
- Start, stop, restart, delete
- Bulk operations with progress tracking
- Container shell access (xterm.js)

### 4. Stack Management
- Docker Compose deployments
- Import from running containers
- Real-time deployment progress
- Layer-by-layer image pull tracking

### 5. Intelligent Auto-Restart
- Per-container configuration
- Configurable retry logic
- Cooldown periods

### 6. Advanced Alerting
- **Channels:** Discord, Slack, Telegram, Pushover, Gotify, SMTP
- Customizable templates
- Alert rule evaluation engine

### 7. Health Checks
- HTTP/HTTPS endpoint monitoring
- Auto-restart on failure
- Custom check intervals

### 8. Container Updates
- Automatic update detection
- Scheduled update execution
- Rollback capability

### 9. Blackout Windows
- Schedule maintenance periods
- Suppress alerts during windows

### 10. Event Logging
- Comprehensive audit trail
- Filtering and search
- Real-time event streaming

---

## Security Features

- **Multi-user support** with role-based access control (RBAC)
  - **Admin:** Full access - manage users, hosts, containers, all settings
  - **User:** Standard access - manage containers and hosts
  - **Readonly:** View-only access - no modifications allowed
- **Session-based authentication** with secure cookies
- **API key authentication** for programmatic access
- **Rate limiting** on all endpoints
- **mTLS support** for remote Docker connections
- **Password hashing** with Argon2/bcrypt
- **CORS configuration** for production
- **Security audit logging**
- **Alpine Linux base** (reduced attack surface)
- **no-new-privileges** container security option

---

## Testing Infrastructure

### Backend Tests
- **Unit tests:** Authentication, monitoring, notifications, updates, etc.
- **Integration tests:** Full API testing
- **Location:** `backend/tests/`
- **Framework:** pytest

### Frontend Tests
- **Unit tests:** Component testing with Vitest
- **E2E tests:** Playwright
- **Location:** `ui/tests/`

---

## Build & Deployment

### Docker Build
Multi-stage build process:
1. **Stage 1:** Go builder (stats-service + compose-service)
2. **Stage 2:** Node.js builder (React frontend)
3. **Stage 3:** Python runtime with compiled assets

### Environment Variables
| Variable | Purpose |
|----------|---------|
| `TZ` | Timezone configuration |
| `BASE_PATH` | Reverse proxy subpath |
| `DOCKMON_EXTERNAL_URL` | Notification action links |
| `DOCKMON_CORS_ORIGINS` | CORS configuration |
| `REVERSE_PROXY_MODE` | Enable HTTP mode |

### Volume Mounts
- `/app/data` - Persistent storage (database, configs)
- `/var/run/docker.sock` - Local Docker access

---

## API Architecture

### REST API (v2)
- Session-based or API key authentication
- JSON request/response format
- Comprehensive error handling
- Rate limiting per endpoint type

### WebSocket Endpoints
- `/ws` - Real-time container updates
- `/ws/stats` - Live statistics streaming
- `/ws/logs` - Container log streaming
- `/ws/agent` - Agent communication

---

## Database Schema

Uses SQLAlchemy 2.0 with Alembic migrations. Key models:

- `User` / `UserPrefs` - User accounts and preferences
- `DockerHostDB` - Host configurations
- `ContainerUpdate` / `UpdatePolicy` - Update management
- `AlertRuleV2` / `AlertV2` - Alert configuration
- `NotificationChannel` - Notification settings
- `AutoRestartConfig` - Auto-restart rules
- `Agent` - Remote agent registrations
- `DeploymentMetadata` - Stack deployments

---

## Observations & Recommendations

### Strengths
1. **Comprehensive feature set** - Covers all aspects of Docker monitoring
2. **Modern tech stack** - Latest versions of Python, Go, React
3. **Strong typing** - TypeScript strict mode, Pydantic models
4. **Security-focused** - Multiple authentication methods, mTLS support
5. **Well-documented** - Extensive wiki and inline documentation
6. **Flexible deployment** - Works with various reverse proxies

### Areas for Improvement
1. **Main.py size** - At ~6,000 lines, consider further modularization
2. **Database** - SQLite may limit scaling; consider PostgreSQL support
3. **Test coverage** - Could benefit from more comprehensive E2E tests
4. **API versioning** - v2 exists; consider deprecation strategy for v1

### Technical Debt Indicators
- Large monolithic files (main.py)
- Some inline configuration that could be externalized
- Mixed authentication approaches (cookies + API keys)

---

## License Considerations

DockMon uses **Business Source License 1.1**:

✅ **Permitted:**
- Internal company use
- Personal projects
- MSP/consulting services
- Forking and modification

❌ **Not Permitted:**
- SaaS offerings
- Commercial monitoring platform embedding
- Standalone commercial hosting

**Change Date:** 2027-01-01 (converts to Apache 2.0)

---

## Conclusion

DockMon is a mature, feature-rich Docker monitoring platform with a modern architecture combining Python, Go, and React. The project demonstrates strong engineering practices with security-first design, comprehensive testing infrastructure, and extensive documentation. The multi-service architecture within a single container simplifies deployment while maintaining separation of concerns.

---

*Report generated by analyzing the DockMon repository structure, source code, and documentation.*
