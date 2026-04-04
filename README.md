# Retinálny obrazový systém

Tento projekt je navrhnutý na ukladanie, správu a spracovanie obrazov očných sietnic. Na serverovej strane sa spracovávajú dáta a uchovávajú sa v MySQL databáze, zatiaľ čo klientská časť (webové rozhranie) umožňuje prístup k databáze, spúšťanie spracovateľských algoritmov a prezeranie výsledkov.

## Cieľ projektu

Cieľom aplikácie je:
- Ukladať a spravovať obrazy očných sietnic a s nimi spojené údaje.
- Umožniť spúšťanie preddefinovaných algoritmov (klasifikácia, segmentácia a detekcia) na vybraný obraz.
- Poskytnúť prehľadné webové rozhranie pre správu databázy a prístup z mobilných zariadení pomocou PWA (Progressive Web Apps).

## Funkcionality

1. **Server aplikácia s MySQL databázou**  
   - Ukladanie informácií o používateľoch (s rôznymi úrovňami prístupu).  
   - Uchovávanie anonymizovaných údajov o pacientoch.  
   - Evidovanie ciest k súborom obsahujúcim obrazy očných sietnic.

2. **Web rozhranie pre správu databázy**  
   - Prehľadné zobrazenie obrazov a výsledkov spracovania podľa jednotlivých používateľov.  
   - Administratívne nástroje pre správu a údržbu databázy.

3. **Web formulár pre mobilné zariadenia (PWA)**  
   - Responzívny prístup cez progresívnu webovú aplikáciu optimalizovanú pre mobilné zariadenia.
   

4. **Testovanie funkcionalít**  
   - Jednotkové a integračné testy na overenie funkčnosti celej aplikácie.  
   - Zabezpečenie kvality a spoľahlivosti implementovaných riešení.

## Technológie

- **Backend:** Flask (Python) s PostgreSQL databázou
- **Frontend:** HTML, CSS, JavaScript
- **Algoritmy:** Preddefinované algoritmy pre klasifikáciu, segmentáciu a detekciu obrazov

---

## 🚀 Developer Setup Guide

---

## 🐳 Docker Compose Setup (Recommended)

Najrýchlejší spôsob spustenia celej aplikácie. Nevyžaduje lokálnu inštaláciu Pythonu ani PostgreSQL — stačí Docker.

### Prerequisites

