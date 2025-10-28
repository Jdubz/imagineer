import { describe, it, expect, expectTypeOf } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

import type { AuthStatus } from '../types/shared';
import authStatusSchemaRaw from '../../../shared/schema/auth_status.json';

const authStatusSchema: JsonSchema = authStatusSchemaRaw as JsonSchema;

type JsonSchema = typeof authStatusSchema;

const TS_PRIMITIVES: Record<string, string> = {
  string: 'string',
  boolean: 'boolean',
  number: 'number',
  integer: 'number',
  null: 'null',
};

type PropertySchema = JsonSchema['properties'][string];

function tsType(prop: PropertySchema): string {
  if ('enum' in prop && Array.isArray(prop.enum)) {
    return prop.enum.map((value) => JSON.stringify(value)).join(' | ');
  }

  const schemaType = prop.type;
  if (Array.isArray(schemaType)) {
    const includesNull = schemaType.includes('null');
    const subTypes = schemaType
      .filter((type) => type !== 'null')
      .map((type) => tsType({ ...prop, type }));
    const base = subTypes.filter(Boolean).join(' | ') || 'unknown';
    return includesNull ? `${base} | null` : base;
  }

  if (schemaType === 'array') {
    return `Array<${tsType(prop.items ?? ({} as PropertySchema))}>`;
  }

  if (schemaType === 'object') {
    return 'Record<string, unknown>';
  }

  if (typeof schemaType === 'string') {
    return TS_PRIMITIVES[schemaType] ?? 'unknown';
  }

  if ('anyOf' in prop && Array.isArray(prop.anyOf)) {
    return prop.anyOf.map((option) => tsType(option as PropertySchema)).join(' | ');
  }

  if ('oneOf' in prop && Array.isArray(prop.oneOf)) {
    return prop.oneOf.map((option) => tsType(option as PropertySchema)).join(' | ');
  }

  return 'unknown';
}

type ParsedInterface = Map<string, { optional: boolean; type: string }>;

function parseInterfaceBody(source: string): ParsedInterface {
  const match = source.match(/export interface AuthStatus \{([\s\S]*?)\n\}/);
  if (!match) {
    throw new Error('Unable to locate AuthStatus interface in shared.ts');
  }

  const [, body] = match;
  const result: ParsedInterface = new Map();

  body
    .trim()
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .forEach((line) => {
      const sanitized = line.replace(/;$/, '');
      const [rawName, rawType] = sanitized.split(':');
      const optional = rawName.endsWith('?');
      const name = optional ? rawName.slice(0, -1) : rawName;
      const type = rawType.trim();
      result.set(name, { optional, type });
    });

  return result;
}

describe('shared API contract', () => {
  it('keeps the AuthStatus TypeScript interface aligned with the JSON schema', () => {
    const sharedTsPath = path.resolve(__dirname, '../types/shared.ts');
    const interfaceSource = fs.readFileSync(sharedTsPath, 'utf-8');
    const parsed = parseInterfaceBody(interfaceSource);

    const requiredKeys = new Set(authStatusSchema.required ?? []);
    const expectedEntries: ParsedInterface = new Map();
    Object.entries(authStatusSchema.properties).forEach(([key, value]) => {
      expectedEntries.set(key, {
        optional: !requiredKeys.has(key),
        type: tsType(value),
      });
    });

    expect(Array.from(parsed.keys()).sort()).toEqual(Array.from(expectedEntries.keys()).sort());
    expectedEntries.forEach((expected, key) => {
      const actual = parsed.get(key);
      expect(actual).toBeDefined();
      expect(actual?.optional).toBe(expected.optional);
      expect(actual?.type).toBe(expected.type);
    });

    // Type-level assertion: if schema adds new fields, this will fail without interface update.
    type SchemaKeys = keyof typeof authStatusSchema.properties;
    type RequiredKeys = typeof authStatusSchema.required extends readonly string[]
      ? (typeof authStatusSchema.required)[number]
      : never;
    type OptionalKeys = Exclude<SchemaKeys, RequiredKeys>;

    expectTypeOf<AuthStatus>().toMatchTypeOf<
      { [key in RequiredKeys]: unknown } & { [key in OptionalKeys]?: unknown }
    >();
  });
});
