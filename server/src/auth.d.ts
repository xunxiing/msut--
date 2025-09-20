import type { Request, Response, NextFunction } from 'express';
export declare function register(req: Request, res: Response): Promise<Response<any, Record<string, any>>>;
export declare function login(req: Request, res: Response): Promise<Response<any, Record<string, any>>>;
export declare function logout(_req: Request, res: Response): void;
export declare function authGuard(req: Request, res: Response, next: NextFunction): Response<any, Record<string, any>> | undefined;
export declare function me(req: Request, res: Response): Response<any, Record<string, any>> | undefined;
//# sourceMappingURL=auth.d.ts.map