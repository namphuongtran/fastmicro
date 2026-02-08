# 1.0.0 (2026-02-08)


### Bug Fixes

* add flake8-builtins (A) rule to prevent builtin shadowing ([f29e6e4](https://github.com/namphuongtran/fastmicro/commit/f29e6e4bf7817c71e762394cfae92dbd9490766d))
* add ServiceClient config property, async context manager, and adjust coverage threshold ([f0868c4](https://github.com/namphuongtran/fastmicro/commit/f0868c47f3d14190f5edbf38d2a67630aa21b99f))
* **audit-service:** rename 'list' method to 'list_events' to avoid shadowing builtin ([8b2f6b5](https://github.com/namphuongtran/fastmicro/commit/8b2f6b54f62bb3eec1926620aeefa22faa2368fb))
* **ci:** complete Poetry to uv migration with proper ruff fixes ([5405600](https://github.com/namphuongtran/fastmicro/commit/5405600ac8596145f711e65367728b8068703362)), closes [#6](https://github.com/namphuongtran/fastmicro/issues/6)
* **ci:** configure semantic-release for Python monorepo ([767144d](https://github.com/namphuongtran/fastmicro/commit/767144d6090c19a8b2297d6af15ef0c08f5adaea))
* **ci:** remove duplicate GitHub Actions services causing port conflict ([d6471a0](https://github.com/namphuongtran/fastmicro/commit/d6471a09695c8d4ba767fb1cac9ce1eb489dbed2))
* **ci:** resolve integration-tests and frontend build failures ([fe0a4b9](https://github.com/namphuongtran/fastmicro/commit/fe0a4b99c9e6cfbc63cc2ef495934356dfec90ea))
* **ci:** resolve linting errors in identity-admin-service ([245711e](https://github.com/namphuongtran/fastmicro/commit/245711e8b85cb1cf2a7262121db3d33baa183a1b))
* **ci:** update integration tests workflow and add type-check script ([55df240](https://github.com/namphuongtran/fastmicro/commit/55df240a56acbd9748e0e9cafa32532463ae7632))
* **ci:** use --all-groups flag to install dev dependencies including shared library ([b852289](https://github.com/namphuongtran/fastmicro/commit/b85228960b639ef546ebd432195a9809ba704ea5))
* **docker:** simplify Dockerfiles to fix shared library path issue ([0fae543](https://github.com/namphuongtran/fastmicro/commit/0fae543425881b57acae09abd91338fd65881b18))
* **docker:** update bitnami/redis to 'latest' tag ([3e549e7](https://github.com/namphuongtran/fastmicro/commit/3e549e71f781f349685ea2f5a820deb104429639))
* **identity-admin:** fix Dockerfile healthcheck and port configuration ([56d9c88](https://github.com/namphuongtran/fastmicro/commit/56d9c889a3f22dad0fc907be47c20878d64fb9ef))
* **metastore:** add dedicated PostgreSQL following DDD principles ([cf8a7b1](https://github.com/namphuongtran/fastmicro/commit/cf8a7b12b9d42e60bcb3ad3966591eee129619fb))
* rename 'name' to 'flag_name'/'config_name' in logger extra dict ([883897f](https://github.com/namphuongtran/fastmicro/commit/883897f2ae7c3926f885210a9f9c8a97498977a6))
* resolve ruff formatting issues in shared library ([bd95b77](https://github.com/namphuongtran/fastmicro/commit/bd95b77d9c51f9c86cf05ef2fb915d896c523763))
* resolve ruff import sorting issues in shared library ([47f7473](https://github.com/namphuongtran/fastmicro/commit/47f7473e8709e27e7e9f7880286fbcf68661803c))
* resolve ruff lint and format errors across all services ([c64ea54](https://github.com/namphuongtran/fastmicro/commit/c64ea54741314d321014e3b172b5bc91dd0bd0b2))
* resolve service healthcheck and configuration issues ([f356934](https://github.com/namphuongtran/fastmicro/commit/f356934370786a9fa7828217e4edc803d978bee3))
* **shared:** add shared[all] to dev dependencies for testing ([0bd4b00](https://github.com/namphuongtran/fastmicro/commit/0bd4b0056f9cc6c51181ee3f9d403e37718605ea))
* **webshell:** fix Next.js 15 build errors ([bf7ac76](https://github.com/namphuongtran/fastmicro/commit/bf7ac7631896cd96b11e3da87751aefb39dcbe84))
* **webshell:** resolve ESLint folder naming and unused import warnings ([89649af](https://github.com/namphuongtran/fastmicro/commit/89649af9b084275aa2525bfdc5ccd7201bddccaf))


### Code Refactoring

* **infra:** move monitoring into infrastructure directory ([c47f01b](https://github.com/namphuongtran/fastmicro/commit/c47f01b0ae955856503fb03ca55d6aab1e8e899a))


### Features

* add identity-service auth, UI pages, messaging module, and service context ([b9bc0e6](https://github.com/namphuongtran/fastmicro/commit/b9bc0e628321f940b4c0e768f8e9df19eaf56e8c))
* **ci:** add identity-admin-service to all workflows ([28b0f06](https://github.com/namphuongtran/fastmicro/commit/28b0f061461aef7fdecd694edbc3439ffa6ea87c))
* **ci:** add identity-service to Python CI pipeline ([19c97d9](https://github.com/namphuongtran/fastmicro/commit/19c97d9c56e8c2bdaab2c65029661604a4983783))
* complete shared library restructure and service modernization ([c4e1cb1](https://github.com/namphuongtran/fastmicro/commit/c4e1cb1017e7ccede06ebfcde355ea63d334319b))
* identity-admin-service and IdP security enhancements ([5945986](https://github.com/namphuongtran/fastmicro/commit/59459866566afd4dd5ef9b010be9c0fd9eaae25c))
* **identity-service:** Add Python Identity Provider with OAuth2/OIDC ([760e857](https://github.com/namphuongtran/fastmicro/commit/760e857b1bc57e9a0baa30b246c4ba1893ce66e6))
* modernize password hashing and Dockerfiles ([6333d70](https://github.com/namphuongtran/fastmicro/commit/6333d706abe67b93f149c60fc2150a3913394eb9))
* **shared:** add FastAPI request logging middleware ([e3f5f82](https://github.com/namphuongtran/fastmicro/commit/e3f5f8276020b08ca7edaf717fc83929819bd3f8))
* **shared:** Add Phase 1 Foundation - exceptions, constants, utils ([c5dc522](https://github.com/namphuongtran/fastmicro/commit/c5dc5223f6ae1b47f63cedfad6a60b7e1a8b666b))
* **shared:** add standardized structlog configuration ([4709061](https://github.com/namphuongtran/fastmicro/commit/4709061268aab65700e7082109b444fb1f007f0d))


### BREAKING CHANGES

* **infra:** If using old volume paths, update to:
  ./infrastructure/monitoring/prometheus/
  ./infrastructure/monitoring/grafana/
