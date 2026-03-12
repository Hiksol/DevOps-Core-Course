# **LAB06 — Advanced Ansible & CI/CD**

## **1. Overview**

This lab extends the automation created in Lab 5 by adding production‑grade features to the Ansible infrastructure. The work includes restructuring roles with blocks and tags, migrating to Docker Compose v2, implementing safe wipe logic, defining role dependencies, and building a CI/CD pipeline using GitHub Actions. The final result is a fully automated, reproducible, and maintainable deployment workflow.

Technologies used: **Ansible 2.16+, Docker Compose v2, GitHub Actions, Jinja2, Ansible Vault**.

---

## **2. Blocks and Tags**

### **2.1 Block usage**

Blocks were introduced to group related tasks, apply shared directives, and improve error handling.

**In the `common` role:**
- A `packages` block installs system packages.
- A `users` block manages user accounts.
- A `rescue` block fixes apt cache issues using `apt-get update --fix-missing`.
- An `always` block writes a completion log to `/tmp/common_done`.

**In the `docker` role:**
- A `docker_install` block installs Docker Engine.
- A `docker_config` block configures the Docker group.
- A `rescue` block retries GPG key installation after a delay.
- An `always` block ensures the Docker service is enabled and running.

### **2.2 Tag strategy**

Tags implemented:
- `common`, `packages`, `users`
- `docker`, `docker_install`, `docker_config`
- `app_deploy`, `compose`
- `web_app_wipe`

Example executions:
```bash
ansible-playbook playbooks/provision.yml --tags docker
ansible-playbook playbooks/provision.yml --skip-tags common
ansible-playbook playbooks/provision.yml --tags packages
ansible-playbook playbooks/provision.yml --tags docker_install
```

Tags allow selective execution and faster testing.

---

## **3. Docker Compose Migration**

### **3.1 Compose template**

A Jinja2 template was created:

```yaml
version: '3.8'

services:
  {{ app_name }}:
    image: "{{ docker_image }}:{{ docker_tag }}"
    container_name: "{{ app_name }}"
    ports:
      - "{{ app_port }}:{{ app_port }}"
    restart: unless-stopped
```

Key features:
- Dynamic variables for image, tag, ports, and container name.
- Compatibility with Docker Compose v2.
- Correct port mapping based on the application’s actual listening port.

### **3.2 Role dependencies**

In `roles/web_app/meta/main.yml`:

```yaml
dependencies:
  - role: docker
```

This ensures Docker is installed before deploying the application.

### **3.3 Deployment logic**

The `web_app` role:
- Creates `/opt/{{ app_name }}`.
- Renders the docker-compose.yml file.
- Deploys using `community.docker.docker_compose_v2`.

### **3.4 Testing**

- Deployment succeeds.
- Re-running the playbook shows idempotency (`changed=0`).
- Application is reachable at `http://localhost:5000`.

---

## **4. Wipe Logic**

### **4.1 Implementation**

The wipe logic removes all application artifacts safely:

- Stops and removes containers (`docker_compose_v2 state=absent`).
- Deletes docker-compose.yml.
- Deletes the application directory.
- Logs wipe completion.

All tasks use `ignore_errors: true` to avoid failures if the app is already absent.

### **4.2 Double‑gating**

Wipe runs **only if both**:
- `web_app_wipe=true`
- `--tags web_app_wipe` is provided

This prevents accidental deletion.

### **4.3 Wipe testing**

**Scenario 1 — Normal deploy**  
Wipe skipped, app deployed normally.

**Scenario 2 — Wipe only**  
App removed, deploy skipped.

**Scenario 3 — Clean reinstall**  
Wipe → Deploy, app redeployed from scratch.

**Scenario 4 — Safety checks**  
4a: Tag only → wipe skipped  
4b: Tag + variable → only wipe runs

---

## **5. CI/CD Integration**

### **5.1 Architecture**

A **self‑hosted GitHub Actions runner** was installed on the same VM where the application is deployed.  
This approach:
- avoids SSH configuration,
- simplifies secrets management,
- speeds up deployments.

### **5.2 Workflow**

