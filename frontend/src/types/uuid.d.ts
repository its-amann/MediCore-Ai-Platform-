declare module 'uuid' {
  export function v4(): string;
  export function v1(): string;
  export function v3(name: string, namespace: string): string;
  export function v5(name: string, namespace: string): string;
  export function parse(uuid: string): Uint8Array;
  export function stringify(buffer: Uint8Array, offset?: number): string;
  export function validate(uuid: string): boolean;
  export function version(uuid: string): number;
}