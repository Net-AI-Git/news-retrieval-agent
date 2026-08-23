### Template AI Microservice API

#### Template Setup — fill these before first run
After cloning, replace every `<FILL_ME>` / `<project-name>` placeholder:
1. `pyproject.toml` → `name` — set the service name.
2. `README.md` clone commands below → replace `<project-name>` with the new repo name.
3. `.env` → fill every `<FILL_ME>` value (copy from the template `.env`, see path at the bottom).
4. `src/conts.py` → `OTEL_SERVICE_NAME` — set the OpenTelemetry service name used by OpenSearch.

#### Local Run
- Copy the .env file to your local repo, this file contains the environment variables.

- Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then install the project dependencies:
```bash
uv sync
```

- Run the uvicorn server:
```bash
uv run uvicorn main:app
```


- Verify the API works properly at http://127.0.0.1:8000/api/ping, and there are no errors in the console.


- Clone the template into a new project 
```bash
# 1. Clone the existing repository
git clone https://github.com/<organization>/<project-name>.git
 
# 2. Move into the cloned repository directory
cd <project-name>
 
# 3. Remove the old remote
git remote remove origin
 
# 4. (Create a new repository in GitHub manually)
 
# 5. Add the new remote
git remote add origin https://github.com/<organization>/<new-repo>.git
 
# 6. Push all branches to the new repo
git push --all origin
 
# 7. Push all tags to the new repo
git push --tags origin
 
# 8. Verify remotes (optional)
git remote -v
```

- Copy `.env.example` to `.env` in the project root and fill every placeholder.
