declare module 'slugify' {
  function slugify(str: string, options?: {
    lower?: boolean;
    strict?: boolean;
    replacement?: string;
    remove?: RegExp;
    trim?: boolean;
  }): string;
  export default slugify;
}

// 用户接口类型
export interface User {
  id: number;
  email: string;
  name: string;
  password_hash: string;
  created_at?: string;
}

// JWT 载荷接口类型
export interface JWTPayload {
  uid: number;
  email: string;
  name: string;
  iat?: number;
  exp?: number;
}

// 扩展 Express Request 接口
declare module 'express' {
  interface Request {
    user?: JWTPayload;
  }
}