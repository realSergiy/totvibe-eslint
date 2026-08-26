import * as z from 'zod';

export const NodeReleaseIndexSchema = z.array(z.object({ version: z.string() }));
const RuntimeSchema = z.object({ version: z.string() });
const DevEnginesSchema = z.object({ runtime: RuntimeSchema });
export const ToolchainManifestSchema = z.object({
  devEngines: DevEnginesSchema,
});
