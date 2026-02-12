# Identity Management

Manage the core entities of your directory: Users, Groups, and Departments (Organizational Units).

## Users

### User List
View and search all users in the directory. You can filter by name, email, or other attributes.

![User List](assets/users/list.png)

### create User
To add a new user, click the "Create User" button. Fill in the required basic information such as Username, First Name, and Last Name.

![Create User Modal](assets/users/create_modal.png)

### User Details
Click on a user to view their full profile and manage specific settings.

- **General**: Basic profile information.
  ![User Details General](assets/users/details_general.png)
- **Unix**: Manage POSIX attributes like UID, GID, and Login Shell.
  ![User Details Unix](assets/users/details_unix.png)
- **SSH Keys**: Manage public SSH keys for server access.
  ![User Details SSH](assets/users/details_ssh.png)
- **Mail**: Configure email attributes.
  ![User Details Mail](assets/users/details_mail.png)
- **Groups**: Manage group memberships.
  ![User Details Groups](assets/users/details_groups.png)
- **Permissions**: View assigned ACLs and effective permissions.
  ![User Details Permissions](assets/users/details_permissions.png)

## Groups

### Group List
View all groups in the directory.

![Group List](assets/groups/list.png)

### Create Group
Create new groups for organizing users and managing permissions.

![Create Group Modal](assets/groups/create_modal.png)

### Group Details
View group members and attributes.

![Group Details](assets/groups/details.png)

## Departments

### Department List
Manage the organizational hierarchy with Departments (OUs).

![Departments List](assets/departments/list.png)

### Create Department
Add new departments to structure your directory.

![Create Department Modal](assets/departments/create_modal.png)