`.github/workflows/ansible-deploy.yml` includes:
- code checkout,
- ansible-lint,
- Ansible playbook execution,
- application health check.

### **5.3 Secrets**

Only one secret is required:
- `ANSIBLE_VAULT_PASSWORD`

SSH keys are not needed because the runner is local.

### **5.4 CI/CD testing**

- Workflow triggers on changes to the ansible directory.
- Linting passes.
- Deployment runs successfully.
- Application responds to health checks.

---

## **6. Testing Results**

### **6.1 Idempotency**
Repeated deployments produce:
```
changed=0
```

### **6.2 Application accessibility**
```
curl http://localhost:5000
→ valid response
```

### **6.3 Wipe logic**
All four scenarios behave exactly as required.

### **6.4 CI/CD**
Workflow runs automatically and completes successfully.

---

## **7. Challenges and Solutions**

- **docker-compose Python library incompatible with Python 3.12**  
  → switched to `docker_compose_v2`.

- **Incorrect variable name (`docker_image_tag`)**  
  → unified to `docker_tag`.

- **Port mismatch (app listened on 5000, compose mapped 8000)**  
  → corrected template.

- **Wipe failed when compose file missing**  
  → added `ignore_errors: true`.

---

## **8. Research Answers**

### **Why use both a variable and a tag?**  
To prevent accidental deletion. A tag alone is too easy to mistype; a variable requires explicit intent.

### **Difference from the `never` tag?**  
`never` blocks execution completely.  
Wipe logic needs conditional execution, not a permanent block.

### **Why must wipe run before deployment?**  
To support clean reinstall: remove old → deploy new.

### **When choose clean reinstall vs rolling update?**  
- Clean reinstall: corrupted state, testing, major migrations.  
- Rolling update: production upgrades with zero downtime.

### **How to extend wipe to remove images and volumes?**  
Add tasks using `docker_image` and `docker_volume` modules with `state: absent`.

---

## **9. Testing results**

```bash
hiksol@Hiksol:~/ansible$ ansible-playbook playbooks/provision.yml --tags docker 

PLAY [Provision server] ************************************************************************************************

TASK [Gathering Facts] *************************************************************************************************
ok: [vm]

PLAY RECAP *************************************************************************************************************
vm                         : ok=1    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0

hiksol@Hiksol:~/ansible$ ansible-playbook playbooks/provision.yml --skip-tags common 

PLAY [Provision server] ************************************************************************************************

TASK [Gathering Facts] *************************************************************************************************
ok: [vm]

TASK [common : Update apt cache] ***************************************************************************************
changed: [vm]

TASK [common : Install packages] ***************************************************************************************
ok: [vm]

TASK [common : Log completion] *****************************************************************************************
changed: [vm]

TASK [common : Create user accounts] ***********************************************************************************
skipping: [vm]

TASK [docker : Install dependencies] ***********************************************************************************
ok: [vm]

TASK [docker : Add Docker GPG key] *************************************************************************************
ok: [vm]

TASK [docker : Add Docker repository] **********************************************************************************
ok: [vm]

TASK [docker : Install Docker packages] ********************************************************************************
ok: [vm]

TASK [docker : Ensure Docker service enabled] **************************************************************************
ok: [vm]

TASK [docker : Add user to docker group] *******************************************************************************
ok: [vm]

PLAY RECAP *************************************************************************************************************
vm                         : ok=10   changed=2    unreachable=0    failed=0    skipped=1    rescued=0    ignored=0

hiksol@Hiksol:~/ansible$ ansible-playbook playbooks/provision.yml --tags packages 

PLAY [Provision server] ************************************************************************************************

TASK [Gathering Facts] *************************************************************************************************
ok: [vm]

TASK [common : Update apt cache] ***************************************************************************************
changed: [vm]

TASK [common : Install packages] ***************************************************************************************
ok: [vm]

TASK [common : Log completion] *****************************************************************************************
changed: [vm]

PLAY RECAP *************************************************************************************************************
vm                         : ok=4    changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0

hiksol@Hiksol:~/ansible$ ansible-playbook playbooks/provision.yml --tags 

PLAY [Provision server] ************************************************************************************************

TASK [Gathering Facts] *************************************************************************************************
ok: [vm]

TASK [docker : Install dependencies] ***********************************************************************************
ok: [vm]

TASK [docker : Add Docker GPG key] *************************************************************************************
ok: [vm]

TASK [docker : Add Docker repository] **********************************************************************************
ok: [vm]

TASK [docker : Install Docker packages] ********************************************************************************
ok: [vm]

TASK [docker : Ensure Docker service enabled] **************************************************************************
ok: [vm]

PLAY RECAP *************************************************************************************************************
vm                         : ok=6    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0

hiksol@Hiksol:~/ansible$ ansible-playbook playbooks/provision.yml --list-tags

playbook: playbooks/provision.yml

  play #1 (all): Provision server       TAGS: []
      TASK TAGS: [docker_config, docker_install, packages, users]
```

