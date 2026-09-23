---

## `ARCHITECTURE.md`
```markdown
# System Architecture & Design Patterns

## Overview
The `cyberark_auth_module` abstracts authentication mechanics across CyberArk product lines behind unified interfaces.

## Class & Execution Hierarchy

```text
               +-----------------------+
               | CyberArkAuthFactory   |
               +-----------+-----------+
                           |
            +--------------+--------------+
            |                             |
            v                             v
+-----------------------+     +-----------------------+
|   BaseAuthenticator   |     |       CCPClient       |
+-----------+-----------+     +-----------+-----------+
            |                             |
            v                             |
+-----------------------+                 |
|  OAuth2Authenticator  |                 |
+-----------+-----------+                 |
            |                             |
            +--------------+--------------+
                           |
                           v
              +--------------------------+
              |     ResilientSession     |
              +------------+-------------+
                           |
                           v
              +--------------------------+
              | CyberArk REST Endpoints  |
              +--------------------------+
