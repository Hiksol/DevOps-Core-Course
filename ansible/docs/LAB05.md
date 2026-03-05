# Lab 5 — Ansible Fundamentals — Report

## 1. Architecture Overview

- **Ansible version**: `ansible 2.16.3` (output: `ansible --version` on control node)
- **Target VM**: Ubuntu 24.04 LTS, IP `192.168.0.53`, running on VirtualBox (bridged network)
- **Role‑based structure**:
  ```
  ansible/
    ├── inventory/
    │   └── hosts.ini
    │── group_vars/
    │   └── all.yml
    ├── roles/
    │   ├── common/
    │   │   ├── defaults/
    │   │   │   └── main.yml
    │   │   └── tasks/
    │   │       └── main.yml
    │   ├── docker/
    │   │   ├── defaults/
    │   │   │   └── main.yml
    │   │   ├── handlers/
    │   │   │   └── main.yml
    │   │   └── tasks/
    │   │       └── main.yml
    │   └── app_deploy/
    │       ├── defaults/
    │       │   └── main.yml
    │       └── tasks/
    │           └── main.yml
    ├── playbooks/
    │   ├── provision.yml
    │   └── deploy.yml
    ├── ansible.cfg
    └── docs/
        └── LAB05.md
  ```
- **Why roles?**  
  Roles promote code reuse, simplify maintenance, and provide a clear, modular structure. Each role encapsulates a specific piece of functionality (system basics, Docker installation, application deployment) and can be reused across different projects or hosts.

## 2. Roles Documentation

### 2.1 `common`
- **Purpose**: Perform basic system setup: update APT cache, install essential packages, and (optionally) set timezone.
- **Key variables** No variables – packages are hardcoded in tasks
- **Handlers**: None.
- **Dependencies**: None.

### 2.2 `docker`
- **Purpose**: Install Docker CE, ensure the service is running, add the current user to the `docker` group, and install the Python Docker module required for Ansible’s docker modules.
- **Key variables**: No role-specific variables – the user `hiksol` is hardcoded in the task that adds it to the `docker` group.
- **Handlers**:
  - `restart docker` – restarts the Docker daemon when needed.
- **Dependencies**: None, but requires `common` for basic tools (curl, etc.).

### 2.3 `app_deploy`
- **Purpose**: Deploy the containerised Python application:
  - Log in to Docker Hub using Vault‑encrypted credentials.
  - Pull the Docker image.
  - Stop and remove any existing container with the same name.
  - Run a new container with proper port mapping and restart policy.
  - Wait for the application to be ready (port check) and verify its health endpoint.
- **Key variables** (defaults and Vault‑provided):
  ```yaml
  app_port: 5000
  docker_image_tag: latest
  dockerhub_username: hiksol
  dockerhub_password: ***
  app_name: devops-info-service
  docker_image: "{{ dockerhub_username }}/{{ app_name }}"
  app_container_name: "{{ app_name }}"
  ```
- **Handlers**: None used in this deployment (no restart triggered).
- **Dependencies**: Requires Docker to be installed (role `docker`).

## 3. Idempotency Demonstration

### First run of `provision.yml`
```
$ ansible-playbook playbooks/provision.yml --ask-pass --ask-become-pass
SSH password:
BECOME password[defaults to SSH password]:

PLAY [Provision server] ************************************************************************************************
TASK [Gathering Facts] *************************************************************************************************ok: [vm]

TASK [common : Update apt cache] ***************************************************************************************ok: [vm]

TASK [common : Install common packages] ********************************************************************************changed: [vm]

TASK [docker : Install dependencies] ***********************************************************************************ok: [vm]

TASK [docker : Add Docker GPG key] *************************************************************************************changed: [vm]

TASK [docker : Add Docker repository] **********************************************************************************changed: [vm]

TASK [docker : Install Docker] *****************************************************************************************changed: [vm]

TASK [docker : Ensure Docker running] **********************************************************************************ok: [vm]

TASK [docker : Add user to docker group] *******************************************************************************changed: [vm]

RUNNING HANDLER [docker : restart docker] ******************************************************************************changed: [vm]

PLAY RECAP *************************************************************************************************************vm                         : ok=10   changed=6    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

### Second run of `provision.yml`
```
$ ansible-playbook playbooks/provision.yml --ask-pass --ask-become-pass
SSH password:
BECOME password[defaults to SSH password]:

