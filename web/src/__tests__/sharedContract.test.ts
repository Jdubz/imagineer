import { describe, it, expect, expectTypeOf } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

import type { ZodTypeAny } from 'zod';

import type {
  AuthStatus,
  ImageMetadata as SharedImageMetadata,
  Job as SharedJob,
  JobsResponse as SharedJobsResponse,
} from '../types/shared';
import authStatusSchemaRaw from '../../../shared/schema/auth_status.json';
import imageMetadataSchemaRaw from '../../../shared/schema/image_metadata.json';
import jobSchemaRaw from '../../../shared/schema/job.json';
import jobsResponseSchemaRaw from '../../../shared/schema/jobs_response.json';
import { AuthStatusSchema, ImageMetadataSchema, JobSchema, JobsResponseSchema } from '../lib/schemas';

type PropertySchema = {
  type?: string | string[];
  enum?: unknown[];
  items?: PropertySchema;
  properties?: Record<string, PropertySchema>;
  required?: string[];
  additionalProperties?: boolean | PropertySchema;
  anyOf?: PropertySchema[];
  oneOf?: PropertySchema[];
  $ref?: string;
};

type JsonSchema = {
  name: string;
  description?: string;
  type: string;
  properties: Record<string, PropertySchema>;
  required?: string[];
  additionalProperties?: boolean | PropertySchema;
};

const authStatusSchema = authStatusSchemaRaw as JsonSchema;
const imageMetadataSchema = imageMetadataSchemaRaw as JsonSchema;
const jobSchema = jobSchemaRaw as JsonSchema;
const jobsResponseSchema = jobsResponseSchemaRaw as JsonSchema;

const sharedTypesPath = path.resolve(__dirname, '../types/shared.ts');

type ParsedInterface = Map<string, { optional: boolean; type: string }>;

type SchemaCase = {
  name: string;
  schema: JsonSchema;
  zod: ZodObjectLike;
  typeAssertion: () => void;
};

type ZodObjectLike = ZodTypeAny & { shape: Record<string, ZodTypeAny> };

const schemaRegistry = new Map<string, JsonSchema>([
  [authStatusSchema.name, authStatusSchema],
  [imageMetadataSchema.name, imageMetadataSchema],
  [jobSchema.name, jobSchema],
  [jobsResponseSchema.name, jobsResponseSchema],
]);

const schemaCases: readonly SchemaCase[] = [
  {
    name: 'AuthStatus',
    schema: authStatusSchema,
    zod: AuthStatusSchema,
    typeAssertion: () => {
      type SchemaKeys = keyof typeof authStatusSchemaRaw.properties;
      type RequiredKeys = typeof authStatusSchemaRaw.required extends readonly string[]
        ? (typeof authStatusSchemaRaw.required)[number]
        : never;
      type OptionalKeys = Exclude<SchemaKeys, RequiredKeys>;

      expectTypeOf<AuthStatus>().toMatchTypeOf<
        { [key in RequiredKeys]: unknown } & { [key in OptionalKeys]?: unknown }
      >();
    },
  },
  {
    name: 'ImageMetadata',
    schema: imageMetadataSchema,
    zod: ImageMetadataSchema,
    typeAssertion: () => {
      type SchemaKeys = keyof typeof imageMetadataSchemaRaw.properties;
      type RequiredKeys = typeof imageMetadataSchemaRaw.required extends readonly string[]
        ? (typeof imageMetadataSchemaRaw.required)[number]
        : never;
      type OptionalKeys = Exclude<SchemaKeys, RequiredKeys>;

      expectTypeOf<SharedImageMetadata>().toMatchTypeOf<
        { [key in RequiredKeys]: unknown } & { [key in OptionalKeys]?: unknown }
      >();
    },
  },
  {
    name: 'Job',
    schema: jobSchema,
    zod: JobSchema,
    typeAssertion: () => {
      type SchemaKeys = keyof typeof jobSchemaRaw.properties;
      type RequiredKeys = typeof jobSchemaRaw.required extends readonly string[]
        ? (typeof jobSchemaRaw.required)[number]
        : never;
      type OptionalKeys = Exclude<SchemaKeys, RequiredKeys>;

      expectTypeOf<SharedJob>().toMatchTypeOf<
        { [key in RequiredKeys]: unknown } & { [key in OptionalKeys]?: unknown }
      >();
    },
  },
  {
    name: 'JobsResponse',
    schema: jobsResponseSchema,
    zod: JobsResponseSchema,
    typeAssertion: () => {
      expectTypeOf<SharedJobsResponse>().toMatchTypeOf<{
        current: SharedJob | null;
        queue: SharedJob[];
        history: SharedJob[];
      }>();
    },
  },
];