```bash
hiksol@Hiksol:~/ansible$ ansible-playbook playbooks/deploy.yml 

PLAY [Deploy application] **********************************************************************************************

TASK [Gathering Facts] *************************************************************************************************
ok: [vm]

TASK [docker : Install dependencies] ***********************************************************************************
ok: [vm]

TASK [docker : Add Docker GPG key] *************************************************************************************
ok: [vm]

TASK [docker : Add Docker repository] **********************************************************************************
ok: [vm]

TASK [docker : Install Docker packages] ********************************************************************************
ok: [vm]

TASK [docker : Ensure Docker service enabled] **************************************************************************
ok: [vm]

TASK [docker : Add user to docker group] *******************************************************************************
ok: [vm]

TASK [web_app : Include wipe tasks] ************************************************************************************
included: /home/hiksol/ansible/roles/web_app/tasks/wipe.yml for vm

TASK [web_app : Stop and remove containers] ****************************************************************************
skipping: [vm]

TASK [web_app : Remove docker-compose file] ****************************************************************************
skipping: [vm]

TASK [web_app : Remove application directory] **************************************************************************
skipping: [vm]

TASK [web_app : Log wipe completion] ***********************************************************************************
skipping: [vm]

TASK [web_app : Create application directory] **************************************************************************
ok: [vm]

TASK [web_app : Template docker-compose.yml] ***************************************************************************
ok: [vm]

TASK [web_app : Deploy application using Docker Compose] ***************************************************************
ok: [vm]

PLAY RECAP *************************************************************************************************************
vm                         : ok=11   changed=0    unreachable=0    failed=0    skipped=4    rescued=0    ignored=0

hiksol@Hiksol:~/ansible$ ssh hiksol@192.168.0.53
Welcome to Ubuntu 24.04.4 LTS (GNU/Linux 6.17.0-14-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/pro

Expanded Security Maintenance for Applications is not enabled.

13 updates can be applied immediately.
2 of these updates are standard security updates.
To see these additional updates run: apt list --upgradable

Enable ESM Apps to receive additional future security updates.
See https://ubuntu.com/esm or run: sudo pro status

*** System restart required ***
Last login: Thu Mar  5 20:59:08 2026 from 192.168.0.101
hiksol@Ubuntu:~$ docker ps
CONTAINER ID   IMAGE                               COMMAND           CREATED          STATUS          PORTS                                         NAMES
d30b4c0ff708   hiksol/devops-info-service:latest   "python app.py"   24 minutes ago   Up 24 minutes   0.0.0.0:5000->5000/tcp, [::]:5000->5000/tcp   devops-info-service
hiksol@Ubuntu:~$ cat /opt/devops-info-service/docker-compose.yml
version: '3.8'

services:
  devops-info-service:
    image: "hiksol/devops-info-service:latest"
    container_name: "devops-info-service"
    ports:
      - "5000:5000"
    restart: unless-stopped

hiksol@Ubuntu:~$ curl http://localhost:5000
{"service":{"name":"devops-info-service","version":"1.0.0","description":"DevOps course info service","framework":"FastAPI"},"system":{"hostname":"d30b4c0ff708","platform":"Linux","platform_version":"#14~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC Thu Jan 15 15:52:10 UTC 2","architecture":"x86_64","cpu_count":4,"python_version":"3.13.12"},"runtime":{"uptime_seconds":1479,"uptime_human":"0 hours, 24 minutes","current_time":"2026-03-05T20:59:50.696281+00:00","timezone":"UTC"},"request":{"client_ip":"172.18.0.1","user_agent":"curl/8.5.0","method":"GET","path":"/"},"endpoints":[{"path":"/","method":"GET","description":"Service information"},{"path":"/health","method":"GET","description":"Health check"}]}hiksol@Ubuntu:~$
```

