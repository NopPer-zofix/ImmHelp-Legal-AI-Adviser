import { createHttpApi } from './http';
import { createMockApi } from './mock';
import { session } from '../lib/storage';

export { ApiError } from './http';

export const isMock = import.meta.env.VITE_MOCK === 'true';

export const api = isMock ? createMockApi() : createHttpApi(import.meta.env.VITE_API_URL || '/api', () => session.load()?.token);
