/**
 * PROMEOS - Service API (compatibility layer)
 *
 * This file re-exports everything from the modular api/ directory.
 * All existing imports like `import { getSites } from '../services/api'` continue working.
 *
 * For new code, prefer importing from domain-specific modules:
 *   import { getSites } from '../services/api/patrimoine'
 *   import { loginAuth } from '../services/api/auth'
 */
export { default } from './api/core';
export * from './api/index';
