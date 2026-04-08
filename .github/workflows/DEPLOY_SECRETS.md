# Pipeline secrets and variables

## Required secrets

Must be set in **Settings → Secrets and variables → Actions → Secrets**.
The pipeline will fail or behave insecurely without these.

| Secret | Description |
|---|---|
| `TAILSCALE_AUTHKEY` | Tailscale auth key used to join the VPN before SSH. |
| `SERVER_IP` | IP or hostname of the deployment target (Tailscale or public). |
| `SERVER_USER` | SSH username on the target server. |
| `SSH_PRIVATE_KEY` | Private SSH key matching a key authorized on the target server. At least one of `SSH_PRIVATE_KEY` or `SSH_PASSWORD` must be set. |
| `SSH_PASSWORD` | Password for the SSH user. Used as fallback when `SSH_PRIVATE_KEY` is not set or key auth fails. |
| `DB_PASSWORD` | PostgreSQL password for the `DB_USER` account. |
| `SECRET_KEY` | Flask session signing secret. Use a long random string. |
| `JWT_SECRET_KEY` | JWT token signing secret. Use a long random string. |
| `ADMIN_EMAIL` | Email used to bootstrap the initial super admin account. |
| `ADMIN_PASSWORD` | Password used to bootstrap the initial super admin account. |
| `AZURE_STORAGE_SAS_TOKEN` | SAS token forwarded to the classifier service. |
| `PGADMIN_DEFAULT_PASSWORD` | Login password for the pgAdmin web interface. |

## Optional variables

Set in **Settings → Secrets and variables → Actions → Variables**.
All have safe fallback values; override only when the defaults do not fit your server.

| Variable | Default | Description |
|---|---|---|
| `DEPLOY_PATH` | `$HOME/<repo-name>` | Absolute path to the project on the target server. |
| `DB_USER` | `postgres` | PostgreSQL username. |
| `DB_NAME` | `retinal_db` | PostgreSQL database name. |
| `DB_PORT` | `5432` | Host port published for PostgreSQL. |
| `FLASK_PORT` | `8080` | Host port published for the Flask application. |
| `PROCESSING_SERVICE_PORT` | `5000` | Host port published for the classifier service. |
| `LOG_LEVEL` | `INFO` | Log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, `TRACE`). |
| `LOG_FORMAT` | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | Python logging format string. |
| `LOG_FILE` | `app.log` | Log file path inside the containers. |
| `PGADMIN_DEFAULT_EMAIL` | `admin@example.com` | Login email for the pgAdmin web interface. |
| `PGADMIN_PORT` | `5050` | Host port published for pgAdmin. |