- **Docker Desktop** (zahŕňa Docker Engine aj Docker Compose) — [Download](https://www.docker.com/products/docker-desktop/)
- **Git** — [Download](https://git-scm.com/downloads)

### ▶️ Spustenie v 3 krokoch

**1. Naklonujte repozitár**

```bash
git clone https://FEI-STU-DR-LAB@dev.azure.com/FEI-STU-DR-LAB/ExplainableAI-for-DR-diagnosis/_git/drapp-client-server
cd drapp-client-server
```

**2. Vytvorte `.env` súbor**

Skopírujte `env_example` a nastavte tajné kľúče:

```bash
# Linux / macOS / Git Bash
cp env_example .env

# Windows PowerShell
Copy-Item env_example .env
```

Minimálne hodnoty, ktoré je potrebné zmeniť v `.env`:

```env
SECRET_KEY=your-strong-secret-key
JWT_SECRET_KEY=your-strong-jwt-secret
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-admin-password
```

Všetky ostatné hodnoty majú bezpečné predvolené nastavenia a Docker Compose ich automaticky prepíše správnymi internými adresami (napr. `DATABASE_URL` a `MOCK_API_URL` sú nastavené na mená kontajnerov vnútri siete).

**3. Spustite aplikáciu**

```bash
docker compose -f build/docker/docker-compose.yml up --build
```

Pri prvom spustení Docker stiahne obrazy a zostaví kontajnery. Nasledujúce spustenia sú rýchlejšie:

```bash
docker compose -f build/docker/docker-compose.yml up
```

### 🌐 Dostupné služby

| Služba | URL | Popis |
|---|---|---|
| Flask aplikácia | http://localhost:8080 | Hlavné webové rozhranie |
| Mock inference API | http://localhost:5000 | Simulovaný AI server |
| PostgreSQL | `localhost:5432` | Databáza (napr. pre pgAdmin) |

### 🛑 Zastavenie a čistenie

```bash
# Zastavenie kontajnerov (dáta zostanú zachované)
docker compose -f build/docker/docker-compose.yml down

# Zastavenie + odstránenie databázových volumes (vymaže všetky dáta!)
docker compose -f build/docker/docker-compose.yml down -v

# Prebudovanie kontajnerov po zmene kódu
docker compose -f build/docker/docker-compose.yml up --build
```

### ⚙️ Konfigurácia portov

Porty je možné zmeniť v `.env` súbore bez úpravy `build/docker/docker-compose.yml`:

```env
FLASK_PORT=8080       # Port Flask aplikácie
MOCK_API_PORT=5000    # Port mock inference servera
DB_PORT=5432          # Port PostgreSQL
```

### 📋 Správa jednotlivých služieb

```bash
# Sledovanie logov konkrétnej služby
docker compose -f build/docker/docker-compose.yml logs -f flask-app
docker compose -f build/docker/docker-compose.yml logs -f mock-api
docker compose -f build/docker/docker-compose.yml logs -f db

# Reštart jednej služby
docker compose -f build/docker/docker-compose.yml restart flask-app

# Spustenie príkazu vo vnútri kontajnera (napr. migrácie)
docker compose -f build/docker/docker-compose.yml exec flask-app python migrate.py db upgrade
```

---

## 🛠️ Manual (Local) Setup

Ak preferujete manuálne nastavenie bez Dockera:

### Prerequisites

Pred začatím práce na projekte sa uistite, že máte nainštalované:

1. **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
2. **PostgreSQL** - [Download PostgreSQL](https://www.postgresql.org/download/)
3. **Git** - [Download Git](https://git-scm.com/downloads)
4. **Make** (pre Windows: [Make for Windows](http://gnuwin32.sourceforge.net/packages/make.htm) alebo použite WSL)

### 🔧 Quick Setup (Recommended)

Pre rýchle nastavenie vývojového prostredia:

```bash
# 1. Klonujte repozitár
git clone <repository-url>
cd drapp-client-server/flask-app
make setup-dev

# 3. Aktivujte virtuálne prostredie
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Nastavte databázu
make init-db

# 5. Spustite aplikáciu a mock server
make both-servers
```

### 📋 Manual Setup

Ak preferujete manuálne nastavenie:

#### 1. Virtual Environment

```bash
# Vytvorte virtuálne prostredie
python -m venv venv

# Aktivujte ho
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

#### 2. Install Dependencies

```bash
# Nainštalujte základné závislosti
pip install --upgrade pip
pip install -r requirements.txt

# Pre development (testing, linting, formatting)
pip install pytest pytest-cov flake8 black isort pre-commit
```

#### 3. Environment Configuration

Vytvorte `.env` súbor v `flask-app/` adresári (používajte `env_example` ako šablónu):

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost/retinal_db
SQLALCHEMY_DATABASE_URI=postgresql://username:password@localhost/retinal_db

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your-secret-key-here

# Port Configuration (configurable)
FLASK_PORT=8080          # Default: 8080 - Flask application port
MOCK_API_PORT=5000       # Default: 5000 - Mock inference server port

# Mock API Configuration
MOCK_API_URL=http://localhost:5000
```

**Port Configuration:**
- `FLASK_PORT` - Port pre Flask aplikáciu (predvolene: 8080)
- `MOCK_API_PORT` - Port pre mock inference server (predvolene: 5000)
- Porty sú plne konfigurovateľné cez environment premenné

#### 4. Database Setup

```bash
# Inicializujte databázu
make init-db

# Alebo manuálne:
python migrate.py db init
python migrate.py db migrate -m "Initial migration"
python migrate.py db upgrade
```

### 🏃 Running the Application

#### Development Mode

```bash
# Spustite Flask aplikáciu v development móde
make dev

# Alebo manuálne:
set FLASK_ENV=development && set FLASK_DEBUG=1 && python run.py
```

#### Mock Inference Server

Mock server simuluje AI spracovanie obrazov. Porty sú konfigurovateľné cez environment premenné:

```bash
# V popredí (foreground) - použije MOCK_API_PORT alebo default 5000
make mock-server

# V pozadí (background) - použije MOCK_API_PORT alebo default 5000
make stop-mock-server

# Spustenie oboch serverov naraz (porty sú konfigurovateľné)
make both-servers
```

**Príklad s custom portami:**
```bash
# Nastavte custom porty
export FLASK_PORT=3000
export MOCK_API_PORT=4000

# Spustite servery s custom portami
make both-servers  # Flask: 3000, Mock: 4000
```

### 🧪 Testing

```bash
# Spustite testy
make test

# Alebo manuálne:
pytest tests/ -v --cov=server --cov-report=html --cov-report=term
```

### 📁 Project Structure

```
TP2025_Server-Client_app/
├── build/
│   └── docker/
│       ├── docker-compose.yml  # Orchestrates all services
│       ├── Dockerfile         # Docker image for the Flask app
│       └── Dockerfile.mock    # Docker image for the mock inference server
├── mock_api.py               # Mock inference server (FastAPI / uvicorn)
├── env_example               # Template for .env file
├── .devcontainer/
│   └── devcontainer.json     # VS Code Dev Container config
└── flask-app/
    ├── run.py                # Application entry point
    ├── requirements.txt      # Python dependencies
    ├── Makefile              # Development commands
    ├── server/               # Flask backend
    │   ├── models/           # Database models
    │   ├── routes/           # API routes
    │   └── services/         # Business logic
    ├── client/               # Frontend (HTML / CSS / JS)
    ├── tests/                # Test files
    ├── migrations/           # Alembic DB migrations
    └── uploads/              # Uploaded files (persisted via Docker volume)
```

### 🛠️ Available Make Commands

Pre zobrazenie všetkých dostupných príkazov:

```bash
make help
```

**Najdôležitejšie príkazy:**

- `make setup-dev` - Kompletné nastavenie development prostredia
- `make both-servers` - Spustenie Flask app + mock servera (porty konfigurovateľné cez env)
- `make dev` - Development režim Flask aplikácie (port konfigurovateľný cez FLASK_PORT)
- `make mock-server` - Spustenie mock servera (port konfigurovateľný cez MOCK_API_PORT)
- `make health-check` - Kontrola stavu Flask aplikácie
- `make health-check-mock` - Kontrola stavu mock servera
- `make test` - Spustenie testov
- `make clean` - Vyčistenie dočasných súborov
- `make migrate msg="description"` - Vytvorenie novej migrácie
- `make upgrade` - Aplikovanie migrácií

### 🔍 Common Issues & Solutions

#### 1. Database Connection Issues

```bash
# Overte, že PostgreSQL beží
# Windows: services.msc -> PostgreSQL
# Linux: sudo systemctl status postgresql

# Vytvorte databázu ak neexistuje
createdb retinal_db
```

#### 2. Port Already in Use

```bash
# Kontrola portov (použijú sa konfigurovateľné porty z env)
netstat -ano | findstr :8080  # Flask default port
netstat -ano | findstr :5000  # Mock server default port

# Alebo použite make príkazy pre health check
make health-check      # Kontrola Flask app
make health-check-mock # Kontrola mock server

# Zastavte proces alebo zmeňte port v .env súbore
```

#### 3. Virtual Environment Issues

```bash
# Odstráňte a vytvorte znovu
rm -rf venv  # Linux/Mac
rmdir /s venv  # Windows
make venv
```

### 📝 Development Workflow

1. **Vytvorte nový branch** pre vašu funkcionalitu
2. **Aktivujte virtual environment**
3. **Spustite testy** pred začatím práce: `make test`
4. **Implementujte zmeny**
5. **Formátujte kód**: `make format`
6. **Spustite linting**: `make lint`
7. **Spustite testy**: `make test`
8. **Vytvorte commit a push**

### 🚀 Production Deployment

```bash
# Production setup
make prod-setup

# Alebo manuálne:
pip install -r requirements.txt
python migrate.py db upgrade
python run.py
```

### 🔧 Environment Variables

**Port Configuration:**
```bash
FLASK_PORT=8080        # Flask application port (default: 8080)
MOCK_API_PORT=5000     # Mock inference server port (default: 5000)
```

**Logging Configuration:**
```bash
LOG_LEVEL=INFO         # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL, TRACE (default: INFO)
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s  # Log format
LOG_FILE=app.log       # Log file path (default: app.log)
```

**Database Configuration:**
```bash
DATABASE_URL=postgresql://username:password@localhost/retinal_db
SQLALCHEMY_DATABASE_URI=postgresql://username:password@localhost/retinal_db
```

**Security Configuration:**
```bash
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
```

### 📊 Logging Features

Aplikácia podporuje konfigurovateľné úrovne logovania cez environment premennú `LOG_LEVEL`:

**Dostupné úrovne logovania:**
- `TRACE` - Najdetailnejšie logování (custom level)
- `DEBUG` - Debugging informácie, SQL queries
- `INFO` - Základné informácie o behu aplikácie (default)
- `WARNING` - Varovania
- `ERROR` - Chyby
- `CRITICAL` - Kritické chyby

**Príklady použitia:**
```bash
# Development s detailným logovaním
export LOG_LEVEL=DEBUG
make dev

# Production s minimálnym logovaním
export LOG_LEVEL=WARNING
make run

# Trace level pre debugging
export LOG_LEVEL=TRACE
LOG_FILE=logs/debug.log make both-servers
```

**Konfigurácia log súboru:**
```bash
# Základný log súbor
LOG_FILE=app.log

# Log súbor v adresári
LOG_FILE=logs/retinal_app.log

# Oddelené log súbory pre komponenty
LOG_FILE=logs/flask_$(date +%Y%m%d).log
```

**Log výstup:**
- **Console** - Všetky log správy sa zobrazujú v konzole
- **File** - Všetky log správy sa ukladajú do súboru (default: `app.log`)
- **SQL Queries** - V DEBUG/TRACE móde sa zobrazujú SQL dotazy

### 📞 Support

Pre otázky a problémy:
- Vytvorte issue v GitHub repozitári
- Kontaktujte vývojový tím

