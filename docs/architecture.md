# Architecture

## High-Level System Architecture

Heracles follows a modular architecture with a clear separation of concerns between the frontend, API, core logic, and plugins.

![System Architecture Diagram](assets/architecture/system_architecture.png)

### Components

*   **Frontend**: Heracles UI (React)
    *   Modern, responsive web interface built with React, Vite, and Shadcn/UI.
    *   Communicates with the backend via REST API (HTTPS).
*   **Backend**: Heracles API (FastAPI)
    *   Python-based REST API handling request validation, authentication, and business logic.
    *   Integrates with Heracles Core for heavy lifting.
    *   Uses Redis for caching and recurring tasks (Celery).
    *   Persists application state (audit logs, settings) in PostgreSQL.
*   **Core**: Heracles Core (Rust)
    *   High-performance library handling LDAP protocol operations, cryptography, and schema validation.
    *   Exposed to Python via PyO3 bindings.
    *   Communicates directly with the Directory Store.
*   **Plugins**: Extension System
    *   Python modules that hook into the API lifecycle to extend functionality (e.g., DNS, DHCP, Sudo).
*   **Data Layer**:
    *   **OpenLDAP**: The authoritative source for identity and infrastructure data.
    *   **PostgreSQL**: Relational database for application-specific data.
    *   **Redis**: In-memory data store for caching and queues.

## Demo Environment

The demo environment (`make demo`) provisions a complete, isolated network of virtual machines using Vagrant to simulate a real-world deployment.

![Demo Environment Diagram](assets/architecture/demo_environment.png)

### Topology

All Virtual Machines reside on a private host-only network (`192.168.56.0/24`) and interact with the main Heracles infrastructure running on the host machine.

*   **ns1** (`192.168.56.11`):
    *   **Role**: DNS Server (BIND9).
    *   **Integration**: Synchronizes DNS zones directly from Heracles LDAP.
*   **dhcp1** (`192.168.56.12`):
    *   **Role**: DHCP Server (ISC DHCP).
    *   **Integration**: Fetches configuration and subnet definitions from Heracles LDAP.
*   **mail1** (`192.168.56.13`):
    *   **Role**: Mail Server (Postfix + Dovecot).
    *   **Integration**: Authenticates users directly against Heracles LDAP.
*   **server1** (`192.168.56.20`) & **workstation1** (`192.168.56.21`):
    *   **Role**: Client Machines.
    *   **Integration**: Joined to the domain using SSSD, allowing users to log in with their Heracles credentials.