PLAY [Provision server] ************************************************************************************************
TASK [Gathering Facts] *************************************************************************************************ok: [vm]

TASK [common : Update apt cache] ***************************************************************************************ok: [vm]

TASK [common : Install common packages] ********************************************************************************ok: [vm]

TASK [docker : Install dependencies] ***********************************************************************************ok: [vm]

TASK [docker : Add Docker GPG key] *************************************************************************************ok: [vm]

TASK [docker : Add Docker repository] **********************************************************************************ok: [vm]

TASK [docker : Install Docker] *****************************************************************************************ok: [vm]

TASK [docker : Ensure Docker running] **********************************************************************************ok: [vm]

TASK [docker : Add user to docker group] *******************************************************************************ok: [vm]

PLAY RECAP *************************************************************************************************************vm                         : ok=9    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

**Analysis**:  
- **First run** – six tasks reported `changed`. These were: installing common packages, adding Docker’s GPG key, adding the Docker repository, installing Docker, adding the user to the `docker` group, and the handler restarting Docker. All these actions modified the system.
- **Second run** – every task reported `ok` (green). No changes were made because the desired state (packages installed, repository configured, user already in the group) was already present.

**Why idempotent?**  
All tasks use state‑based modules (`apt`, `apt_key`, `apt_repository`, `user`, `service`) that check the current state before applying any change. For example, `apt: name=docker-ce state=present` will install the package only if it is missing; otherwise it does nothing. This guarantees that running the playbook multiple times does not introduce unintended changes.

## 4. Ansible Vault Usage

Sensitive data (Docker Hub credentials) are stored in an encrypted file:

```
inventory/group_vars/all.yml
```

The file was created with:

```bash
ansible-vault create inventory/group_vars/all.yml
```

and contains:

```yaml
---
dockerhub_username: hiksol
dockerhub_password: ***
app_name: devops-info-service
docker_image: "{{ dockerhub_username }}/{{ app_name }}"
docker_image_tag: latest
app_port: 5000
app_container_name: "{{ app_name }}"
```

**Vault password management**:  
The vault password is stored in a separate file `.vault_pass` (added to `.gitignore`) and referenced in `ansible.cfg`:

```ini
[defaults]
vault_password_file = .vault_pass
```

This allows playbooks to be run without manually entering the password each time, while keeping the password out of version control.

**Why Ansible Vault?**  
It enables secure storage of secrets (passwords, tokens) inside a Git repository. Without encryption, credentials would be exposed to anyone with access to the code. Vault ensures that only authorised users (who know the password) can view or modify the secrets.

## 5. Deployment Verification