const PRIMITIVE_SAMPLES: Record<'string' | 'number' | 'boolean', unknown> = {
  string: 'value',
  number: 42,
  boolean: true,
};

const FALLBACK_SAMPLES: Record<'object' | 'array', unknown> = {
  object: { sample: true },
  array: ['sample'],
};

function tsType(prop: PropertySchema): string {
  if (prop.enum) {
    return prop.enum.map((value) => JSON.stringify(value)).join(' | ');
  }

  if (prop.$ref) {
    const schemaType = prop.type;
    if (Array.isArray(schemaType) && schemaType.includes('null')) {
      return `${prop.$ref} | null`;
    }
    return prop.$ref;
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
    const itemType = tsType((prop.items ?? {}) as PropertySchema);
    return `Array<${itemType}>`;
  }

  if (schemaType === 'object') {
    const properties = prop.properties;
    if (properties && Object.keys(properties).length > 0) {
      const required = new Set(prop.required ?? []);
      const members = Object.entries(properties).map(([key, value]) => {
        const optional = required.has(key) ? '' : '?';
        return `${key}${optional}: ${tsType(value)}`;
      });
      return `{ ${members.join('; ')} }`;
    }

    const additional = prop.additionalProperties;
    if (additional === false) {
      return 'Record<string, never>';
    }
    if (additional && typeof additional === 'object') {
      return `Record<string, ${tsType(additional)}>`;
    }
    return 'Record<string, unknown>';
  }

  if (typeof schemaType === 'string') {
    if (schemaType === 'integer') {
      return 'number';
    }
    return schemaType;
  }

  if (prop.anyOf) {
    return prop.anyOf.map((option) => tsType(option)).join(' | ');
  }

  if (prop.oneOf) {
    return prop.oneOf.map((option) => tsType(option)).join(' | ');
  }

  return 'unknown';
}

function parseInterfaceBody(source: string, interfaceName: string): ParsedInterface {
  const pattern = new RegExp(`export interface ${interfaceName} \\{([\\s\\S]*?)\\r?\\n\\}`, 'm');
  const match = source.match(pattern);
  if (!match) {
    throw new Error(`Unable to locate ${interfaceName} interface in shared.ts`);
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
      const separatorIndex = sanitized.indexOf(':');
      if (separatorIndex === -1) {
        throw new Error(`Unable to parse interface line: ${line}`);
      }
      const rawName = sanitized.slice(0, separatorIndex);
      const rawType = sanitized.slice(separatorIndex + 1);
      const optional = rawName.endsWith('?');
      const name = optional ? rawName.slice(0, -1) : rawName;
      const type = rawType.trim();
      result.set(name, { optional, type });
    });

  return result;
}

function buildExpectedEntries(schema: JsonSchema): ParsedInterface {
  const requiredKeys = new Set(schema.required ?? []);
  const entries: ParsedInterface = new Map();
  Object.entries(schema.properties).forEach(([key, value]) => {
    entries.set(key, {
      optional: !requiredKeys.has(key),
      type: tsType(value),
    });
  });
  return entries;
}

describe('shared API contract', () => {
  it('keeps the TypeScript interfaces aligned with the JSON schemas', () => {
    const interfaceSource = fs.readFileSync(sharedTypesPath, 'utf-8');

    schemaCases.forEach(({ name, schema, typeAssertion }) => {
      const parsed = parseInterfaceBody(interfaceSource, name);
      const expected = buildExpectedEntries(schema);

      expect(Array.from(parsed.keys()).sort()).toEqual(Array.from(expected.keys()).sort());
      expected.forEach((expectedEntry, key) => {
        const actual = parsed.get(key);
        expect(actual).toBeDefined();
        expect(actual?.optional).toBe(expectedEntry.optional);
        expect(actual?.type).toBe(expectedEntry.type);
      });

      typeAssertion();
    });
  });

  it('keeps the Zod schemas aligned with the JSON schemas', () => {
    schemaCases.forEach(({ schema, zod }) => {
      const zodShape = zod.shape;
      const jsonKeys = Object.keys(schema.properties);

      expect(Object.keys(zodShape).sort()).toEqual(jsonKeys.sort());

      const requiredKeys = new Set(schema.required ?? []);

      jsonKeys.forEach((key) => {
        const propertySchema = schema.properties[key];
        const zodProperty = zodShape[key];

        expect(zodProperty).toBeDefined();

        assertOptionality(zodProperty, requiredKeys.has(key));
        assertTypeCompatibility(zodProperty, propertySchema);
      });
    });
  });
});

function assertOptionality(schema: ZodTypeAny, isRequired: boolean) {
  const result = schema.safeParse(undefined);

  if (isRequired) {
    expect(result.success).toBe(false);
  } else {
    expect(result.success).toBe(true);
  }
}