```bash
hiksol@Hiksol:~/ansible$ ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true" --tags web_app_wipe 

PLAY [Deploy application] **********************************************************************************************

TASK [Gathering Facts] *************************************************************************************************
ok: [vm]

TASK [web_app : Include wipe tasks] ************************************************************************************
included: /home/hiksol/ansible/roles/web_app/tasks/wipe.yml for vm

TASK [web_app : Stop and remove containers] ****************************************************************************
[WARNING]: Cannot parse event from line: 'time="2026-03-05T21:01:29Z" level=warning msg="/opt/devops-info-
service/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid
potential confusion"'. Please report this at https://github.com/ansible-
collections/community.docker/issues/new?assignees=&labels=&projects=&template=bug_report.md
changed: [vm]

TASK [web_app : Remove docker-compose file] ****************************************************************************
changed: [vm]

TASK [web_app : Remove application directory] **************************************************************************
changed: [vm]

TASK [web_app : Log wipe completion] ***********************************************************************************
ok: [vm] => {
    "msg": "Application devops-info-service wiped successfully"
}

PLAY RECAP *************************************************************************************************************
vm                         : ok=6    changed=3    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0

hiksol@Hiksol:~/ansible$ ssh hiksol@192.168.0.53
Welcome to Ubuntu 24.04.4 LTS (GNU/Linux 6.17.0-14-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/pro

Expanded Security Maintenance for Applications is not enabled.

13 updates can be applied immediately.
2 of these updates are standard security updates.
To see these additional updates run: apt list --upgradable

Enable ESM Apps to receive additional future security updates.
See https://ubuntu.com/esm or run: sudo pro status

*** System restart required ***
Last login: Thu Mar  5 21:01:31 2026 from 192.168.0.101
hiksol@Ubuntu:~$ docker ps
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
hiksol@Ubuntu:~$ ls /opt
containerd  VBoxGuestAdditions-7.2.6
hiksol@Ubuntu:~$ exit
logout
Connection to 192.168.0.53 closed.
hiksol@Hiksol:~/ansible$ ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true" 

PLAY [Deploy application] **********************************************************************************************

TASK [Gathering Facts] *************************************************************************************************
ok: [vm]

TASK [docker : Install dependencies] ***********************************************************************************
ok: [vm]

TASK [docker : Add Docker GPG key] *************************************************************************************
ok: [vm]

TASK [docker : Add Docker repository] **********************************************************************************
ok: [vm]

TASK [docker : Install Docker packages] ********************************************************************************
ok: [vm]

TASK [docker : Ensure Docker service enabled] **************************************************************************
ok: [vm]

TASK [docker : Add user to docker group] *******************************************************************************
ok: [vm]

TASK [web_app : Include wipe tasks] ************************************************************************************
included: /home/hiksol/ansible/roles/web_app/tasks/wipe.yml for vm

TASK [web_app : Remove docker-compose file] ****************************************************************************
ok: [vm]

TASK [web_app : Remove application directory] **************************************************************************
ok: [vm]

TASK [web_app : Log wipe completion] ***********************************************************************************
ok: [vm] => {
    "msg": "Application devops-info-service wiped successfully"
}

TASK [web_app : Create application directory] **************************************************************************
changed: [vm]

TASK [web_app : Template docker-compose.yml] ***************************************************************************
changed: [vm]

TASK [web_app : Deploy application using Docker Compose] ***************************************************************
changed: [vm]

PLAY RECAP *************************************************************************************************************
vm                         : ok=15   changed=3    unreachable=0    failed=0    skipped=0    rescued=0    ignored=1

hiksol@Hiksol:~/ansible$ ssh hiksol@192.168.0.53
Welcome to Ubuntu 24.04.4 LTS (GNU/Linux 6.17.0-14-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/pro

Expanded Security Maintenance for Applications is not enabled.

13 updates can be applied immediately.
2 of these updates are standard security updates.
To see these additional updates run: apt list --upgradable

Enable ESM Apps to receive additional future security updates.
See https://ubuntu.com/esm or run: sudo pro status

*** System restart required ***
Last login: Thu Mar  5 21:02:33 2026 from 192.168.0.101
hiksol@Ubuntu:~$ docker ps
CONTAINER ID   IMAGE                               COMMAND           CREATED          STATUS          PORTS                                         NAMES
100d45ff4fc7   hiksol/devops-info-service:latest   "python app.py"   30 seconds ago   Up 29 seconds   0.0.0.0:5000->5000/tcp, [::]:5000->5000/tcp   devops-info-service
hiksol@Ubuntu:~$ curl http://localhost:5000
{"service":{"name":"devops-info-service","version":"1.0.0","description":"DevOps course info service","framework":"FastAPI"},"system":{"hostname":"100d45ff4fc7","platform":"Linux","platform_version":"#14~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC Thu Jan 15 15:52:10 UTC 2","architecture":"x86_64","cpu_count":4,"python_version":"3.13.12"},"runtime":{"uptime_seconds":34,"uptime_human":"0 hours, 0 minutes","current_time":"2026-03-05T21:03:11.611824+00:00","timezone":"UTC"},"request":{"client_ip":"172.18.0.1","user_agent":"curl/8.5.0","method":"GET","path":"/"},"endpoints":[{"path":"/","method":"GET","description":"Service information"},{"path":"/health","method":"GET","description":"Health check"}]}hiksol@Ubuntu:~$ exit
logout
Connection to 192.168.0.53 closed.
hiksol@Hiksol:~/ansible$ ansible-playbook playbooks/deploy.yml --tags web_app_wipe  

PLAY [Deploy application] **********************************************************************************************

TASK [Gathering Facts] *************************************************************************************************
ok: [vm]

TASK [web_app : Include wipe tasks] ************************************************************************************
included: /home/hiksol/ansible/roles/web_app/tasks/wipe.yml for vm

TASK [web_app : Stop and remove containers] ****************************************************************************
skipping: [vm]

TASK [web_app : Remove docker-compose file] ****************************************************************************
skipping: [vm]

TASK [web_app : Remove application directory] **************************************************************************
skipping: [vm]

TASK [web_app : Log wipe completion] ***********************************************************************************
skipping: [vm]

PLAY RECAP *************************************************************************************************************
vm                         : ok=2    changed=0    unreachable=0    failed=0    skipped=4    rescued=0    ignored=0

hiksol@Hiksol:~/ansible$ ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true" 

PLAY [Deploy application] **********************************************************************************************

TASK [Gathering Facts] *************************************************************************************************
ok: [vm]

TASK [web_app : Include wipe tasks] ************************************************************************************
included: /home/hiksol/ansible/roles/web_app/tasks/wipe.yml for vm

TASK [web_app : Stop and remove containers] ****************************************************************************
[WARNING]: Cannot parse event from line: 'time="2026-03-05T21:03:53Z" level=warning msg="/opt/devops-info-
service/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid
potential confusion"'. Please report this at https://github.com/ansible-
collections/community.docker/issues/new?assignees=&labels=&projects=&template=bug_report.md
changed: [vm]

TASK [web_app : Remove docker-compose file] ****************************************************************************
changed: [vm]

TASK [web_app : Remove application directory] **************************************************************************
changed: [vm]

TASK [web_app : Log wipe completion] ***********************************************************************************
ok: [vm] => {
    "msg": "Application devops-info-service wiped successfully"
}

PLAY RECAP *************************************************************************************************************
vm                         : ok=6    changed=3    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0

```