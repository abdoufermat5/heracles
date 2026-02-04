# Changelog - heracles-ui

All notable changes to the Heracles UI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- API compatibility check on startup with non-blocking warning

## [0.8.0-beta] - 2026-02-04

### Added
- **Phase 3 Complete**: All plugin UIs operational
- Department selector in sidebar with persistent state
- Department breadcrumb navigation
- Context-aware data filtering (users, groups, plugins)
- Plugin pages:
  - POSIX: Account activation, POSIX groups, mixed groups
  - Sudo: Rules list, detail, create/edit forms
  - SSH: User tab with key management
  - Systems: List, detail, create with 7 system types
  - DNS: Zones list, zone detail with records table
  - DHCP: Services, subnets, hosts, pools tree view
- Host selector component for POSIX system trust
- Dashboard with contextual statistics

### Changed
- Version properly set (was 0.0.0)
- All plugin routes integrated

## [0.5.0-beta] - 2026-01-20

### Added
- **Phase 2 Complete**: Core identity UI
- User management pages (list, detail, create, edit)
- Group management pages (list, detail, create, edit)
- User lock/unlock functionality
- Password change dialog
- Group member management
- POSIX tab on user detail page

## [0.1.0-alpha] - 2026-01-15

### Added
- **Phase 1 Complete**: Foundation UI
- React 19 + Vite 7 setup
- TailwindCSS v4 + shadcn/ui component library (19 components)
- Main layout with sidebar navigation
- Login page with validation
- Authentication store (Zustand)
- React Query v5 integration
- Protected route wrapper
- Dashboard with quick actions
- API client with token refresh
- Common components: PageHeader, Loading, ErrorDisplay, EmptyState, ConfirmDialog
- Dark/light theme support

### Tech Stack
- React 19.2
- TypeScript 5
- Vite 7
- TanStack Query 5
- Zustand 5
- React Router 7
- React Hook Form 7
- Zod 3.24
- Lucide React icons
- Recharts for dashboard charts

[Unreleased]: https://github.com/abdoufermat5/heracles/compare/heracles-ui/v0.8.0-beta...HEAD
[0.8.0-beta]: https://github.com/abdoufermat5/heracles/compare/heracles-ui/v0.5.0-beta...heracles-ui/v0.8.0-beta
[0.5.0-beta]: https://github.com/abdoufermat5/heracles/compare/heracles-ui/v0.1.0-alpha...heracles-ui/v0.5.0-beta
[0.1.0-alpha]: https://github.com/abdoufermat5/heracles/releases/tag/heracles-ui/v0.1.0-alpha