### Successful `deploy.yml` run (after fixing role structure)
```
$ ansible-playbook playbooks/deploy.yml --ask-vault-pass --ask-pass --ask-become-pass
SSH password:
BECOME password[defaults to SSH password]:
Vault password:

PLAY [Deploy application] ***********************************************************************************************

TASK [Gathering Facts] **************************************************************************************************
ok: [vm]

TASK [app_deploy : Log in to Docker Hub] ********************************************************************************
ok: [vm]

TASK [app_deploy : Pull Docker image] ***********************************************************************************
changed: [vm]

TASK [app_deploy : Stop and remove existing container] ******************************************************************
ok: [vm]

TASK [app_deploy : Run application container] ***************************************************************************
changed: [vm]

TASK [app_deploy : Wait for application to be ready] ********************************************************************
ok: [vm]

TASK [app_deploy : Verify health endpoint] ******************************************************************************
ok: [vm]

PLAY RECAP **************************************************************************************************************
vm                         : ok=7    changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

### Container status
```
$ ssh hiksol@192.168.0.53 "docker ps"
CONTAINER ID   IMAGE                               COMMAND           CREATED         STATUS         PORTS                    NAMES
22fc82492fc9   hiksol/devops-info-service:latest   "python app.py"   5 minutes ago   Up 5 minutes   0.0.0.0:5000->5000/tcp   devops-info-service
```

### Application health and main endpoint

**From inside the VM** (to confirm local operation):
```bash
hiksol@Ubuntu:~$ curl http://localhost:5000/
{
  "service": {
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course info service",
    "framework": "FastAPI"
  },
  "system": {
    "hostname": "22fc82492fc9",
    "platform": "Linux",
    "platform_version": "#14~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC Thu Jan 15 15:52:10 UTC 2",
    "architecture": "x86_64",
    "cpu_count": 4,
    "python_version": "3.13.12"
  },
  "runtime": {
    "uptime_seconds": 2990,
    "uptime_human": "0 hours, 49 minutes",
    "current_time": "2026-02-26T19:19:41.235517+00:00",
    "timezone": "UTC"
  },
  "request": {
    "client_ip": "192.168.0.101",
    "user_agent": "curl/8.5.0",
    "method": "GET",
    "path": "/"
  },
  "endpoints": [
    {"path": "/", "method": "GET", "description": "Service information"},
    {"path": "/health", "method": "GET", "description": "Health check"}
  ]
}
hiksol@Ubuntu:~$ curl http://localhost:5000/health
{"status":"healthy","timestamp":"2026-02-26T19:19:44.819294+00:00","uptime_seconds":2993}
```

**From the host machine** (verifying external accessibility):
```
$ curl http://192.168.0.53:5000
(identical output as above)
$ curl http://192.168.0.53:5000/health
{"status":"healthy","timestamp":"2026-02-26T19:19:44.819294+00:00","uptime_seconds":2993}
```

**Handlers**: No handlers were triggered during deployment because the role does not currently define any (e.g., restarting the container is done directly in the run task).

## 6. Key Decisions

- **Why use roles instead of plain playbooks?**  
  Roles enable clean separation of concerns, making the code easier to understand, reuse, and maintain. Each role can be developed and tested independently.

- **How do roles improve reusability?**  
  A well‑written role can be included in any playbook, across different projects, simply by referencing it. Variables allow the role to adapt to different environments.

- **What makes a task idempotent?**  
  Using modules that check the current state and apply changes only when necessary (e.g., `apt: state=present`, `user: state=present`). This ensures that running the task multiple times does not alter the system after the first successful run.

- **How do handlers improve efficiency?**  
  Handlers are triggered only when a task reports a change. For example, restarting Docker only after its configuration has been updated avoids unnecessary service restarts, reducing downtime and improving performance.

- **Why is Ansible Vault necessary?**  
  Vault encrypts sensitive information such as passwords and API tokens, allowing them to be stored securely in version control without exposing them to unauthorized users.

## 7. Challenges Encountered (and Solutions)

1. **Undefined variable errors during `deploy.yml`**  
   - *Problem*: Variables from `group_vars/all.yml` were not being loaded because the file was placed in the wrong location.  
   - *Solution*: Moved `group_vars/` into the `inventory/` directory (as per Ansible’s search path when `inventory` points to a specific file). After the change, variables were correctly resolved.

2. **Docker image pull failing with 404**  
   - *Problem*: The image `hiksol/devops-app:latest` did not exist on Docker Hub.  
   - *Solution*: Built the image from the application source and pushed it to Docker Hub using `docker build` and `docker push`.

3. **`sudo` password prompts during ad‑hoc commands**  
   - *Problem*: Commands like `ansible webservers -a "sudo ufw status"` failed because Ansible could not provide a terminal for sudo.  
   - *Solution*: Used `ssh -t` directly for interactive sudo commands, or configured passwordless sudo on the target VM for automation (not implemented here but recommended).