function assertTypeCompatibility(schema: ZodTypeAny, property: PropertySchema) {
  const allowedTypes = extractJsonTypes(property);

  allowedTypes
    .filter((type) => type !== 'null')
    .forEach((type) => {
      const sample = buildSampleForType(type, property);
      if (sample !== undefined) {
        const result = schema.safeParse(sample);
        expect(result.success).toBe(true);
      }
    });

  const nullResult = schema.safeParse(null);
  if (allowedTypes.includes('null')) {
    expect(nullResult.success).toBe(true);
  } else {
    expect(nullResult.success).toBe(false);
  }

  ['string', 'number', 'boolean', 'object', 'array'].forEach((type) => {
    if (allowedTypes.includes(type)) {
      return;
    }

    const sample =
      buildSampleForType(type, property) ??
      (type in PRIMITIVE_SAMPLES
        ? PRIMITIVE_SAMPLES[type as keyof typeof PRIMITIVE_SAMPLES]
        : FALLBACK_SAMPLES[type as keyof typeof FALLBACK_SAMPLES]);

    if (sample !== undefined) {
      const result = schema.safeParse(sample);
      expect(result.success).toBe(false);
    }
  });
}

function extractJsonTypes(property: PropertySchema): string[] {
  const schemaType = property.type;

  if (Array.isArray(schemaType)) {
    return schemaType.map(normalizeSchemaType).filter((type) => type !== 'unknown');
  }

  if (typeof schemaType === 'string') {
    return [normalizeSchemaType(schemaType)].filter((type) => type !== 'unknown');
  }

  if (property.properties) {
    return ['object'];
  }

  if (property.items) {
    return ['array'];
  }

  return [];
}

function normalizeSchemaType(value: string): string {
  if (value === 'integer') {
    return 'number';
  }
  return value;
}

function buildSampleForType(type: string, property: PropertySchema): unknown | undefined {
  if (property.enum && property.enum.length > 0) {
    const match = property.enum.find((value) => {
      if (type === 'string') {
        return typeof value === 'string';
      }
      if (type === 'number') {
        return typeof value === 'number';
      }
      if (type === 'boolean') {
        return typeof value === 'boolean';
      }
      if (type === 'object') {
        return typeof value === 'object' && value !== null && !Array.isArray(value);
      }
      if (type === 'array') {
        return Array.isArray(value);
      }
      return false;
    });
    if (match !== undefined) {
      return match;
    }
  }

  if (type === 'string' || type === 'number' || type === 'boolean') {
    return PRIMITIVE_SAMPLES[type as keyof typeof PRIMITIVE_SAMPLES];
  }

  if (type === 'object') {
    const referencedSchema = property.$ref ? schemaRegistry.get(property.$ref) : undefined;
    const schemaProperties = referencedSchema?.properties ?? property.properties ?? {};
    if (Object.keys(schemaProperties).length === 0) {
      return {};
    }

    const requiredSource =
      referencedSchema?.required ?? property.required ?? Object.keys(schemaProperties);
    const requiredKeys = new Set(requiredSource);
    const result: Record<string, unknown> = {};

    requiredKeys.forEach((key) => {
      const child =
        (referencedSchema?.properties?.[key] as PropertySchema | undefined) ??
        (schemaProperties[key] as PropertySchema | undefined);
      if (!child) {
        return;
      }
      const sample = getSampleForSchema(child);
      if (sample !== undefined) {
        result[key] = sample;
      }
    });

    return result;
  }

  if (type === 'array') {
    const { items } = property;
    if (!items) {
      return [];
    }

    const itemSample = getSampleForSchema(items);
    if (itemSample === undefined) {
      return [];
    }

    return [itemSample];
  }

  return undefined;
}

function getSampleForSchema(property: PropertySchema): unknown | undefined {
  if (property.$ref) {
    const referencedSchema = schemaRegistry.get(property.$ref);
    if (!referencedSchema) {
      return undefined;
    }
    return buildSampleFromSchema(referencedSchema);
  }

  const types = extractJsonTypes(property);
  for (const type of types) {
    if (type === 'null') {
      continue;
    }
    const sample = buildSampleForType(type, property);
    if (sample !== undefined) {
      return sample;
    }
  }
  return undefined;
}

function buildSampleFromSchema(schema: JsonSchema): Record<string, unknown> {
  const properties = schema.properties ?? {};
  if (Object.keys(properties).length === 0) {
    return {};
  }

  const requiredKeys = new Set(schema.required ?? Object.keys(properties));
  const sample: Record<string, unknown> = {};
  requiredKeys.forEach((key) => {
    const property = properties[key];
    if (!property) {
      return;
    }
    const value = getSampleForSchema(property);
    if (value !== undefined) {
      sample[key] = value;
    }
  });

  return sample;
}
