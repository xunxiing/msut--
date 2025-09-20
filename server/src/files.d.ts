import type { Request, Response } from 'express';
import multer from 'multer';
export declare const upload: multer.Multer;
export declare function createResource(req: Request, res: Response): Response<any, Record<string, any>> | undefined;
export declare function uploadToResource(req: Request, res: Response): Response<any, Record<string, any>> | undefined;
export declare function getResource(req: Request, res: Response): Response<any, Record<string, any>> | undefined;
export declare function listResources(req: Request, res: Response): void;
export declare function downloadFile(req: Request, res: Response): void | Response<any, Record<string, any>>;
//# sourceMappingURL=files.d.ts.map